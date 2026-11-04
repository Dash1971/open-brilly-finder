"""Single-writer final fresh-evidence audit; preserves the prepared database."""
import collections
import hashlib
import importlib.util
import json
import pathlib
import shutil
import sqlite3
import sys

sys.dont_write_bytecode=True
ROOT=pathlib.Path(__file__).resolve().parent
load=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
save=lambda n,x:(ROOT/n).write_text(json.dumps(x,indent=2)+'\n')
spec=importlib.util.spec_from_file_location('v7_corpus',ROOT/'corpus.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
prepared=ROOT/'corpus.sqlite3';original_hash=sha(prepared)
assert original_hash=='cafe2a3e589f0d045c3402d2f8b17887b322557b9ad9780155422a291657293b'
working=ROOT/'workingassessment.db';assert not working.exists(),'Do not silently overwrite a working assessment'
queue=load(ROOT/'FINALQUEUE.json')['accounts'];excluded=set(load(ROOT/'exclude-games.json')['game_ids'])
known=set(load(ROOT/'known-position-exclusions.json')['canonical_first_four'])
canon=lambda f:' '.join(m.chess.Board(f).fen().split()[:4])
rawfiles=[ROOT/'evidence'/f'{a.lower()}-fresh-review.json' for a in m.ACCOUNTS]
raw_by_account={a:load(p) for a,p in zip(m.ACCOUNTS,rawfiles)}
allraw=[row for rows in raw_by_account.values() for row in rows]
assert len(allraw)==217
keys=[(r['game_id'],r['ply']) for r in allraw];assert len(keys)==len(set(keys)), 'Repeated canonical fresh identities need review'
audit={};primary=[]
for account,rows in raw_by_account.items():
    q=queue[account];bykey={(r['game_id'],r['ply']):r for r in rows}
    positives=[r for r in rows if r.get('selected') is True and r['sample_role']=='positive_target']
    negatives=[r for r in rows if r.get('selected') is True and r['sample_role']=='negative_control']
    selected=[r for r in rows if r.get('selected') is True]
    assert len(selected)==40 and len(positives)==len(negatives)==20
    assert all(m.canonical_label(r['label'])=='!!' for r in positives)
    assert all(m.canonical_label(r['label']) not in ['!!','unknown'] for r in negatives)
    expected_positive=[];seen_games=set()
    for target in q['targets']:
        key=(target['game_id'],target['ply']);assert key in bykey,('missing_original_nominee',account,key)
        observed=bykey[key]
        assert observed['source_type']=='fresh_review'
        if m.canonical_label(observed['label'])=='!!':expected_positive.append(key)
        candidates=target['control_candidates'];chosen=[r for r in negatives if r['game_id']==target['game_id']]
        assert len(chosen)==1,('initial_game_negative_quota',account,target['game_id'])
        expected_negative=None
        for candidate in candidates:
            ck=(candidate['game_id'],candidate['ply'])
            assert ck in bykey,('missing_earlier_frozen_control',account,ck)
            if m.canonical_label(bykey[ck]['label'])!='!!':expected_negative=ck;break
        assert expected_negative==(chosen[0]['game_id'],chosen[0]['ply'])
        seen_games.add(chosen[0]['game_id'])
    assert len(seen_games)==20
    reserves=list(q['reserves'])
    if account=='GothamChess':reserves+=load(ROOT/'gothamchess-positive-topup-queue.json')['ordered_positive_candidates']
    visited_reserves=[]
    for target in reserves:
        if len(expected_positive)==20:break
        key=(target['game_id'],target['ply']);assert key in bykey,('missing_earlier_positive_reserve',account,key)
        visited_reserves.append(key)
        if m.canonical_label(bykey[key]['label'])=='!!':expected_positive.append(key)
    assert set(expected_positive)=={(r['game_id'],r['ply']) for r in positives}
    assert len(expected_positive)==20
    audit[account]={'raw_captures':len(rows),'primary_brilliant':20,'primary_nonbrilliant':20,'secondary':len(rows)-40,
        'all_original20_nominees_captured':True,'negative_keys_exact_original20_games_and_first_nonbrilliant_frozen_control':True,
        'positive_keys_follow_original_then_frozen_reserve_order':True,'visited_positive_reserves':[f'{g}:{p}' for g,p in visited_reserves]}
    primary.extend(selected)

shutil.copyfile(prepared,working)
conn=sqlite3.connect(working);conn.row_factory=sqlite3.Row
for g in load(ROOT/'gothamchess-positive-topup-pgn.json')['games']:
    m.import_pgn(conn,g['pgn'],g['source_link'],g['captured_at'],{g['game_id']})
imports=[m.import_evidence(conn,p) for p in rawfiles]
assert all(not x['excluded_known_games_skipped'] for x in imports)
assert conn.execute("SELECT count(*) FROM observations WHERE source_type='fresh_review'").fetchone()[0]==217
allboards=0;coach_counts=collections.Counter();conflicts=collections.defaultdict(set)
for raw in allraw:
    gid,ply=str(raw['game_id']),raw['ply'];assert gid not in excluded
    pos=conn.execute('SELECT * FROM positions WHERE game_id=? AND ply=?',(gid,ply)).fetchone();assert pos
    assert all(raw[k]==pos[k] for k in ['san','uci','fen_before','fen_after']), (gid,ply,'PGN_identity')
    assert canon(pos['fen_before']) not in known and canon(pos['fen_after']) not in known,(gid,ply,'known_position')
    board=m.observed_board(raw);assert board==pos['fen_after'].split()[0],(gid,ply,'rendered_board')
    allboards+=1
    score=m.canonical_label(raw['label']);assert score!='unknown';conflicts[(gid,ply)].add(score=='!!')
    coach_counts[raw.get('coach_completeness','unspecified')]+=1
assert not any(len(v)>1 for v in conflicts.values())
out=[]
for raw in primary:
    gid,ply=str(raw['game_id']),raw['ply'];game=conn.execute('SELECT * FROM games WHERE game_id=?',(gid,)).fetchone()
    pos=conn.execute('SELECT * FROM positions WHERE game_id=? AND ply=?',(gid,ply)).fetchone()
    ident=str(raw.get('observation_id') or m.sha(json.dumps(raw,sort_keys=True)))
    obs=conn.execute('SELECT * FROM observations WHERE observation_id=?',(ident,)).fetchone();assert obs
    label=m.canonical_label(raw['label']);headers=json.loads(game['headers_json'])
    row={k:pos[k] for k in ['game_id','ply','san','uci','fen_before','fen_after','clock_seconds']}
    row.update(account=raw['account'],truth=label=='!!',label_class='fresh_brilliant' if label=='!!' else 'fresh_non_brilliant',
        fresh_label=label,observed_label_raw=raw['label'],fresh_observation_id=ident,source_observation_id=ident,
        fresh_captured_at=raw['captured_at'],fresh_source_link=raw['source_link'],source_link=raw['source_link'],
        source_type='fresh_review',sample_role=raw['sample_role'],board_identity_captured=True,board_missing=False,
        identity_basis='Exact official full-PGN game/SAN/UCI/ply/FEN and captured rendered after-board',
        split='prospective_v7_test',source_cohort='frozen_v7_prospective_main200',pgn_sha256=game['pgn_sha256'],
        date=game['date'],white=game['white'],black=game['black'],white_rating=game['white_rating'],black_rating=game['black_rating'],
        time_control=game['time_control'],game_type='daily' if '/daily/' in headers.get('Link','') else 'live',
        sampling_category=raw.get('sampling_category'),categories=raw.get('categories',[]),coach_completeness=raw.get('coach_completeness'),
        selection_addendum=raw.get('selection_addendum'))
    out.append(row)
out.sort(key=lambda r:(m.ACCOUNTS.index(r['account']),r['game_id'],r['ply']))
assert len(out)==len({(r['game_id'],r['ply']) for r in out})==200
assert collections.Counter(r['truth'] for r in out)=={True:100,False:100}
save('root-frozen-final200queue.json',out);save('primary-moves.json',out)
ids={r['game_id'] for r in out};games=[dict(r) for r in conn.execute('SELECT * FROM games ORDER BY game_id') if r['game_id'] in ids]
assert len(games)==len(ids)==109
(ROOT/'selected-assessment-games.pgn').write_text('\n\n'.join(g['pgn'].strip() for g in games)+'\n')
save('selected-assessment-pgn-provenance.json',{'games':len(games),'primary_moves':200,'raw_http_headers_included':False,
    'records':[{k:g[k] for k in ['game_id','pgn_sha256','source_link','captured_at','total_plies']} for g in games]})
save('working-observations-export.json',[dict(r) for r in conn.execute('SELECT * FROM observations ORDER BY game_id,ply,captured_at,observation_id')])
metadata={'final_primary_queue_sha256':sha(ROOT/'root-frozen-final200queue.json'),'fresh_primary_selection_authority':'Selected canonical fresh records audited against frozen target/reserve/control order; gallery selected flags never choose primary.',
    'all217raw_identity_and_board_checks':True,'primary_moves':200,'primary_games':len(games),'fresh_captures':217,'secondary_fresh_captures':17}
for key,value in metadata.items():conn.execute('INSERT INTO metadata VALUES(?,?)',(key,json.dumps(value)))
conn.commit();assert conn.execute('PRAGMA integrity_check').fetchone()[0]=='ok';assert not conn.execute('PRAGMA foreign_key_check').fetchall();conn.close()
assert sha(prepared)==original_hash
sourcehash={n:sha(ROOT/n) for n in ['FREEZE.json','ADAPTER-FREEZE.json','PROTOCOL-FREEZE.json','QUEUE-FREEZE.json','FINALQUEUE.json','NATIVE-SUBSET-FREEZE.json','GOTHAM-QUOTA-COMPLETION-ADDENDUM.json','GOTHAM-TOPUP-GO.json']}
final={'frozen_at_utc':m.now(),'scope':'All200primary fresh labels finalized before any model/engine evaluation; predictor source unchanged. Current truth is joined after model outputs. No gallery-label-only negatives.',
    'primary_moves':200,'brilliant':100,'explicit_nonbrilliant':100,'primary_games':len(games),'all_raw_fresh_captures':217,'secondary_fresh_captures':17,
    'all217_raw_boards_PGN_SAN_UCI_FEN_ply_verified':True,'all571_reviewed_games_excluded':True,'all46194known_before_and_after_positions_excluded':True,
    'no_conflicting_fresh_binary_labels':True,'per_account_selection_audit':audit,'coach_quality_counts':dict(coach_counts),
    'prepared_database_sha256_unchanged':original_hash,'working_database':'workingassessment.db','working_database_sha256':sha(working),
    'primary_queue':'root-frozen-final200queue.json','primary_queue_sha256':sha(ROOT/'root-frozen-final200queue.json'),
    'raw_file_sha256':{str(p.relative_to(ROOT)):sha(p) for p in rawfiles},'source_and_protocol_freeze_sha256':sourcehash,
    'output_sha256':{n:sha(ROOT/n) for n in ['primary-moves.json','selected-assessment-games.pgn','selected-assessment-pgn-provenance.json','working-observations-export.json']},
    'database_integrity':'ok','database_foreign_keys':'ok','engine_searches_or_model_scores_performed':False,
    'selection_audit_originals_not_reimported':True,'knvb_partition_not_reimported':True}
save('FINAL-DATA-FREEZE.json',final)
print(json.dumps({'complete':True,'primary_moves':200,'primary_games':len(games),'raw217_verified':True,'primary_queue_sha256':final['primary_queue_sha256'],
    'working_database_sha256':final['working_database_sha256'],'final_data_freeze_sha256':sha(ROOT/'FINAL-DATA-FREEZE.json')}))
