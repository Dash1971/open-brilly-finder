"""Bounded copy of approved data and frozen existing results; no recomputation."""
import csv
import hashlib
import json
import pathlib
import re
import shutil
import sqlite3
from datetime import datetime, timezone

R = pathlib.Path(__file__).resolve().parent
W = R.parent.parent
P = W / 'mute-chess-research/studies/brilliant-moves'
PRIVATE = R / 'publication-data-v5'
OLD = R.parent / 'brilliants-final-2026-11-03'
NEW = R / 'future-validation-v5'
P.mkdir(exist_ok=True)
(P / 'data/protocol').mkdir(parents=True, exist_ok=True)
load = lambda p: json.loads(p.read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
mapping = []
normalizations = []

def relative(p):
    return str(p.resolve().relative_to(W))

def normalize(v):
    if isinstance(v, dict):
        return {normalize(k): normalize(x) for k, x in v.items()}
    if isinstance(v, list):
        return [normalize(x) for x in v]
    if isinstance(v, str):
        cleaned = v.replace(str(W) + '/', '')
        if cleaned.startswith('/'):
            cleaned = 'local-runtime-path-omitted/' + pathlib.Path(cleaned).name
        if cleaned != v:
            # Mapping records use hashes, never leak the omitted absolute path.
            normalizations.append({'original_value_sha256': hashlib.sha256(v.encode()).hexdigest(), 'replacement': cleaned})
        return cleaned
    return v

def put(source, destination, json_normalize=False):
    target = P / destination
    target.parent.mkdir(parents=True, exist_ok=True)
    if json_normalize:
        target.write_text(json.dumps(normalize(load(source)), indent=2) + '\n')
    else:
        shutil.copyfile(source, target)
    mapping.append({'source_artifact': relative(source), 'source_sha256': sha(source), 'public_artifact': destination,
        'public_sha256': sha(target), 'normalization': 'local paths only' if json_normalize else 'byte-identical'})

for name in ['corpus.sqlite3', 'selected-games.pgn', 'observations-export.json']:
    put(PRIVATE / name, name)
for name in ['pgn-provenance.json', 'archival-game-metadata.json', 'source-hash-audit.json']:
    put(PRIVATE / name, 'data/' + name)
for path in sorted((PRIVATE / 'protocol').iterdir()):
    put(path, 'data/protocol/' + path.name)

evidence = [
    (OLD / 'analysis-baseline.json', 'data/development-baseline.json'),
    (OLD / 'analysis-panel.json', 'data/development-panel.json'),
    (OLD / 'analysis-stronger.json', 'data/development-stronger.json'),
    (NEW / 'engine-core/analysis-core.json', 'data/test-baseline.json'),
    (NEW / 'engine-core/fresh-results.json', 'data/test-results.json'),
    (NEW / 'engine-s/results.json', 'data/test-sequence-results.json'),
    (R / 'astra/v5/sequence-reference/results.json', 'data/development-sequence-results.json'),
    (R / 'learning-v5/forest-diagnostic/predictions.json', 'data/development-forest-predictions.json'),
    (NEW / 'engine-core/forest-predictions.json', 'data/test-forest-predictions.json'),
    (R / 'uniform-stronger-v5/SUMMARY.json', 'data/development-uniform-summary.json'),
    (R / 'uniform-stronger-v5/baseline-results.json', 'data/development-baseline-results.json'),
    (R / 'learning-v5/forest-diagnostic/RESULTS.json', 'data/development-forest-summary.json'),
    (NEW / 'CORE-FREEZE.json', 'data/protocol/CORE-FREEZE.json'),
    (NEW / 'engine-core/FINAL-AUDIT.json', 'data/protocol/FINAL-AUDIT.json'),
]
for source, destination in evidence:
    put(source, destination, True)

forest = {r['key']: r for r in load(R / 'learning-v5/forest-diagnostic/predictions.json')}
sequence = {r['key']: r for r in load(R / 'astra/v5/sequence-reference/results.json')['rows']}
ec = {r['key']: r for r in load(R / 'uniform-stronger-v5/baseline-results.json')['rows']}
fresh = {r['key']: r for r in load(NEW / 'engine-core/fresh-results.json')['rows']}
fresh_forest = {r['key']: r for r in load(NEW / 'engine-core/forest-predictions.json')['rows']}
assert len(forest) == len(sequence) == 848 and len(fresh) == 200
moves = load(PRIVATE / 'moves.json')
for row in moves:
    key = f'{row["game_id"]}:{row["ply"]}'
    if row['role'] == 'development':
        f = forest[key]
        assert f['truth'] == row['is_brilliant'] and sequence[key]['truth'] == row['is_brilliant']
        row.update(frozen_forest_award=f['full_fit_award_NOT_validation'],
            frozen_forest_prediction_role='training_resubstitution_NOT_validation',
            frozen_forest_current_p=f['full_current_raw_p'], frozen_forest_previous_p=f['full_previous_raw_p'],
            development_oof_award=f['cv_award'], development_oof_fold=f['fold'],
            development_oof_current_p=f['cv_current_raw_p'], development_oof_previous_p=f['cv_previous_raw_p'],
            S_award=sequence[key]['awarded'], ec_direct_award=ec[key]['ec_direct_symbol'] == '!!')
    else:
        f = fresh[key]
        assert f['truth'] == row['is_brilliant']
        scores = fresh_forest[key]['forest']['window_scores']
        row.update(frozen_forest_award=f['awards']['forest'], frozen_forest_prediction_role='fresh_prospective_test',
            frozen_forest_current_p=scores['current'], frozen_forest_previous_p=scores['previous'],
            development_oof_award=None, development_oof_fold=None, development_oof_current_p=None,
            development_oof_previous_p=None, S_award=f['awards']['S'], ec_direct_award=f['awards']['ec_direct'])
(P / 'moves.json').write_text(json.dumps(moves, indent=2) + '\n')
with (P / 'moves.csv').open('w', newline='') as stream:
    writer = csv.DictWriter(stream, fieldnames=list(moves[0]))
    writer.writeheader()
    for row in moves:
        writer.writerow({k: json.dumps(v, sort_keys=True) if isinstance(v, (list, dict)) else v for k, v in row.items()})

manifest = load(PRIVATE / 'manifest.json')
manifest.update(publication_status='public_staging_root_review_no_commit_or_push', predictions_included=True,
    artifact_scope='Selected545games only; full PGNs once per game. Raw source corpora unchanged. Frozen predictions joined only in moves.json/CSV, with development/test roles separate. No monthly archives, engine binaries, node_modules, or raw HTTP metadata.',
    prediction_roles='Full frozen model on848 development = training resubstitution; development OOF separate. Frozen200 = prospective test. Never pool train and test headline metrics.',
    ec_direct_note='Direct raw En Croissant symbol from frozen matched baseline; shared-window confirmation is a separate comparator.',
    files={name: sha(P / name) for name in ['moves.json', 'moves.csv', 'corpus.sqlite3', 'selected-games.pgn', 'observations-export.json']})
manifest.pop('artifact_sha256', None)
(P / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
provenance = {'staged_at_utc': datetime.now(timezone.utc).isoformat(), 'scope': 'Approved1048moves/545games data staging; no recomputation, training, source edits, commit or push.',
    'roles': manifest['roles'], 'board_proofs': {'verified': 1041, 'missing': 7},
    'source_mapping': mapping, 'path_normalizations': normalizations,
    'secondary_observations': 'All included games raw observation rows retained. New210fresh captures comprise200primary+10secondary.',
    'database_note': 'SQLite retains identity/evidence tables without prediction columns. Prediction joins are in moves.json/CSV only; raw source evidence is byte-identical.',
    'historical_splits': 'Only archive metadata; all848former examples are now development. Current test200 remains separate.',
    'old618_archive': 'Original published dataset remains recoverable in Git commit c6969d1; no duplicated full archive.',
    'no_binaries_dependencies_http_headers_or_monthly_archives': True,
    'data_file_sha256': {str(p.relative_to(P)): sha(p) for p in (P / 'data').rglob('*') if p.is_file()}}
(P / 'DATA-PROVENANCE.json').write_text(json.dumps(provenance, indent=2) + '\n')
private = re.compile(r'/(?:Users|private|var/folders|home|tmp)/')
bad_key = re.compile(r'"(?:cookies?|set-cookie|authorization|request_headers|response_headers|http_headers)"\s*:', re.I)
ours = [P / n for n in ['moves.json', 'moves.csv', 'observations-export.json', 'manifest.json', 'DATA-PROVENANCE.json', 'selected-games.pgn']]
ours += [p for p in (P / 'data').rglob('*') if p.is_file()]
for p in ours:
    text = p.read_text()
    assert not private.search(text), str(p)
    assert not bad_key.search(text), str(p)
    assert 'coffeechessandpizza' not in text.lower(), str(p)
db = sqlite3.connect(f'file:{P / "corpus.sqlite3"}?mode=ro', uri=True)
assert db.execute('pragma integrity_check').fetchone()[0] == 'ok'
assert db.execute('select count(*) from games').fetchone()[0] == 545
assert db.execute('select count(*) from labeled_moves').fetchone()[0] == 1048
print(json.dumps({'ready': True, 'moves': len(moves), 'games': 545, 'evidence_artifacts': len(evidence), 'predictions_roles_separate': True}))
