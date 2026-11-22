#!/usr/bin/env python3
"""Fixtures for the TypeScript port: inputs in the app's review-window shape, expected features and score."""
import json, pickle, random, glob
import numpy as np
import v6ref, v6build
from v6train import score
from features import cp_of, pick
model=json.load(open('v6-model.json')); cols=model['features']
random.seed(11)
cases=[]
def to_line(uci, cp_mover, white_mover, pv=None):
    cpw = cp_mover if white_mover else -cp_mover
    if abs(cp_mover) >= 9010 or cp_mover == -10000:
        n = 0 if cp_mover == -10000 else (10000 - abs(cp_mover)) // 10
        m = n if cp_mover > 0 else -n
        return {'mate': m if white_mover else -m, 'moves': [uci] if uci else []}
    return {'cp': cpw, 'moves': [uci] if uci else []}
for prefix, n in (('',260),('opp/',60),('dash/',17)):
    items=v6build.load(prefix); random.shuffle(items)
    # make sure special situations are represented
    special=[it for it in items if it[2]['in_check_before'] or it[2]['promo'] or it[1] is None or it[2]['gives_check']][:40]
    for key,fen_prev,r,e in (items[:n]+special):
        d,lines=pick(e['before'],12)
        if not lines: continue
        before=[(l[1][0],cp_of(l[0])) for l in lines[:2]]
        da,la=pick(e['accept'],12); dd,ld=pick(e['decline'],12); c=[]
        if la: c.append((-cp_of(la[0][0]),la[0][1][0]))
        if ld: c.append((-cp_of(ld[0][0]),ld[0][1][0]))
        if not c: continue
        after=min(c)
        f=v6ref.v6_features(fen_prev,r['fen_before'],r['uci'],before,after)
        if f is None: continue
        x=[float(f[k]) for k in cols]; white=r['color']=='w'
        cases.append(dict(key=f"{prefix}{key[0]}:{key[1]}",san=r.get('san',''),label=bool(r.get('label')),
            fenPrev=fen_prev,fenBefore=r['fen_before'],fenAfter=r['fen_after'],uci=r['uci'],
            before=[{'uci':m,'cp':cp} for m,cp in before],after={'cp':after[0],'reply':after[1]},
            window=dict(positions=([fen_prev] if fen_prev else [])+[r['fen_before'],r['fen_after']],
                        beforeLines=[to_line(m,cp,white) for m,cp in before],
                        afterLines=[to_line(after[1],after[0],white)]),
            features={k:(float(f[k]) if isinstance(f[k],float) else int(f[k])) for k in cols},score=float(score(model,x))))
seen=set(); out=[]
for c in cases:
    if c['key'] not in seen: seen.add(c['key']); out.append(c)
json.dump(dict(model_features=cols,cutoff=model['cutoff'],cases=out),open('ts/v6-fixtures-full.json','w'))
print(len(out),'cases; awarded',sum(c['score']>=model['cutoff'] for c in out),'cutoff',round(model['cutoff'],4))
