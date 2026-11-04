"""One separate bounded capacity optimization; root hash GO required. No assessment I/O."""
import os
for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','VECLIB_MAXIMUM_THREADS','MKL_NUM_THREADS']:os.environ[k]='1'
import ast,hashlib,json,math,resource,subprocess,sys,time
from pathlib import Path
sys.dont_write_bytecode=True;sys.path.insert(0,'/private/tmp/mute-research-plot');import numpy as np
ROOT=Path(__file__).resolve().parents[1]
KERNEL=ROOT.parent/'brilliants-improvement-2026-11-03/learning-v5/forest-diagnostic/fit.py'
KERNEL_SHA='005050c4c2f9d90178464e007de7112fc77a9f4c2b8bd10c4a8058655c73c18f'
CAPACITY=Path(__file__).with_name('capacity-tree.py');CAPACITY_SHA='4aefb35307853d707f5aac869bac8ce3e0db9706ec92017316341778643d3ae2'
CONFIGS=[{'profile':'baseline','depth':6,'minleaf':8,'mtry':12,'cost':c} for c in [1,3]]+[{'profile':'richer','depth':8,'minleaf':4,'mtry':24,'cost':c} for c in [1,3]]+[{'profile':'baseline','depth':6,'minleaf':8,'mtry':12,'cost':5}]
COSTS=list(range(5));CUTOFFS=[.50,.60,.70,.75,.80,5/6,.85,.90,.95]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def fold_map(groups,n,salt):
 ordered=sorted(set(groups),key=lambda g:(hashlib.sha256((salt+':'+str(g)).encode()).hexdigest(),str(g)))
 return {g:i%n for i,g in enumerate(ordered)}
def choose(records,reference,n_hard):
 budget=min(reference['FP'],math.floor(.005*n_hard))
 feasible=[r for r in records if r['FP']<=budget and r['TP']>=reference['TP'] and r['TP']>0]
 if not feasible:return {'selected':reference,'budget':budget,'feasible_points':0,'fallback':True,'qualifying_improvement':False}
 best=max(feasible,key=lambda r:(r['TP'],-r['FP'],r['cutoff'],r['cost'],-r['depth'],r['minleaf'],-r['mtry']))
 return {'selected':best,'budget':budget,'feasible_points':len(feasible),'fallback':False,'qualifying_improvement':best['TP']>reference['TP'] or best['FP']<reference['FP']}
def main():
 global guard
 input_path,protocol_path,go_path,out=map(Path,sys.argv[1:]);protocol=json.loads(protocol_path.read_text());go=json.loads(go_path.read_text())
 assert go['optimization_authorized'] and go['all_research_browser_tabs_closed']
 assert go['input_sha256']==sha(input_path)==protocol['input_sha256']
 assert go['script_sha256']==sha(__file__) and go['protocol_sha256']==sha(protocol_path)
 assert sha(KERNEL)==KERNEL_SHA==protocol['kernel_sha256']
 assert sha(CAPACITY)==CAPACITY_SHA==protocol['capacity_source_sha256']
 assert protocol['configs']==CONFIGS and protocol['cutoffs']==CUTOFFS and protocol['outer_folds']==5 and protocol['inner_folds']==3
 assert not out.exists();out.mkdir(parents=True)
 start=time.monotonic();cpu_start=time.process_time();last_pressure=0.
 def resource_guard():
  nonlocal last_pressure
  rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform=='darwin' else 1024)
  if time.monotonic()-start>=600 or time.process_time()-cpu_start>=600 or rss>=512*1024*1024 or (ROOT/'STOP').exists():raise RuntimeError('Fixed600s/512MiB/STOP limit; no partial winner or retry')
  if time.monotonic()-last_pressure>=1:
   p=subprocess.run(['sysctl','-n','kern.memorystatus_vm_pressure_level'],capture_output=True,text=True,check=True);last_pressure=time.monotonic()
   if int(p.stdout)!=1:raise RuntimeError('Memory pressure not normal')
 guard=resource_guard
 def write(name,obj):(out/name).write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n')
 try:
  guard();assert subprocess.run(['pgrep','-x','stockfish'],capture_output=True).returncode!=0
  tree_ast=next(n for n in ast.parse(CAPACITY.read_text()).body if isinstance(n,ast.ClassDef) and n.name=='Tree');exec(compile(ast.Module(body=[tree_ast],type_ignores=[]),str(CAPACITY),'exec'),globals())
  data=json.loads(input_path.read_text());cases=data['cases'];base=data['predictors'];names=base+[n+'__missing' for n in base];assert len(cases)==3724 and len(base)==75 and len(names)==150
  assert len({c['key'] for c in cases})==len(cases)
  # The trusted assembly already unions all aliases. Assert no current game or
  # canonical-before identity straddles group components before making folds.
  game_group={};position_group={}
  for c in cases:
   for game in {c['game_id']}|{k.rsplit(':',1)[0] for k in c.get('aliases',[])}:assert game_group.setdefault(game,c['group'])==c['group']
   p=' '.join(c['fen_before'].split()[:4]);assert position_group.setdefault(p,c['group'])==c['group']
   assert type(c['truth']) is bool
  windows=[c['windows'][w] for c in cases for w in ['current','previous']]
  for w in windows:assert set(w['features'])==set(base)
  X=np.array([[float(w['features'][n]) if w['features'][n] is not None else np.nan for n in base]+[float(w['features'][n] is None) for n in base] for w in windows]);assert not np.isinf(X).any()
  truth=np.array([c['truth'] for c in cases],dtype=bool);y=np.repeat(truth,2);ids=np.repeat(np.arange(len(cases)),2)
  eligible=np.array([w['eligible'] for w in windows],dtype=bool);eligible_counts=np.bincount(ids[eligible],minlength=len(cases))
  guards=eligible.reshape(-1,2).all(axis=1)&np.array([c['confidence_sufficient'] for c in cases])&~np.array([any(c['windows'][w]['features']['physical_unknown'] for w in ['current','previous']) for c in cases])
  hard=~truth&np.array([c['negative_bucket']!='easy_error' for c in cases]);easy=~truth&~hard
  group_order=sorted({c['group'] for c in cases});group_index={g:i for i,g in enumerate(group_order)};cg=np.array([group_index[c['group']] for c in cases]);groups=np.repeat(cg,2)
  trees_fitted=0
  def inspect(node,profile,depth=0):
   if node['kind']=='leaf':assert node['distinct_moves']>=profile['minleaf'] and 0<=node['raw_p']<=1
   else:assert depth<profile['depth'] and 0<=node['feature_index']<150;inspect(node['left'],profile,depth+1);inspect(node['right'],profile,depth+1)
  def forest(train_cases,test_cases,cost,seed,keep=False):
   nonlocal trees_fitted
   profile=CONFIGS[cost]
   train_codes=np.unique(cg[train_cases]);assert not set(cg[train_cases])&set(cg[test_cases])
   train=np.flatnonzero(eligible&np.repeat(np.isin(np.arange(len(cases)),train_cases),2));test=np.ravel(np.column_stack([2*test_cases,2*test_cases+1]))
   weights=np.array([(profile['cost'] if not y[i] else 1)/max(1,eligible_counts[ids[i]]) for i in range(len(windows))]);result=np.zeros(len(test));trees=[]
   for number in range(64):
    guard();rng=np.random.default_rng(np.random.SeedSequence([20261103,*seed,number]));draws=rng.choice(train_codes,size=len(train_codes),replace=True);mult=np.bincount(draws,minlength=len(group_order));ix=np.repeat(train,mult[groups[train]])
    assert set(groups[ix])<=set(train_codes) and np.array_equal(np.bincount(ix,minlength=len(windows))[train],mult[groups[train]])
    trainer=Tree(X,y,ids,weights,names,groups,rng,profile['depth'],profile['minleaf'],profile['mtry']);model=trainer.fit(ix);inspect(model,profile);result+=trainer.predict(model,test)/64;trees_fitted+=1
    if keep:trees.append(model)
   return result.reshape(-1,2),trees
  def awards(scores,idx,cutoff):return (scores>=cutoff).all(axis=1)&guards[idx]
  def metrics(pred,idx):
   yy=truth[idx];hh=hard[idx];ee=easy[idx]
   return {'TP':int((pred&yy).sum()),'FN':int((~pred&yy).sum()),'FP':int((pred&hh).sum()),'TN':int((~pred&hh).sum()),'hard_negative_n':int(hh.sum()),'easy_error_FP':int((pred&ee).sum()),'easy_error_TN':int((~pred&ee).sum())}
  def select(predictions,idx):
   records=[{'config':cost,**CONFIGS[cost],'cutoff':cutoff,**metrics(awards(predictions[cost],idx,cutoff),idx)} for cost in COSTS for cutoff in CUTOFFS]
   reference=next(r for r in records if r['config']==4 and r['cutoff']==5/6)
   return {**choose(records,reference,int(hard[idx].sum())),'reference':reference,'points':records}
  all_cases=np.arange(len(cases));outer_map=fold_map(group_order,5,'mute-optimization-v1-outer');outer=np.array([outer_map[c['group']] for c in cases]);outer_pred=np.zeros(len(cases),dtype=bool);outer_ref=np.zeros(len(cases),dtype=bool);outer_records=[]
  for fold in range(5):
   train_cases=all_cases[outer!=fold];test_cases=all_cases[outer==fold];imap=fold_map([cases[i]['group'] for i in train_cases],3,'mute-optimization-v1-inner-'+str(fold));inner=np.array([imap[cases[i]['group']] for i in train_cases]);oof={cost:np.full((len(train_cases),2),np.nan) for cost in COSTS}
   for inner_fold in range(3):
    ti=train_cases[inner!=inner_fold];vi=train_cases[inner==inner_fold]
    for cost in COSTS:oof[cost][inner==inner_fold],_=forest(ti,vi,cost,[10,fold,inner_fold])
   assert all(np.isfinite(v).all() for v in oof.values());selection=select(oof,train_cases);chosen=selection['selected'];preds={}
   for cost in sorted({4,chosen['config']}):preds[cost],_=forest(train_cases,test_cases,cost,[20,fold])
   outer_pred[test_cases]=awards(preds[chosen['config']],test_cases,chosen['cutoff']);outer_ref[test_cases]=awards(preds[4],test_cases,5/6)
   outer_records.append({'fold':fold,'inner_selection':selection,'outer_candidate':metrics(outer_pred[test_cases],test_cases),'outer_reference':metrics(outer_ref[test_cases],test_cases),'test_keys':[cases[i]['key'] for i in test_cases]})
   write('OUTER-PROGRESS.json',{'status':'incomplete_until_all_steps_finish','folds':outer_records,'trees_fitted':trees_fitted})
  # Final selection never consults outer scores. Independent fixed5fold OOF on
  # all training cases provides its own calibration scores for the same rule.
  fmap=fold_map(group_order,5,'mute-optimization-v1-final');final_fold=np.array([fmap[c['group']] for c in cases]);final_oof={cost:np.full((len(cases),2),np.nan) for cost in COSTS}
  for fold in range(5):
   ti=all_cases[final_fold!=fold];vi=all_cases[final_fold==fold]
   for cost in COSTS:final_oof[cost][final_fold==fold],_=forest(ti,vi,cost,[30,fold])
  assert all(np.isfinite(v).all() for v in final_oof.values());final_selection=select(final_oof,all_cases);chosen=final_selection['selected'];_,trees=forest(all_cases,np.array([],dtype=int),chosen['config'],[5],True)
  guard();model={'features':names,'trees':trees};write('forest-candidate.json',model);write('cutoff-config.json',{**CONFIGS[chosen['config']],'threshold_both_windows':chosen['cutoff'],'physical_unknown_abstains':True,'confidence_and_eligibility_required':True})
  write('FINAL-OOF.json',{'selection':final_selection,'rows':[{'key':c['key'],'fold':int(final_fold[i]),'scores':{str(cost):final_oof[cost][i].tolist() for cost in COSTS}} for i,c in enumerate(cases)]})
  report={'scope':'Nested group CV estimates the fixed optimization procedure on training data; no new independent validation or promotion. Seen654 excluded entirely.','outer_pooled':metrics(outer_pred,all_cases),'reference_pooled':metrics(outer_ref,all_cases),'outer_folds':outer_records,'final_selection':final_selection,'trees_fitted':trees_fitted,'elapsed_seconds':time.monotonic()-start,'cpu_seconds':time.process_time()-cpu_start,'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform=='darwin' else 1024)}
  write('RESULTS.json',report);guard();write('FREEZE.json',{'status':'complete','input_sha256':sha(input_path),'protocol_sha256':sha(protocol_path),'script_sha256':sha(__file__),'kernel_sha256':KERNEL_SHA,'capacity_source_sha256':CAPACITY_SHA,'go_sha256':sha(go_path),'model_sha256':sha(out/'forest-candidate.json'),'cutoff_sha256':sha(out/'cutoff-config.json'),'results_sha256':sha(out/'RESULTS.json')});print(json.dumps({k:report[k] for k in ['outer_pooled','reference_pooled','trees_fitted','elapsed_seconds']}))
 except Exception as e:
  for name in ['forest-candidate.json','cutoff-config.json','FREEZE.json']:(out/name).unlink(missing_ok=True)
  write('STOPPED.json',{'reason':str(e),'no_partial_winner':True,'no_automatic_retry':True});raise
if __name__=='__main__':main()
