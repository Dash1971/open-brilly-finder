"""Bounded overnight importer: one writer, existing scripts, no engine or fitting."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, os, re, subprocess, sys, time

ROOT = Path(__file__).resolve().parent
END = datetime.fromisoformat('2026-11-03T23:57:39+00:00')
STATE = ROOT / 'IMPORT-WORKER-STATE.json'
LOG = ROOT / 'import-worker.log'
STOP = ROOT / 'STOP_IMPORT'
started = datetime.now(timezone.utc).isoformat()
state = dict(pid=os.getpid(), started_at_utc=started, stop_at_utc=END.isoformat(),
             interval_seconds=30, status='starting', sole_sqlite_writer=True,
             worker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
             scope='Completed saved evidence only; no browser, engine, fitting, publication or app changes.')
if STATE.exists():
    old = json.loads(STATE.read_text())
    if old.get('status') in {'starting', 'waiting', 'importing', 'freezing'}:
        try:
            os.kill(int(old['pid']), 0)
        except ProcessLookupError:
            pass
        else:
            raise SystemExit('An importer worker is already active; do not create a second writer.')

def save(**updates):
    state.update(updates, updated_at_utc=datetime.now(timezone.utc).isoformat())
    temp = STATE.with_suffix('.tmp')
    temp.write_text(json.dumps(state, indent=2) + '\n')
    temp.replace(STATE)

def completed_signature():
    files = list(ROOT.glob('collector-*/*-complete.json'))
    for path in ROOT.glob('collector-b/*.json'):
        if not re.fullmatch(r'\d+\.json', path.name):
            continue
        try:
            value = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        if value.get('completed_at') and value.get('all_export_brilliants_UI_verified') and value.get('all_planned_UI_checks_complete'):
            files.append(path)
    return tuple(sorted((str(p.relative_to(ROOT)), p.stat().st_size, p.stat().st_mtime_ns) for p in files))

def run(script, *args):
    command = [sys.executable, str(ROOT / script), *args]
    result = subprocess.run(command, cwd=ROOT.parents[1], text=True, capture_output=True)
    with LOG.open('a') as log:
        log.write('\n' + datetime.now(timezone.utc).isoformat() + ' ' + json.dumps(command) + '\n')
        log.write(result.stdout + result.stderr)
    return result

save(status='waiting')
previous = None
while datetime.now(timezone.utc) < END and not STOP.exists():
    signature = completed_signature()
    if signature != previous:
        save(status='importing', completed_markers=len(signature))
        result = run('import-verified.py')
        if result.returncode == 0:
            previous = signature
            counts = json.loads((ROOT / 'COUNTS.json').read_text())
            save(last_successful_import_utc=counts['updated_at'], counts=counts)
            while not STOP.exists():
                numbers = [int(p.stem.rsplit('-', 1)[1]) for p in ROOT.glob('ENGINE-BATCH-[0-9][0-9].json')]
                number = f'{max(numbers, default=0) + 1:02d}'
                save(status='freezing', requested_next_batch=number)
                frozen = run('prepare-engine-batch.py', '--batch', number, '--min-games', '20')
                if frozen.returncode != 0:
                    save(last_error='Batch preparation failed; see import-worker.log. No engine launched.')
                    break
                receipt = json.loads(frozen.stdout)
                if receipt.get('status') != 'frozen':
                    save(waiting_for_training_games=receipt)
                    break
                save(last_frozen_batch=receipt)
        else:
            save(last_error='Importer failed; partial or invalid evidence is preserved. See import-worker.log.')
        save(status='waiting')
    time.sleep(min(30, max(0, (END - datetime.now(timezone.utc)).total_seconds())))
save(status='stopped', reason='STOP_IMPORT flag' if STOP.exists() else 'Overnight deadline plus 120-second verification grace')
