#!/usr/bin/env python3
"""Bind root-frozen 200 identities to four existing core collectors; no searches."""
import argparse, hashlib, json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p, data):
    p.write_text(json.dumps(data, indent=2) + '\n')

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--primary', type=Path, required=True)
    p.add_argument('--db', type=Path, required=True)
    p.add_argument('--root-core-freeze', type=Path, required=True,
                   help='Explicit root-provided completed identity-freeze artifact; run only after GO')
    a = p.parse_args()
    if (ROOT/'PLAN.json').exists():
        raise ValueError('Already prepared: no automatic re-freeze/retry')
    rows = json.loads(a.primary.read_text())
    keys = {(str(t['game_id']), int(t['ply'])) for t in rows}
    if len(rows) != 200 or len(keys) != 200:
        raise ValueError('Require exactly200 root-validated unique primary keys')
    expected = {f"{g}:{i}" for g, ply in keys for i in range(max(0,ply-2),ply+1)}
    if len(expected) > 600:
        raise ValueError('Core exceeds600 unique position limit')
    freeze_hash = sha(a.root_core_freeze)
    (ROOT/'primary-moves.json').write_bytes(a.primary.read_bytes())
    partitions = []
    for worker in range(4):
        part = sorted([t for t in rows if int(hashlib.sha256(str(t['game_id']).encode()).hexdigest(),16)%4 == worker],
                      key=lambda t:(str(t['game_id']),int(t['ply'])))
        path = ROOT/f'partition-{worker}.json'; save(path, part)
        partitions.append({'worker':worker, 'file':path.name, 'sha256':sha(path),
                           'cases':len(part), 'games':len({t['game_id'] for t in part}),
                           'snapshots':len({(t['game_id'],i) for t in part for i in range(max(0,t['ply']-2),t['ply']+1)})})
    plan = {'prepared_at':datetime.now(timezone.utc).isoformat(),
            'scope':'Frozen fresh-test core only. No S lookback warmup, no fitting or partial metrics.',
            'metadata':{'quantity_completion_authorized':True,'tuning_authorized':False,
                        'root_core_freeze_sha256':freeze_hash},
            'root_core_freeze_path':str(a.root_core_freeze.resolve()),
            'primary_source':str(a.primary.resolve()),'primary_sha256':sha(a.primary),
            'db_path':str(a.db.resolve()),'db_sha256':sha(a.db),
            'engine':{'path':'/opt/homebrew/bin/stockfish','sha256':sha('/opt/homebrew/bin/stockfish'),
                      'nodes_per_position':300000,'threads_per_worker':1,'hash_mb_per_worker':64,
                      'multipv':'min(2, legal roots)','workers':4},
            'cases':200,'snapshots':len(expected),'partitions':partitions,
            'wall_safeguard_seconds_per_worker':600,'automatic_retries':False,
            'cache_policy':'Fresh process per partition; clear hash/new UCI game per whole game; chronological full-PGN positions.',
            'script_hashes':{f:sha(ROOT/f) for f in ('analysis.py','prepare.py','merge.py','replay-forest.py')}}
    save(ROOT/'PLAN.json',plan)
    print(json.dumps({'status':'prepared_not_started','cases':200,'snapshots':len(expected),'partitions':partitions}))

if __name__ == '__main__':
    main()
