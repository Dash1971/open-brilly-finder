import sys,json,subprocess,time,resource
from pathlib import Path
sys.dont_write_bytecode=True
from feature_kernel import extract_features
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4];FINAL=ROOT/'research/brilliants-final-2026-11-03';IMPROVE=HERE.parents[2]
NODE='/private/tmp/node-v24.22.1-darwin-arm64/bin/node';LOADER=IMPROVE/'root/frozen-v4/node_modules/tsx/dist/loader.mjs'
inputs=[];keys=[]
for name in ['analysis-baseline.json','analysis-panel.json']:
 d=json.loads((FINAL/name).read_text())
 for t in d['targets']:
  snaps=[{**d['snapshots'][i],'quality':'fixed-sf18:'+d['engine_sha256']} for i in t['snapshot_ids']]
  inputs.append({'fen_before':t['fen_before'],'fen_after':t['fen_after'],'uci':t['uci'],'snaps':snaps});keys.append(f"{t['game_id']}:{t['ply']}")
 del d
start=time.monotonic()
process=subprocess.run([NODE,'--no-warnings','--import',str(LOADER),str(HERE/'context.mts')],input=json.dumps(inputs),text=True,capture_output=True,check=True)
contexts=json.loads(process.stdout);del process
reference=json.loads((IMPROVE/'learning-v5/features.json').read_text());expected={c['key']:c for c in reference['cases']};predictors=reference['predictors'];del reference
mismatches=[];results=[]
for i,(t,c,key) in enumerate(zip(inputs,contexts,keys)):
 actual=extract_features(t,c);want=expected[key];diff=[]
 for which in ['current','previous']:
  assert sorted(actual['windows'][which]['features'])==predictors
  for f in predictors:
   x=actual['windows'][which]['features'][f];y=want['windows'][which]['features'][f]
   if x!=y:diff.append({'window':which,'feature':f,'actual':x,'expected':y})
  if actual['windows'][which]['eligible']!=want['windows'][which]['eligible']:diff.append({'window':which,'feature':'eligible'})
 if actual['confidence_sufficient']!=want['confidence_sufficient']:diff.append({'feature':'confidence'})
 if diff:mismatches.append({'key':key,'differences':diff})
 results.append(actual)
 if i%100==0:print('progress',i,'mismatch_cases',len(mismatches),flush=True)
(HERE/'parity-results.json').write_text(json.dumps({'cases':len(results),'predictors':len(predictors),'mismatches':mismatches,'elapsed_seconds':time.monotonic()-start,'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss},indent=2)+'\n')
(HERE/'extracted-848.json').write_text(json.dumps({'scope':'Recomputed feature values only; no identity or label inputs to kernel. Case order is original corpus order.','cases':results},separators=(',',':'))+'\n')
print('DONE',len(results),'mismatch cases',len(mismatches),'seconds',time.monotonic()-start,'rss',resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
