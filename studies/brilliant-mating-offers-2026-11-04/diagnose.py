"""Post-evaluation descriptions only; no revised rules or fitted parameters."""
import json,math,sys
from pathlib import Path
sys.dont_write_bytecode=True
from rule import mating_rule
H=Path(__file__).resolve().parent;W=H.parents[1]
def read(p):return json.loads(p.read_text())
data=read(W/'mute-chess-research-overnight-2026-11-03/studies/brilliant-training-2026-11-03/data/training.json');cases={c['key']:c for c in data['cases']}
rows=read(H/'PREDICTIONS.json');result=read(H/'RESULTS.json')
sys.path.insert(0,'/private/tmp/brilly-research-deps')
import chess
fields=['best_mapped_score','after_mapped_score','prior_mapped_score','best_second_gap_pp','same_root_rank','ec_sacrifice','mating_acceptance','physical_debt3_min','physical_debt3_max','offered_role_q','offered_role_r','offered_role_n','offered_role_b','offered_piece_moved']
evidence={r['key']:r for r in [json.loads(line) for line in (W/'research/brilliant-conditional-gap-2026-11-04/ENGINE-EVIDENCE.jsonl').read_text().splitlines()]}
def describe(r):
 c=cases[r['key']];b=chess.Board(c['fen_before']);move=chess.Move.from_uci(c['uci']);san=b.san(move);b.push(move)
 witnesses=[]
 for offer in evidence.get(r['key'],{}).get('offers',[]):
  bb=b.copy();m=chess.Move.from_uci(offer['uci']);a=bb.san(m);bb.push(m)
  for reply in list(bb.legal_moves):
   rs=bb.san(reply);bb.push(reply)
   if bb.is_checkmate():witnesses.append([a,rs])
   bb.pop()
 return {**r,'game_id':c['game_id'],'san':san,'uci':c['uci'],'fen_before':c['fen_before'],'negative_bucket':c['negative_bucket'], 'mate_acceptance_witnesses':witnesses,'features':{w:{n:c['windows'][w]['features'][n] for n in fields} for w in ['current','previous']}}
hits=[describe(r) for r in rows if r['mating_rule']]
def counts(rr):
 return {a:{'TP':sum(r['truth'] and r['outer_awards'][a] for r in rr),'FP':sum(not r['truth'] and r['outer_awards'][a] for r in rr),'positives':sum(r['truth'] for r in rr),'negatives':sum(not r['truth'] for r in rr)} for a in result['outer_pooled']}
hard=[r for r in rows if r['eligible'] and not cases[r['key']]['windows']['current']['features']['ec_sacrifice']]
fresh=[r for r in hard if r['cohort'].startswith('batch-')]
# Final model is diagnostic only; user's Chess.com label is not fabricated.
freeze=read(H/'MODEL-FREEZE.json');point=freeze['selected']
if point['kind']=='custom':
 model=read(H/'selected-model.json')
 def score(f):
  vals=[float(f[n]) if f[n] is not None else math.nan for n in data['predictors']]+[float(f[n] is None) for n in data['predictors']]
  ps=[]
  for tree in model['trees']:
   n=tree
   while n['kind']=='split':
    v=vals[n['feature_index']];n=n['left' if math.isnan(v) or v<=n['threshold'] else 'right']
   ps.append(n['raw_p'])
  return sum(ps)/len(ps)
else:
 import joblib,numpy as np
 model=joblib.load(H/'selected-model.joblib')
 def score(f):
  vals=[float(f[n]) if f[n] is not None else np.nan for n in data['predictors']]+[float(f[n] is None) for n in data['predictors']]
  return float(model.predict_proba(np.array([vals]))[0,1])
ne=read(W/'research/ne5-queen-sacrifice-2026-11-04/DIAGNOSTICS.json');sn=read(W/'research/ne5-queen-sacrifice-2026-11-04/SNAPSHOTS.json')
fen=' '.join(sn['profiles'][0]['input']['positions'][1].split()[:4])
overlaps=[c['key'] for c in cases.values() if ' '.join(c['fen_before'].split()[:4])==fen]
nei=[]
for n in ne['rows']:
 f=n['forest'];c={'confidence_sufficient':f['confidenceSufficient'],'windows':f['windows']};rule=mating_rule(c);ss={w:score(c['windows'][w]['features']) for w in ['current','previous']};base=min(ss.values())>=point['threshold']
 nei.append({'budget':n['budget'],'rule_matches':rule,'saved_deployed_model_awarded':f['awarded'],'research_final_model_scores':ss,'research_final_model_awarded':base,'always_on_addon_awarded':base or rule,'final_selected_policy_awarded':base or (point.get('mating_enabled',False) and rule)})
out={'scope':'Post-evaluation diagnostics; no revised parameters. Ne5 Chess.com label unverified, not included in performance counts.','rule_hits':hits,'hard_subgroup':counts(hard),'fresh_hard_subgroup':counts(fresh),'rule_subgroup':counts([r for r in rows if r['mating_rule']]),'ne5':nei,'ne5_dataset_position_overlaps':overlaps}
(H/'DIAGNOSTICS.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({'rule_hits':[{k:r[k] for k in ['key','truth','cohort','san','mate_acceptance_witnesses']} for r in hits], 'ne5':nei,'position_overlaps':overlaps},indent=2))
