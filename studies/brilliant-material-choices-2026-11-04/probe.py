"""Bounded known-case material choice diagnostic; no classification or refitting."""
import sys,ast,hashlib,io,json,signal,time,importlib.util
from pathlib import Path
from datetime import datetime,timezone
sys.dont_write_bytecode=True
sys.path.insert(0,'/private/tmp/brilly-research-deps')
import chess,chess.engine,chess.pgn
H=Path(__file__).resolve().parent
SOURCE=H.parent/'brilliant-mating-mechanisms-2026-11-04/CASES.json'
AUGMENT=H.parent/'brilliants-training-overnight-2026-11-03/adapter/augment-pv.py'
COLLECTOR=H.parent/'brilliants-prospective-v7-2026-11-03/adapter/sf18-collect.py'
ENGINE=Path('/opt/homebrew/bin/stockfish')
ENGINE_SHA='ae4c93fa9676ca7750d0714342fd8a5b1d018000fc6e0f6cedf112067b5ef374'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def now():return datetime.now(timezone.utc).isoformat()
def write(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def guard(*args):
 if args or time.monotonic()-START>=300:raise TimeoutError('Frozen300 second total cap; no retries')
def detail(b,info):
 score=info['score'].white();kind='mate' if score.is_mate() else 'cp';value=score.mate() if score.is_mate() else score.score();a=b.copy(stack=True);sans=[];ucis=[];fens=[];invalid=None
 for m in info['pv']:
  if m not in a.legal_moves:invalid=m.uci();break
  sans.append(a.san(m));ucis.append(m.uci());a.push(m);fens.append(a.fen())
 return {'score_white':{kind:value},'score_mover':{kind:value*(1 if b.turn else -1)},'moves':ucis,'san':' '.join(sans),'fen_after_each_ply':fens,'pv_plies':len(ucis),'pv_end_fen':a.fen(),'pv_end_terminal':a.is_game_over(claim_draw=False),'pv_end_result':a.result(claim_draw=False) if a.is_game_over(claim_draw=False) else None,'pv_invalid_move':invalid,'pv_horizon_caveat':'A finite nonterminal PV is truncated evidence; no invented later outcome.','root_uci':ucis[0] if ucis else None,'root_san':sans[0] if sans else None}
def search(engine,b,count,roots=None):
 guard();engine.configure({'Clear Hash':None});pending=[];completed=[];start=time.monotonic()
 with engine.analysis(b,chess.engine.Limit(nodes=3000000),multipv=count,root_moves=roots,game=object()) as stream:
  for info in stream:
   guard()
   if not all(k in info for k in ('score','pv','depth')) or not info['pv'] or info.get('upperbound') or info.get('lowerbound'):continue
   rank=info.get('multipv',1)
   if rank!=len(pending)+1:pending=[]
   if rank!=len(pending)+1 or info['pv'][0] not in b.legal_moves:continue
   if roots is not None and info['pv'][0] not in roots:raise ValueError('Root constraint violated')
   pending.append(info)
   if rank==count:
    if len({x['depth'] for x in pending})==1 and len({x['pv'][0] for x in pending})==count:
     snap={'depth':pending[0]['depth'],'reported_nodes':pending[-1].get('nodes'),'lines':[detail(b,x) for x in pending]}
     if not completed or snap['depth']>completed[-1]['depth']:completed.append(snap);completed=completed[-2:]
     else:completed[-1]=snap
    pending=[]
 return {'status':'complete' if completed else 'no_complete_window','current':completed[-1] if completed else None,'previous':completed[-2] if len(completed)>1 else None,'elapsed_seconds':time.monotonic()-start,'multipv':count,'nodes_limit':3000000,'root_moves':None if roots is None else [m.uci() for m in roots]}
def main():
 global START
 if (H/'PROTOCOL.json').exists() or (H/'CHOICES.json').exists():raise ValueError('Refuse overwrite or retry')
 assert sha(ENGINE)==ENGINE_SHA
 spec=importlib.util.spec_from_file_location('choice_augment',AUGMENT);aug=importlib.util.module_from_spec(spec);spec.loader.exec_module(aug)
 deps={str(Path(m.__file__).resolve()):sha(m.__file__) for m in list(sys.modules.values()) if getattr(m,'__file__',None) and str(m.__file__).endswith('.py') and ('research/' in str(m.__file__) or 'brilly-research-deps' in str(m.__file__))}
 deps[str(aug.fk.pk.mp.__file__)]=sha(aug.fk.pk.mp.__file__)
 cases=json.loads(SOURCE.read_text());assert len(cases)==19
 protocol={'frozen_at':now(),'purpose':'Known-case material choices diagnostic only; preserve contradictions; no new rule, classification, refit, rating analysis or validation claim.','case_keys':[c['key'] for c in cases],'input_path':str(SOURCE),'input_sha256':sha(SOURCE),'script_sha256':sha(__file__),'engine_path':str(ENGINE),'engine_sha256':ENGINE_SHA,'dependency_sha256':deps,'qualifier_source_sha256':sha(AUGMENT),'collector_reference_sha256':sha(COLLECTOR),'python':sys.version,'threads':1,'hash_mb':64,'nodes_per_query':3000000,'maximum_queries':57,'total_wall_cap_seconds':300,'retry_policy':'No retries, no threshold tuning. Save unknown/incomplete evidence.','history':'Reconstruct exact full original PGN history; verify before and after FEN and played move. Fresh UCI game token and Clear Hash for every query.','query_order':['unrestricted before MultiPV=min(4,legal move count)','before restricted to no immediate offer roots, MultiPV1, unless rootset empty','before played-only MultiPV1 if actual move absent from current unrestricted top4, or current window unknown'],'snapshot_method':'Small local implementation of collector same-depth complete-window logic generalized to count and root_moves; retain last two complete depth windows.','rootset':'All legal roots tested using original augment-pv.qualify(before,after). No immediate offer means no qualifying profitable immediate nonpawn capture; unknown qualifier roots excluded and explicitly recorded. This does not guarantee preservation: checks may postpone a threat.','qualifier':'Opponent legal nonpawn/nonking captures: net same-square exchange gain > immediate mover material credit +100; original512-node offer budget.','score':'White and mover oriented cp or mate, no forced cp conversion for mates; contexts differ across unrestricted and constrained searches.','pv':'Full returned legal SAN/UCI PV and per-ply FEN, terminal status. Finite nonterminal lines remain truncated, not material outcome claims.'}
 write(H/'PROTOCOL.json',protocol)
 START=time.monotonic();signal.signal(signal.SIGALRM,guard);signal.alarm(300)
 out={'status':'running','started_at':now(),'protocol_sha256':sha(H/'PROTOCOL.json'),'queries_started':0,'queries_completed':0,'cases':[]};engine=None
 try:
  for c in cases:
   guard();g=chess.pgn.read_game(io.StringIO(c['pgn']));assert g and not g.errors;b=g.board();played=None
   for ply,m in enumerate(g.mainline_moves(),1):
    if ply==int(c['ply']):before=b.copy(stack=True);played=m;b.push(m);after=b.copy(stack=True);break
    b.push(m)
   assert played and played.uci()==c['uci'] and before.fen()==c['fen_before'] and after.fen()==c['fen_after']
   roots=[]
   for m in sorted(before.legal_moves,key=lambda m:m.uci()):
    guard();a=before.copy(stack=True);san=a.san(m);a.push(m);offers,unknown,nodes=aug.qualify(before,a)
    roots.append({'uci':m.uci(),'san':san,'fen_after':a.fen(),'qualifier_unknown':unknown,'qualifier_nodes':nodes,'qualifying_offers':offers,'no_immediate_offer':not offers and not unknown})
   out['cases'].append({'key':c['key'],'group':c['group'],'played_uci':played.uci(),'played_san':before.san(played),'mover':c['mover'],'fen_before':before.fen(),'fen_after':after.fen(),'pgn_sha256':hashlib.sha256(c['pgn'].encode()).hexdigest(),'before_history_uci':[m.uci() for m in before.move_stack],'legal_roots':roots,'no_immediate_offer_roots':[r['uci'] for r in roots if r['no_immediate_offer']],'qualifier_unknown_roots':[r['uci'] for r in roots if r['qualifier_unknown']]})
  write(H/'CHOICES.json',out)
  engine=chess.engine.SimpleEngine.popen_uci(str(ENGINE));engine.configure({'Threads':1,'Hash':64});out['engine_id']=engine.id
  for c,row in zip(cases,out['cases']):
   guard();g=chess.pgn.read_game(io.StringIO(c['pgn']));b=g.board()
   for u in row['before_history_uci']:b.push_uci(u)
   def query(name,count,roots=None):
    guard();assert out['queries_started']<57;out['queries_started']+=1;row[name]={'status':'started'};write(H/'CHOICES.json',out);row[name]=search(engine,b,count,roots);out['queries_completed']+=1;write(H/'CHOICES.json',out)
   query('unrestricted',min(4,b.legal_moves.count()))
   safe=[chess.Move.from_uci(u) for u in row['no_immediate_offer_roots']]
   if safe:query('no_immediate_offer_best',1,safe)
   else:row['no_immediate_offer_best']={'status':'empty_rootset','current':None,'previous':None}
   current=row['unrestricted'].get('current');actual=next((l for l in current['lines'] if l['root_uci']==row['played_uci']),None) if current else None
   if actual:row['played_only']={'status':'not_needed_actual_in_current_top4','current_unrestricted_rank':next(i+1 for i,l in enumerate(current['lines']) if l['root_uci']==row['played_uci'])}
   else:query('played_only',1,[chess.Move.from_uci(row['played_uci'])])
   write(H/'CHOICES.json',out)
  out['status']='complete'
 except Exception as e:out.update(status='incomplete',reason=repr(e))
 finally:
  signal.alarm(0)
  if engine:engine.close()
  out.update(completed_at=now(),wall_seconds=time.monotonic()-START);write(H/'CHOICES.json',out)
 print(json.dumps({k:out[k] for k in ['status','queries_started','queries_completed','wall_seconds']}))
if __name__=='__main__':main()
