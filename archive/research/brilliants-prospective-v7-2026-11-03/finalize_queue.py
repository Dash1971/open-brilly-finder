"""Finish the prelabel queue using the existing four-control ranking/import method."""
import collections
import copy
import hashlib
import importlib.util
import json
import pathlib
import sqlite3
import sys

sys.dont_write_bytecode=True
ROOT=pathlib.Path(__file__).resolve().parent
W=ROOT.parent.parent
load=lambda p:json.loads(p.read_text())
save=lambda n,x:(ROOT/n).write_text(json.dumps(x,indent=2)+'\n')
def sha(path):
    value=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1048576),b''):value.update(chunk)
    return value.hexdigest()
assert not (ROOT/'QUEUE-FREEZE.json').exists(),'No silent overwrite of frozen queue'
spec=importlib.util.spec_from_file_location('v7_corpus',ROOT/'corpus.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
protocol=load(ROOT/'PROTOCOL-FREEZE.json');source=load(ROOT/'FREEZE.json');adapter=load(ROOT/'ADAPTER-FREEZE.json')
assert protocol['prepared_plan_sha256']==sha(ROOT/'PLAN-PREPARED.json')
assert adapter['source_freeze_sha256']==sha(ROOT/'FREEZE.json')
checks=[]
for receipt in [source,adapter]:
    for name,meta in receipt['files'].items():
        assert sha(ROOT/name)==meta['sha256'],name
        checks.append({'artifact':name,'sha256':meta['sha256']})
plan=copy.deepcopy(load(ROOT/'PLAN-PREPARED.json'))
plan.update(frozen_at_utc=m.now(),status='Exact prelabel main queue frozen; awaiting root GO; no fresh labels or engines.',
    final_source_freeze_sha256=sha(ROOT/'FREEZE.json'),adapter_freeze_sha256=sha(ROOT/'ADAPTER-FREEZE.json'),
    protocol_freeze_sha256=sha(ROOT/'PROTOCOL-FREEZE.json'),reporting='All1048previouslabels are development and excluded. This200 is prospective for unchangedv7; direct-change panel separate. No retuning.')
save('PLAN.json',plan)
known=set(load(ROOT/'known-position-exclusions.json')['canonical_first_four'])
excluded=set(load(ROOT/'exclude-games.json')['game_ids'])
canon=lambda fen:' '.join(m.chess.Board(fen).fen().split()[:4])
gallery={(r['game_id'],r['ply']) for r in load(ROOT/'historical-pool-snapshot.json')['rows']}
priority={'apparent_piece_offer':0,'quiet_attacked_defended_piece':1,'recapture_exchange':2,'other_capture':3,'other_quiet':4}
accounts={};summary={};games=set();identities=set()
for account in m.ACCOUNTS:
    path=ROOT/f'{account.lower()}-ui-queue.json';queue=load(path);bank=queue['controls'];frozen=[]
    assert len(queue['targets'])==20
    for target in queue['targets']+queue['reserves']:
        gid=target['game_id'];assert gid not in excluded
        assert canon(target['fen_before']) not in known and canon(target['fen_after']) not in known
        matches=[r for r in bank if r['game_id']==gid and (gid,r['ply']) not in gallery]
        matches.sort(key=lambda r:(priority[r['sampling_priority']],abs(r['ply']-target['ply']),r['ply'],r['uci']))
        controls=[]
        for rank,raw in enumerate(matches[:4]):
            row=dict(raw);assert canon(row['fen_before']) not in known and canon(row['fen_after']) not in known
            row.update(frozen_control_rank=rank,current_label='unknown',label='unknown',selected=False,
                sample_role='negative_candidate',selection_reason='Fixedrawdescriptorpriority then nearest targetply; no policy predictions/currentlabels',paired_positive_key=f'{gid}:{target["ply"]}')
            controls.append(row);frozen.append(row)
        assert len(controls)==4
        primary=target in queue['targets']
        target.update(control_candidates=controls,matched_control_draft=controls[0],control_reserves=controls[1:],
            current_label='unknown',selected=primary,selection_status='primary_historical_nomination' if primary else 'frozen_order_positive_reserve',selected_at=plan['frozen_at_utc'])
        if primary:
            identity=(canon(target['fen_before']),target['uci']);assert gid not in games and identity not in identities
            games.add(gid);identities.add(identity)
    queue.update(status='FROZEN_PENDING_ROOT_GO_NO_CURRENT_LABELS',controls=frozen,
        control_policy='Use each target control_candidates rank0then1–3. RetainALLexplicit labels; ifall4unusable stop/report. Never select unfrozen controls.',
        positive_reserve_policy='Advance exact frozen order only; retain all gallery/current disagreements and secondary observations.')
    save(path.name,queue);save(f'evidence/{account.lower()}-gallery-selected.json',queue['targets'])
    accounts[account]=queue
    summary[account]={'targets':20,'positive_reserves':len(queue['reserves']),'primary_control_candidates':80,
        'all_targets_and_reserves_have4controls':True,'categories':dict(collections.Counter(t['sampling_category'] for t in queue['targets']))}
assert len(games)==len(identities)==100
conn=m.connect(ROOT/'corpus.sqlite3')
assert conn.execute("SELECT count(*) FROM observations WHERE source_type='fresh_review'").fetchone()[0]==0
for account in m.ACCOUNTS:m.import_evidence(conn,ROOT/'evidence'/f'{account.lower()}-gallery-selected.json')
validation=m.validate(conn)
assert not validation['indexing_mismatches'] and not validation['observations_waiting_for_pgn'] and not validation['known_regression_fen_matches'],validation
m.export(conn)
assert conn.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
assert conn.execute("SELECT count(*) FROM observations WHERE source_type='fresh_review'").fetchone()[0]==0
save('FINALQUEUE.json',{'frozen_at_utc':m.now(),'status':'AwaitingrootGO; no fresh labels/engines','target_game_count':100,
    'planned_primary_moves':200,'targets_per_account':20,'selection':'Fixed predeclared mute-prospective-v7 account/category/game/ply SHA256/categoryroundrobin; no currentlabels/policyoutputs.',
    'summary':summary,'accounts':accounts})
queuehash=sha(ROOT/'FINALQUEUE.json')
native=[]
for account,queue in accounts.items():
    ordered=sorted(queue['targets'],key=lambda t:hashlib.sha256(f'{queuehash}:{account}:{t["game_id"]}'.encode()).hexdigest())
    for t in ordered[:2]:native.append({'account':account,'game_id':t['game_id'],'nominee_ply':t['ply'],'pgn_sha256':t['pgn_sha256'],
        'selection_hash':hashlib.sha256(f'{queuehash}:{account}:{t["game_id"]}'.encode()).hexdigest(),'label_status':'ALLcurrentlabelsUNKNOWN'})
assert len(native)==len({r['game_id'] for r in native})==10
save('NATIVE-SUBSET-FREEZE.json',{'frozen_at_utc':m.now(),'queue_sha256':queuehash,'source_freeze_sha256':sha(ROOT/'FREEZE.json'),
    'adapter_freeze_sha256':sha(ROOT/'ADAPTER-FREEZE.json'),'selection':'First2peraccount bySHA256(queueHash:account:gameID), before anyfreshlabels. Fullgame nativeflow, not selected move only.',
    'games':native,'profile':adapter['native_profile']})
names=['PLAN.json','PLAN-PREPARED.json','PROTOCOL-FREEZE.json','FREEZE.json','ADAPTER-FREEZE.json','FINALQUEUE.json','NATIVE-SUBSET-FREEZE.json',
    'exclude-games.json','known-position-exclusions.json','known-regression-fens.json','historical-pool-snapshot.json','ELIGIBLE-PGN-POOL.json',
    'MONTHLY-CACHE-SNAPSHOT.json','PUBLIC-PGN-RESOLUTION.json','corpus.py','prepare_cached_pgn.py','prepare_controls.py','prepare-controls.mts','select_draft.py','finalize_queue.py','control-preparation-summary.json']
names += [f'{a.lower()}-ui-queue.json' for a in m.ACCOUNTS]
names += [p.name for p in sorted(ROOT.glob('*-gallery-topup-raw.json'))]
freeze={'frozen_at_utc':m.now(),'all_current_labels_unknown':True,'fresh_review_observations':0,'targets':100,'planned_fresh_primary_moves':200,
    'class_target':{'brilliant':100,'explicit_non_brilliant':100},'accounts':summary,'file_sha256':{n:sha(ROOT/n) for n in names},
    'final_source_freeze_sha256':sha(ROOT/'FREEZE.json'),'adapter_freeze_sha256':sha(ROOT/'ADAPTER-FREEZE.json'),
    'prelabel_protocol_initial_source_sha256':protocol['source_freeze_sha256'],'note_source_finalization':'Protocol initialsource pin is archival; finalsourcearchive/adapter frozen before newlabels and pinned separately.',
    'source_and_adapter_files_verified':checks,'all571reviewed_games_excluded':True,'all46194knownpositions_excluded':True,
    'full_PGN_identity_validation':validation,'prepared_database_sha256':sha(ROOT/'corpus.sqlite3'),
    'raw_gallery_audit':'Everyoriginalrawgallerycard remains in hashed *-gallery-topup-raw.json, including duplicate/excludedcards. No unresolvednominations silently substituted.',
    'no_engines_or_current_review_labels':True,'native_subset_receipt':'NATIVE-SUBSET-FREEZE.json'}
save('QUEUE-FREEZE.json',freeze);conn.close()
print(json.dumps({'ready_for_root_review':True,'summary':summary,'targetgames':100,'fresh_reviews':0,'queue_sha256':queuehash,
    'queue_freeze_sha256':sha(ROOT/'QUEUE-FREEZE.json'),'native_subset_games':10,'source_files_checked':len(checks)}))
