#!/usr/bin/env python3
"""One fixed depth-four feature extension; no new searches or configuration grid."""
import csv,json,resource,sys,time
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,'/private/tmp/mute-research-plot')
import numpy as np
from cart_kernel import Tree,metrics,rules,case_prediction
ROOT=Path(__file__).resolve().parent
started=time.monotonic();data=json.loads((ROOT/'features.json').read_text());cases=data['cases'];windows=data['window_rows'];names=data['predictors'];names=names+[n+'__missing' for n in names]
X=np.array([[float(r['features'][n]) if r['features'][n] is not None else np.nan for n in data['predictors']]+[float(r['features'][n] is None) for n in data['predictors']] for r in windows]);y=np.array([r['truth'] for r in windows]);truth=np.array([c['truth'] for c in cases]);ids=np.repeat(np.arange(len(cases)),2);folds=np.array([r['fold'] for r in windows]);eligible=np.array([r['eligible'] for r in windows]);counts=np.bincount(ids[eligible],minlength=len(cases));weights=np.array([(5 if not y[i] else 1)/max(1,counts[ids[i]]) for i in range(len(windows))]);points=('default_cost5','strict98');all_predictions=[];summary={};trees={};fold_models={}
# Audit grouping before any model sees labels.
for key in ('game_id','group'):
 mapping={}
 for c in cases:
  assert mapping.setdefault(c[key],c['fold'])==c['fold']
positions={}
for c in cases:
 f=' '.join(c['fen_before'].split()[:4]);assert positions.setdefault(f,c['fold'])==c['fold']
for depth in (4,):
 spec=f'depth{depth}';cv={p:np.zeros(len(windows),dtype=bool) for p in points};fold_models[spec]={}
 for fold in range(5):
  trainer=Tree(X,y,ids,weights,names,depth);train=np.flatnonzero(eligible&(folds!=fold));test=np.flatnonzero(folds==fold);model=trainer.fit(train);fold_models[spec][str(fold)]=model
  for point in points:cv[point][test]=trainer.predict(model,test,point)
 trainer=Tree(X,y,ids,weights,names,depth);full=trainer.fit(np.flatnonzero(eligible));trees[spec]=full;summary[spec]={}
 for point in points:
  predicted=case_prediction(cv[point],windows,cases);resub=case_prediction(trainer.predict(full,np.arange(len(windows)),point),windows,cases);summary[spec][point]={'grouped_cv':metrics(truth,predicted),'folds':{str(fold):metrics(truth[np.array([c['fold']==fold for c in cases])],predicted[np.array([c['fold']==fold for c in cases])]) for fold in range(5)},'full_fit_resubstitution_only':metrics(truth,resub)}
  for i,c in enumerate(cases):all_predictions.append({'key':c['key'],'game_id':c['game_id'],'ply':c['ply'],'san':c['san'],'group':c['group'],'fold':c['fold'],'truth':c['truth'],'model':spec,'operating_point':point,'cv_award':bool(predicted[i]),'cv_current':bool(cv[point][2*i]),'cv_previous':bool(cv[point][2*i+1]),'current_eligible':windows[2*i]['eligible'],'previous_eligible':windows[2*i+1]['eligible'],'full_fit_award_NOT_validation':bool(resub[i])})
 (ROOT/(spec+'-rules.txt')).write_text('Full-data descriptive fit; not held-out performance.\n'+'\n'.join(rules(full))+'\n')
eligible_cases=case_prediction(np.ones(len(windows),dtype=bool),windows,cases);baseline=np.array([c['baseline_v4'] for c in cases]);output={'scope':'All848 unblinded development. One authorized depth4 shallow-surprise feature extension; unchanged folds/guards, no winner selection or independent-test claim.','training_cases':len(cases),'window_rows':len(windows),'features':len(names),'folds':5,'minimum_leaf_distinct_cases':15,'negative_weight':5,'strict_operating_point':'RAW unweighted leaf fraction >=0.98, not weighted/calibrated probability.','baseline_v4_descriptive':metrics(truth,baseline),'hard_eligibility_ceiling':metrics(truth,eligible_cases),'results':summary,'elapsed_seconds':round(time.monotonic()-started,3),'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
for name,obj in [('RESULTS.json',output),('trees-full.json',trees),('trees-folds.json',fold_models),('predictions.json',all_predictions)]: (ROOT/name).write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n')
with (ROOT/'predictions.csv').open('w') as stream:
 writer=csv.DictWriter(stream,fieldnames=list(all_predictions[0]));writer.writeheader();writer.writerows(all_predictions)
assert output['peak_rss_bytes']<256*1024*1024
print(json.dumps(output,indent=2))
