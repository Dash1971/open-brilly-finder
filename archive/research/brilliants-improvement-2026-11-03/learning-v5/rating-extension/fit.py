#!/usr/bin/env python3
"""One rating predictor, two fixed evaluation schemes; no model/capacity search."""
import csv,collections,hashlib,json,resource,sys,time
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,'/private/tmp/mute-research-plot')
import numpy as np
from cart_kernel import Tree,metrics,rules,case_prediction
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent;ACCOUNTS=('nelsi','hansen','KNVB','GothamChess','Hikaru');POINTS=('default_cost5','strict98')
def load(p):return json.loads(p.read_text())
def metric(y,p):return metrics(y,p) if len(y) else {'n':0,'TP':0,'FN':0,'FP':0,'TN':0,'agreement':None,'recall':None,'false_award_rate':None,'sample_precision':None,'FN_plus5FP':0}
start=time.monotonic();data=load(ROOT/'features.json');protocol=load(ROOT/'PROTOCOL.json');assert hashlib.sha256((BASE/'features.json').read_bytes()).hexdigest()==protocol['base_feature_sha256'];cases=data['cases'];windows=data['window_rows'];y=np.array([r['truth'] for r in windows]);truth=np.array([c['truth'] for c in cases]);ids=np.repeat(np.arange(len(cases)),2);eligible=np.array([r['eligible'] for r in windows]);folds=np.array([r['fold'] for r in windows]);account=np.array([c['account'] for c in cases]);row_account=np.repeat(account,2);groups=np.array([r['group'] for r in windows]);casegroups=np.array([c['group'] for c in cases]);cohort=np.array([c['cohort'] for c in cases]);counts=np.bincount(ids[eligible],minlength=len(cases));weights=np.array([(5 if not y[i] else 1)/max(1,counts[ids[i]]) for i in range(len(windows))]);baseline_rows=load(BASE/'predictions.json');results={};models={'group_cv':{},'leave_one_account_out':{},'full_fit_rating':None};predictions=[];training_audit=[];fit_count=0
for feature_set in ('original75','plus_rating'):
 predictors=data['predictors_original75' if feature_set=='original75' else'predictors_plus_rating'];names=predictors+[n+'__missing' for n in predictors];X=np.array([[float(r['features'][n]) if r['features'][n] is not None else np.nan for n in predictors]+[float(r['features'][n] is None) for n in predictors] for r in windows]);results[feature_set]={}
 for scheme in ('group_cv','leave_one_account_out'):
  cv={p:np.zeros(len(windows),dtype=bool) for p in POINTS};models[scheme][feature_set]={}
  if scheme=='group_cv' and feature_set=='original75':
   for point in POINTS:
    saved={r['key']:r for r in baseline_rows if r['model']=='depth4' and r['operating_point']==point}
    for i,c in enumerate(cases):cv[point][2*i]=saved[c['key']]['cv_current'];cv[point][2*i+1]=saved[c['key']]['cv_previous']
  else:
   for held in (range(5) if scheme=='group_cv' else ACCOUNTS):
    if scheme=='group_cv':test=folds==held;train=eligible&(folds!=held)
    else:
     test=row_account==held;heldgroups=set(groups[test]);train=eligible&(row_account!=held)&~np.isin(groups,list(heldgroups))
    assert not set(groups[train])&set(groups[test]);trainer=Tree(X,y,ids,weights,names,4);model=trainer.fit(np.flatnonzero(train));fit_count+=1;models[scheme][feature_set][str(held)]=model
    for point in POINTS:cv[point][test]=trainer.predict(model,np.flatnonzero(test),point)
    training_audit.append({'feature_set':feature_set,'scheme':scheme,'held_out':str(held),'train_eligible_window_rows':int(train.sum()),'train_distinct_cases':len(set(ids[train])),'test_cases':len(set(ids[test])),'train_test_group_overlap':0})
  results[feature_set][scheme]={}
  for point in POINTS:
   pred=case_prediction(cv[point],windows,cases);partitions={}
   for part in ('all848','core818','panel30'):
    mask=np.ones(len(cases),dtype=bool) if part=='all848' else cohort==part
    partitions[part]=metric(truth[mask],pred[mask])
   by_account={}
   for a in ACCOUNTS:
    by_account[a]={}
    for part in ('all848','core818','panel30'):
     mask=(account==a)&(np.ones(len(cases),dtype=bool) if part=='all848' else cohort==part);by_account[a][part]=metric(truth[mask],pred[mask])
   results[feature_set][scheme][point]={'partitions':partitions,'by_account':by_account}
   for i,c in enumerate(cases):predictions.append({'key':c['key'],'game_id':c['game_id'],'ply':c['ply'],'san':c['san'],'account_AUDIT_ONLY':c['account'],'cohort_AUDIT_ONLY':c['cohort'],'mover_rating':c['mover_rating'],'group':c['group'],'group_fold':c['fold'],'feature_set':feature_set,'scheme':scheme,'operating_point':point,'truth':c['truth'],'award':bool(pred[i]),'current_tree_positive':bool(cv[point][2*i]),'prior_tree_positive':bool(cv[point][2*i+1]),'current_eligible':windows[2*i]['eligible'],'prior_eligible':windows[2*i+1]['eligible']})
 if feature_set=='plus_rating':
  trainer=Tree(X,y,ids,weights,names,4);model=trainer.fit(np.flatnonzero(eligible));fit_count+=1;models['full_fit_rating']=model;resub={}
  for point in POINTS:resub[point]=metric(truth,case_prediction(trainer.predict(model,np.arange(len(windows)),point),windows,cases))
  (ROOT/'full-rating-rules.txt').write_text('Full-data descriptive fit, not held-out performance.\n'+'\n'.join(rules(model))+'\n')
assert fit_count==16
output={'scope':'848already-unblindeddevelopment cases. Fixed grouped CV and leave-one-account-out diagnostics; no independent-validation, causal rating-effect or beginner-curve claim.','model':protocol['model'],'feature_sets':protocol['feature_sets'],'metrics':results,'full_rating_resubstitution_NOT_validation':resub,'new_training_runs':fit_count,'grouped_original75_reused_without_refit':True,'training_audit':training_audit,'elapsed_seconds':round(time.monotonic()-start,3),'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
for name,x in [('RESULTS.json',output),('trees.json',models),('predictions.json',predictions)]: (ROOT/name).write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
with (ROOT/'predictions.csv').open('w') as f:
 writer=csv.DictWriter(f,fieldnames=list(predictions[0]));writer.writeheader();writer.writerows(predictions)
assert output['peak_rss_bytes']<256*1024*1024
print(json.dumps({'metrics':{a:{b:{p:v['partitions'] for p,v in points.items()} for b,points in schemes.items()} for a,schemes in results.items()},'runs':fit_count,'elapsed_seconds':output['elapsed_seconds'],'peak_rss_bytes':output['peak_rss_bytes']},indent=2))
