"""Focused independent verification of frozen rule, folds, awards and counts."""
import collections,hashlib,json,math,sys
from pathlib import Path
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;W=H.parents[1]
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
r=read(H/'RESULTS.json');p=read(H/'PROTOCOL.json');freeze=read(H/'EVALUATION-FREEZE.json');model=read(H/'MODEL-FREEZE.json');rows=read(H/'PREDICTIONS.json')
data=read(W/'mute-chess-research-overnight-2026-11-03/studies/brilliant-training-2026-11-03/data/training.json');cases={c['key']:c for c in data['cases']}
old={x['key']:x for x in read(W/'research/brilliant-standard-learners-2026-11-04/PREDICTIONS.json')}
for n,f in [('protocol','PROTOCOL.json'),('script','evaluate.py'),('rule','rule.py')]:assert sha(H/f)==freeze[n+'_sha256']==r[n+'_sha256']
for path,digest in p['source_sha256'].items():assert sha(W/path)==digest
assert model['selected']==r['final_training_only_selection']['selected']
assert model['script_sha256']==freeze['script_sha256'] and model['protocol_sha256']==freeze['protocol_sha256']
assert sha(H/('selected-model.json' if model['selected']['kind']=='custom' else 'selected-model.joblib'))==model['model_sha256']
def independent_base_rule(c):
 if not c['confidence_sufficient']:return False
 for w in ['current','previous']:
  d=c['windows'][w];f=d['features']
  if not d['eligible']:return False
  for n in ['ec_sacrifice','physical_unknown','prior_history_missing','attribution_unknown']:
   if f[n] is not False:return False
  if f['mating_acceptance'] is not True:return False
  for n in ['prior_offer_gain_same_square_max','prior_offer_gain_original_square_max','same_root_rank','best_second_gap_pp','best_mapped_score','prior_mapped_score']:
   if f[n] is None or not math.isfinite(f[n]):return False
  if f['prior_offer_gain_same_square_max']!=0 or f['prior_offer_gain_original_square_max']!=0:return False
  if f['same_root_rank']!=1 or f['best_second_gap_pp']<=10:return False
  chances=[100/(1+math.exp(-.00368208*max(-1000,min(1000,f[n])))) for n in ['best_mapped_score','prior_mapped_score']]
  if chances[0]-chances[1]<=5:return False
 return True
features=read(H/'FEATURES.json')
def independent_rule(c):
 return independent_base_rule(c) and all(features[c['key']][w]['nonmate_material_win']==0 for w in ['current','previous'])
assert len(rows)==len({x['key'] for x in rows})==3724
groupfold={};gamefold={};fenfold={}
for x in rows:
 c=cases[x['key']];o=old[x['key']];fold=x['outer_fold']
 assert x['truth']==c['truth'] and x['group']==c['group'] and x['mating_rule']==independent_rule(c)
 assert groupfold.setdefault(c['group'],fold)==fold
 for game in {c['game_id']}|{a.rsplit(':',1)[0] for a in c.get('aliases',[])}:assert gamefold.setdefault(game,fold)==fold
 assert fenfold.setdefault(' '.join(c['fen_before'].split()[:4]),fold)==fold
 assert fold==o['outer_fold'] and x['final_calibration_fold']==o['final_calibration_fold']
 for kind in ['custom','standard_rf']:
  for field in ['outer_scores','final_calibration_scores']:assert abs(x[field][kind]-o[field][kind])<1e-12
 for arm in ['custom_fixed','custom_retuned','standard_rf']:assert x['outer_awards'][arm]==o['outer_awards'][arm]
 selection=r['outer_folds'][fold]['inner_selection']
 for arm,pred in x['outer_awards'].items():
  point=selection['selected'] if arm=='selected_procedure' else selection['base_selected'] if arm=='base_only_selector' else selection['points'][arm]
  expected=(x['outer_scores'][point['kind']]>=point['threshold'] and x['eligible']) or (x['mating_rule'] and point.get('mating_enabled',False))
  assert pred==expected and (x['eligible'] or not pred)
for sel in [f['inner_selection'] for f in r['outer_folds']]+[r['final_training_only_selection']]:
 ref=sel['points']['custom_fixed']
 for arm,point in sel['points'].items():
  if not arm.endswith('_always'):
   assert point['FP']<=ref['FP'] and point['FP']*ref['TP']<=ref['FP']*point['TP']
  if arm.endswith('_gated'):assert point['mating_enabled']==(point['inner_rule_added_TP']>0 and point['inner_rule_added_FP']==0)
 assert not sel['selected']['arm'].endswith('_always')
def counts(rr,arm):
 cc=collections.Counter(('T' if x['truth']==x['outer_awards'][arm] else 'F')+('P' if x['outer_awards'][arm] else 'N') for x in rr)
 return {n:cc[n] for n in ['TP','FP','TN','FN']}
for arm,expected in r['outer_pooled'].items():
 assert counts(rows,arm)=={n:expected[n] for n in ['TP','FP','TN','FN']}
 ex=r['outside_pilot_groups'][arm];assert counts([x for x in rows if not x['pilot_group']],arm)=={n:ex[n] for n in ['TP','FP','TN','FN']}
 for fold in r['outer_folds']:
  ex=fold['test_metrics'][arm];assert counts([x for x in rows if x['outer_fold']==fold['fold']],arm)=={n:ex[n] for n in ['TP','FP','TN','FN']}
assert r['fits']==51 and r['elapsed_seconds']<600 and r['peak_rss_bytes']<512*1024**2
# Fair selector-only counterfactual: same available base models, remove rule arms.
# Prior standard study also offered hist_boost, so its selected_procedure isn't this control.
priority={'custom_fixed':4,'custom_retuned':3,'standard_rf':2};basearms={}
for f in r['outer_folds']:
 points=f['inner_selection']['points'];basearms[f['fold']]=max(priority,key=lambda a:(points[a]['TP'],-points[a]['FP'],priority[a]))
cp=[{**x,'outer_awards':{'base_only_selector':x['outer_awards'][basearms[x['outer_fold']]]}} for x in rows]
# Feature hashes and independent material arithmetic on every saved mating-capture PV.
fp=read(H/'FEATURE-PROTOCOL.json');ex=read(H/'EXTRACTION.json')
assert sha(H/'FEATURES.json')==freeze['feature_sha256']==ex['feature_sha256']
assert sha(H/'FEATURE-PROTOCOL.json')==freeze['feature_protocol_sha256']==ex['protocol_sha256']
assert sha(H/'EXTRACTION.json')==freeze['extraction_sha256']
assert sha(H/'extract.py')==fp['extract_script_sha256']
for path,digest in fp['source_sha256'].items():assert sha(W/path)==digest
assert sha(H/'CHECKS.json')==ex['checks_sha256'] and sha(H/'HIT-TRACES.json')==ex['hit_traces_sha256']
assert set(features)==set(cases)
sys.path.insert(0,'/private/tmp/brilly-research-deps')
import chess
raw={x['key']:x for x in map(json.loads,(W/'research/brilliant-conditional-gap-2026-11-04/ENGINE-EVIDENCE.jsonl').read_text().splitlines())}
def material(b,mover):
 return sum(v*(len(b.pieces(p,mover))-len(b.pieces(p,not mover))) for p,v in [(1,90),(2,300),(3,300),(4,500),(5,1000)])
linecount=0
for key,dd in ex['diagnostics'].items():
 c=cases[key];before=chess.Board(c['fen_before']);mover=before.turn;baseline=material(before,mover)
 for win,d in dd.items():
  states=[]
  for capture in d['captures']:
   offer=next(o for o in raw[key]['offers'] if o['uci']==capture['acceptance']);accepted=chess.Board(c['fen_after']);accepted.push_uci(offer['uci']);assert accepted.fen()==offer['accepted_fen']
   for reply in capture['mate_in_one_witnesses']:
    b=accepted.copy();b.push_uci(reply);assert b.is_checkmate()
   if capture['reason']=='missing_complete_window':states.append(None)
   snap=offer['snapshot'].get(win)
   if not snap:continue
   for line,t in zip(snap['lines'],capture['lines']):
    b=accepted.copy();gain=None;mate=False
    for ply,u in enumerate(line.get('moves',[]),2):
     assert chess.Move.from_uci(u) in b.legal_moves;b.push_uci(u);mate=mate or b.is_checkmate()
     if ply==12:gain=material(b,mover)-baseline
    assert gain==t['gain12_cp']
    favorable=line.get('mate') is None and line.get('cp') is not None and (1 if mover else -1)*line['cp']>0
    draw=t['terminal'] and t['terminal']['winner'] is None
    expected=0 if not favorable or mate or draw else None if gain is None else int(gain>=300)
    assert expected==t['state'];states.append(expected);linecount+=1
  expected=1 if 1 in states else None if None in states or not d['captures'] else 0
  assert expected==features[key][win]['nonmate_material_win']
assert linecount==read(H/'CHECKS.json')['assertions']['legal_full_saved_pvs']==532
assert counts(cp,'base_only_selector')=={n:r['outer_pooled']['base_only_selector'][n] for n in ['TP','FP','TN','FN']}
diag=read(H/'DIAGNOSTICS.json');assert not diag['ne5']['training_position_overlap']
assert all(x['refined_rule_match'] and x['final_selected_policy_awarded'] for x in diag['ne5']['profiles'])
checks=['frozen source, protocol, evaluator, rule and selected model hashes','independent rule recomputation on all3724cases','whole group/game/alias/position fold integrity','original outer/final model scores and awards exactly reproduced','all awards recomputed from frozen operating points and rule','inner activation and wrong-award constraints','pooled/per-fold/nonpilot confusion counts','runtime/RSS/fit limits','same-model baseline-only selector counterfactual','frozen feature protocol/source hashes','all532saved mating-capture PVs legal and materialgain arithmetic','allfeature states and conservative missingness independently recomputed','Ne5 separate and included only as diagnostic']
out={'status':'pass','checks':checks,'same_model_baseline_only_selector':{'fold_arms':basearms,**counts(cp,'base_only_selector')},'artifact_sha256':{f:sha(H/f) for f in ['rule.py','evaluate.py','PROTOCOL.json','EVALUATION-FREEZE.json','RESULTS.json','PREDICTIONS.json','DIAGNOSTICS.json','FEATURES.json','FEATURE-PROTOCOL.json','EXTRACTION.json','verify.py']}}
(H/'VERIFICATION.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out['same_model_baseline_only_selector']));print('PASS:',len(checks),'focused checks')
