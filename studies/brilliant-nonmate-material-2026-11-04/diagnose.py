"""Post-evaluation descriptions and separate verified-Ne5 diagnostic. No fitting/tuning."""
import importlib.util,io,json,sys,math
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,'/private/tmp/brilly-research-deps')
import chess,chess.pgn
from extract import extract_case
from base_rule import mating_rule as old_rule
H=Path(__file__).resolve().parent;W=H.parents[1]
def read(p):return json.loads(p.read_text())
data=read(W/'mute-chess-research-overnight-2026-11-03/studies/brilliant-training-2026-11-03/data/training.json');cases={c['key']:c for c in data['cases']}
features=read(H/'FEATURES.json');rows=read(H/'PREDICTIONS.json');result=read(H/'RESULTS.json');old=read(W/'research/brilliant-mating-offers-2026-11-04/DIAGNOSTICS.json');op={r['key']:r for r in read(W/'research/brilliant-mating-offers-2026-11-04/PREDICTIONS.json')}
pmap={r['key']:r for r in rows}
hits=[{**h,'new_features':features[h['key']],'new_awards':pmap[h['key']]['outer_awards'],'retained_by_refinement':pmap[h['key']]['mating_rule']} for h in old['rule_hits']]
def metrics(rr,arm):
 tp=sum(r['truth'] and r['outer_awards'][arm] for r in rr);fp=sum(not r['truth'] and r['outer_awards'][arm] for r in rr)
 return {'TP':tp,'FP':fp,'positive':sum(r['truth'] for r in rr),'negative':sum(not r['truth'] for r in rr)}
hard=[r for r in rows if r['eligible'] and not cases[r['key']]['windows']['current']['features']['ec_sacrifice']];fresh=[r for r in hard if r['cohort'].startswith('batch-')]
# Broad descriptive separation, not an independently selected classifier.
sep={}
for state in [0,1,None]:
 rr=[r for r in hard if all(features[r['key']][w]['nonmate_material_win']==state for w in ['current','previous'])]
 sep[str(state)]={'positive':sum(r['truth'] for r in rr),'negative':sum(not r['truth'] for r in rr)}
# New300k accepting-branch probes for the user's game, outside all eval rows.
pgn=(W/'research/ne5-queen-sacrifice-2026-11-04/game.pgn').read_text();g=chess.pgn.read_game(io.StringIO(pgn));b=g.board();boards=[b.copy(stack=True)]
for m in g.mainline_moves():b.push(m);boards.append(b.copy(stack=True))
e=read(H/'NE5-ACCEPTANCE.json');nf,nd=extract_case(boards[10],boards[11],e['offers'])
freeze=read(H/'MODEL-FREEZE.json');point=freeze['selected'];oldne=read(W/'research/ne5-queen-sacrifice-2026-11-04/DIAGNOSTICS.json')
if point['kind']=='custom':
 model=read(H/'selected-model.json')
 def score(f):
  vals=[float(f[n]) if f[n] is not None else math.nan for n in data['predictors']]+[float(f[n] is None) for n in data['predictors']];scores=[]
  for t in model['trees']:
   while t['kind']=='split':
    v=vals[t['feature_index']];t=t['left' if math.isnan(v) or v<=t['threshold'] else 'right']
   scores.append(t['raw_p'])
  return sum(scores)/len(scores)
else:
 import joblib,numpy as np
 model=joblib.load(H/'selected-model.joblib')
 def score(f):
  vals=[float(f[n]) if f[n] is not None else np.nan for n in data['predictors']]+[float(f[n] is None) for n in data['predictors']]
  return float(model.predict_proba(np.array([vals]))[0,1])
nei=[]
for r in oldne['rows']:
 c={'confidence_sufficient':r['forest']['confidenceSufficient'],'windows':r['forest']['windows']};oldmatch=old_rule(c);newmatch=oldmatch and all(nf[w]['nonmate_material_win']==0 for w in ['current','previous']);scores={w:score(c['windows'][w]['features']) for w in ['current','previous']};base=min(scores.values())>=point['threshold']
 nei.append({'original_position_budget':r['budget'],'acceptance_budget':300000,'original_rule_match':oldmatch,'refined_rule_match':newmatch,'baseline_scores':scores,'baseline_awarded':base,'final_selected_policy_awarded':base or (point.get('mating_enabled',False) and newmatch)})
fen=' '.join(boards[10].fen().split()[:4]);assert not [c for c in cases.values() if ' '.join(c['fen_before'].split()[:4])==fen]
out={'rule_hits':hits,'eligible_hard_separation_both_windows_same_state':sep,'hard_metrics':{a:metrics(hard,a) for a in result['outer_pooled']},'fresh_hard_metrics':{a:metrics(fresh,a) for a in result['outer_pooled']},'ne5':{'chesscom':read(H/'CHESSCOM-NE5.json'),'features':nf,'traces':nd,'profiles':nei,'training_position_overlap':False},'historical_unrefined_comparison':{a:{'TP':sum(r['truth'] and r['outer_awards'][a] for r in op.values()),'FP':sum(not r['truth'] and r['outer_awards'][a] for r in op.values())} for a in ['custom_mating_always','standard_rf_mating_always','custom_mating_gated','standard_rf_mating_gated']}}
(H/'DIAGNOSTICS.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'ne5_features':nf,'ne5_profiles':nei,'hard_separation':sep,'hits':[{k:r[k] for k in ['key','san','truth','new_features','retained_by_refinement']} for r in hits]},indent=2))
