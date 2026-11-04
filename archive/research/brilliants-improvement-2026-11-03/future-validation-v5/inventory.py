"""Offline readiness inventory, reusing validation corpus identity rules; no DB writes or collection."""
import collections
import functools
import hashlib
import importlib.util
import json
import pathlib
import re
import sqlite3
import sys
from datetime import datetime,timezone
sys.dont_write_bytecode=True
ROOT=pathlib.Path(__file__).resolve().parent
IMPROVE=ROOT.parent
WORKSPACE=IMPROVE.parent.parent
VALIDATION=IMPROVE/'validation'
FINAL=IMPROVE.parent/'brilliants-final-2026-11-03'
spec=importlib.util.spec_from_file_location('existing_validation_corpus',VALIDATION/'corpus.py')
helpers=importlib.util.module_from_spec(spec);spec.loader.exec_module(helpers)
chess=helpers.chess
SEED='mute-future-validation-v5-v1'
CATEGORIES=['Queen Sacrifice','Rook Sacrifice','Bishop Sacrifice','Knight Sacrifice','All Types']
ACCOUNTS=['nelsi','hansen','KNVB','GothamChess','Hikaru']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,data):(ROOT/name).write_text(json.dumps(data,indent=2)+'\n')
@functools.lru_cache(maxsize=100000)
def canon(fen):return ' '.join(chess.Board(fen).fen().split()[:4])
def records(obj):
    if isinstance(obj,dict):
        if obj.get('game_id') and isinstance(obj.get('ply'),int):yield obj
        for value in obj.values():yield from records(value)
    elif isinstance(obj,list):
        for value in obj:yield from records(value)
def read(path):return json.loads(path.read_text())
def readonly(path):
    conn=sqlite3.connect(f'file:{path}?mode=ro',uri=True);conn.row_factory=sqlite3.Row;return conn

final_db=readonly(FINAL/'corpus.sqlite3')
current439={r[0] for r in final_db.execute('select game_id from games')};assert len(current439)==439
final_db.close()
prior325=set(read(VALIDATION/'exclude-games.json')['game_ids']);assert len(prior325)==325
exclusion_reasons=collections.defaultdict(set)
for gid in current439:exclusion_reasons[gid].add('all_current439_game_corpus')
for gid in prior325:exclusion_reasons[gid].add('prior325_reviewed_or_regression_games')
study_dirs=[p for p in IMPROVE.parent.glob('brilliants*') if p.is_dir() and p!=ROOT]
db_paths=sorted({p/'corpus.sqlite3' for p in study_dirs if (p/'corpus.sqlite3').exists()}|{VALIDATION/'corpus.sqlite3',FINAL/'corpus.sqlite3',WORKSPACE/'mute-chess-research/studies/brilliant-moves/corpus.sqlite3'})
source_paths=set(db_paths)|{VALIDATION/'exclude-games.json',VALIDATION/'known-regression-fens.json',VALIDATION/'corpus.py',VALIDATION/'prepare.py',VALIDATION/'PLAN.json'}
evidence_paths=sorted({p for d in study_dirs+[VALIDATION] for p in (d/'evidence').glob('*.json')})
explicit_ui_sources=collections.defaultdict(set)
for path in evidence_paths:
    source_paths.add(path)
    for row in records(read(path)):
        if row.get('source_type')=='fresh_review' or (row.get('observed_page_url') and row.get('displayed_label_text')):
            gid=str(row['game_id']);exclusion_reasons[gid].add('saved_UI_review_evidence_including_secondary');explicit_ui_sources[gid].add(str(path.relative_to(WORKSPACE)))
for d in study_dirs+[VALIDATION]:
    for path in d.glob('*checkpoint*.json'):
        source_paths.add(path);obj=read(path)
        for key in ['currentGame','current_game','known_unpaired_positive_game']:
            if isinstance(obj.get(key),(str,int)) and str(obj[key]).isdigit():exclusion_reasons[str(obj[key])].add('explicit_review_checkpoint_current_game')
        for key in ['used','used_keys']:
            for value in obj.get(key,[]):
                if isinstance(value,str) and re.match(r'^\d+:\d+$',value):exclusion_reasons[value.split(':')[0]].add('explicit_review_checkpoint_used_key')
        if obj.get('last_control_observed_before_pause',{}).get('game_id'):
            exclusion_reasons[str(obj['last_control_observed_before_pause']['game_id'])].add('explicit_review_checkpoint_observed_control')
games={};positions={};known={r['canonical_first_four'] for r in read(VALIDATION/'known-regression-fens.json')['positions']}
for path in db_paths:
    conn=readonly(path)
    for r in conn.execute("select distinct game_id from observations where source_type='fresh_review'"):
        exclusion_reasons[r[0]].add('any_cached_DB_fresh_review_including_secondary')
    for r in conn.execute('select * from games'):games.setdefault(r['game_id'],dict(r))
    for r in conn.execute('select * from positions'):positions.setdefault((r['game_id'],r['ply']),dict(r))
    conn.close()
excluded=set(exclusion_reasons)
for (gid,_),p in positions.items():
    if gid in excluded:known.update([canon(p['fen_before']),canon(p['fen_after'])])
assert current439<=excluded and prior325<=excluded
save('exclude-games.json',{'game_ids':sorted(excluded),'counts':{'current439':439,'prior325':325,'union':len(excluded),'additional_UI_review_games_beyond_their_union':len(excluded-current439-prior325)},
    'reasons':{gid:sorted(reasons) for gid,reasons in sorted(exclusion_reasons.items())},'explicit_UI_evidence_sources':{gid:sorted(paths) for gid,paths in sorted(explicit_ui_sources.items())},
    'coverage':'Known savedUIcaptures, allcachedfresh-reviewDBrows, explicitcheckpointcurrent/used/observedcontrols; galleryURLs alone do not prove a reviewvisit. No browser was inspected.'})
save('known-position-exclusions.json',{'normalization':'python-chess normalized first4FENfields, before AND after; all cached full positions in excluded games plus prior25904regression exclusions','count':len(known),'canonical_first_four':sorted(known)})

raw_candidates={};candidate_sources=collections.defaultdict(set)
# Existing ready pools preserve full-page category verification and PGN identity.
for account in ACCOUNTS:
    path=VALIDATION/f'{account.lower()}-candidate-pool.json';source_paths.add(path)
    for row in read(path):
        key=(str(row['game_id']),row['ply']);raw_candidates.setdefault(key,dict(row));candidate_sources[key].add(str(path.relative_to(WORKSPACE)))
# Include still-pending cached cards to report the ceiling, not silently lose them.
path=VALIDATION/'cached-candidates-COLLECTOR-ONLY.json';source_paths.add(path)
for row in read(path):
    key=(str(row['game_id']),row['ply'])
    raw_candidates.setdefault(key,dict(row));candidate_sources[key].update(row.get('sources',[]));candidate_sources[key].add(str(path.relative_to(WORKSPACE)))
gallery_keys=set(raw_candidates)
ready=collections.defaultdict(list);pending=collections.defaultdict(list);rejected=collections.defaultdict(list)
account_names={a.lower():a for a in ACCOUNTS}
for key,raw in raw_candidates.items():
    account=account_names.get(str(raw.get('account','')).lower());gid,ply=key
    if account is None:continue
    if gid in excluded:continue
    p=positions.get(key);g=games.get(gid)
    if not p or not g:
        pending[account].append({'game_id':gid,'ply':ply,'reason':'No validated game/position in existing SQLite caches; monthlyarchives not rescanned because card-count ceiling is already insufficient.','sources':sorted(candidate_sources[key])});continue
    if canon(p['fen_before']) in known or canon(p['fen_after']) in known:
        rejected[account].append({'game_id':gid,'ply':ply,'reason':'reviewed_development_before_or_after_position_overlap'});continue
    mover=g['white'] if p['fen_before'].split()[1]=='w' else g['black']
    if mover.lower()!=account.lower():rejected[account].append({'game_id':gid,'ply':ply,'reason':'account_not_to_move'});continue
    observed=helpers.observed_board(raw)
    if observed and observed!=p['fen_after'].split()[0]:rejected[account].append({'game_id':gid,'ply':ply,'reason':'captured_gallery_board_mismatch'});continue
    if raw.get('san') and raw['san']!=p['san']:rejected[account].append({'game_id':gid,'ply':ply,'reason':'observed_SAN_mismatch'});continue
    if raw.get('uci') and raw['uci']!=p['uci']:rejected[account].append({'game_id':gid,'ply':ply,'reason':'observed_UCI_mismatch'});continue
    header=json.loads(g['headers_json']);match=re.search(r'/(live|daily)/',header.get('Link','')+' '+header.get('Site',''))
    if not match:rejected[account].append({'game_id':gid,'ply':ply,'reason':'namespace_unverified'});continue
    categories=raw.get('categories') or ([raw['sampling_category']] if raw.get('sampling_category') in CATEGORIES[:4] else [])
    categories=[c for c in categories if c in CATEGORIES[:4]]
    ready[account].append({'game_id':gid,'ply':ply,'account':account,**{k:p[k] for k in ['san','uci','fen_before','fen_after']},
        'categories':categories,'historical_gallery_label':'!!','current_label':'unknown','current_label_absence_is_not_negative':True,
        'game_type':match[1],'source_link':f'https://www.chess.com/analysis/game/{match[1]}/{gid}/review?move={ply-1}',
        'historical_gallery_sources':sorted(candidate_sources[key]),'original_capture_timestamp':raw.get('captured_at') or raw.get('capture_timestamp'),
        'pgn_sha256':g['pgn_sha256'],'pgn_source':g['source_link'],'pgn_cached_at':g['captured_at']})

banks={}
for account in ACCOUNTS:
    path=VALIDATION/f'control-candidates-v2-{account.lower()}.json';source_paths.add(path);banks[account]=read(path)
priority={'apparent_piece_offer':0,'quiet_attacked_defended_piece':1,'recapture_exchange':2,'other_capture':3,'other_quiet':4}
draft={};inventory={};usedgames=set();usedident=set()
for account in ACCOUNTS:
    groups={cat:[] for cat in CATEGORIES}
    for row in ready[account]:
        for cat in row['categories'] or ['All Types']:
            rank=hashlib.sha256(f'{SEED}|{account}|{cat}|{row["game_id"]}|{row["ply"]}'.encode()).hexdigest()
            groups[cat].append({**row,'sampling_category':cat,'selection_hash':rank})
    for rows in groups.values():rows.sort(key=lambda x:x['selection_hash'])
    selected=[];reserves=[];localgames=set();localident=set()
    while any(groups.values()):
        for cat in CATEGORIES:
            while groups[cat]:
                row=groups[cat].pop(0);ident=(canon(row['fen_before']),row['uci'])
                if row['game_id'] in localgames|usedgames or ident in localident|usedident:continue
                localgames.add(row['game_id']);localident.add(ident)
                if len(selected)<20:selected.append(row);usedgames.add(row['game_id']);usedident.add(ident)
                else:reserves.append(row)
                break
    for row in selected:
        controls=[]
        for original in banks[account]['rows']:
            key=(str(original['game_id']),original['ply'])
            if key[0]!=row['game_id'] or key in gallery_keys or canon(original['fen_before']) in known or canon(original['fen_after']) in known:continue
            actual=positions.get(key)
            if not actual or any(actual[f]!=original[f] for f in ['san','uci','fen_before','fen_after']):continue
            x=dict(original);x.update(label='unknown',selected=False,future_role='negative_candidate_not_confirmed',
                ranking_priority=priority.get(original.get('sampling_priority'),4),distance_from_target=abs(original['ply']-row['ply']))
            controls.append(x)
        controls.sort(key=lambda x:(x['ranking_priority'],x['distance_from_target'],x['ply'],x['uci']))
        row['matched_control_draft']=controls[0] if controls else None;row['control_reserves']=controls[1:4]
    category_inventory={cat:{'moves':sum(cat in (r['categories'] or ['All Types']) for r in ready[account]),'unique_games':len({r['game_id'] for r in ready[account] if cat in (r['categories'] or ['All Types'])})} for cat in CATEGORIES}
    cards_upper=len({str(r['game_id']) for r in raw_candidates.values() if str(r.get('account','')).lower()==account.lower() and str(r['game_id']) not in excluded})
    inventory[account]={'validated_eligible_moves':len(ready[account]),'validated_eligible_unique_games':len({r['game_id'] for r in ready[account]}),'categories':category_inventory,
        'draft_target_games':len(selected),'target_shortfall_to20':20-len(selected),'draft_reserve_games':len(reserves),
        'targets_with_primary_control':sum(bool(r['matched_control_draft']) for r in selected),'targets_with_three_control_reserves':sum(len(r['control_reserves'])==3 for r in selected),
        'pending_game_position_cards':pending[account],'pending_unique_games':len({r['game_id'] for r in pending[account]}),
        'all_unexcluded_cached_card_unique_games_upper_bound':cards_upper,'rejected':rejected[account]}
    draft[account]={'targets':selected,'positive_reserves':reserves,'eligible_hash_order_by_category':{cat:sorted([{'game_id':r['game_id'],'ply':r['ply'],'hash':hashlib.sha256(f'{SEED}|{account}|{cat}|{r["game_id"]}|{r["ply"]}'.encode()).hexdigest()} for r in ready[account] if cat in (r['categories'] or ['All Types'])],key=lambda x:x['hash']) for cat in CATEGORIES}}
complete=all(x['draft_target_games']==20 for x in inventory.values())
assert not complete,'If unexpectedly complete, stop for parent review instead of silently expanding this inventory task'
timestamp=datetime.now(timezone.utc).isoformat()
save('QUEUEDRAFT.json',{'status':'INCOMPLETE_OFFLINE_READINESS_ONLY_DO_NOT_COLLECT','created_at_utc':timestamp,'candidate_source_not_chosen_or_frozen':True,
    'requires_new_candidate_source_freeze_before_any_fresh_labels':True,'seed':SEED,'hash_format':'SHA256(seed|account|category|numeric_game_id|one_based_ply)',
    'selection':'Existing PLAN category round robin Queen/Rook/Bishop/Knight/AllTypes; one target/game and canonical-before+UCI unique; preserve unavailable categories.',
    'controls':'Cached unchanged raw-v2 descriptors only; priority rawoffers, quietattacked+defendedpieces, recaptures, othercaptures, otherquiet; then nearesttargetply,ply,UCI. One primarycontrol and at most3reserves, all currentlabels UNKNOWN.',
    'accounts':draft})
save('INVENTORY.json',{'status':'STOPPED_AT_INVENTORY_CACHED_SOURCE_INSUFFICIENT','created_at_utc':timestamp,'goal':'100futureBrilliant+100explicitnon,20/account/class; no currentlabels collected or assumed.',
    'exclusions':{'current439':439,'prior325':325,'all_known_review_game_union':len(excluded),'known_canonical_positions':len(known)},
    'accounts':inventory,'total_draft_positive_targets':sum(x['draft_target_games'] for x in inventory.values()),
    'total_target_shortfall_to100':sum(x['target_shortfall_to20'] for x in inventory.values()),
    'no_new_services_downloads_browser_engine_or_database_framework':True,'monthly_archives_not_rescanned':'No candidate-card source can be conjured from PGNs; at least one account is below20 even under unvalidated-card upper bound. Per instruction, stop inventory without expanded preparation.',
    'no_control_or_target_is_a_confirmed_new_label':True})
save('PROVENANCE.json',{'existing_methods_reused':['validation/corpus.py observed_board/game identity helpers','validation/prepare.py position/account/namespace/FENchecks/category-roundrobinmethod','validation/PLAN.json exclusions and controlselection hierarchy','validation/control-candidates-v2-* unchanged pinned predicate descriptors'],
    'sources':{str(p.relative_to(WORKSPACE)):{'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(source_paths)},
    'script_sha256':sha(pathlib.Path(__file__)),'output_sha256':{n:sha(ROOT/n) for n in ['exclude-games.json','known-position-exclusions.json','QUEUEDRAFT.json','INVENTORY.json']}})
print(json.dumps({'excluded_games':len(excluded),'known_positions':len(known),'accounts':{a:{k:v for k,v in x.items() if k in ['draft_target_games','target_shortfall_to20','draft_reserve_games','pending_unique_games','all_unexcluded_cached_card_unique_games_upper_bound','targets_with_primary_control']} for a,x in inventory.items()}},indent=2))
