"""Study-only annotated-PGN/UI import. No browser, network, engine or fitting."""
from pathlib import Path
import hashlib,io,json,re,sqlite3,sys
from datetime import datetime,timezone
from urllib.parse import urlparse,parse_qs
sys.path.insert(0,'/private/tmp/brilly-research-deps');import chess,chess.pgn
ROOT=Path(__file__).resolve().parent;DB=ROOT/'dataset.sqlite3'
NAGS={1:'great',2:'mistake',3:'brilliant',4:'blunder',6:'inaccuracy',9:'miss'}
ALIASES={'!!':'brilliant','!':'great','?':'mistake','??':'blunder','?!':'inaccuracy'}
EASY={'mistake','blunder','inaccuracy','miss'};HARD={'great','best','excellent','good','interesting'}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();load=lambda p:json.loads(p.read_text());now=lambda:datetime.now(timezone.utc).isoformat();canon=lambda f:' '.join(chess.Board(f).fen().split()[:4])
def label(value):
 t=str(value or '').strip();t=ALIASES.get(t,t.lower());t=re.sub(r'^(?:is |a |an |the )','',t);t=re.sub(r' move[!.]*$','',t).strip().rstrip('!.')
 if t in {'brilliant','great','mistake','blunder','inaccuracy','miss','best','excellent','good','interesting','book','forced'}:return t
 raise ValueError('Unrecognized explicit UI label '+str(value))
def ui_san(text):
 # Chess.com SVG badges can prepend CSS style-node text to selected SAN.
 # Strip only recognized cls-N CSS rules; never accept an arbitrary suffix.
 return re.sub(r'\.cls-\d+\{[^{}]*\}', '', str(text or '')).strip()
def pieces(fen):return sorted(('w'if p.color else'b')+p.symbol().lower()+':'+str(chess.square_file(s)+1)+str(chess.square_rank(s)+1)for s,p in chess.Board(fen).piece_map().items())
def parse(pgn):
 game=chess.pgn.read_game(io.StringIO(pgn));assert game and not game.errors,'Invalid PGN';b=game.board();rows=[]
 for ply,node in enumerate(game.mainline(),1):
  before=b.fen();san=b.san(node.move);uci=node.move.uci();b.push(node.move);after=b.fen();rows.append({'ply':ply,'san':san,'uci':uci,'fen_before':before,'fen_after':after,'before_key':canon(before),'after_key':canon(after),'nags':sorted(node.nags)})
 return game,rows
def main():
 queues={}
 for p in sorted(ROOT.glob('queue-*.json')):
  for g in load(p).get('games',[]):
   if g['game_id']in queues:assert queues[g['game_id']]['pgn_sha256']==g['pgn_sha256']and queues[g['game_id']]['split']==g['split']
   queues[g['game_id']]=g
 epath=ROOT/'ASSESSMENT-POSITION-EXCLUSIONS.json';known=set(load(epath)['canonical_first_four'])if epath.exists()else set(load(ROOT/'EXCLUSIONS-FIRST-WAVE.json')['known_canonical_before_after'])
 cx=sqlite3.connect(DB);cx.execute('pragma foreign_keys=on');cx.executescript('''
 CREATE TABLE IF NOT EXISTS games(game_id TEXT PRIMARY KEY,source_account TEXT,split TEXT,pgn TEXT,pgn_sha256 TEXT,review_pgn TEXT,export_sha256 TEXT,headers_json TEXT,total_plies INTEGER,source_link TEXT,imported_at TEXT,complete_file TEXT,complete_sha256 TEXT,checks_sha256 TEXT);
 CREATE TABLE IF NOT EXISTS positions(game_id TEXT,ply INTEGER,san TEXT,uci TEXT,fen_before TEXT,fen_after TEXT,before_key TEXT,after_key TEXT,nags_json TEXT,PRIMARY KEY(game_id,ply));
 CREATE TABLE IF NOT EXISTS observations(id TEXT PRIMARY KEY,game_id TEXT,ply INTEGER,label TEXT,source_type TEXT,source_file TEXT,source_sha256 TEXT,captured_at TEXT,source_url TEXT,rendered_board_verified INTEGER,evidence_json TEXT);
 CREATE TABLE IF NOT EXISTS labels(game_id TEXT,ply INTEGER,label TEXT,is_brilliant INTEGER,negative_bucket TEXT,source_account TEXT,mover TEXT,mover_rating INTEGER,split TEXT,dataset_use TEXT,example_key TEXT,rendered_board_verified INTEGER,source_types TEXT,PRIMARY KEY(game_id,ply));
 CREATE TABLE IF NOT EXISTS quarantines(game_id TEXT,reason TEXT,detail TEXT,created_at TEXT,PRIMARY KEY(game_id,reason));
 CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY,value TEXT);
 CREATE TABLE IF NOT EXISTS game_strata(game_id TEXT PRIMARY KEY,source_kind TEXT,sampling_version TEXT);
 CREATE INDEX IF NOT EXISTS observations_game_ply ON observations(game_id,ply);
 CREATE INDEX IF NOT EXISTS labels_example ON labels(example_key);
 CREATE INDEX IF NOT EXISTS labels_use ON labels(dataset_use);
 ''');cx.execute('insert or ignore into metadata values(?,?)',('plan_initial_sha256',sha(ROOT/'PLAN.json')));cx.execute('insert or replace into metadata values(?,?)',('plan_sha256',sha(ROOT/'PLAN.json')));cx.execute('insert or replace into metadata values(?,?)',('SAN_normalization','Only recognized SVG cls-N CSS rules and surrounding whitespace removed for exact SAN comparison; raw observations remain unchanged.'));cx.execute('insert or replace into metadata values(?,?)',('nag_mapping',json.dumps(NAGS,sort_keys=True)))
 new=[]
 complete_files=list(ROOT.glob('collector-*/*-complete.json'))
 for candidate in ROOT.glob('collector-b/*.json'):
  meta=load(candidate)
  if isinstance(meta,dict) and meta.get('completed_at') and meta.get('all_export_brilliants_UI_verified') and meta.get('all_planned_UI_checks_complete'):complete_files.append(candidate)
 for complete in sorted(complete_files):
  metadata=load(complete);embedded='UI_verifications' in metadata
  gid=str(metadata.get('game_id') or complete.name.removesuffix('-complete.json'));export=complete.with_name(gid+'.review-export.pgn' if embedded else gid+'-export.pgn');checksfile=complete if embedded else complete.with_name(gid+'-checks.json')
  try:
   assert gid in queues,'No frozen queue identity';g=queues[gid];old=cx.execute('select export_sha256,complete_sha256,checks_sha256 from games where game_id=?',(gid,)).fetchone();hashes=(sha(export),sha(complete),sha(checksfile))
   if old:
    assert tuple(old)==hashes,'Completed source changed after import';continue
   official,positions=parse(g['pgn']);review,rpos=parse(export.read_text());assert official.board().fen()==review.board().fen()and[(p['san'],p['uci'],p['fen_after'])for p in positions]==[(p['san'],p['uci'],p['fen_after'])for p in rpos],'Export/official mainline mismatch';checks=metadata['UI_verifications'] if embedded else load(checksfile);by={p['ply']:p for p in positions};ui={}
   for check in checks:
    raw_check=check
    if embedded:
     tokens=[]
     for text in check.get('pieces',[]):
      piece=re.search(r'([wb][prnbqk])',text);square=re.search(r'square-([1-8][1-8])',text)
      if piece and square:tokens.append(piece.group(1)+':'+square.group(1))
     check={**check,'raw_verification':raw_check,'observed':{'label':check.get('ui_label',check.get('displayed_label_text')),'pieces':tokens,'selected_data_node':check.get('selected_node'),'selected_san':check.get('selected_text')},'source_url':check.get('observed_url')}
    ply=int(check['ply']);p=by[ply];o=check.get('observed',check.get('raw_observed',{}));assert str(check.get('game_id',gid))==gid
    assert check.get('uci',p['uci'])==p['uci']and check.get('fen_after',p['fen_after'])==p['fen_after']
    assert o.get('selected_data_node')==f'0-{ply-1}'and ui_san(o.get('selected_san'))==p['san'],'Selected node/SAN mismatch'
    assert sorted(o.get('pieces',[]))==pieces(p['fen_after']),'Rendered board mismatch';url=check.get('source_url',check.get('source_link',''));assert re.search(r'/'+g['game_namespace']+'/'+gid+r'(?:/|\?|$)',url),'Source game namespace/ID mismatch'
    ui.setdefault(ply,[]).append((label(o['label']),check))
   for p in rpos:
    mapped={NAGS[n]for n in p['nags']if n in NAGS}
    if 'brilliant'in mapped:assert any(l=='brilliant'for l,c in ui.get(p['ply'],[])),'Export Brilliant lacks individual visible verification'
   cx.execute('savepoint onegame')
   cx.execute('insert into games values(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(gid,g['account'],g['split'],g['pgn'],g['pgn_sha256'],export.read_text(),hashes[0],json.dumps(dict(official.headers)),len(positions),g['review_url'],now(),str(complete.relative_to(ROOT)),hashes[1],hashes[2]))
   for p,rp in zip(positions,rpos):
    cx.execute('insert into positions values(?,?,?,?,?,?,?,?,?)',(gid,p['ply'],p['san'],p['uci'],p['fen_before'],p['fen_after'],p['before_key'],p['after_key'],json.dumps(rp['nags'])))
    for n in rp['nags']:
     if n not in NAGS:continue
     evidence={'nag':n,'method_check':'method-check/visible-label-checks.json','individual_UI_verified':False,'official_pgn_sha256':g['pgn_sha256']};ident=f'{gid}:{p["ply"]}:nag:{n}:{hashes[0]}'
     cx.execute('insert into observations values(?,?,?,?,?,?,?,?,?,?,?)',(ident,gid,p['ply'],NAGS[n],'explicit_review_export_NAG',str(export.relative_to(ROOT)),hashes[0],load(complete).get('captured_at',load(complete).get('completed_at',now())),g['review_url'],0,json.dumps(evidence)))
    for k,(l,c)in enumerate(ui.get(p['ply'],[])):
     ident=f'{gid}:{p["ply"]}:ui:{k}:{hashes[2]}'
     cx.execute('insert into observations values(?,?,?,?,?,?,?,?,?,?,?)',(ident,gid,p['ply'],l,'visible_Game_Review',str(checksfile.relative_to(ROOT)),hashes[2],c.get('captured_at'),c.get('source_url',c.get('source_link')),1,json.dumps(c,ensure_ascii=False)))
   cx.execute('release onegame');cx.execute('delete from quarantines where game_id=?',(gid,));cx.commit();new.append(gid)
  except Exception as error:
   try:cx.execute('rollback to onegame');cx.execute('release onegame')
   except sqlite3.OperationalError:pass
   cx.execute('insert or replace into quarantines values(?,?,?,?)',(gid,'source_identity_or_validation',str(error),now()));cx.commit()
 for gid,source_kind in cx.execute('select game_id,source_account from games').fetchall():
  q=queues[gid];cx.execute('insert or replace into game_strata values(?,?,?)',(gid,q.get('source_kind','gallery_nomination'),q.get('control_sampling_version','See immutable per-game control evidence and sampling amendment')))
 # Labels deduplicate agreeing source observations; conflicting explicit labels never override.
 cx.execute('delete from labels');cx.row_factory=sqlite3.Row
 for g in cx.execute('select * from games').fetchall():
  h=json.loads(g['headers_json']);positions={p['ply']:dict(p)for p in cx.execute('select * from positions where game_id=?',(g['game_id'],))}
  grouped={}
  for obs in cx.execute('select * from observations where game_id=?',(g['game_id'],)):grouped.setdefault(obs['ply'],[]).append(dict(obs))
  for ply,obs in grouped.items():
   p=positions[ply];labels={o['label']for o in obs};l=next(iter(labels))if len(labels)==1 else'CONFLICT';turn=chess.Board(p['fen_before']).turn;mover=h.get('White'if turn else'Black');rating=h.get('WhiteElo'if turn else'BlackElo');rating=int(rating)if rating and rating.isdigit()else None;use='quarantine_conflict'if l=='CONFLICT'else g['split'];example=hashlib.sha256((p['before_key']+'\n'+p['uci']).encode()).hexdigest()
   if use=='assessment'and(p['before_key']in known or p['after_key']in known):use='exclude_assessment_known_position'
   cx.execute('insert into labels values(?,?,?,?,?,?,?,?,?,?,?,?,?)',(g['game_id'],ply,l,None if l=='CONFLICT' else int(l=='brilliant'),'easy_error'if l in EASY else'hard_ordinary'if l in HARD else'other_explicit'if l!='brilliant'else'positive',g['source_account'],mover,rating,g['split'],use,example,max(o['rendered_board_verified']for o in obs),json.dumps(sorted({o['source_type']for o in obs}))))
 # Cross-game identical examples cannot leak from new training into assessment.
 cx.execute("update labels set dataset_use='quarantine_position_binary_conflict' where example_key in(select example_key from labels where is_brilliant is not null group by example_key having min(is_brilliant)<>max(is_brilliant))")
 cx.execute("update labels set dataset_use='quarantine_game_source' where game_id in(select game_id from quarantines)")
 cx.execute("update labels set dataset_use='exclude_assessment_training_overlap' where dataset_use='assessment'and example_key in(select example_key from labels where dataset_use='training')")
 cx.execute("update labels set dataset_use='exclude_assessment_training_position' where dataset_use='assessment' and exists(select 1 from positions a where a.game_id=labels.game_id and a.ply=labels.ply and(a.before_key in(select p.before_key from labels l join positions p using(game_id,ply)where l.dataset_use='training') or a.before_key in(select p.after_key from labels l join positions p using(game_id,ply)where l.dataset_use='training') or a.after_key in(select p.before_key from labels l join positions p using(game_id,ply)where l.dataset_use='training') or a.after_key in(select p.after_key from labels l join positions p using(game_id,ply)where l.dataset_use='training')))")
 cx.commit();count=lambda sql:cx.execute(sql).fetchone()[0]
 summary={'updated_at':now(),'newly_imported_games':new,'games':count('select count(*)from games'),'game_split_counts':dict(cx.execute('select split,count(*)from games group by split')),'source_strata_game_counts':dict(cx.execute('select source_kind,count(*)from game_strata group by source_kind')),'source_strata_label_counts':dict(cx.execute('select s.source_kind,count(*)from labels l join game_strata s using(game_id)group by s.source_kind')),'explicit_unique_game_ply_labels':count('select count(*)from labels'),'unambiguous_unique_game_ply_labels':count("select count(*)from labels where label<>'CONFLICT'"),'brilliant':count("select count(*)from labels where label='brilliant'"),'hard_ordinary_negatives':count("select count(*)from labels where negative_bucket='hard_ordinary'"),'easy_error_negatives':count("select count(*)from labels where negative_bucket='easy_error'"),'other_explicit_negatives':count("select count(*)from labels where negative_bucket='other_explicit' and label<>'CONFLICT'"),'conflicting_game_ply_labels':count("select count(*)from labels where label='CONFLICT'"),'label_counts':dict(cx.execute('select label,count(*)from labels group by label')),'dataset_use_counts':dict(cx.execute('select dataset_use,count(*)from labels group by dataset_use')),'individual_rendered_board_verified_labels':count('select count(*)from labels where rendered_board_verified=1'),'observations':count('select count(*)from observations'),'unknown_unannotated_positions':count('select count(*)from positions where not exists(select 1 from labels where labels.game_id=positions.game_id and labels.ply=positions.ply)'),'duplicate_position_move_labels':count('select count(*)from labels')-count('select count(distinct example_key)from labels'),'quarantines':[dict(x)for x in cx.execute('select *from quarantines')],'scope':'Explicit export NAGs use validated method mapping; every Brilliant must have its own UI board check. Unannotated positions are unknown. No model eligibility/experimental usefulness has been computed.','database':'dataset.sqlite3'}
 (ROOT/'COUNTS.json').write_text(json.dumps(summary,indent=2)+'\n');cx.close();print(json.dumps({k:v for k,v in summary.items()if k not in ['quarantines','label_counts','scope']},indent=2))
if __name__=='__main__':main()
