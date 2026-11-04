"""One authorized frozen training batch; existing SF18 search/extractor, no fitting."""
import sys,io,json,time,hashlib,importlib.util,subprocess,datetime,os
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];RESEARCH=ROOT.parent
KERNEL=RESEARCH/'brilliants-prospective-v7-2026-11-03/adapter/sf18-collect.py'
KERNEL_SHA='c3b923604b99481100d6da620cdf11689494b579520e7f8186235bc856cfc1bd'
EXTRACTOR=RESEARCH/'brilliants-improvement-2026-11-03/astra/v5/fresh-extractor'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,d):
 tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(d,indent=2,allow_nan=False)+'\n');tmp.replace(p)
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
queue=Path(sys.argv[1]);expected=sys.argv[2];name=sys.argv[3]
if sha(queue)!=expected or sha(KERNEL)!=KERNEL_SHA:raise ValueError('Frozen queue/kernel hash mismatch')
if '/' in name or not name.startswith('batch-'):raise ValueError('Invalid local batch name')
output=ROOT/'engine-batches'/name;output.mkdir(exist_ok=False)
plan=json.loads((ROOT/'PLAN.json').read_text());deadline=datetime.datetime.fromisoformat(plan['deadline_utc'].replace('Z','+00:00')).timestamp()
freeze=json.loads((EXTRACTOR/'FREEZE.json').read_text())
for p,h in freeze['sha256'].items():
 if sha(p)!=h:raise ValueError('Frozen extractor dependency changed:'+p)
spec=importlib.util.spec_from_file_location('frozen_search',KERNEL);kernel=importlib.util.module_from_spec(spec);spec.loader.exec_module(kernel)
import chess,chess.engine,chess.pgn
sys.path.insert(0,str(EXTRACTOR));import extractor
batch=json.loads(queue.read_text());games={str(g['game_id']):g for g in batch['games']};targets=batch['targets']
if not targets or any(t.get('split')!='training' for t in targets):raise ValueError('TRAINING-only targets required')
if any(g.get('split')!='training' for g in games.values()):raise ValueError('Assessment game forbidden')
if len({(str(t['game_id']),int(t['ply'])) for t in targets})!=len(targets):raise ValueError('Duplicate targets')
if sha(kernel.ENGINE)!=kernel.ENGINE_SHA:raise ValueError('Engine binary changed')
existing=subprocess.run(['pgrep','-x','stockfish'],capture_output=True,text=True)
if existing.returncode==0:raise ValueError('Other Stockfish process active; stop')
started=time.monotonic();last_pressure=0.;pressure=None
base_guard=kernel.guard
def guard():
 global last_pressure,pressure
 base_guard()
 if time.time()>=deadline or (ROOT/'STOP').exists():raise TimeoutError('Deadline or parent STOP')
 if time.monotonic()-last_pressure>=1:
  result=subprocess.run(['sysctl','-n','kern.memorystatus_vm_pressure_level'],capture_output=True,text=True)
  if result.returncode:raise RuntimeError('Cannot verify memory pressure')
  pressure=int(result.stdout.strip());last_pressure=time.monotonic()
  if pressure!=1:raise TimeoutError('Memory pressure not normal:'+str(pressure))
kernel.guard=guard;kernel.ROOT=ROOT;kernel.START=started
receipt={'authorized_scope':'Root authorized one training-only600-second batch; no model fit','queue_sha256':expected,'script_sha256':sha(__file__),'kernel_sha256':sha(KERNEL),'extractor_freeze_sha256':sha(EXTRACTOR/'FREEZE.json'),'plan_sha256':sha(ROOT/'PLAN.json'),'deadline_utc':plan['deadline_utc'],'created_at_utc':now()};write(output/'INPUT-FREEZE.json',receipt)
result={'status':'running','started_at':now(),'engine_sha256':kernel.ENGINE_SHA,'nodes_per_position':300000,'threads':1,'hash_mb':64,'source_queue_sha256':expected,'targets':[],'snapshots':{},'session_policy':'One process; clearHash/new session pergame; chronological requested positions with fullPGN history.'};write(output/'analysis.json',result)
engine=None
try:
 guard();engine=chess.engine.SimpleEngine.popen_uci(kernel.ENGINE);engine.configure({'Threads':1,'Hash':64});result['engine_id']=engine.id
 for gid in sorted(games):
  selected=[t for t in targets if str(t['game_id'])==gid]
  if not selected:continue
  g=games[gid];pgn=g['pgn'];pgnsha=hashlib.sha256(pgn.encode()).hexdigest()
  if pgnsha!=g['pgn_sha256']:raise ValueError('PGN hash mismatch:'+gid)
  game=chess.pgn.read_game(io.StringIO(pgn))
  if game is None or game.errors:raise ValueError('Invalid PGN:'+gid)
  wanted={p for t in selected for p in range(max(0,int(t['ply'])-2),int(t['ply'])+1)};board=game.board();boards={0:board.copy(stack=True)};moves={}
  for ply,move in enumerate(game.mainline_moves(),1):
   before=board.fen();san=board.san(move);board.push(move);moves[ply]={'san':san,'uci':move.uci(),'fen_before':before,'fen_after':board.fen()}
   if ply in wanted:boards[ply]=board.copy(stack=True)
  for t in selected:
   for k in ['san','uci','fen_before','fen_after']:
    if t.get(k)!=moves[int(t['ply'])][k]:raise ValueError('Target identity mismatch:'+gid+':'+str(t['ply'])+':'+k)
  engine.configure({'Clear Hash':None});session=object()
  for ply in sorted(wanted):
   s=kernel.search(engine,boards[ply],300000,session);s.update(game_id=gid,position_ply=ply,fen=boards[ply].fen(),pgn_sha256=pgnsha);result['snapshots'][f'{gid}:{ply}']=s;result['recorded_search_seconds']=kernel.SEARCH_SPENT;write(output/'analysis.json',result)
  for t in selected:result['targets'].append({**t,'snapshot_ids':[f'{gid}:{p}' for p in range(max(0,int(t['ply'])-2),int(t['ply'])+1)]})
 result['status']='complete'
except Exception as e:result.update(status='incomplete',reason=str(e))
finally:
 if engine:engine.quit()
 result.update(completed_at=now(),recorded_search_seconds=kernel.SEARCH_SPENT,wall_seconds=time.monotonic()-started);write(output/'analysis.json',result)
if result['status']!='complete':print(json.dumps({'status':result['status'],'reason':result.get('reason')}));sys.exit(1)
rows=[];feature_status='running'
try:
 for offset in range(0,len(result['targets']),16):
  guard();ts=result['targets'][offset:offset+16];requests=[{'pgn':games[str(t['game_id'])]['pgn'],'ply':int(t['ply']),'snapshots':[result['snapshots'][k] for k in t['snapshot_ids']]} for t in ts]
  cases=extractor.extract_batch(requests);model=json.loads(extractor.MODEL_PATH.read_text())
  for t,c in zip(ts,cases):rows.append({'key':str(t['game_id'])+':'+str(t['ply']),'split':'training','features':c,'forest':extractor.score_fixed_forest(c,model)})
  write(output/'features.json',{'status':'running','rows':rows})
 feature_status='complete'
except Exception as e:feature_status='incomplete';result['feature_failure']=str(e)
write(output/'features.json',{'status':feature_status,'rows':rows,'failure':result.get('feature_failure')})
summary={'status':feature_status,'games':len(games),'targets':len(targets),'snapshots':len(result['snapshots']),'feature_cases':len(rows),'eligible_both':sum(all(r['features']['windows'][w]['eligible'] for w in ['current','previous']) for r in rows),'baseline_awards':sum(r['forest']['award'] for r in rows),'physical_unknown':sum(r['features']['windows']['current']['features']['physical_unknown'] for r in rows),'engine_seconds':kernel.SEARCH_SPENT,'total_seconds':time.monotonic()-started,'analysis_sha256':sha(output/'analysis.json'),'features_sha256':sha(output/'features.json')};write(output/'SUMMARY.json',summary);print(json.dumps(summary))
