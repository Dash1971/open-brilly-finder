"""Read-only case comparison export. No models, cutoffs or new classification rule."""
import json,sys,math,hashlib
from pathlib import Path
sys.dont_write_bytecode=True;sys.path.insert(0,'/private/tmp/brilly-research-deps')
import chess
H=Path(__file__).resolve().parent;S=H.parent/'brilliant-mating-prospective-2026-11-04'
read=lambda p:json.loads(p.read_text())
source={x['key']:x for x in read(S/'SCORED.json')['rows']};labels=read(S/'RESULTS.json')['cases'];selected=[x for x in labels if x['new_award'] or x['label']=='Brilliant']
def sanline(fen,moves):
 b=chess.Board(fen);ss=[]
 for u in moves:
  m=chess.Move.from_uci(u);assert m in b.legal_moves;ss.append(b.san(m));b.push(m)
 return ' '.join(ss)
def failures(c,w):
 f=c['features']['windows'][w]['features'];wc=lambda s:100/(1+math.exp(-.00368208*s))
 checks={'eligible':c['features']['windows'][w]['eligible'],'ec_false':f['ec_sacrifice'] is False,'physical_known':f['physical_unknown'] is False,'history_known':f['prior_history_missing'] is False,'attribution_known':f['attribution_unknown'] is False,'mating_acceptance':f['mating_acceptance'] is True,'no_prior_same_offer':f['prior_offer_gain_same_square_max']==0,'no_prior_original_offer':f['prior_offer_gain_original_square_max']==0,'played_rank1':f['same_root_rank']==1,'gap_above10':f['best_second_gap_pp'] is not None and f['best_second_gap_pp']>10,'improvement_above5':f['prior_mapped_score'] is not None and wc(f['best_mapped_score'])-wc(f['prior_mapped_score'])>5}
 return [k for k,v in checks.items() if not v]
out=[]
for l in selected:
 c=source[l['key']];b=chess.Board(c['fen_before']);mover=b.turn
 roots={}
 for idx,name in enumerate(['prior_own_after','before','after']):
  s=c['snapshots'][idx];roots[name]={w:[{**{k:line[k] for k in ['cp','mate'] if k in line},'cp_mover':(1 if mover else -1)*line['cp'] if 'cp'in line else None,'mate_mover':(1 if mover else -1)*line['mate'] if 'mate'in line else None,'san':sanline(s['fen'],line['moves']),'moves':line['moves']} for line in s[w]['lines']] if s.get(w) else None for w in ['current','previous']}
 accepts=[]
 for a in c['acceptance_evidence']:
  aa=chess.Board(c['fen_after']);accept_san=aa.san(chess.Move.from_uci(a['uci']));accepts.append({'uci':a['uci'],'san':accept_san,'windows':{w:[{**{k:line[k] for k in ['cp','mate'] if k in line},'cp_mover':(1 if mover else -1)*line['cp'] if 'cp'in line else None,'mate_mover':(1 if mover else -1)*line['mate'] if 'mate'in line else None,'san':sanline(a['accepted_fen'],line['moves']),'moves':line['moves']} for line in a['snapshot'][w]['lines']] if a['snapshot'].get(w) else None for w in ['current','previous']}})
 group='correct_award' if l['new_award'] and l['label']=='Brilliant' else 'wrong_award' if l['new_award'] else 'missed_brilliant'
 out.append({'group':group,**l,'fen_before':c['fen_before'],'fen_after':c['fen_after'],'fen_prior':c['previous_own_after'],'mover':'white' if mover else 'black','pgn':c['pgn'],'uci':c['uci'],'offers':c['offers'],'witnesses':c['witnesses'],'roots':roots,'acceptances':accepts,'features':c['features'],'window_scores':c['window_scores'],'base_rule_failures':{w:failures(c,w) for w in ['current','previous']},'material_features':c['material_features'],'material_diagnostics':c['material_diagnostics']})
(H/'CASES.json').write_text(json.dumps(out,indent=2)+'\n')
for group in ['correct_award','wrong_award','missed_brilliant']:
 rr=[r for r in out if r['group']==group];(H/(group+'.json')).write_text(json.dumps(rr,indent=2)+'\n')
print('Prepared',len(out),'cases.')
for c in out:
 f=c['features']['windows']['current']['features'];print(c['group'],c['key'],c['san'],c['base_rule_failures'],c['material_features'])
