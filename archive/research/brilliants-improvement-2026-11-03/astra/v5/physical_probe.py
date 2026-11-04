"""Development-only 3-ply conditional physical-material probe. No chess-engine search.
After each qualifying acceptance search three plies of captures/promotions, all legal
check evasions, and stand-pat only outside check. Terminal positions retain physical
material; mate and checked horizon leaves are diagnostics, never physical proof.
"""
import json,sys,time,importlib.util
from pathlib import Path
sys.path.insert(0,'/private/tmp/brilly-research-deps')
import chess
ROOT=Path('research/brilliants-improvement-2026-11-03');PUB=Path('mute-chess-research/studies/brilliant-moves');OUT=ROOT/'astra/v5'
s=importlib.util.spec_from_file_location('mp','mute-chess-research/studies/brilliant-moves-2026-11-03/material-features.py');mp=importlib.util.module_from_spec(s);s.loader.exec_module(mp)
class Budget:
 def __init__(self):self.nodes=0;self.leafchecks=0;self.mates=0;self.evasions=0;self.start=time.monotonic()
 def visit(self):
  self.nodes+=1
  if self.nodes>10000 or time.monotonic()-self.start>.25:raise TimeoutError()
def physical(b,color):return mp.material(b)*(1 if b.turn==color else -1)
def search(b,color,depth,budget,alpha=-100000,beta=100000):
 budget.visit();value=physical(b,color);moves=list(b.legal_moves)
 if not moves:
  budget.mates+=b.is_checkmate();return value,[]
 if depth==0:
  budget.leafchecks+=b.is_check();return value,[]
 check=b.is_check();selected=moves if check else [m for m in moves if b.is_capture(m) or m.promotion]
 if check:budget.evasions+=sum(not b.is_capture(m) for m in selected)
 maximizing=b.turn==color;best=(-100000 if maximizing else 100000) if check else value;line=[]
 for m in selected:
  b.push(m)
  try:score,rest=search(b,color,depth-1,budget,alpha,beta)
  finally:b.pop()
  if (score>best if maximizing else score<best):best=score;line=[m.uci()]+rest
  if maximizing:alpha=max(alpha,best)
  else:beta=min(beta,best)
  if alpha>=beta:break
 return best,line
old=json.loads((PUB/'analysis-baseline.json').read_text());new=json.loads((ROOT/'validation/analysis-baseline.json').read_text());v3={(r['game_id'],r['ply']):r for r in json.loads((PUB/'comparison-v3.json').read_text())['rows']};changes={x['key']:x for x in json.loads((ROOT/'root/concrete-offer-experiments.json').read_text())['variants']['combined']['changes']};fresh={(r['game_id'],r['ply']):r for r in json.loads((ROOT/'validation/frozen-v4-results.json').read_text())['rows']};out=[]
for cohort,data in [('old618',old),('new200',new)]:
 for t in data['targets']:
  key=f"{t['game_id']}:{t['ply']}";b=chess.Board(t['fen_before']);after=chess.Board(t['fen_after']);color=b.turn;base=physical(b,color);credit=max(0,physical(after,color)-base)
  if cohort=='old618':
   r=v3[t['game_id'],t['ply']];truth=r['primary_fresh_binary_label']=='brilliant';sym=changes[key]['experimental']['symbol'] if key in changes else r['mute_v3']['symbol']
  else:r=fresh[t['game_id'],t['ply']];truth=r['truth_brilliant'];sym=r['v4']['symbol']
  result={'key':key,'cohort':cohort,'san':t['san'],'truth':truth,'v4':sym,'raw_before':base,'credit':credit,'acceptances':[],'unknown':False};budget=Budget()
  afterscore=data['snapshots'][t['snapshot_ids'][-1]]['current']['lines'][0]
  result['winning_mate_current']=afterscore.get('mate',0)*(1 if color else -1)>0
  result['acceptance_mate_in_one']=False
  try:
   for m in list(after.generate_legal_captures()):
    victim=after.piece_at(m.to_square)
    if not victim or victim.piece_type in (1,6):continue
    san=after.san(m);value=mp.gain(after,m);after.push(m)
    try:
     net=value-mp.same_square(after,m.to_square,mp.Budget())
     if net<=credit+100:continue
     for reply in list(after.legal_moves):
      after.push(reply);result['acceptance_mate_in_one']|=after.is_checkmate();after.pop()
     outcome,line=search(after,color,3,budget)
    finally:after.pop()
    result['acceptances'].append({'uci':m.uci(),'san':san,'victim':victim.symbol(),'offer_net':net,'debt3':base-outcome,'conditional_line':mp.line_san(after,[m.uci()]+line)})
  except TimeoutError:result['unknown']=True
  result.update(nodes=budget.nodes,checked_horizon_leaves=budget.leafchecks,mate_terminals=budget.mates,quiet_evasions_generated=budget.evasions)
  result['max_debt3']=max((x['debt3'] for x in result['acceptances']),default=None) if not result['unknown'] else None
  out.append(result)
(OUT/'physical-818.json').write_text(json.dumps(out,indent=2)+'\n')
print('rows',len(out),'unknown',sum(x['unknown'] for x in out),'nodes',sum(x['nodes'] for x in out),'maxnodes',max(x['nodes'] for x in out))
for cohort in ['old618','new200']:
 for kind in ['TP','FP','FN']:
  r=[x for x in out if x['cohort']==cohort and ((x['truth'] and x['v4']=='!!') if kind=='TP' else (not x['truth'] and x['v4']=='!!') if kind=='FP' else(x['truth'] and x['v4']!='!!'))]
  print(cohort,kind,len(r),'raw_offer',sum(bool(x['acceptances']) for x in r),'debt>100',sum(x['max_debt3'] is not None and x['max_debt3']>100 for x in r),'unknown',sum(x['unknown'] for x in r))
for x in out:
 if x['cohort']=='new200' and x['v4']=='!!' and not x['truth']:print(x)
