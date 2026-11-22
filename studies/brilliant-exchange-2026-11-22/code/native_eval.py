#!/usr/bin/env python3
"""Score Mute Exchange on native Stockfish 19 Fast evidence and compare with Mute Selective's native decisions."""
import pickle, json, numpy as np, pandas as pd
from v6train import score, table, fit, thr_for
import ccjoin
from sklearn.model_selection import GroupKFold
model=json.load(open('v6-model.json')); cols=model['features']; cut=model['cutoff']
rows=pickle.load(open('native_rows.pkl','rb'))
def sc(f,m=model): return float(score(m,[float(f[k]) for k in cols])) if f is not None else 0.0
for r in rows: r['s_cur']=sc(r['f_cur']); r['s_prev']=sc(r['f_prev'])
cc,_=ccjoin.build('moves.pkl'); rev=(cc.cls=='brilliant'); revgames=set(cc.index.get_level_values(0))
P=pickle.load(open('v6-preds.pkl','rb')); test_games={k[0] for k in P['index']}; sf18=dict(zip(P['index'],P['ps']))
df=pd.DataFrame([{k:v for k,v in r.items() if not k.startswith('f_')} for r in rows]); df=df[~df.excluded]
df['rev']=[bool(rev.get((g,p),False)) for g,p in zip(df.game_id,df.ply)]
out={}
def line(name,d,a,ref='gallery'):
    g=d.gallery.values; rv=d.rev.values; n=int(g.sum())
    res=dict(awards=int(a.sum()),found=int((a&g).sum()),false_vs_gallery=int((a&~g).sum()),false_by_both=int((a&~g&~rv).sum()),gallery=n)
    out[name]=res; print(f"  {name:62s} awards {res['awards']:4d} found {res['found']:4d} ({res['found']/n:.1%}) false {res['false_vs_gallery']:3d}"+(f" false-by-both {res['false_by_both']}" if ref=='both' else ''))
t=df[df.game_id.isin(test_games)]
print(f"A. 337 held-out games, native Stockfish 19 Fast evidence (gallery Brilliants {int(t.gallery.sum())})")
line('Mute Selective (native)',t,t.selective.values,'both')
line('Mute Exchange, shipped model + cutoff, native evidence',t,(t.s_cur>=cut).values,'both')
line('  ... also requiring the previous iteration to agree',t,((t.s_cur>=cut)&(t.s_prev>=cut)).values,'both')
s18=np.array([sf18.get((g,p),0.0) for g,p in zip(t.game_id,t.ply)])
line('Mute Exchange on the SF18 research evidence (as published)',t,s18>=cut,'both')
both=(t.s_cur>=cut).values&(s18>=cut); print('     awards in common between native and SF18 evidence:',int(both.sum()),'| score correlation',round(float(np.corrcoef(t.s_cur.values,s18)[0,1]),3))
o=np.argsort(-t.s_cur.values); g=t.gallery.values[o]; cf=np.cumsum(~g); ct=np.cumsum(g)
for cap in (10,15,18,25): i=np.searchsorted(cf,cap,side='right')-1; print(f"     native evidence at <= {cap} false: {int(ct[i])} found")
json.dump(out,open('native_results_337.json','w'),indent=1)
df.to_pickle('native_df.pkl')
