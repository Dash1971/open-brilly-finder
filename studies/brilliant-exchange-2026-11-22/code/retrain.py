#!/usr/bin/env python3
"""Retrain on Chess.com's fresh review labels (where available) and evaluate on held-out Witty test games against both standards."""
import os, pickle, csv, gzip, sys, json, numpy as np, pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import GroupKFold
from sklearn.metrics import precision_recall_curve
from m2 import load
import ccjoin
D="../open-brilly-finder/studies/brilliant-selective-2026-11-06/data/"
DROP={'label','elo','elo_diff','clk','spent','tc_base','ply'}
def feats(prefix=''):
    base=load(prefix+('feats-d%s.pkl'%os.environ['DEPTH'] if os.environ.get('DEPTH') else 'feats.pkl')); base=base[base.hang_see>=2]
    parts=[base[[c for c in base.columns if c not in DROP]]]+[load(prefix+f'feats{k}.pkl').reindex(base.index) for k in (2,4,5,6)]
    X=pd.concat(parts,axis=1); X=X.loc[:,~X.columns.duplicated()]; X.index.names=['game_id','ply']
    return X, base.label.rename_axis(['game_id','ply'])
def fit(X,y,seed=0):
    return HistGradientBoostingClassifier(max_iter=400,learning_rate=0.05,max_leaf_nodes=31,min_samples_leaf=20,l2_regularization=1.0,random_state=seed).fit(X,y)
def thr_for(y,s,prec):
    p,r,t=precision_recall_curve(y,s); ok=p[:-1]>=prec
    return float(t[np.argmax(r[:-1]*ok)]) if ok.any() else 1.0
if __name__=='__main__':
    Xo,gal=feats('')                               # own moves (gallery accounts)
    cc,_=ccjoin.build('moves.pkl'); rev=(cc.cls=='brilliant').astype(int)
    own=pd.DataFrame({'gal':gal.astype(int)}).join(rev.rename('rev'))
    own['y']=own.rev.where(own.rev.notna(),own.gal).astype(int); own['has_rev']=own.rev.notna()
    Xp=None
    if os.path.exists('opp/feats6.pkl'):
        Xp,_=feats('opp/'); ccp,_=ccjoin.build('opp/moves.pkl'); revp=(ccp.cls=='brilliant').astype(int).rename('rev')
        opp=pd.DataFrame(index=Xp.index).join(revp); opp=opp[opp.rev.notna()]; Xp=Xp.loc[opp.index][Xo.columns]
        print('opponent candidates with review labels:',len(opp),'brilliant',int(opp.rev.sum()))
    Xd=None
    if os.path.exists('dash/feats6.pkl'):
        Xd,_=feats('dash/'); Xd=Xd[Xo.columns]; dinfo={(r['game_id'],r['ply']):r for r in pickle.load(open('dash/moves.pkl','rb'))}
    DASH_KEY={('tjxdTRho',11),('bJPg3bse',24),('DEFZuyyq',27),('EKJK1jEv',33),('l2M7NFx8',24),('4Qh1Qi9C',46)}
    info={(r['game_id'],r['ply']):r for r in pickle.load(open('moves.pkl','rb'))}
    key=np.array([' '.join(info[k]['fen_before'].split()[:4])+info[k]['uci'] for k in Xo.index]); acct=np.array([info[k]['account'] for k in Xo.index])
    W={(w['game_id'],int(w['ply'])):w for w in csv.DictReader(gzip.open(D+'witty-all-own-move-outcomes.csv.gz','rt')) if w['primary']=='True'}
    wg={k[0] for k in W}; gid=np.array(Xo.index.get_level_values(0))
    revgames=set(cc.index.get_level_values(0)); test_games=wg&revgames
    te=np.isin(gid,list(test_games))&np.array([k in W for k in Xo.index])
    inw=np.isin(gid,list(wg)); overlap=np.isin(key,list(set(key[te])))
    tr=~inw&~overlap
    allrows=cc[cc.index.get_level_values(0).isin(test_games)]
    gal_pos=sum(1 for k,w in W.items() if k[0] in test_games and w['truth']=='True'); rev_pos=int((allrows.cls=='brilliant').sum())
    either=int(((allrows.gallery==1)|(allrows.cls=='brilliant')).sum())
    pub=np.array([W[k]['selective']=='!!' for k in Xo.index[te]]); galt=own.gal.values[te]; revt=own.rev.values[te].astype(int)
    print(f"held-out Witty test games with a fresh review: {len(test_games)} | gallery Brilliants {gal_pos} | today's review Brilliants {rev_pos} | either {either}")
    def line(name,a):
        tpg=int((a&(galt==1)).sum()); fpg=int((a&(galt==0)).sum()); tpr=int((a&(revt==1)).sum()); fpr=int((a&(revt==0)).sum()); fboth=int((a&(galt==0)&(revt==0)).sum())
        print(f"  {name:44s} awards {int(a.sum()):4d} | gallery: found {tpg} ({tpg/gal_pos:.1%}) false {fpg} | today's review: found {tpr} ({tpr/rev_pos:.1%}) false {fpr} | false by both {fboth}")
    line('published Mute Selective',pub)
    Xa=Xo.values.astype(float); res={}
    variants=[('A gallery labels (as before)',own.gal.values,False),('B fresh review labels where available',own.y.values,False)]
    if Xp is not None: variants.append(('C  B + opponents\' moves',own.y.values,True))
    for name,yv,use_opp in variants:
        Xt,yt,gt=Xa[tr],yv[tr],gid[tr]
        if use_opp:
            og=np.array(Xp.index.get_level_values(0)); om=~np.isin(og,list(wg))
            Xt=np.vstack([Xt,Xp.values.astype(float)[om]]); yt=np.concatenate([yt,opp.rev.values.astype(int)[om]]); gt=np.concatenate([gt,og[om]])
        oof=np.zeros(len(yt))
        for a,b in GroupKFold(5).split(Xt,yt,gt): oof[b]=fit(Xt[a],yt[a]).predict_proba(Xt[b])[:,1]
        models=[fit(Xt,yt,s) for s in range(5)]
        ps=np.mean([m.predict_proba(Xa[te])[:,1] for m in models],axis=0)
        print(f"{name}  (train rows {len(yt)}, positives {int(yt.sum())})")
        for prec in (0.93,0.953,0.97,0.985):
            th=thr_for(yt,oof,prec); line(f'cutoff for {prec:.1%} training precision ({th:.2f})',ps>=th)
        res[name]=ps
        if Xd is not None:
            pdash=np.mean([m.predict_proba(Xd.values.astype(float))[:,1] for m in models],axis=0)
            ths={prec:thr_for(yt,oof,prec) for prec in (0.93,0.953,0.97)}
            print('   Dash games (score, then award at the 93% / 95.3% / 97% cutoffs):')
            for k,p in zip(Xd.index,pdash):
                r=dinfo[k]
                if (r['game_id'],r['ply']) in DASH_KEY: print(f"     {r['game_id']} ply {r['ply']:3d} {r['san']:8s} score {p:.3f}  "+' / '.join('YES' if p>=ths[q] else 'no' for q in (0.93,0.953,0.97)))
    pickle.dump((Xo.index[te],res,galt,revt,pub),open('retrain_preds.pkl','wb'))
