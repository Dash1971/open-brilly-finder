#!/usr/bin/env python3
"""Write the published data files for the study."""
import os, glob, gzip, csv, json, pickle, hashlib, shutil, numpy as np, pandas as pd
import pb, ccparse, ccjoin
from v6train import table
OUT="../open-brilly-finder/studies/brilliant-exchange-2026-11-22/"
D="../open-brilly-finder/studies/brilliant-selective-2026-11-06/data/"
CLS=ccjoin.CLS
# 1. every move Chess.com classified in the 1,005 re-reviewed games
n=0
with gzip.open(OUT+'data/chesscom-review-moves.csv.gz','wt',newline='') as f:
    w=csv.writer(f); w.writerow(['game_id','ply','uci','chesscom_class','eval_cp_white','mate_white','depth','played_is_best','best_uci','best_eval_cp_white','best_mate_white'])
    for path in sorted(glob.glob('ccreview/*.json')):
        gid=os.path.basename(path)[:-5]
        try: P,_=ccparse.plies(path)
        except Exception: continue
        def sc(s):
            if not s or 1 not in s: return '',''
            d={a:c for a,b,c in s[1]}
            if 1 in d: return pb.zz(d[1]),''
            if 2 in d: return '',d[2]
            if 3 in d: return '',-d[3]
            return 0,''
        for p in P:
            cp,mt=sc(p['score']); bcp,bmt=sc(p.get('best_score')) if p.get('best') else ('','')
            w.writerow([gid,p['ply'],p['played'][0],CLS.get(p['cls'],p['cls']),cp,mt,(p['score'] or {}).get(2,''),int(not p.get('best')),p['best'][0] if p.get('best') else '',bcp,bmt]); n+=1
print('review moves',n)
# 2. candidate table
Xo=table(''); Xp=table('opp/'); cols=list(Xo.columns)
R={(r['game_id'],r['ply']):r for r in pickle.load(open('moves.pkl','rb'))}; Ro={(r['game_id'],r['ply']):r for r in pickle.load(open('opp/moves.pkl','rb'))}
cc,_=ccjoin.build('moves.pkl'); ccp,_=ccjoin.build('opp/moves.pkl')
P=pickle.load(open('v6-preds.pkl','rb')); score=dict(zip(P['index'],P['ps'])); cut=P['ths']['medium']
W={(w['game_id'],int(w['ply'])):w for w in csv.DictReader(gzip.open(D+'witty-all-own-move-outcomes.csv.gz','rt')) if w['primary']=='True'}
with gzip.open(OUT+'data/candidates.csv.gz','wt',newline='') as f:
    w=csv.writer(f); w.writerow(['game_id','ply','side','account','san','uci','fen_before','gallery_brilliant','chesscom_review_class','role','exchange_score']+cols)
    for X,RR,C,side in ((Xo,R,cc,'gallery account'),(Xp,Ro,ccp,'opponent')):
        for k,row in zip(X.index,X.values):
            r=RR[k]; rc=C.cls.get(k,'') if k in C.index else ''
            if side=='opponent' and not rc: continue
            role='held-out test' if k in score else 'training'
            w.writerow([k[0],k[1],side,r['account'] if side=='gallery account' else '',r['san'],r['uci'],r['fen_before'],int(r['label']) if side=='gallery account' else '',rc,role,f"{score[k]:.6f}" if k in score else '']+[('%g'%v) for v in row])
# 3. held-out outcomes
with open(OUT+'data/heldout-outcomes.csv','w',newline='') as f:
    w=csv.writer(f); w.writerow(['game_id','ply','san','uci','gallery_brilliant','chesscom_review_today','mute_selective','exchange_score','exchange_brilliant'])
    for k,p,g,rv,pu in zip(P['index'],P['ps'],P['gal'],P['rev'],P['pub']):
        w.writerow([k[0],k[1],R[k]['san'],R[k]['uci'],int(g),cc.cls.get(k,''),int(pu),f"{p:.6f}",int(p>=cut)])
    # gallery Brilliants in these games that are not candidates count as misses
    tg={k[0] for k in P['index']}; have=set(P['index'])
    for k,wr in W.items():
        if k[0] in tg and k not in have and (wr['truth']=='True' or wr['selective']=='!!'):
            w.writerow([k[0],k[1],wr['san'],wr['uci'],int(wr['truth']=='True'),cc.cls.get(k,'') if k in cc.index else '',int(wr['selective']=='!!'),'',0])
# 4. model, fixtures, reference code
m=json.load(open('v6-model.json')); m['name']='mute-brilliant-v8'; json.dump(m,open(OUT+'model/mute-exchange-model.json','w'),separators=(',',':'))
shutil.copy('ts/v6-fixtures.json',OUT+'model/parity-fixtures.json')
shutil.copy('lila/ui/analyse/src/noSweatBrilliantExchange.ts',OUT+'model/noSweatBrilliantExchange.ts')
for s in ('extract_moves.py','engine_pass.py','features.py','features2.py','features4.py','features5.py','features6.py','lines.py','v6ref.py','v6build.py','v6train.py','retrain.py','pb.py','ccparse.py','ccjoin.py','deep.py','m2.py','study_stats.py','study_export.py','recv.py'):
    shutil.copy(s,OUT+'code/'+s)
st=json.load(open('study_stats.json')); st.pop('curve',None); json.dump(st,open(OUT+'data/study-stats.json','w'),indent=1)
print('sha',hashlib.sha256(open(OUT+'model/mute-exchange-model.json','rb').read()).hexdigest())
for f in sorted(glob.glob(OUT+'data/*')+glob.glob(OUT+'model/*')): print(os.path.getsize(f)//1024,'KB',f.split('2026-11-22/')[1])
