#!/usr/bin/env python3
"""Join actual mover PGN rating; account/cohort are audit/fold metadata only."""
import collections,csv,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent;FINAL=BASE.parent.parent/'brilliants-final-2026-11-03';ACCOUNTS=('nelsi','hansen','KNVB','GothamChess','Hikaru')
def load(p):return json.loads(p.read_text())
data=load(BASE/'features.json');protocol=load(ROOT/'PROTOCOL.json');assert hashlib.sha256((BASE/'features.json').read_bytes()).hexdigest()==protocol['base_feature_sha256'];metadata={};source_hashes={}
for filename,cohort in (('analysis-baseline.json','core818'),('analysis-panel.json','panel30')):
 path=FINAL/filename;source_hashes[filename]=hashlib.sha256(path.read_bytes()).hexdigest()
 for t in load(path)['targets']:
  side='white' if t['fen_before'].split()[1]=='w' else'black';account=next(a for a in ACCOUNTS if a.lower()==t[side].lower());raw=t.get(side+'_rating')
  try:rating=float(raw) if raw is not None else None
  except (TypeError,ValueError):rating=None
  metadata[f"{t['game_id']}:{t['ply']}"]={'account':account,'cohort':cohort,'mover_rating':rating}
assert len(metadata)==848
for c in data['cases']:
 c.update(metadata[c['key']])
 for w in c['windows'].values():w['features']['mover_rating']=c['mover_rating']
for row in data['window_rows']:
 row.update(metadata[row['key']]);row['features']['mover_rating']=row['mover_rating']
data['predictors_original75']=list(data['predictors']);data['predictors_plus_rating']=data['predictors']+['mover_rating'];data['scope']='One actual-mover PGN rating extension on848unblindeddevelopment cases. Account and cohort are audit/fold metadata, not predictors.'
(ROOT/'features.json').write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')
with (ROOT/'features.csv').open('w') as f:
 names=['key','window','truth','eligible','group','fold','account','cohort']+data['predictors_plus_rating'];out=csv.DictWriter(f,fieldnames=names);out.writeheader()
 for row in data['window_rows']:out.writerow({**{k:row[k] for k in names[:8]},**row['features']})
audit={}
for account in ACCOUNTS:
 rows=[c for c in data['cases'] if c['account']==account];ratings=[c['mover_rating'] for c in rows if c['mover_rating'] is not None];ratios={}
 for cohort in ('all848','core818','panel30'):
  z=[c for c in rows if cohort=='all848' or c['cohort']==cohort];ratios[cohort]={'n':len(z),'Brilliant':sum(c['truth'] for c in z),'non_Brilliant':sum(not c['truth'] for c in z)}
 held_groups={c['group'] for c in rows};training=[c for c in data['cases'] if c['account']!=account and c['group'] not in held_groups];trainratings=[c['mover_rating'] for c in training if c['mover_rating'] is not None];low=min(trainratings);high=max(trainratings)
 audit[account]={'classes':ratios,'rating_min':min(ratings),'rating_max':max(ratings),'missing_rating':len(rows)-len(ratings),'LOAO_training_cases_after_group_purge':len(training),'LOAO_extra_cases_purged_for_shared_group':sum(c['account']!=account and c['group'] in held_groups for c in data['cases']),'LOAO_training_rating_min':low,'LOAO_training_rating_max':high,'held_out_ratings_outside_training_range':sum(not low<=x<=high for x in ratings),'held_out_known_ratings':len(ratings)}
assert all(x['classes']['core818']['Brilliant']==x['classes']['core818']['non_Brilliant'] for x in audit.values())
(ROOT/'PRE-FIT-AUDIT.json').write_text(json.dumps({'account_is_not_predictor':True,'core_balanced_within_every_account':True,'panel_class_imbalance_retained_and_reported_separately':True,'source_hashes':source_hashes,'accounts':audit},indent=2)+'\n');print(json.dumps(audit,indent=2))
