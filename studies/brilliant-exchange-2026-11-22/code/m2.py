import pickle, numpy as np, pandas as pd, sys
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import GroupKFold
from sklearn.metrics import average_precision_score, precision_recall_curve
DROP={'label','elo','elo_diff','clk','spent','tc_base','ply'}
def load(name):
    df=pd.DataFrame.from_dict(pickle.load(open(name,'rb')),orient='index'); df.index=pd.MultiIndex.from_tuples(df.index); return df
def cv(X,y,g,seed=0):
    oof=np.zeros(len(y))
    for tr,te in GroupKFold(5).split(X,y,g):
        m=HistGradientBoostingClassifier(max_iter=400,learning_rate=0.05,max_leaf_nodes=31,min_samples_leaf=20,l2_regularization=1.0,random_state=seed).fit(X[tr],y[tr])
        oof[te]=m.predict_proba(X[te])[:,1]
    return oof
def rep(name,y,oof):
    p,r,t=precision_recall_curve(y,oof)
    out=[]
    for pr in (0.99,0.97,0.95,0.90):
        ok=p[:-1]>=pr; out.append(f"R@P{int(pr*100)}={max(r[:-1][ok]) if ok.any() else 0:.3f}")
    print(f"{name:28s} AP={average_precision_score(y,oof):.4f} "+' '.join(out),flush=True)
if __name__=='__main__':
    base=load('feats.pkl'); base=base[base.hang_see>=2]
    y=base.label.values; g=base.index.get_level_values(0).values
    cols=[c for c in base.columns if c not in DROP]
    eng=[c for c in cols if c in ('depth_before','best_cp','best_is_mate','rank','alt_cp','alt2_cp','alt_net','played_cp_before','has_decline','accept_cp','decline_cp','played_cp','accept_is_best','acc_minus_dec','accept_mate_for_mover','played_mate','cp_loss','wc_best','wc_played','wc_loss','wc_alt','wc_gain_vs_alt','wc_alt2','wc_accept','wc_decline')]
    rep('full depth',y,cv(base[cols].values.astype(float),y,g))
    rep('board-only (no engine)',y,cv(base[[c for c in cols if c not in eng and not c.startswith('mat_pv') and c not in('pv_len','pv_mate','recover_ply')]].values.astype(float),y,g))
    comb=base[cols].copy()
    for d in (8,10,12,14,16):
        f=load(f'feats-d{d}.pkl').loc[base.index]
        rep(f'depth<={d}',y,cv(f[cols].values.astype(float),y,g))
        for c in eng: comb[f'{c}_d{d}']=f[c].values
    oof=cv(comb.values.astype(float),y,g)
    rep('all depths combined',y,oof)
    comb.to_pickle('comb.pkl'); pickle.dump(pd.Series(oof,index=base.index),open('oof-comb.pkl','wb'))
