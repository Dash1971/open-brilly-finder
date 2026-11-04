import copy,json,sqlite3,time,resource
from pathlib import Path
from extractor import extract_batch,prepare,score_fixed_forest,MODEL_PATH
HERE=Path(__file__).resolve().parent;IMPROVE=HERE.parents[2];FINAL=IMPROVE.parent/'brilliants-final-2026-11-03'
db=sqlite3.connect(FINAL/'corpus.sqlite3');model=json.loads(MODEL_PATH.read_text());inputs=[];keys=[];snapshot_bank={};quality=''
for name in ['analysis-baseline.json','analysis-panel.json']:
 d=json.loads((FINAL/name).read_text());quality='fixed-sf18:'+d['engine_sha256'];snapshot_bank.update(d['snapshots'])
 for t in d['targets']:
  pgn=db.execute('select pgn from games where game_id=?',(t['game_id'],)).fetchone()[0]
  inputs.append({'pgn':pgn,'ply':t['ply'],'snapshots':[{**d['snapshots'][i],'quality':quality} for i in t['snapshot_ids']]});keys.append(f"{t['game_id']}:{t['ply']}")
 del d
reference=json.loads((IMPROVE/'learning-v5/features.json').read_text());expected={c['key']:c for c in reference['cases']};predictions={r['key']:r for r in json.loads((IMPROVE/'learning-v5/forest-diagnostic/predictions.json').read_text()) if r['operating_point']=='cost5'};original_fens={c['fen_before'] for c in reference['cases']};del reference
start=time.monotonic();differences=[];score_differences=[];max_error=0;awards=0
for start_index in range(0,len(inputs),64):
 batch=extract_batch(inputs[start_index:start_index+64])
 for offset,actual in enumerate(batch):
  key=keys[start_index+offset];want=expected[key]
  for w in ['current','previous']:
   for f,x in actual['windows'][w]['features'].items():
    y=want['windows'][w]['features'][f]
    if x!=y:differences.append({'key':key,'window':w,'feature':f,'actual':x,'expected':y})
   assert actual['windows'][w]['eligible']==want['windows'][w]['eligible']
  assert actual['confidence_sufficient']==want['confidence_sufficient'];score=score_fixed_forest(actual,model);r=predictions[key]
  err=max(abs(score['window_scores'][w]-r[f'full_{w}_raw_p']) for w in ['current','previous']);max_error=max(max_error,err)
  if score['award']!=r['full_fit_award_NOT_validation'] or err>1e-14:score_differences.append({'key':key,'max_score_difference':err})
  awards+=score['award']
 print('processed',min(start_index+64,len(inputs)),'feature_differences',len(differences),flush=True)
# Two new-to-training, unlabeled positions with existing exact saved history windows.
for name in ['six-snapshots.json','completion-snapshots.json']:snapshot_bank.update(json.loads((IMPROVE/'astra/v5/repeat-award'/name).read_text())['snapshots'])
unseen=[]
for gid,ply in [('184514610842',69),('187780686673',34)]:
 pgn=db.execute('select pgn from games where game_id=?',(gid,)).fetchone()[0];req={'pgn':pgn,'ply':ply,'snapshots':[{**snapshot_bank[f'{gid}:{p}'],'quality':quality} for p in [ply-2,ply-1,ply]]};t=prepare(**req);assert t['fen_before'] not in original_fens;assert f'{gid}:{ply}' not in keys
 features=extract_batch([req])[0];unseen.append({'audit_case':f'{gid}:{ply}','label_accessed':False,'not_training_before_position':True,'features':features,'forest':score_fixed_forest(features,model)})
# Enforced malformed-history and missing-evidence boundaries.
base=inputs[0];bad=copy.deepcopy(base);bad['snapshots'][-1]['fen']=bad['snapshots'][-2]['fen']
try:prepare(**bad);raise AssertionError('Wrong FEN accepted')
except ValueError:pass
bad=copy.deepcopy(base);bad['snapshots'][-1].pop('quality')
try:prepare(**bad);raise AssertionError('Missing provenance accepted')
except ValueError:pass
bad=copy.deepcopy(base);bad['snapshots'][-1]['current']['lines'][0]['moves']=['a1a1']
try:prepare(**bad);raise AssertionError('Illegal PV accepted')
except ValueError:pass
missing=copy.deepcopy(base);missing['snapshots'][-2]['previous']=None
mc=extract_batch([missing])[0];assert mc['windows']['previous']['eligible'] is False;assert score_fixed_forest(mc,model)['award'] is False
report={'scope':'Full PGN validated extraction;848exact numerical/missingness and model-parity checks, no retraining. Two new-to-training PGN positions use only saved engine windows and no labels.','cases':len(inputs),'features':75,'windows':1696,'feature_differences':differences,'score_differences':score_differences,'max_float_score_error':max_error,'full_training_awards_NOT_validation':awards,'checks':['all848PGN/SAN-independent legal move+snapshot+PV validation','wrong FEN rejected','missing quality provenance rejected','illegal PV rejected','missing previous window produces ineligible nonaward'],'unseen':unseen,'elapsed_seconds':time.monotonic()-start,'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
(HERE/'pipeline-checks.json').write_text(json.dumps(report,indent=2)+'\n');print('DONE',len(differences),len(score_differences),max_error,resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
