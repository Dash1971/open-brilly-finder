#!/usr/bin/env python3
"""Like-for-like with the published 1,000-game test: train on the six development accounts only, test on all 1,000 Witty games with native evidence."""
import pickle, json, numpy as np, pandas as pd
from sklearn.model_selection import GroupKFold
from v6train import table, fit, thr_for
import ccjoin
Xo=table(''); Xp=table('opp/'); cols=list(Xo.columns)
R=pickle.load(open('moves.pkl','rb')); info={(r['game_id'],r['ply']):r for r in R}
acct=np.array([info[k]['account'] for k in Xo.index]); gal=np.array([int(info[k]['label']) for k in Xo.index])
cc,_=ccjoin.build('moves.pkl'); rev=(cc.cls=='brilliant').astype(int).reindex(Xo.index); y=np.where(rev.notna(),rev.fillna(0),gal).astype(int)
ccp,_=ccjoin.build('opp/moves.pkl'); revp=(ccp.cls=='brilliant').astype(int).reindex(Xp.index)
oppacct={(r['game_id'],r['ply']):r for r in pickle.load(open('opp/moves.pkl','rb'))}
gamesacct={}
for r in R: gamesacct.setdefault(r['game_id'],r['account'])
rows=pickle.load(open('native_rows.pkl','rb')); nat=[r for r in rows if not r['excluded']]
testkeys={' '.join(info[(r['game_id'],r['ply'])]['fen_before'].split()[:4])+r['uci'] for r in nat if (r['game_id'],r['ply']) in info}
key=np.array([' '.join(info[k]['fen_before'].split()[:4])+info[k]['uci'] for k in Xo.index])
tr=(acct!='Witty_Alien')&~np.isin(key,list(testkeys))
og=np.array(Xp.index.get_level_values(0)); om=revp.notna().values&np.array([gamesacct.get(g)!='Witty_Alien' for g in og])
Xt=np.vstack([Xo.values[tr],Xp.values[om]]).astype(float); yt=np.concatenate([y[tr],revp.values[om].astype(int)]); gt=np.concatenate([np.array(Xo.index.get_level_values(0))[tr],og[om]])
oof=np.zeros(len(yt))
for a,b in GroupKFold(5).split(Xt,yt,gt): oof[b]=fit(Xt[a],yt[a]).predict_proba(Xt[b])[:,1]
m=fit(Xt,yt,0); cut=thr_for(yt,oof,0.953); cut_strict=thr_for(yt,oof,0.97)
Xn=np.array([[float(r['f_cur'][k]) for k in cols] if r['f_cur'] is not None else [np.nan]*len(cols) for r in nat]); ok=~np.isnan(Xn).any(axis=1)
s=np.zeros(len(nat)); s[ok]=m.predict_proba(Xn[ok])[:,1]
g=np.array([r['gallery'] for r in nat]); sel=np.array([r['selective'] for r in nat]); n=int(g.sum())
print(f"B. all 1,000 games, native Stockfish 19 Fast evidence; model trained on the six development accounts only (rows {len(yt)}, Brilliants {int(yt.sum())}); gallery Brilliants {n}")
res={}
def line(name,a): res[name]=dict(awards=int(a.sum()),found=int((a&g).sum()),false=int((a&~g).sum())); print(f"  {name:58s} awards {int(a.sum()):4d} found {int((a&g).sum()):4d} ({(a&g).sum()/n:.1%}) false {int((a&~g).sum()):3d}")
line('Mute Selective (native, published)',sel)
line(f'Mute Exchange, frozen medium cutoff {cut:.3f}',s>=cut)
line(f'Mute Exchange, frozen strict cutoff {cut_strict:.3f}',s>=cut_strict)
o=np.argsort(-s); cf=np.cumsum(~g[o]); ct=np.cumsum(g[o])
for cap in (20,38,57):
    i=np.searchsorted(cf,cap,side='right')-1; res[f'at_{cap}_false']=int(ct[i]); print(f"     at <= {cap} false: {int(ct[i])} found ({ct[i]/n:.1%})")
pickle.dump({(r['game_id'],r['ply']):float(v) for r,v in zip(nat,s)},open('native_dev6_scores.pkl','wb'))
json.dump(dict(train_rows=int(len(yt)),train_brilliants=int(yt.sum()),gallery=n,cut_medium=cut,cut_strict=cut_strict,results=res),open('native_results_1000.json','w'),indent=1)
