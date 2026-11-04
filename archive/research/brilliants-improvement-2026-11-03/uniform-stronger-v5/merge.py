#!/usr/bin/env python3
"""Merge only clean uniform-worker/tail windows; never substitute old engine scores."""
import hashlib,json,sys
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,'/private/tmp/brilly-research-deps')
import chess
ROOT=Path(__file__).resolve().parent
read=lambda p:json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
plan=read(ROOT/'PLAN.json');identities=read(ROOT/'primary-moves.json');expected={f"{t['game_id']}:{ply}" for t in identities for ply in range(max(0,t['ply']-2),t['ply']+1)};assert len(expected)==2445
snapshots={};targets={};provenance=[];worker_summaries=[]
for partition in plan['partitions']:
 i=partition['worker'];basepath=ROOT/f'analysis-worker-{i}.json';base=read(basepath);tailpath=ROOT/f'analysis-tail-{i}.json';sources=[(basepath,base)]
 if base['status']!='complete':
  if not tailpath.exists():raise RuntimeError('Stopped worker needs its authorized once-only tail: '+str(i))
  tail=read(tailpath)
  if tail['status']!='complete':raise RuntimeError('Tail incomplete; no old-value substitution allowed')
  if tail['completed_output_sha256']!=sha(basepath):raise RuntimeError('Tail base checkpoint changed')
  assert not set(base['snapshots'])&set(tail['snapshots']);sources.append((tailpath,tail))
 spent=sum(d.get('recorded_search_seconds',0) for p,d in sources);assert spent<=1600
 local=set();boundary=[]
 for path,d in sources:
  assert d['nodes_per_position']==1500000 and d['threads']==1 and d['hash_mb']==64 and d['engine_sha256']==plan['engine']['sha256']
  if d['subset_sha256']!=partition['sha256']:raise RuntimeError('Partition selection changed')
  provenance.append({'file':path.name,'sha256':sha(path),'snapshots':len(d['snapshots']),'recorded_search_seconds':d.get('recorded_search_seconds',0),'status':d['status'],'script_sha256':d['script_sha256'],'tt_restart_boundaries':d.get('tt_restart_boundaries',[])})
  boundary+=d.get('tt_restart_boundaries',[])
  for key,s in d['snapshots'].items():
   assert key in expected and key not in snapshots;board=chess.Board(s['fen']);assert s['quality']=='uniform-development-sf18-1500000'
   for window in ('current','previous'):
    w=s.get(window)
    if w is None:continue
    roots=[l['moves'][0] for l in w['lines'] if l['moves']]
    if not s['terminal']:
     assert len(roots)==min(2,board.legal_moves.count()) and len(set(roots))==len(roots)
     assert all(chess.Move.from_uci(move) in board.legal_moves for move in roots)
   snapshots[key]=s;local.add(key)
  for target in d['targets']:
   key=target['game_id']+':'+str(target['ply'])
   if key in targets:assert targets[key]==target
   else:targets[key]=target
 assert len(local)==partition['snapshots'];worker_summaries.append({'worker':i,'completed_snapshots':len(local),'recorded_search_seconds':spent,'tail_used':len(sources)>1,'partial_game_TT_restarts':sum(bool(x['partial_game_cache_restart']) for x in boundary)})
assert set(snapshots)==expected and len(targets)==848
for identity in identities:
 key=identity['game_id']+':'+str(identity['ply']);t=targets[key];assert t['uci']==identity['uci'] and t['fen_before']==identity['fen_before'] and t['fen_after']==identity['fen_after']
 assert snapshots[t['snapshot_ids'][-2]]['fen']==t['fen_before'] and snapshots[t['snapshot_ids'][-1]]['fen']==t['fen_after']
 for sid in t['snapshot_ids']:assert snapshots[sid]['pgn_sha256']==t['pgn_sha256']
result={'status':'complete','stage':'uniform-stronger-development','nodes_per_position':1500000,'engine_sha256':plan['engine']['sha256'],'threads_per_worker':1,'hash_mb_per_worker':64,'workers':4,'target_count':848,'snapshot_count':2445,'development_only':True,'uniform_requested_node_budget':True,'cache_session_note':'Whole-game clean sessions initially; any once-only tail TT restart boundaries are preserved in source provenance. No claim of identical warm-cache history at those boundaries.','baseline_or_targeted_engine_values_substituted':0,'recorded_search_seconds':sum(x['recorded_search_seconds'] for x in worker_summaries),'worker_summaries':worker_summaries,'source_provenance':provenance,'plan_sha256':sha(ROOT/'PLAN.json'),'targets':sorted(targets.values(),key=lambda t:(t['game_id'],t['ply'])),'snapshots':{k:snapshots[k] for k in sorted(snapshots,key=lambda k:(k.rsplit(':',1)[0],int(k.rsplit(':',1)[1])))}}
assert result['recorded_search_seconds']<=6400
out=ROOT/'analysis-uniform.json';tmp=out.with_suffix('.json.tmp');tmp.write_text(json.dumps(result,indent=2)+'\n');tmp.replace(out);(ROOT/'MERGE-AUDIT.json').write_text(json.dumps({k:v for k,v in result.items() if k not in ('targets','snapshots')},indent=2)+'\n');print(json.dumps({'status':'complete','cases':848,'snapshots':2445,'recorded_search_seconds':result['recorded_search_seconds'],'worker_summaries':worker_summaries}))
