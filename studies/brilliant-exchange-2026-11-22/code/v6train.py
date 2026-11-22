#!/usr/bin/env python3
"""Train, evaluate and export the v6 model (app-compatible features, depth-12 evidence)."""
import os, pickle, csv, gzip, json, sys, numpy as np, pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import GroupKFold
from sklearn.metrics import precision_recall_curve
import ccjoin
D="../open-brilly-finder/studies/brilliant-selective-2026-11-06/data/"
DEPTH=os.environ.get('DEPTH','12')
def table(prefix):
    d=pickle.load(open(f'{prefix}v6-d{DEPTH}.pkl','rb')); df=pd.DataFrame.from_dict(d,orient='index'); df.index=pd.MultiIndex.from_tuples(df.index,names=['game_id','ply']); return df
def fit(X,y,seed=0):
    return HistGradientBoostingClassifier(max_iter=400,learning_rate=0.05,max_leaf_nodes=31,min_samples_leaf=20,l2_regularization=1.0,random_state=seed).fit(X,y)
def thr_for(y,s,prec):
    p,r,t=precision_recall_curve(y,s); ok=p[:-1]>=prec
    return float(t[np.argmax(r[:-1]*ok)])
def export(m,cols,cutoff,meta):
    trees=[]
    for (p,) in m._predictors:
        n=p.nodes
        trees.append(dict(f=[int(x) for x in n['feature_idx']],t=[float(x) for x in n['num_threshold']],l=[int(x) for x in n['left']],r=[int(x) for x in n['right']],v=[float(x) for x in n['value']],leaf=[int(x) for x in n['is_leaf']]))
    return dict(meta,features=cols,baseline=float(m._baseline_prediction.ravel()[0]),cutoff=cutoff,trees=trees)
def score(model,x):
    raw=model['baseline']
    for t in model['trees']:
        i=0
        while not t['leaf'][i]: i=t['l'][i] if x[t['f'][i]]<=t['t'][i] else t['r'][i]
        raw+=t['v'][i]
    return 1/(1+np.exp(-raw))
if __name__=='__main__':
    Xo=table(''); Xp=table('opp/'); Xd=table('dash/'); cols=list(Xo.columns)
    R=pickle.load(open('moves.pkl','rb')); info={(r['game_id'],r['ply']):r for r in R}
    gal=pd.Series({k:int(info[k]['label']) for k in Xo.index}); gal.index.names=['game_id','ply']
    cc,_=ccjoin.build('moves.pkl'); rev=(cc.cls=='brilliant').astype(int).reindex(Xo.index)
    y=rev.where(rev.notna(),gal.reindex(Xo.index)).astype(int).values; galv=gal.reindex(Xo.index).values
    ccp,_=ccjoin.build('opp/moves.pkl'); revp=(ccp.cls=='brilliant').astype(int).reindex(Xp.index); okp=revp.notna().values
    W={(w['game_id'],int(w['ply'])):w for w in csv.DictReader(gzip.open(D+'witty-all-own-move-outcomes.csv.gz','rt')) if w['primary']=='True'}
    wg={k[0] for k in W}; gid=np.array(Xo.index.get_level_values(0)); test_games=wg&set(cc.index.get_level_values(0))
    key=np.array([' '.join(info[k]['fen_before'].split()[:4])+info[k]['uci'] for k in Xo.index])
    te=np.isin(gid,list(test_games))&np.array([k in W for k in Xo.index]); overlap=np.isin(key,list(set(key[te])))
    tr=~np.isin(gid,list(test_games))&~overlap     # shipped model: everything except the held-out games (other Witty test games without a review stay in)
    og=np.array(Xp.index.get_level_values(0)); om=okp&~np.isin(og,list(test_games))
    Xt=np.vstack([Xo.values[tr],Xp.values[om]]).astype(float); yt=np.concatenate([y[tr],revp.values[om].astype(int)]); gt=np.concatenate([gid[tr],og[om]])
    oof=np.zeros(len(yt))
    for a,b in GroupKFold(5).split(Xt,yt,gt): oof[b]=fit(Xt[a],yt[a]).predict_proba(Xt[b])[:,1]
    m=fit(Xt,yt,0)
    ps=m.predict_proba(Xo.values[te].astype(float))[:,1]
    allrows=cc[cc.index.get_level_values(0).isin(test_games)]
    gal_pos=sum(1 for k,w in W.items() if k[0] in test_games and w['truth']=='True'); rev_pos=int((allrows.cls=='brilliant').sum())
    galt=galv[te]; revt=rev.values[te].astype(int); pub=np.array([W[k]['selective']=='!!' for k in Xo.index[te]])
    out={'depth':DEPTH,'test_games':len(test_games),'gallery_positives':gal_pos,'review_positives':rev_pos,'train_rows':int(len(yt)),'train_positives':int(yt.sum()),'rows':[]}
    def line(name,a,thr=None):
        d=dict(name=name,cutoff=thr,awards=int(a.sum()),found_gallery=int((a&(galt==1)).sum()),false_gallery=int((a&(galt==0)).sum()),found_review=int((a&(revt==1)).sum()),false_review=int((a&(revt==0)).sum()),false_both=int((a&(galt==0)&(revt==0)).sum()))
        out['rows'].append(d); print(f"  {name:34s} awards {d['awards']:4d} | gallery: found {d['found_gallery']} ({d['found_gallery']/gal_pos:.1%}) false {d['false_gallery']} | review: found {d['found_review']} false {d['false_review']} | false by both {d['false_both']}")
    print(f"v6 app-compatible features at depth {DEPTH}: train rows {len(yt)} (positives {int(yt.sum())}); held-out games {len(test_games)}; gallery Brilliants {gal_pos}")
    line('published Mute Selective',pub)
    ths={}
    for prec,nm in ((0.93,'loose'),(0.953,'medium'),(0.97,'strict'),(0.985,'very strict')):
        ths[nm]=thr_for(yt,oof,prec); line(f'v6 {nm} (training precision {prec:.1%})',ps>=ths[nm],ths[nm])
    pdash=m.predict_proba(Xd.values.astype(float))[:,1]; dinfo={(r['game_id'],r['ply']):r for r in pickle.load(open('dash/moves.pkl','rb'))}
    out['dash']=[]
    for k,p in zip(Xd.index,pdash):
        if k in {('tjxdTRho',11),('bJPg3bse',24),('DEFZuyyq',27),('EKJK1jEv',33),('l2M7NFx8',24),('4Qh1Qi9C',46)}:
            out['dash'].append(dict(game=k[0],ply=int(k[1]),san=dinfo[k]['san'],score=float(p),medium=bool(p>=ths['medium']))); print(f"   Dash {k[0]} {dinfo[k]['san']:7s} score {p:.3f} medium: {'YES' if p>=ths['medium'] else 'no'}")
    out['cutoffs']=ths
    if DEPTH=='12':
        model=export(m,cols,ths['medium'],dict(name='mute-brilliant-v6',trained='2026-11-22',learner='sklearn HistGradientBoostingClassifier 400x31',evidence='Stockfish 18, fixed 200k-node searches capped at depth 12'))
        json.dump(model,open('v6-model.json','w'),separators=(',',':'))
        # exported scorer must equal sklearn
        chk=np.array([score(model,x) for x in Xo.values[te][:300].astype(float)]); print('export max abs diff vs sklearn:',float(np.abs(chk-ps[:300]).max()),'| model bytes',os.path.getsize('v6-model.json'))
        pickle.dump(dict(index=Xo.index[te],ps=ps,gal=galt,rev=revt,pub=pub,ths=ths,oof=oof,yt=yt),open('v6-preds.pkl','wb'))
    json.dump(out,open(f'v6-results-d{DEPTH}.json','w'),indent=1)
