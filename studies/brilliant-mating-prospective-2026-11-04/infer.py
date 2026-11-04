"""Bounded prospective inference only. Exact fixed forest and mating exception; no labels."""
import ast,collections,hashlib,importlib.util,io,json,math,sys,time
from pathlib import Path
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;W=H.parents[1]
sys.path.insert(0,'/private/tmp/brilly-research-deps');sys.path.insert(0,str(W/'research/brilliants-improvement-2026-11-03/astra/v5/fresh-extractor'))
import chess,chess.engine,chess.pgn
import extractor
from base_rule import mating_rule
from nonmate_extract import extract_case
START=time.monotonic();SEARCH_SPENT=0.;ACTIVE_SEARCH=None

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,v):(H/n).write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
def guard():
 if time.monotonic()-START>=900:raise TimeoutError('Frozen900second inference cap; no retry')
def loadmodule(name,p):
 spec=importlib.util.spec_from_file_location(name,p);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod

def main():
 freeze=json.loads((H/'CANDIDATE-FREEZE.json').read_text());receipt=json.loads((H/'RUN-FREEZE.json').read_text())
 for path,digest in receipt['source_sha256'].items():assert sha(Path(path))==digest
 for path,digest in freeze['artifact_sha256'].items():assert sha(H/path)==digest
 for path,digest in json.loads((W/'research/brilliants-improvement-2026-11-03/astra/v5/fresh-extractor/FREEZE.json').read_text())['sha256'].items():assert sha(Path(path))==digest
 assert not (H/'SCORED.json').exists()
 source=W/'research/brilliants-prospective-v7-2026-11-03/adapter/sf18-collect.py'
 funcs=[n for n in ast.parse(source.read_text()).body if isinstance(n,ast.FunctionDef) and n.name in ['packed','search']]
 exec(compile(ast.Module(body=funcs,type_ignores=[]),str(source),'exec'),globals())
 pv=loadmodule('qualify_pv',W/'research/brilliants-training-overnight-2026-11-03/adapter/augment-pv.py')
 mined=json.loads((H/'MINED.json').read_text());targets=mined['candidates']
 order=lambda c:(hashlib.sha256(('mute-mating-prospective-case-20261104:'+c['game_id']+':'+str(c['ply'])).encode()).hexdigest(),c['game_id'],c['ply'])
 targets=sorted(targets,key=order)[:400];model=json.loads((H/'forest.json').read_text());cutoff=freeze['forest_threshold'];rows=[];searches=0;reason=None
 sf=chess.engine.SimpleEngine.popen_uci('/opt/homebrew/bin/stockfish');sf.configure({'Threads':1,'Hash':64})
 def snapshot(board):
  nonlocal searches
  guard();sf.configure({'Clear Hash':None});ss=search(sf,board,300000,object());ss['fen']=board.fen();searches+=1;return ss
 try:
  for i,c in enumerate(targets):
   guard();g=chess.pgn.read_game(io.StringIO(c['pgn']));assert g and not g.errors
   b=g.board();boards={0:b.copy(stack=True)}
   for ply,m in enumerate(g.mainline_moves(),1):
    b.push(m)
    if ply in [c['ply']-2,c['ply']-1,c['ply']]:boards[ply]=b.copy(stack=True)
    if ply==c['ply']:break
   before,after=boards[c['ply']-1],boards[c['ply']]
   assert before.fen()==c['fen_before'] and after.fen()==c['fen_after'] and after.peek().uci()==c['uci']
   snaps=[snapshot(boards[p]) for p in [c['ply']-2,c['ply']-1,c['ply']]]
   f=extractor.extract_batch([{'pgn':c['pgn'],'ply':c['ply'],'snapshots':snaps}])[0]
   scores=extractor.score_fixed_forest(f,model)['window_scores']
   eligible=f['confidence_sufficient'] and all(f['windows'][w]['eligible'] and not f['windows'][w]['features']['physical_unknown'] for w in ['current','previous'])
   baseline=eligible and min(scores.values())>=cutoff;rule=mating_rule(f);offers=[];material=None;detail=None
   if rule:
    qq,unknown,_=pv.qualify(before,after)
    if not unknown:
     assert len(qq)<=4
     for u in sorted(qq):
      a=after.copy(stack=True);a.push_uci(u);offers.append({'uci':u,'accepted_fen':a.fen(),'snapshot':snapshot(a)})
     material,detail=extract_case(before,after,offers)
   extra=rule and material is not None and all(material[w]['nonmate_material_win']==0 for w in ['current','previous'])
   rows.append({**c,'key':c['game_id']+':'+str(c['ply']),'snapshots':snaps,'features':f,'window_scores':scores,'eligible':bool(eligible),'base_rule':bool(rule),'acceptance_evidence':offers,'material_features':material,'material_diagnostics':detail,'baseline_award':bool(baseline),'candidate_award':bool(baseline or extra),'refined_rule':bool(extra),'new_award':bool(extra and not baseline)})
   if len(rows)%10==0:
    write('INFERENCE-PROGRESS.json',{'completed':len(rows),'total':len(targets),'searches':searches,'new_awards':sum(r['new_award'] for r in rows),'base_rule':sum(r['base_rule'] for r in rows),'elapsed_seconds':time.monotonic()-START})
    print(json.dumps({'completed':len(rows),'searches':searches,'new_awards':sum(r['new_award'] for r in rows),'elapsed':round(time.monotonic()-START,1)}),flush=True)
 except TimeoutError as e:reason=str(e)
 finally:sf.quit()
 write('SCORED.json',{'status':'partial' if reason else 'complete','reason':reason,'rows':rows,'expected':len(targets),'searches':searches,'elapsed_seconds':time.monotonic()-START,'candidate_freeze_sha256':sha(H/'CANDIDATE-FREEZE.json'),'run_freeze_sha256':sha(H/'RUN-FREEZE.json')})
 # One target per whole game across both strata, no targetposition duplicates.
 usedgames=set();usedpos=set();positives=[]
 for c in rows:
  pos=' '.join(c['fen_before'].split()[:4])
  if c['new_award'] and c['game_id'] not in usedgames and pos not in usedpos and len(positives)<12:
   positives.append(c);usedgames.add(c['game_id']);usedpos.add(pos)
 pool=[c for c in rows if not c['candidate_award']]
 def distance(c,anchor):
  a=c['features']['windows']['current']['features'];b=anchor['features']['windows']['current']['features']
  cat=sum(a[n]!=b[n] for n in ['move_capture','move_check','offered_role_q','offered_piece_moved'])
  num=sum(abs((a[n] or 0)-(b[n] or 0))/scale for n,scale in [('best_mapped_score',100),('best_second_gap_pp',10),('prior_mapped_score',100)])
  return (not c['base_rule'],cat,num,order(c))
 controls=[]
 for j in range(12):
  available=[c for c in pool if c['game_id'] not in usedgames and ' '.join(c['fen_before'].split()[:4]) not in usedpos]
  if not available:break
  anchor=positives[j%len(positives)] if positives else available[0]
  c=min(available,key=lambda x:distance(x,anchor));controls.append(c);usedgames.add(c['game_id']);usedpos.add(' '.join(c['fen_before'].split()[:4]))
 queued=[{k:c[k] for k in ['key','game_id','ply','uci','san','fen_before','fen_after','pgn','baseline_award','candidate_award','new_award','base_rule','refined_rule','material_features']}|{'stratum':'new_award' if c['new_award'] else 'near_control'} for c in positives+controls]
 write('REVIEW-QUEUE.json',{'scope':'Predictions and queue frozen before Chess.com labels; all queued observations retained','rows':queued,'candidate_freeze_sha256':sha(H/'CANDIDATE-FREEZE.json'),'scored_sha256':sha(H/'SCORED.json')})
 write('PRELABEL-FREEZE.json',{'created_at_unix':time.time(),'sha256':{f:sha(H/f) for f in ['CANDIDATE-FREEZE.json','INPUTS.json','MINED.json','infer.py','RUN-FREEZE.json','SCORED.json','REVIEW-QUEUE.json']},'new_award_targets':len(positives),'near_control_targets':len(controls),'labels_read':0})
 print(json.dumps({'status':'queue_frozen','completed_cases':len(rows),'new_award_targets':len(positives),'near_control_targets':len(controls),'elapsed_seconds':time.monotonic()-START}),flush=True)
if __name__=='__main__':main()
