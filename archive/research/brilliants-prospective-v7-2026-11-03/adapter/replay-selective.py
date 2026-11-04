"""One bounded replay of the unchanged selective model on the frozen new 200.

Reuses recorded core evidence; no fitting, tuning, engine searches or publication.
"""
import hashlib
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT.parent / 'brilliants-improvement-2026-11-03'
EXTRACTOR = OLD / 'astra/v5/fresh-extractor'
OUT = ROOT / 'selective-replay'
OUT.mkdir(exist_ok=True)
load = lambda p: json.loads(Path(p).read_text())
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()

freeze = load(EXTRACTOR / 'FREEZE.json')
for p, expected in freeze['sha256'].items():
    if sha(p) != expected:
        raise ValueError('Frozen predictor dependency changed: ' + p)
sys.path.insert(0, str(EXTRACTOR))
from extractor import extract_batch, score_fixed_forest

paths = {k: ROOT / p for k, p in {
    'core': 'sf18-core.json',
    'database': 'workingassessment.db',
    'primary_queue': 'root-frozen-final200queue.json',
    'primary_results': 'primary-results.json',
    'data_freeze': 'FINAL-DATA-FREEZE.json',
}.items()}
bank = load(paths['core'])
assert bank['status'] == 'complete' and len(bank['targets']) == 200
assert bank['nodes_per_position'] == 300000 and bank['threads'] == 1 and bank['hash_mb'] == 64
assert bank['source_sha256'] == sha(paths['database'])
assert bank['queue_sha256'] == sha(paths['primary_queue'])
model_path = OLD / 'learning-v5/forest-diagnostic/forest-full.json'
assert sha(model_path) == '44704ac06378d3f671a4eed959e21959f759c0437c71af1f9119d1081293c0b7'
output = OUT / 'predictions.json'
if output.exists():
    raise ValueError('Preserve existing replay; no automatic replacement')

receipt = {
    'started_at_utc': datetime.now(timezone.utc).isoformat(),
    'scope': 'Unchanged selective model on the exact new 200 using existing core snapshots. No tuning, training, searches, PR or report changes.',
    'input_sha256': {k: sha(p) for k, p in paths.items()},
    'model_sha256': sha(model_path),
    'extractor_freeze_sha256': sha(EXTRACTOR / 'FREEZE.json'),
    'adapter_sha256': sha(__file__),
    'predictor_dependencies_verified': len(freeze['sha256']),
}
(OUT / 'RUN-FREEZE.json').write_text(json.dumps(receipt, indent=2) + '\n')
db = sqlite3.connect('file:' + str(paths['database']) + '?mode=ro', uri=True)
requests = []
for target in bank['targets']:
    pgn, pgn_sha = db.execute('select pgn,pgn_sha256 from games where game_id=?', (target['game_id'],)).fetchone()
    assert pgn_sha == target['pgn_sha256'] == hashlib.sha256(pgn.encode()).hexdigest()
    snapshots = [bank['snapshots'][key] for key in target['snapshot_ids']]
    requests.append({'pgn': pgn, 'ply': target['ply'], 'snapshots': snapshots})
db.close()
cases = extract_batch(requests)
assert len(cases) == 200
model = load(model_path)
rows = [{'key': str(t['game_id']) + ':' + str(t['ply']), 'features': case,
         'selective': score_fixed_forest(case, model)}
        for t, case in zip(bank['targets'], cases)]
assert len({r['key'] for r in rows}) == 200
for k, p in paths.items():
    assert sha(p) == receipt['input_sha256'][k]
for p, expected in freeze['sha256'].items():
    assert sha(p) == expected
output.write_text(json.dumps({'run_freeze_sha256': sha(OUT / 'RUN-FREEZE.json'), 'rows': rows}, indent=2, allow_nan=False) + '\n')
print(json.dumps({'status': 'complete', 'moves': len(rows), 'predictions_sha256': sha(output), 'metrics_computed': False}), flush=True)
