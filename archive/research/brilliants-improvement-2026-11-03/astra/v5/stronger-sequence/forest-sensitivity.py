"""One unchanged full-fit forest cross-budget diagnostic; no fitting/threshold search."""
import sys,json,hashlib,sqlite3,time,resource,collections
from pathlib import Path
HERE=Path(__file__).resolve().parent;IMPROVE=HERE.parents[2];FINAL=IMPROVE.parent/'brilliants-final-2026-11-03';EXTRACTOR=HERE.parent/'fresh-extractor'
sys.dont_write_bytecode=True;sys.path.insert(0,str(EXTRACTOR))
from extractor import extract_batch,score_fixed_forest,MODEL_PATH
freeze=json.loads((EXTRACTOR/'FREEZE.json').read_text())
for name,digest in freeze['sha256'].items():
 assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest,'Frozen source/model mismatch'
model=json.loads(MODEL_PATH.read_text());data=json.loads((IMPROVE/'uniform-stronger-v5/analysis-uniform.json').read_text());assert len(data['targets'])==848
reference=json.loads((IMPROVE/'learning-v5/features.json').read_text());cases={c['key']:c for c in reference['cases']};del reference
predictions={r['key']:r for r in json.loads((IMPROVE/'learning-v5/forest-diagnostic/predictions.json').read_text()) if r['operating_point']=='cost5'}
db=sqlite3.connect(FINAL/'corpus.sqlite3');rows=[];changes=collections.Counter();missing_changes=collections.Counter();start=time.monotonic();matrices={name:{'TP':0,'FP':0,'FN':0,'TN':0} for name in ['baseline_full_fit','stronger_full_fit']}
for batchstart in range(0,848,64):
 targets=data['targets'][batchstart:batchstart+64];requests=[]
 for t in targets:
  pgn=db.execute('select pgn from games where game_id=?',(t['game_id'],)).fetchone()[0]
  requests.append({'pgn':pgn,'ply':t['ply'],'snapshots':[{**data['snapshots'][i],'quality':'uniform-sf18-1500000:'+data['engine_sha256']} for i in t['snapshot_ids']]})
 actuals=extract_batch(requests)
 for t,a in zip(targets,actuals):
  key=f"{t['game_id']}:{t['ply']}";b=cases[key];old=predictions[key];score=score_fixed_forest(a,model);diff=[]
  for window in ['current','previous']:
   for feature,value in a['windows'][window]['features'].items():
    previous=b['windows'][window]['features'][feature]
    if value!=previous:
     changes[feature]+=1;missing_changes[feature]+=int((value is None)!=(previous is None));diff.append({'window':window,'feature':feature,'before':previous,'after':value})
  truth=b['truth'];base=old['full_fit_award_NOT_validation'];new=score['award']
  for name,pred in [('baseline_full_fit',base),('stronger_full_fit',new)]:matrices[name][('T' if truth==pred else 'F')+('P' if pred else 'N')]+=1
  rows.append({'key':key,'san':t['san'],'truth':truth,'baseline_award':base,'stronger_award':new,'baseline_scores':{w:old[f'full_{w}_raw_p'] for w in ['current','previous']},'stronger_scores':score['window_scores'],'input_changes':diff,'physical_unknown':a['diagnostics']['physical_unknown']})
 print('processed',min(batchstart+64,848),flush=True)
assert matrices['baseline_full_fit']['TP']==247 and matrices['baseline_full_fit']['FP']==0
out={'scope':'Paired development-only cross-budget sensitivity, SF18same engine300k→1.5m. Unchanged FULL-DATA forest, extractor, threshold. Baseline247TP0FP is training resubstitution, NOT OOF223TP2FP; stronger result is NOT validation.','extractor_freeze_sha256':hashlib.sha256((EXTRACTOR/'FREEZE.json').read_bytes()).hexdigest(),'uniform_input_sha256':hashlib.sha256((IMPROVE/'uniform-stronger-v5/analysis-uniform.json').read_bytes()).hexdigest(),'matrices':matrices,'input_changes_per_feature':dict(changes),'missingness_changes_per_feature':{k:v for k,v in missing_changes.items() if v},'cases_with_changed_inputs':sum(bool(r['input_changes']) for r in rows),'award_changes':[r for r in rows if r['baseline_award']!=r['stronger_award']],'physical_unknown':sum(r['physical_unknown'] for r in rows),'rows':rows,'elapsed_seconds':time.monotonic()-start,'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
(HERE/'forest-cross-budget.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:out[k] for k in ['matrices','cases_with_changed_inputs','physical_unknown','elapsed_seconds','peak_rss_bytes']}));db.close()
