"""Paired prospective label accounting; no fitting, tuning or case replacement."""
import collections,hashlib,json,math
from pathlib import Path
H=Path(__file__).resolve().parent
read=lambda n:json.loads((H/n).read_text())
q=read('REVIEW-QUEUE.json');labels=read('LABELS.json');ll={r['key']:r for r in labels['rows']};assert set(ll)=={r['key'] for r in q['rows']}
rows=[{**r,**ll[r['key']]} for r in q['rows']];known=[r for r in rows if r['status']=='verified'];unknown=[r for r in rows if r['status']!='verified']
def metrics(rows,field):
 tp=sum(r['label']=='Brilliant' and r[field] for r in rows);fp=sum(r['label']!='Brilliant' and r[field] for r in rows)
 return {'TP':tp,'FP':fp,'FN':sum(r['label']=='Brilliant' and not r[field] for r in rows),'TN':sum(r['label']!='Brilliant' and not r[field] for r in rows)}
new=[r for r in known if r['new_award']];newtp=sum(r['label']=='Brilliant' for r in new);newfp=len(new)-newtp
if len(new) and newfp==0:upper=1-math.pow(.05,1/len(new))
else:upper=None
out={'scope':'Targeted prospective challenge set, selected label-blind after candidate freeze; not representative population recall/precision. Forest andthreshold unchanged, no fitting.','candidate_freeze_sha256':hashlib.sha256((H/'CANDIDATE-FREEZE.json').read_bytes()).hexdigest(),'prelabel_freeze_sha256':hashlib.sha256((H/'PRELABEL-FREEZE.json').read_bytes()).hexdigest(),'label_sha256':hashlib.sha256((H/'LABELS.json').read_bytes()).hexdigest(),'queued':len(rows),'verified':len(known),'unresolved':len(unknown),'baseline':metrics(known,'baseline_award'),'candidate':metrics(known,'candidate_award'),'incremental':{'correct':newtp,'wrong':newfp,'verified_extra_awards':len(new),'unresolved_extra_awards':sum(r['new_award'] for r in unknown)},'controls':dict(collections.Counter(r['label'] for r in known if not r['new_award'])),'extra_award_labels':dict(collections.Counter(r['label'] for r in new)),'zero_wrong_one_sided95_binomial_upper_if_applicable':upper,'uncertainty_caveat':'Small targeted sample. Binomial bound, when shown, assumes exchangeable independent future cases drawn by this sampling process; not a sitewide bound or guarantee.','verdict':'unresolved' if unknown else 'improved_without_additional_wrong_in_this_sample' if newtp>0 and newfp==0 else 'additional_wrong_awards' if newfp>0 else 'no_incremental_evidence','cases':[{k:r.get(k) for k in ['key','game_id','ply','san','stratum','baseline_award','candidate_award','new_award','status','label','visible_text','url']} for r in rows]}
(H/'RESULTS.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k!='cases'},indent=2))
