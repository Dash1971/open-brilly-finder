#!/usr/bin/env python3
"""Two fixed small CART diagnostics with whole-game/position grouped CV. No ML dependency."""
import csv,hashlib,json,resource,sys,time
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,'/private/tmp/mute-research-plot')
import numpy as np
ROOT=Path(__file__).resolve().parent
class Tree:
 """Weighted-Gini CART; fixed missing-left convention, min15distinct cases per leaf."""
 def __init__(self,X,y,case_ids,weights,names,depth):self.X=X;self.y=y;self.ids=case_ids;self.w=weights;self.names=names;self.depth=depth
 def leaf(self,ix):
  positive=self.y[ix];p=float(self.w[ix][positive].sum());n=float(self.w[ix][~positive].sum());rawp=int(positive.sum());rawn=len(ix)-rawp
  return {'kind':'leaf','window_rows':len(ix),'distinct_cases':len(np.unique(self.ids[ix])),'raw_positive_windows':rawp,'raw_negative_windows':rawn,'raw_positive_fraction':rawp/len(ix),'weighted_positive_support':p,'weighted_negative_support':n,'default_positive':p>n,'strict_positive':rawp/len(ix)>=.98,'positive_leaf_training_cost':n,'negative_leaf_training_cost':p}
 @staticmethod
 def impurity(p,n):return 2*p*n/(p+n)
 def fit(self,ix,depth=0):
  leaf=self.leaf(ix);parent=self.impurity(leaf['weighted_positive_support'],leaf['weighted_negative_support'])
  if depth>=self.depth or leaf['distinct_cases']<30 or parent==0:return leaf
  best=None;bestgain=1e-12
  for feature in range(self.X.shape[1]):
   values=self.X[ix,feature];order=np.argsort(np.nan_to_num(values,nan=-np.inf),kind='stable');indices=ix[order];v=values[order];n=len(indices)
   if n<30:continue
   p=np.cumsum(self.w[indices]*self.y[indices]);neg=np.cumsum(self.w[indices]*(~self.y[indices]));lp=p[:-1];ln=neg[:-1];rp=p[-1]-lp;rn=neg[-1]-ln
   ids=self.ids[indices];_,first=np.unique(ids,return_index=True);_,reverse=np.unique(ids[::-1],return_index=True);last=n-1-reverse;marks=np.zeros(n,dtype=int);marks[first]=1;leftcases=np.cumsum(marks)[:-1];marks[:]=0;marks[last]=1;rightcases=np.cumsum(marks[::-1])[::-1][1:]
   usable=np.isfinite(v[:-1])&np.isfinite(v[1:])&(v[:-1]<v[1:])&(leftcases>=15)&(rightcases>=15)
   if not usable.any():continue
   gains=parent-(self.impurity(lp,ln)+self.impurity(rp,rn));gains[~usable]=-np.inf;j=int(np.argmax(gains));gain=float(gains[j])
   if gain>bestgain:bestgain=gain;best=(feature,float(v[j]+(v[j+1]-v[j])/2),indices[:j+1],indices[j+1:])
  if best is None:return leaf
  f,threshold,left,right=best
  return {'kind':'split','feature':self.names[f],'feature_index':f,'threshold':threshold,'missing_goes':'left','weighted_gini_gain':bestgain,'support':leaf,'left':self.fit(left,depth+1),'right':self.fit(right,depth+1)}
 def predict(self,model,ix,point):
  result=[]
  for row in ix:
   node=model
   while node['kind']=='split':
    value=self.X[row,node['feature_index']];node=node['left' if np.isnan(value) or value<=node['threshold'] else 'right']
   result.append(node['strict_positive' if point=='strict98' else 'default_positive'])
  return np.array(result,dtype=bool)

def metrics(y,pred):
 tp=int(np.sum(y&pred));fn=int(np.sum(y&~pred));fp=int(np.sum(~y&pred));tn=int(np.sum(~y&~pred));return {'n':len(y),'TP':tp,'FN':fn,'FP':fp,'TN':tn,'agreement':(tp+tn)/len(y),'recall':tp/(tp+fn) if tp+fn else None,'false_award_rate':fp/(fp+tn) if fp+tn else None,'sample_precision':tp/(tp+fp) if tp+fp else None,'FN_plus5FP':fn+5*fp}
def rules(node,prefix=''):
 if node['kind']=='leaf':return [prefix+f"LEAF: {node['raw_positive_windows']} Brilliant / {node['raw_negative_windows']} other window rows; {node['distinct_cases']} distinct moves; raw positive fraction={node['raw_positive_fraction']:.4f}; weighted positive={node['weighted_positive_support']:.2f}, negative={node['weighted_negative_support']:.2f}; cost5={node['default_positive']}, strict98={node['strict_positive']}"]
 return [prefix+f"IF {node['feature']} is missing OR <= {node['threshold']:.8g}:"]+rules(node['left'],prefix+'  ')+[prefix+'ELSE:']+rules(node['right'],prefix+'  ')
def case_prediction(window_prediction,windows,cases):
 pred=window_prediction.reshape(len(cases),2);eligible=np.array([r['eligible'] for r in windows]).reshape(len(cases),2);confidence=np.array([c['confidence_sufficient'] for c in cases]);return pred.all(axis=1)&eligible.all(axis=1)&confidence
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
for depth in (3,4):
 spec=f'depth{depth}';cv={p:np.zeros(len(windows),dtype=bool) for p in points};fold_models[spec]={}
 for fold in range(5):
  trainer=Tree(X,y,ids,weights,names,depth);train=np.flatnonzero(eligible&(folds!=fold));test=np.flatnonzero(folds==fold);model=trainer.fit(train);fold_models[spec][str(fold)]=model
  for point in points:cv[point][test]=trainer.predict(model,test,point)
 trainer=Tree(X,y,ids,weights,names,depth);full=trainer.fit(np.flatnonzero(eligible));trees[spec]=full;summary[spec]={}
 for point in points:
  predicted=case_prediction(cv[point],windows,cases);resub=case_prediction(trainer.predict(full,np.arange(len(windows)),point),windows,cases);summary[spec][point]={'grouped_cv':metrics(truth,predicted),'folds':{str(fold):metrics(truth[np.array([c['fold']==fold for c in cases])],predicted[np.array([c['fold']==fold for c in cases])]) for fold in range(5)},'full_fit_resubstitution_only':metrics(truth,resub)}
  for i,c in enumerate(cases):all_predictions.append({'key':c['key'],'game_id':c['game_id'],'ply':c['ply'],'san':c['san'],'group':c['group'],'fold':c['fold'],'truth':c['truth'],'model':spec,'operating_point':point,'cv_award':bool(predicted[i]),'cv_current':bool(cv[point][2*i]),'cv_previous':bool(cv[point][2*i+1]),'current_eligible':windows[2*i]['eligible'],'previous_eligible':windows[2*i+1]['eligible'],'full_fit_award_NOT_validation':bool(resub[i])})
 (ROOT/(spec+'-rules.txt')).write_text('Full-data descriptive fit; not held-out performance.\n'+'\n'.join(rules(full))+'\n')
eligible_cases=case_prediction(np.ones(len(windows),dtype=bool),windows,cases);baseline=np.array([c['baseline_v4'] for c in cases]);output={'scope':'All848 are unblinded development. Grouped CV is a diagnostic, not a new independent test. Two presets, no winner selection.','training_cases':len(cases),'window_rows':len(windows),'features':len(names),'folds':5,'minimum_leaf_distinct_cases':15,'negative_weight':5,'strict_operating_point':'RAW unweighted leaf fraction >=0.98, not weighted/calibrated probability.','baseline_v4_descriptive':metrics(truth,baseline),'hard_eligibility_ceiling':metrics(truth,eligible_cases),'results':summary,'elapsed_seconds':round(time.monotonic()-started,3),'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
for name,obj in [('RESULTS.json',output),('trees-full.json',trees),('trees-folds.json',fold_models),('predictions.json',all_predictions)]: (ROOT/name).write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n')
with (ROOT/'predictions.csv').open('w') as stream:
 writer=csv.DictWriter(stream,fieldnames=list(all_predictions[0]));writer.writeheader();writer.writerows(all_predictions)
assert output['peak_rss_bytes']<256*1024*1024
print(json.dumps(output,indent=2))
