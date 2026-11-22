#!/usr/bin/env python3
"""Every number quoted in the published study, computed in one place -> study_stats.json"""
import pickle, json, collections, csv, gzip, glob, os, numpy as np, pandas as pd
from m2 import load
import ccjoin
S={}
R=pickle.load(open('moves.pkl','rb'))
games={r['game_id'] for r in R}
S['data']=dict(games=len(games),own_moves=len(R),brilliants=sum(r['label'] for r in R),accounts=sorted({r['account'] for r in R if r['account'] in ('Witty_Alien','KNVB','Hikaru','hansen','nelsi','GothamChess','MagnusCarlsen')}))
def top(r):
    h=[o[3] for o in r['offers']]; return max(h,default=0)
cand=[r for r in R if top(r)>=2]
S['candidate_test']=dict(candidates=len(cand),share_of_moves=len(cand)/len(R),brilliants_covered=sum(r['label'] for r in cand),brilliants_total=S['data']['brilliants'],
    net_negative=sum(1 for r in cand if r['cap_val']-top(r)<0),net_negative_brilliants=sum(r['label'] for r in cand if r['cap_val']-top(r)<0),
    brilliant_rate_among_candidates=sum(r['label'] for r in cand)/len(cand))
cat=[r for r in R if r['label'] and r['category'] and 'Sacrifice' in r['category']]
N={2:'Knight',3:'Bishop',4:'Rook',5:'Queen'}
S['candidate_test']['named_piece_cases']=len(cat); S['candidate_test']['named_piece_is_offered']=sum(1 for r in cat if r['category'].split()[0] in {N[o[1]] for o in r['offers'] if o[3]>0})
# label determinism on repeated positions
g=collections.defaultdict(list)
for r in cand: g[(' '.join(r['fen_before'].split()[:4]),r['uci'])].append(r['label'])
d={k:v for k,v in g.items() if len(v)>1}
S['determinism']=dict(repeated_position_moves=len(d),rows=sum(len(v) for v in d.values()),minority_rows=sum(min(sum(v),len(v)-sum(v)) for v in d.values()))
S['determinism']['agreement']=1-S['determinism']['minority_rows']/S['determinism']['rows']
# review collection
cc,_=ccjoin.build('moves.pkl'); S['review']=dict(games=cc.index.get_level_values(0).nunique(),own_moves=len(cc),review_brilliants=int((cc.cls=='brilliant').sum()),gallery_brilliants=int(cc.gallery.sum()),
    both=int(((cc.gallery==1)&(cc.cls=='brilliant')).sum()),gallery_only=int(((cc.gallery==1)&(cc.cls!='brilliant')).sum()),review_only=int(((cc.gallery==0)&(cc.cls=='brilliant')).sum()),
    classes=cc.cls.value_counts().to_dict())
X=pd.read_pickle('X5.pkl'); X.index.names=['game_id','ply']
c=cc[cc.cand==1].drop(columns=['hang_see']).join(X,how='inner'); c['rb']=(c.cls=='brilliant').astype(int)
b=c[c.rb==1]
S['rule']=dict(review_brilliants_that_are_candidates=int(c.rb.sum()),review_brilliants=S['review']['review_brilliants'],is_chesscom_best=int((b.cc_is_best==1).sum()),net_negative=int((b.net<0).sum()),min_cp=int(b.cc_cp.min()),not_in_check=int((b.in_check==0).sum()),
    nonbest_candidates=int((c.cc_is_best==0).sum()),nonbest_brilliant=int(c.rb[c.cc_is_best==0].sum()))
s=c[(c.cc_is_best==1)&(c.net<0)&(c.cc_cp>=-20)&(c.in_check==0)]
S['rule']['base']=dict(n=len(s),brilliant=int(s.rb.sum()))
def cell(m): x=s[m]; return dict(n=int(len(x)),brilliant=int(x.rb.sum()),rate=float(x.rb.mean()) if len(x) else None)
S['rule']['situations']={
 'Moved piece is the one offered; cannot win it straight back':cell((s.moved_safe==0)&(s.acc_net2_min<0)),
 'Moved piece is the one offered; can win it straight back':cell((s.moved_safe==0)&(s.acc_net2_min>=0)),
 'Piece left where it stands; first move on offer':cell((s.moved_safe==1)&(s.hang_age==0)&(s.threat_minus_hang<0)),
 'Piece left where it stands; already on offer the move before':cell((s.moved_safe==1)&(s.hang_age>=1)),
 'Piece left where it stands; own threat at least as big':cell((s.moved_safe==1)&(s.threat_minus_hang>=0)),
 'Already 3+ points ahead in material':cell(s.matdiff>=3)}
# engine scale (candidates with both)
f=load('feats.pkl'); f.index.names=['game_id','ply']; f=f.reindex(c.index)
m=(c.cc_cp.abs()<1500)&(f.played_cp.abs()<1500)
S['engine']=dict(scale_slope=float(np.polyfit(f.played_cp[m].values.astype(float),c.cc_cp[m].values.astype(float),1)[0]),correlation=float(np.corrcoef(f.played_cp[m],c.cc_cp[m])[0,1]),n=int(m.sum()),
    our_top_is_their_best_among_brilliants=float((f['rank'][c.rb==1]==1).mean()))
deep=pickle.load(open('deep.pkl','rb')); ccb=pickle.load(open('ccbest.pkl','rb')); rows=[]
for k,bd in deep.items():
    if k in ccb and k in cc.index:
        rr={'brill':cc.loc[k,'cls']=='brilliant'}
        for dd in (8,10,12,14,16,18,20,22):
            ds=[x for x in bd if x<=dd]; rr[dd]=(bd[max(ds)][0]==ccb[k]) if ds else np.nan
        rows.append(rr)
dfd=pd.DataFrame(rows); S['engine']['by_depth']={int(k):dict(all=float(dfd[k].mean()),brilliants=float(dfd[dfd.brill][k].mean())) for k in (8,10,12,14,16,18,20,22)}; S['engine']['by_depth_positions']=len(dfd); S['engine']['by_depth_brilliants']=int(dfd.brill.sum())
# history effect (gallery labels, all games): stationary sound offers
df=pd.read_pickle('df.pkl'); f4=load('feats4.pkl').reindex(df.index); f2=load('feats2.pkl').reindex(df.index)
h=df[(df.net<0)&(df.in_check==0)&(df.played_cp>=-30)&(df.wc_loss<=5)&(f2.moved_safe==1)&(f2.acc_net2_min<0)]
ha=f4.hang_age.reindex(h.index).clip(0,4)
S['history']={int(k):dict(n=int(v['count']),rate=float(v['mean'])) for k,v in h.groupby(ha).label.agg(['count','mean']).iterrows()}
# shipped model + variants
S['model']=json.load(open('v6-results-d12.json'))
S['ladder_witty1000_at_38_false']={'Mute Selective (published)':774,'Independent rebuild: simple sacrifice test + engine evidence':774,'+ what happens if the piece is taken':835,'+ whether the offer was already standing':854,'+ what the opponent just did':869}
S['variants_heldout337']={'full evidence (accept/decline searches, 3 lines), deep search':{'strict':[283,13,6],'medium':[324,17,9]},'full evidence, depth 12':{'strict':[265,9,5],'medium':[311,18,10]},'app-compatible evidence, depth 12 (shipped)':{'strict':[265,12,6],'medium':[298,18,11]}}
P=pickle.load(open('v6-preds.pkl','rb')); ps,gal,rev=P['ps'],P['gal'],P['rev']; o=np.argsort(-ps)
S['curve']=dict(found=np.cumsum(gal[o]).tolist(),false_gallery=np.cumsum(1-gal[o]).tolist(),false_both=np.cumsum((1-gal[o])*(1-rev[o])).tolist(),score=ps[o].tolist())
json.dump(S,open('study_stats.json','w'),indent=1)
for k in ('data','candidate_test','determinism','review','rule','engine','history'): print(k, json.dumps(S[k])[:900])
