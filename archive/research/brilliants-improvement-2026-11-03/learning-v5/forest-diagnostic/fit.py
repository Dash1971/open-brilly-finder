"""Fixed study-local forest capacity diagnostic, reusing the NumPy CART kernel."""
import csv
import hashlib
import json
import math
import os
import re
import resource
import sys
import time
from pathlib import Path
for setting in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','VECLIB_MAXIMUM_THREADS','MKL_NUM_THREADS']:
    os.environ[setting]='1'
sys.dont_write_bytecode=True
sys.path.insert(0,'/private/tmp/mute-research-plot')
import numpy as np

ROOT=Path(__file__).resolve().parent
START=time.monotonic()
PROTOCOL=json.loads((ROOT/'PROTOCOL.json').read_text())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def rss():
    peak=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return peak if sys.platform=='darwin' else peak*1024
def guard():
    if time.monotonic()-START>175:raise RuntimeError('Prespecified180second wall cap: stopped before serialization; no retry')
    if rss()>256*1024*1024:raise RuntimeError('Prespecified256MB peakRSS cap exceeded; stop, no retry')
def write(name,obj):
    (ROOT/name).write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n')

class Tree:
    """Existing cart.py weighted-Gini kernel; fixed forest/minleaf modifications."""
    def __init__(self,X,y,ids,w,names,groups,rng):
        self.X,self.y,self.ids,self.w,self.names,self.groups,self.rng=X,y,ids,w,names,groups,rng
    def leaf(self,ix):
        positive=self.y[ix]
        return {'kind':'leaf','bootstrap_window_rows':len(ix),'distinct_moves':len(np.unique(self.ids[ix])),
            'distinct_groups':len(np.unique(self.groups[ix])),
            'raw_positive_windows':int(positive.sum()),'raw_negative_windows':int((~positive).sum()),
            'raw_p':float(positive.mean()),'weighted_positive':float(self.w[ix][positive].sum()),
            'weighted_negative':float(self.w[ix][~positive].sum())}
    @staticmethod
    def impurity(p,n):return 2*p*n/(p+n)
    def fit(self,ix,depth=0):
        guard()
        leaf=self.leaf(ix)
        parent=self.impurity(leaf['weighted_positive'],leaf['weighted_negative'])
        if depth>=6 or leaf['distinct_moves']<16 or parent==0:return leaf
        best=None;bestgain=1e-12
        for feature in self.rng.choice(self.X.shape[1],size=math.isqrt(self.X.shape[1]),replace=False):
            values=self.X[ix,feature]
            order=np.argsort(np.nan_to_num(values,nan=-np.inf),kind='stable')
            indices=ix[order];v=values[order];n=len(indices)
            if n<16:continue
            p=np.cumsum(self.w[indices]*self.y[indices]);neg=np.cumsum(self.w[indices]*(~self.y[indices]))
            lp=p[:-1];ln=neg[:-1];rp=p[-1]-lp;rn=neg[-1]-ln
            ids=self.ids[indices]
            _,first=np.unique(ids,return_index=True);_,reverse=np.unique(ids[::-1],return_index=True)
            last=n-1-reverse;marks=np.zeros(n,dtype=int);marks[first]=1;leftcases=np.cumsum(marks)[:-1]
            marks[:]=0;marks[last]=1;rightcases=np.cumsum(marks[::-1])[::-1][1:]
            usable=np.isfinite(v[:-1])&np.isfinite(v[1:])&(v[:-1]<v[1:])&(leftcases>=8)&(rightcases>=8)
            if not usable.any():continue
            gains=parent-(self.impurity(lp,ln)+self.impurity(rp,rn));gains[~usable]=-np.inf
            j=int(np.argmax(gains));gain=float(gains[j])
            if gain>bestgain:
                bestgain=gain;best=(int(feature),float(v[j]+(v[j+1]-v[j])/2),indices[:j+1],indices[j+1:])
        if best is None:return leaf
        f,threshold,left,right=best
        return {'kind':'split','feature':self.names[f],'feature_index':f,'threshold':threshold,'missing_goes':'left',
            'weighted_gini_gain':bestgain,'support':leaf,'left':self.fit(left,depth+1),'right':self.fit(right,depth+1)}
    def predict(self,model,ix):
        result=np.empty(len(ix))
        for j,row in enumerate(ix):
            node=model
            while node['kind']=='split':
                value=self.X[row,node['feature_index']]
                node=node['left' if np.isnan(value) or value<=node['threshold'] else 'right']
            result[j]=node['raw_p']
        return result

data=json.loads((ROOT.parent/'features.json').read_text())
assert sha(ROOT.parent/'features.json')==PROTOCOL['input_sha256']
assert sha(ROOT.parent/'cart.py')==PROTOCOL['existing_cart_sha256']
cases,windows=data['cases'],data['window_rows']
base_names=data['predictors'];names=base_names+[n+'__missing' for n in base_names]
assert len(cases)==848 and len(windows)==1696 and len(base_names)==75 and len(names)==150
banned=re.compile(r'(^|_)(game_id|account|rating|elo|label|truth|san|uci|fen|key|date|result|fold|group|baseline|coach|source)(_|$)')
assert not [n for n in names if banned.search(n)]
for i,c in enumerate(cases):
    assert windows[2*i]['key']==windows[2*i+1]['key']==c['key']
    assert windows[2*i]['window']=='current' and windows[2*i+1]['window']=='previous'
    for r in windows[2*i:2*i+2]:
        assert set(r['features'])==set(base_names) and r['group']==c['group'] and r['fold']==c['fold']
        assert all(v is None or isinstance(v,(int,float,bool)) for v in r['features'].values())
for key in ['game_id','group']:
    mapping={}
    for c in cases:assert mapping.setdefault(c[key],c['fold'])==c['fold']
positions={}
for c in cases:assert positions.setdefault(' '.join(c['fen_before'].split()[:4]),c['fold'])==c['fold']
X=np.array([[float(r['features'][n]) if r['features'][n] is not None else np.nan for n in base_names]+
    [float(r['features'][n] is None) for n in base_names] for r in windows])
assert not np.isinf(X).any()
y=np.array([r['truth'] for r in windows],dtype=bool);truth=np.array([c['truth'] for c in cases],dtype=bool)
ids=np.repeat(np.arange(len(cases)),2);folds=np.array([r['fold'] for r in windows]);eligible=np.array([r['eligible'] for r in windows])
case_folds=np.array([c['fold'] for c in cases]);confidence=np.array([c['confidence_sufficient'] for c in cases])
all_groups=sorted({c['group'] for c in cases});group_index={g:i for i,g in enumerate(all_groups)}
groups=np.array([group_index[r['group']] for r in windows]);group_fold={group_index[c['group']]:c['fold'] for c in cases}
eligible_counts=np.bincount(ids[eligible],minlength=len(cases))
weights=np.array([(5 if not y[i] else 1)/max(1,eligible_counts[ids[i]]) for i in range(len(windows))])
guards=eligible.reshape(len(cases),2).all(axis=1)&confidence
model_audit={'trees':0,'leaves':0,'min_leaf_distinct_moves':10**9,'min_leaf_distinct_groups':10**9,'max_depth':0,
    'whole_group_bootstraps_checked':0,'train_test_group_overlaps':0,'identity_feature_count':0}
def inspect(node,depth,importance):
    model_audit['max_depth']=max(model_audit['max_depth'],depth)
    if node['kind']=='leaf':
        assert node['distinct_moves']>=8
        model_audit['leaves']+=1
        model_audit['min_leaf_distinct_moves']=min(model_audit['min_leaf_distinct_moves'],node['distinct_moves'])
        model_audit['min_leaf_distinct_groups']=min(model_audit['min_leaf_distinct_groups'],node['distinct_groups'])
        assert 0<=node['raw_p']<=1
    else:
        assert 0<=node['feature_index']<150 and depth<6
        importance[node['feature_index']]+=node['weighted_gini_gain']
        inspect(node['left'],depth+1,importance);inspect(node['right'],depth+1,importance)
def forest(fold,test):
    train_group_codes=np.array([g for g in range(len(all_groups)) if fold==5 or group_fold[g]!=fold])
    train=np.flatnonzero(eligible&((folds!=fold) if fold!=5 else np.ones(len(windows),bool)))
    test_groups=set(groups[test]);assert fold==5 or not set(groups[train])&test_groups
    probabilities=np.zeros(len(test));trees=[];hashes=[];bootstrap=[];importances=[]
    for number in range(64):
        guard()
        rng=np.random.default_rng(np.random.SeedSequence([20261103,fold,number]))
        draws=rng.choice(train_group_codes,size=len(train_group_codes),replace=True)
        multiplicities=np.bincount(draws,minlength=len(all_groups))
        ix=np.repeat(train,multiplicities[groups[train]])
        actual=np.bincount(ix,minlength=len(windows))
        expected=np.zeros(len(windows),dtype=int);expected[train]=multiplicities[groups[train]]
        assert np.array_equal(actual,expected)
        model_audit['whole_group_bootstraps_checked']+=1
        trainer=Tree(X,y,ids,weights,names,groups,rng);tree=trainer.fit(ix)
        probabilities+=trainer.predict(tree,test)/64
        importance=np.zeros(len(names));inspect(tree,0,importance)
        importances.append(importance/importance.sum() if importance.sum() else importance)
        model_audit['trees']+=1
        hashes.append(hashlib.sha256(json.dumps(tree,sort_keys=True,separators=(',',':')).encode()).hexdigest())
        bootstrap.append(multiplicities.tolist())
        if fold==5:trees.append(tree)
    return probabilities,trees,hashes,bootstrap,np.mean(importances,axis=0)
def metrics(target,pred):
    tp=int(np.sum(target&pred));fn=int(np.sum(target&~pred));fp=int(np.sum(~target&pred));tn=int(np.sum(~target&~pred))
    return {'n':len(target),'TP':tp,'FN':fn,'FP':fp,'TN':tn,'agreement':(tp+tn)/len(target),
        'recall':tp/(tp+fn) if tp+fn else None,'false_award_rate':fp/(fp+tn) if fp+tn else None,
        'sample_precision':tp/(tp+fp) if tp+fp else None,'FN_plus5FP':fn+5*fp}
def auc(target,score):
    p=score[target];n=score[~target]
    return float(((p[:,None]>n).sum()+.5*(p[:,None]==n).sum())/(len(p)*len(n)))
cv=np.zeros(len(windows));bootstrap_plan={};tree_hashes={};fold_importance={}
try:
    for fold in range(5):
        test=np.flatnonzero(folds==fold)
        cv[test],_,hashes,boot,importance=forest(fold,test)
        tree_hashes[str(fold)]=hashes;bootstrap_plan[str(fold)]=boot;fold_importance[str(fold)]=importance.tolist()
        write('PROGRESS.json',{'completed_outer_folds':fold+1,'trees_fitted':model_audit['trees'],'elapsed_seconds':time.monotonic()-START,'peak_rss_bytes':rss()})
        print(json.dumps({'fold':fold,'elapsed_seconds':round(time.monotonic()-START,3),'peak_rss_bytes':rss()}),flush=True)
    full,trees,hashes,boot,importance=forest(5,np.arange(len(windows)))
    tree_hashes['full']=hashes;bootstrap_plan['full']=boot
    raw_cv=cv.reshape(len(cases),2).min(axis=1);raw_full=full.reshape(len(cases),2).min(axis=1)
    guarded_cv=np.where(guards,raw_cv,0.0);guarded_full=np.where(guards,raw_full,0.0)
    results={};predictions=[]
    for point,threshold in [('cost5',5/6),('strict98',.98)]:
        awarded=(cv.reshape(len(cases),2)>=threshold).all(axis=1)&guards
        fitted=(full.reshape(len(cases),2)>=threshold).all(axis=1)&guards
        results[point]={'threshold':threshold,'grouped_outer_cv':metrics(truth,awarded),
            'folds':{str(f):metrics(truth[case_folds==f],awarded[case_folds==f]) for f in range(5)},
            'full_fit_resubstitution_NOT_validation':metrics(truth,fitted)}
        for i,c in enumerate(cases):predictions.append({'key':c['key'],'game_id':c['game_id'],'ply':c['ply'],'san':c['san'],
            'group':c['group'],'fold':c['fold'],'truth':c['truth'],'operating_point':point,
            'cv_current_raw_p':float(cv[2*i]),'cv_previous_raw_p':float(cv[2*i+1]),'cv_case_min_raw_p':float(raw_cv[i]),
            'current_eligible':bool(eligible[2*i]),'previous_eligible':bool(eligible[2*i+1]),'confidence_sufficient':bool(confidence[i]),
            'cv_award':bool(awarded[i]),'full_current_raw_p':float(full[2*i]),'full_previous_raw_p':float(full[2*i+1]),
            'full_fit_award_NOT_validation':bool(fitted[i])})
    model_audit.update(group_components=len(all_groups),game_ids=len({c['game_id'] for c in cases}),normalized_before_positions=len(positions),
        predictor_names=names,minimum_leaf_requirement=8,bootstrap_population_all_training_components=True,
        labels_only_used_as_training_targets=True,identity_account_rating_coach_labels_not_predictors=True,
        same_existing_outer_folds=True,all_trees_depth_at_most6=True)
    collapsed={n:float(importance[i]+importance[i+75]) for i,n in enumerate(base_names)}
    output={'scope':'Capacity diagnostic only: all848 are unblinded development. Grouped outer-fold estimates are not a new independent validation or production-model approval.',
        'protocol_sha256':sha(ROOT/'PROTOCOL.json'),'script_sha256':sha(Path(__file__)),'input_sha256':sha(ROOT.parent/'features.json'),
        'presets':PROTOCOL,'baseline_v4_descriptive':metrics(truth,np.array([c['baseline_v4'] for c in cases])),
        'hard_eligibility_ceiling':metrics(truth,guards),'results':results,
        'AUC':{'grouped_outer_cv_guarded':auc(truth,guarded_cv),'grouped_outer_cv_raw_min_windows':auc(truth,raw_cv),
            'full_fit_guarded_NOT_validation':auc(truth,guarded_full),'full_fit_raw_NOT_validation':auc(truth,raw_full)},
        'elapsed_seconds':round(time.monotonic()-START,3),'peak_rss_bytes':rss()}
    guard()
    write('forest-full.json',{'protocol_sha256':output['protocol_sha256'],'features':names,'trees':trees})
    write('bootstrap-groups.json',{'group_order':all_groups,'multiplicities_by_forest_and_tree':bootstrap_plan,'tree_sha256':tree_hashes})
    write('MODEL-AUDIT.json',model_audit)
    write('feature-importance.json',{'definition':PROTOCOL['importance'],'full_fit_expanded':sorted([{'feature':n,'importance':float(v)} for n,v in zip(names,importance)],key=lambda x:-x['importance']),
        'full_fit_collapsed':sorted([{'feature':n,'importance':v} for n,v in collapsed.items()],key=lambda x:-x['importance']),
        'outer_fold_expanded':fold_importance})
    write('predictions.json',predictions)
    with (ROOT/'predictions.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(predictions[0]));writer.writeheader();writer.writerows(predictions)
    output['elapsed_seconds']=round(time.monotonic()-START,3);output['peak_rss_bytes']=rss()
    assert output['elapsed_seconds']<=180 and output['peak_rss_bytes']<=256*1024*1024
    write('RESULTS.json',output)
    print(json.dumps({'results':results,'AUC':output['AUC'],'elapsed_seconds':output['elapsed_seconds'],'peak_rss_bytes':output['peak_rss_bytes']},indent=2))
except Exception as error:
    write('STOPPED.json',{'reason':str(error),'elapsed_seconds':time.monotonic()-START,'peak_rss_bytes':rss(),'no_retry':True})
    raise
