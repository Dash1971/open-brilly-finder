"""Training-only saved-feature assembly. No fit, engine, reserved inputs or scoring."""
import json,sys,hashlib,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];R=ROOT.parent;I=R/'brilliants-improvement-2026-11-03';P=R/'brilliants-prospective-v7-2026-11-03';sources={};rows=[]
def load(p):
 sources[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest();return json.loads(p.read_text())
def key(t):return str(t['game_id'])+':'+str(t['ply'])
def canon(f):return ' '.join(f.split()[:4])
def add(f,t,cohort):
 truth=t.get('truth',t.get('is_brilliant',t.get('fresh_label')=='!!'));assert type(truth) is bool
 rows.append({'key':key(t),'game_id':str(t['game_id']),'fen_before':t['fen_before'],'fen_after':t['fen_after'],'uci':t['uci'],'truth':truth,'negative_bucket':t.get('negative_bucket','legacy_mixed'),'cohort':cohort,'windows':f['windows'],'confidence_sufficient':f['confidence_sufficient']})
ident={key(t):t for name in ['primary-moves.json','panel-moves.json'] for t in load(R/'brilliants-final-2026-11-03'/name)}
old=load(I/'learning-v5/features.json')
for f in old['cases']:add(f,{**ident[f['key']],'truth':f['truth']},'former848')
for fp,tp,cohort in [(I/'future-validation-v5/engine-core/forest-predictions.json',I/'future-validation-v5/primary-moves.json','former200'),(P/'selective-replay/predictions.json',P/'root-frozen-final200queue.json','former_new200')]:
 targets=load(tp);ids={key(t):t for t in targets};features=load(fp)['rows']
 assert len(ids)==len(targets) and len(features)==len(ids) and {r['key'] for r in features}==set(ids), 'Legacy target/feature key mismatch'
 for r in features:add(r['features'],ids[r['key']],cohort)
# Root supplies the exact completed batches; never glob mutable/live inputs.
for name in sys.argv[2:]:
 directory=ROOT/'engine-batches'/name;a=load(directory/'analysis.json');f=load(directory/'features.json');assert a['status']==f['status']=='complete'
 ids={key(t):t for t in a['targets']};assert all(t['split']=='training' for t in ids.values())
 assert len(ids)==len(a['targets']) and len(f['rows'])==len(ids) and {r['key'] for r in f['rows']}==set(ids), 'Batch target/feature key mismatch'
 for r in f['rows']:
  assert r['split']=='training';add(r['features'],ids[r['key']],name)
names=old['predictors'];assert len(names)==75 and names==sorted(names)
for r in rows:
 for w in ['current','previous']:
  fs=r['windows'][w]['features'];assert set(fs)==set(names)
  assert all(v is None or isinstance(v,(bool,int,float)) and math.isfinite(v) for v in fs.values())
parent={r['game_id']:r['game_id'] for r in rows}
def find(x):
 while parent[x]!=x:parent[x]=parent[parent[x]];x=parent[x]
 return x
def union(a,b):
 a,b=find(a),find(b);parent[max(a,b)]=min(a,b)
seen={};examples={}
for r in rows:
 p=canon(r['fen_before']);g=r['game_id']
 if p in seen:union(g,seen[p])
 else:seen[p]=g
 examples.setdefault(p+'|'+r['uci'],[]).append(r)
cases=[];quarantine=[];duplicates=[]
for example,rr in sorted(examples.items()):
 if len({r['truth'] for r in rr})>1:quarantine.append({'example':example,'keys':[r['key'] for r in rr]});continue
 r=rr[0];r.update(example=example,group=find(r['game_id']),aliases=[x['key'] for x in rr]);cases.append(r)
 if len(rr)>1:duplicates.append({'kept':r['key'],'aliases':r['aliases'],'policy':'First fixed source order; no outcome or feature selection.'})
out=Path(sys.argv[1]);assert not out.exists();out.parent.mkdir(parents=True,exist_ok=True)
result={'scope':'TRAINING ONLY; original848+400 are no longer independent assessment','sources':sources,'predictors':names,'cases':cases,'quarantine':quarantine,'duplicates':duplicates,'counts':{'raw':len(rows),'deduplicated':len(cases),'positive':sum(r['truth'] for r in cases),'groups':len({r['group'] for r in cases})},'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()};out.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print(json.dumps(result['counts']))
