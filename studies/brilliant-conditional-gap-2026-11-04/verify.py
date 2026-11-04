"""Independent artifact/count checks for the bounded conditional-gap study."""
import collections,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;WORK=HERE.parents[1]
def read(n):return json.loads((HERE/n).read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
p=read('PROTOCOL.json');r=read('RESULTS.json');rows=read('PREDICTIONS.json');e=read('EXTRACTION.json');g=read('GAP-FEATURES.json')
freeze=read('EVALUATION-FREEZE.json');model=read('MODEL-FREEZE.json');source=read('EVALUATOR-SOURCE-FREEZE.json')
data=json.loads((WORK/'mute-chess-research-overnight-2026-11-03/studies/brilliant-training-2026-11-03/data/training.json').read_text())
cases={c['key']:c for c in data['cases']}
assert e['status']=='complete' and e['new_searches']==1419 and e['cached_searches']==62 and e['completed_cases']==1320
assert sha(HERE/'GAP-FEATURES.json')==e['feature_sha256']==freeze['feature_sha256']==r['feature_sha256']
assert sha(HERE/'ENGINE-EVIDENCE.jsonl')==e['evidence_sha256']
assert sha(HERE/'PROTOCOL.json')==e['protocol_sha256']==freeze['protocol_sha256']==r['protocol_sha256']==source['protocol_sha256']
assert sha(HERE/'evaluate.py')==r['script_sha256']==freeze['script_sha256']==source['script_sha256']==model['script_sha256']
assert sha(HERE/'extract.py')==p['extract_script_sha256']
for path,h in p['source_sha256'].items():assert sha(WORK/path)==h
keys=set();cached=new=0;coverage={w:collections.Counter() for w in ['current','previous']}
with (HERE/'ENGINE-EVIDENCE.jsonl').open() as f:
    for line in f:
        v=json.loads(line);k=v['key'];assert k not in keys;keys.add(k)
        assert any(w['eligible'] for w in cases[k]['windows'].values())
        assert v['features']==g[k]
        for w in coverage:
            feature=g[k][w];coverage[w][feature['reason']]+=1
            assert (feature['gap_cp'] is not None)==(feature['reason']=='known')
            if feature['gap_cp'] is not None:assert feature['gap_cp']>=0
        for o in v['offers']:
            cached+=o['source']=='pilot_cache';new+=o['source']=='new'
assert keys=={k for k,c in cases.items() if any(w['eligible'] for w in c['windows'].values())}
assert len(keys)==1320 and cached==62 and new==1419
assert {w:dict(c) for w,c in coverage.items()}==e['coverage']
assert len(rows)==len({x['key'] for x in rows})==3724
group_fold={};game_fold={};before_fold={}
old={x['key']:x for x in json.loads((WORK/'research/brilliant-standard-learners-2026-11-04/PREDICTIONS.json').read_text())}
for x in rows:
    k=x['key'];c=cases[k];fold=x['outer_fold']
    assert x['truth']==c['truth'] and x['group']==c['group']
    assert group_fold.setdefault(c['group'],fold)==fold
    for gid in {c['game_id']}|{a.rsplit(':',1)[0] for a in c.get('aliases',[])}:assert game_fold.setdefault(gid,fold)==fold
    before=' '.join(c['fen_before'].split()[:4]);assert before_fold.setdefault(before,fold)==fold
    assert x['outer_fold']==old[k]['outer_fold'] and x['final_calibration_fold']==old[k]['final_calibration_fold']
    for arm in ['custom_fixed','custom_retuned','standard_rf']:assert x['outer_awards'][arm]==old[k]['outer_awards'][arm]
    for kind in ['custom','standard_rf']:
        assert abs(x['outer_scores'][kind]-old[k]['outer_scores'][kind])<1e-12
        assert abs(x['final_calibration_scores'][kind]-old[k]['final_calibration_scores'][kind])<1e-12
for arm,metrics in r['outer_pooled'].items():
    for filtered,expected in [(rows,metrics),([x for x in rows if not x['pilot_group']],r['outside_pilot_groups'][arm])]:
        cc=collections.Counter(('T' if x['truth']==x['outer_awards'][arm] else 'F')+('P' if x['outer_awards'][arm] else 'N') for x in filtered)
        assert all(cc[n]==expected[n] for n in ['TP','FP','TN','FN'])
    assert all(x['eligible'] or not x['outer_awards'][arm] for x in rows)
    for n in ['TP','FP','TN','FN']:assert sum(f['test_metrics'][arm][n] for f in r['outer_folds'])==metrics[n]
assert r['fits']==101 and r['elapsed_seconds']<600 and r['peak_rss_bytes']<512*1024**2
assert e['elapsed_seconds']<900
assert model['selected']==r['final_training_only_selection']['selected']
modelpath=HERE/('selected-model.json' if model['selected']['kind'].startswith('custom') else 'selected-model.joblib')
assert sha(modelpath)==model['model_sha256']
out={'status':'pass','checks':['allinput/script/protocol/model/evidencehashes','1320eligiblecases covered without label selection',
  '1481branches exactly1419new+62cached','featurecoverage/missingness recomputed','3724unique predictions',
  'wholegame/alias/beforeposition fold integrity','priorouter/finalfold identity','bothoriginal learner scores and3original arm decisions reproduced',
  'pooled and per-fold confusion counts recomputed','nonpilot-test breakdown recomputed','no ineligible awards','runtime/RSS limits','final selection/model consistency'],
  'artifact_sha256':{n:sha(HERE/n) for n in ['PROTOCOL.json','extract.py','evaluate.py','verify.py','EXTRACTION.json','GAP-FEATURES.json','EVALUATION-FREEZE.json','RESULTS.json','PREDICTIONS.json','MODEL-FREEZE.json']}}
(HERE/'VERIFICATION.json').write_text(json.dumps(out,indent=2)+'\n')
print('PASS:',len(out['checks']),'artifact and count checks.')
