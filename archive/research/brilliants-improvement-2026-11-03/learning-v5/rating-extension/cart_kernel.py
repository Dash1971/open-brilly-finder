"""Unchanged depth/minleaf/cost CART kernel from the prespecified semantic diagnostic."""
import numpy as np
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
