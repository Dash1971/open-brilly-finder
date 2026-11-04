"""Bounded final-study data consolidation; no downloads, labels, engines, or app edits."""
import collections
import hashlib
import importlib.util
import io
import json
import pathlib
import sqlite3
import sys
from datetime import datetime, timezone

sys.path.insert(0, '/private/tmp/brilly-research-deps')
import chess.pgn

ROOT = pathlib.Path(__file__).resolve().parent
WORKSPACE = ROOT.parent.parent
OLD = WORKSPACE / 'mute-chess-research/studies/brilliant-moves'
NEW = ROOT.parent / 'brilliants-improvement-2026-11-03/validation'
load = lambda p: json.loads(p.read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
def write(name, data):
    path = ROOT / name
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(data, indent=2) + '\n')
    temporary.replace(path)

spec = importlib.util.spec_from_file_location('original_validation_corpus', NEW / 'corpus.py')
helpers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helpers)
old = load(OLD / 'primary-moves.json')
new = load(NEW / 'primary-moves.json')
assert len(old) == 618 and len(new) == 200
core = []
for source, rows, split in [('reference618', old, 'development'), ('frozen_v4_validation200', new, 'validation')]:
    for original in rows:
        row = dict(original)
        row['source_split_before_consolidation'] = row.get('split')
        row['source_cohort_before_consolidation'] = row.get('source_cohort')
        row['split'] = split
        row['source_cohort'] = source
        row['historical_v4_evaluation_role'] = 'independent_validation' if split == 'validation' else 'development'
        row['future_v5_role'] = 'development_unblinded'
        core.append(row)
core_keys = {(str(r['game_id']), r['ply']) for r in core}
assert len(core_keys) == 818
panel_queue = load(NEW / 'mechanism/panel-queue.json')
frozen_panel = {(str(r['game_id']), r['ply']): r for r in panel_queue['targets']}
raw_panel = load(NEW / 'evidence/mechanism-a-reviews.json') + load(NEW / 'evidence/mechanism-b-reviews.json')
panel = []
for raw in raw_panel:
    key = (str(raw['game_id']), raw['ply'])
    frozen = frozen_panel[key]
    for field in ['game_id', 'ply', 'san', 'uci', 'fen_before', 'fen_after', 'selection_hash', 'category']:
        assert raw[field] == frozen[field]
    label = helpers.canonical_label(raw['label'])
    assert label != 'unknown' and raw['source_type'] == 'fresh_review' and raw['selected'] is True
    ident = str(raw.get('observation_id') or helpers.sha(json.dumps(raw, sort_keys=True)))
    panel.append({**frozen, 'pre_review_selection_label_status': frozen.get('label_status'),
        'label_status': 'fresh_confirmed_brilliant' if label == '!!' else 'fresh_confirmed_non_brilliant',
        'label_class': 'fresh_brilliant' if label == '!!' else 'fresh_non_brilliant',
        'fresh_label': label, 'fresh_observation_id': ident, 'fresh_captured_at': raw['captured_at'],
        'fresh_source_link': raw['source_link'], 'board_identity_captured': bool(helpers.observed_board(raw)),
        'board_missing': not bool(helpers.observed_board(raw)), 'identity_basis': 'Exact frozen game/ply/SAN/UCI and rendered after-board against full legal PGN',
        'split': 'mechanism_panel', 'source_cohort': 'frozen_v4_mechanism_panel',
        'historical_v4_evaluation_role': 'separate_preselected_challenge_panel', 'future_v5_role': 'development_unblinded'})
assert len(panel) == 30 and len({(r['game_id'],r['ply']) for r in panel}) == 30
assert not core_keys & {(r['game_id'],r['ply']) for r in panel}
assert collections.Counter(r['fresh_label'] == '!!' for r in panel) == {True:4, False:26}
write('primary-moves.json', core)
write('panel-moves.json', panel)
print(json.dumps({'early_ready':{'primary-moves.json':len(core),'panel-moves.json':len(panel)}}), flush=True)

old_ids = {r['game_id'] for r in old}
new_ids = {r['game_id'] for r in new}
panel_ids = {r['game_id'] for r in panel}
assert (len(old_ids),len(new_ids),len(panel_ids)) == (299,110,30)
assert not old_ids & (new_ids | panel_ids) and not new_ids & panel_ids
selected_ids = old_ids | new_ids | panel_ids
db_path = ROOT / 'corpus.sqlite3'
if db_path.exists():
    raise RuntimeError('Final corpus already exists; no silent overwrite/rebuild')
sources = [sqlite3.connect(f'file:{path / "corpus.sqlite3"}?mode=ro',uri=True) for path in [OLD,NEW]]
for conn in sources:
    conn.row_factory = sqlite3.Row
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
for table in ['metadata','games','positions','observations']:
    conn.execute(sources[0].execute('select sql from sqlite_master where type="table" and name=?',(table,)).fetchone()[0])
conn.execute('''CREATE VIEW active_observations AS SELECT * FROM observations WHERE rowid IN
 (SELECT MAX(rowid) FROM observations GROUP BY game_id,ply,source_type,captured_at,source_link,account)''')
for table in ['games','positions','observations']:
    columns = [r[1] for r in sources[0].execute(f'pragma table_info({table})')]
    insert = f'INSERT INTO {table} ({",".join(columns)}) VALUES ({",".join("?" for _ in columns)})'
    for source in sources:
        for original in source.execute(f'SELECT * FROM {table}'):
            row = dict(original)
            if row['game_id'] not in selected_ids:
                continue
            if table == 'games':
                row['split'] = 'development' if row['game_id'] in old_ids else 'validation' if row['game_id'] in new_ids else 'mechanism_panel'
                row['split_reason'] = 'Historical frozen-v4 evaluation role; all labels now unblinded development for future v5. Original metadata preserved separately.'
            conn.execute(insert,[row[c] for c in columns])
for raw, target in zip(raw_panel,panel):
    ident = target['fresh_observation_id']
    values = (ident,str(raw['game_id']),raw['ply'],'fresh_review',target['fresh_label'],target['label_status'],raw.get('account'),
        raw.get('san'),raw.get('uci'),raw.get('fen_before'),raw.get('fen_after'),json.dumps(raw.get('categories',[])),
        str(raw['displayed_evaluation']) if raw.get('displayed_evaluation') is not None else None,raw.get('coach_explanation'),
        raw['source_link'],raw['captured_at'],raw.get('evidence_file'),json.dumps(raw,sort_keys=True))
    existing=conn.execute('select raw_json from observations where observation_id=?',(ident,)).fetchone()
    if existing:
        assert existing[0] == values[-1]
    else:
        conn.execute('INSERT INTO observations VALUES('+','.join('?' for _ in values)+')',values)
metadata={'study_id':'brilliants-final-2026-11-03','consolidated_at':datetime.now(timezone.utc).isoformat(),
    'quantity_completion_authorized':True,'tuning_authorized':False,
    'analysis_authorization':'One panel baseline run, SF18/Threads1/Hash64MB/300000nodes; no new labels or searches for core.',
    'training_status':'All848 now unblinded development for futurev5; preserve historicalv4 development/independent-validation/panel roles.',
    'core_moves':818,'panel_moves':30,'core_games':409,'panel_games':30,'total_games':439,
    'source_metadata':{name:{r['key']:json.loads(r['value']) for r in db.execute('select * from metadata')} for name,db in zip(['reference618','validation_and_panel'],sources)},
    'source_database_sha256':{str(p.relative_to(WORKSPACE)/'corpus.sqlite3'):sha(p/'corpus.sqlite3') for p in [OLD,NEW]},
    'panel_freeze_sha256':sha(NEW/'mechanism/PANEL-FREEZE.json')}
for key,value in metadata.items():conn.execute('insert into metadata values(?,?)',(key,json.dumps(value,sort_keys=True)))
conn.commit()

by_game = collections.defaultdict(list)
for row in core+panel:by_game[row['game_id']].append(row)
games,positions_checked=0,0
for game in conn.execute('select * from games order by game_id'):
    assert helpers.sha(game['pgn']) == game['pgn_sha256']
    parsed=chess.pgn.read_game(io.StringIO(game['pgn']))
    assert parsed and not parsed.errors
    board=parsed.board()
    saved={r['ply']:r for r in conn.execute('select * from positions where game_id=?',(game['game_id'],))}
    for ply,move in enumerate(parsed.mainline_moves(),1):
        assert move in board.legal_moves
        p=saved[ply]
        assert (p['san'],p['uci'],p['fen_before'])==(board.san(move),move.uci(),board.fen())
        board.push(move)
        assert p['fen_after']==board.fen()
        positions_checked+=1
    assert len(saved)==game['total_plies']
    for target in by_game[game['game_id']]:
        p=saved[target['ply']]
        for field in ['san','uci','fen_before','fen_after']:assert target[field]==p[field]
        observed=conn.execute('select * from observations where observation_id=?',(target['fresh_observation_id'],)).fetchone()
        assert observed and observed['label']==target['fresh_label']
        raw=json.loads(observed['raw_json']);placement=helpers.observed_board(raw)
        if placement:assert placement==p['fen_after'].split()[0]
    games+=1
assert games==439
counts={t:conn.execute(f'select count(*) from {t}').fetchone()[0] for t in ['games','positions','observations']}
write('observations-export.json',[{**dict(r),'raw':json.loads(r['raw_json'])} for r in conn.execute('select * from observations order by game_id,ply,captured_at,observation_id')])
game_rows=list(conn.execute('select * from games order by game_id'))
(ROOT/'selected-games.pgn').write_text('\n\n'.join(r['pgn'].strip() for r in game_rows)+'\n')
write('public-pgn-provenance.json',{'selected_games':len(game_rows),'raw_http_headers_included':False,'games':[
    {k:r[k] for k in ['game_id','pgn_sha256','source_link','captured_at','total_plies','split']} for r in game_rows]})

def merge_analysis(name, source_files, expected_targets, expected_snapshots):
    datas=[load(p) for p in source_files]
    for key in ['engine_sha256','nodes_per_position','threads','hash_mb']:
        assert len({d[key] for d in datas})==1
    targets=[];snapshots={}
    for index,data in enumerate(datas):
        assert data['status']=='complete'
        for original in data['targets']:
            target=dict(original)
            target['source_split_before_consolidation']=target.get('split')
            target['source_cohort_before_consolidation']=target.get('source_cohort')
            target['split']='development' if index==0 else 'validation'
            target['source_cohort']='reference618' if index==0 else 'frozen_v4_validation200'
            target['future_v5_role']='development_unblinded'
            targets.append(target)
        assert not set(snapshots)&set(data['snapshots'])
        snapshots.update(data['snapshots'])
    assert len(targets)==expected_targets and len(snapshots)==expected_snapshots
    out={k:datas[0][k] for k in ['engine_path','engine_sha256','nodes_per_position','threads','hash_mb','engine_id'] if k in datas[0]}
    out.update(status='complete',stage=datas[0]['stage'],quantity_limit=expected_targets,primary_selection_sha256=sha(ROOT/'primary-moves.json'),
        source_files=[{'path':str(p.relative_to(WORKSPACE)),'sha256':sha(p),'targets':len(d['targets']),'snapshots':len(d['snapshots']),
            'started_at':d.get('started_at'),'completed_at':d.get('completed_at')} for p,d in zip(source_files,datas)],
        scope='Historical v4 roles retained; all targets now unblinded development for futurev5. Stronger subsets are targeted sensitivity, not validation.',
        rule_tuning=False,targets=targets,snapshots=snapshots)
    write(name,out)
merge_analysis('analysis-baseline.json',[OLD/'analysis-baseline.json',NEW/'analysis-baseline.json'],818,2355)
merge_analysis('analysis-stronger.json',[OLD/'analysis-stronger.json',NEW/'analysis-stronger.json'],90,267)
write('manifest.json',{'metadata':metadata,'counts':counts,'validation':{'all_full_PGNs_legally_replayed':True,'all_positions_checked':positions_checked,
    'all848_primary_identities_match':True,'panel_boards_checked':30,'primary_class_counts':dict(collections.Counter(r['fresh_label']=='!!' for r in core)),
    'panel_class_counts':dict(collections.Counter(r['fresh_label']=='!!' for r in panel))},'input_files':{str(p.relative_to(WORKSPACE)):sha(p) for p in [OLD/'primary-moves.json',NEW/'primary-moves.json',NEW/'mechanism/panel-queue.json',NEW/'evidence/mechanism-a-reviews.json',NEW/'evidence/mechanism-b-reviews.json']}})
assert conn.execute('pragma integrity_check').fetchone()[0]=='ok'
conn.close()
for db in sources:db.close()
print(json.dumps({'complete':True,'counts':counts,'positions_legally_checked':positions_checked,'core':818,'panel':30,'baseline_snapshots':2355,'stronger_targets':90,'stronger_snapshots':267}),flush=True)
