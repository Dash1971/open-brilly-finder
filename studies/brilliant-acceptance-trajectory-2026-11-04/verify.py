"""Independent artifact/count checks for the bounded acceptance-trajectory study."""
import collections,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;WORK=HERE.parents[1]
def read(n):return json.loads((HERE/n).read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
p=read('PROTOCOL.json');r=read('RESULTS.json');rows=read('PREDICTIONS.json');e=read('EXTRACTION.json');features=read('TRAJECTORY-FEATURES.json')
freeze=read('EVALUATION-FREEZE.json');model=read('MODEL-FREEZE.json');source=read('EVALUATOR-SOURCE-FREEZE.json');fp=read('FEATURE-PROTOCOL.json')
data=json.loads((WORK/'mute-chess-research-overnight-2026-11-03/studies/brilliant-training-2026-11-03/data/training.json').read_text())
cases={c['key']:c for c in data['cases']}
assert e['status']=='complete' and e['evidence_cases']==1320 and e['offers']==1481
assert sha(HERE/'TRAJECTORY-FEATURES.json')==e['feature_sha256']==freeze['feature_sha256']==r['feature_sha256']
assert sha(HERE/'FEATURE-PROTOCOL.json')==e['protocol_sha256']==freeze['feature_protocol_sha256']
assert sha(HERE/'PROTOCOL.json')==freeze['protocol_sha256']==r['protocol_sha256']
assert sha(HERE/'evaluate.py')==r['script_sha256']==freeze['script_sha256']==source['script_sha256']==model['script_sha256']
assert sha(HERE/'extract.py')==fp['extract_script_sha256']
assert sha(HERE/'EXTRACTION-AT-FREEZE.json')==freeze['extraction_sha256']
frozen_extraction=read('EXTRACTION-AT-FREEZE.json')
assert {k:v for k,v in e.items() if k!='checks_sha256'}=={k:v for k,v in frozen_extraction.items() if k!='checks_sha256'}
for path,h in {**p['source_sha256'],**fp['source_sha256']}.items():assert sha(WORK/path)==h
assert set(features)==set(cases)
coverage={w:collections.Counter() for w in ['current','previous']}
for key,c in cases.items():
    for w in coverage:
        v=features[key][w];d=e['diagnostics'][key][w]
        assert set(v)==set(p['added_features'])
        for n,value in v.items():coverage[w][n]+=value is not None
        if not any(x['eligible'] for x in c['windows'].values()):assert all(x is None for x in v.values())
        if d['reason']!='known':continue
        steps=d['steps'];assert steps[0]['ply']==1 and len(steps)<=12
        assert v['initial_debt_cp']==steps[0]['material_debt']
        assert v['acceptance_mate_outcome'] in [-1,0,1]
        terminal=d['terminal'];full=len(steps)==12 or terminal is not None
        for horizon in [6,12]:
            expected=steps[horizon-1]['material_debt'] if len(steps)>=horizon else steps[-1]['material_debt'] if terminal else None
            assert v['material_debt'+str(horizon)+'_cp']==expected
        recovery=next((s['ply'] for s in steps if s['own_move'] and s['material_debt']<=0),None) if v['initial_debt_cp']>0 else None
        assert v['first_recovery_ply']==recovery
        assert v['recovered_by12']==(int(recovery is not None) if v['initial_debt_cp']>0 and (recovery is not None or full) else None)
        expected_draw=int(terminal['winner'] is None) if terminal else 0 if len(steps)==12 else None
        assert v['terminal_draw_by12']==expected_draw
assert {w:dict(c) for w,c in coverage.items()}==e['coverage']
for fold in r['outer_folds']:
    points=fold['inner_selection']['points'];ref=points['custom_fixed']
    for point in points.values():
        assert point['FP']<=ref['FP']
        assert point['FP']*ref['TP']<=ref['FP']*point['TP']
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
assert read('FEATURE-CHECKS.json')['status']=='passed'
assert model['selected']==r['final_training_only_selection']['selected']
modelpath=HERE/('selected-model.json' if model['selected']['kind'].startswith('custom') else 'selected-model.joblib')
assert sha(modelpath)==model['model_sha256']
out={'status':'pass','checks':['all source/script/protocol/feature/model hashes','1320 eligible cases and1481 saved branches; no new searches','all seven feature coverage, horizons, terminal and recovery definitions recomputed','all3724unique predictions and original folds','whole game/aliases/position fold integrity','baseline outer/final scores and awards exactly reproduced','inner threshold wrong-award count and fraction constraints','pooled/per-fold/nonpilot confusion counts recomputed','no ineligible awards','runtime/RSS limits','final training-only selection/model consistency'],'artifact_sha256':{n:sha(HERE/n) for n in ['PROTOCOL.json','FEATURE-PROTOCOL.json','extract.py','evaluate.py','verify.py','EXTRACTION.json','TRAJECTORY-FEATURES.json','EVALUATION-FREEZE.json','RESULTS.json','PREDICTIONS.json','MODEL-FREEZE.json']}}
(HERE/'VERIFICATION.json').write_text(json.dumps(out,indent=2)+'\n')
print('PASS:',len(out['checks']),'artifact and count checks.')
