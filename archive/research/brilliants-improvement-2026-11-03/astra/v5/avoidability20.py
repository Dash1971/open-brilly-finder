"""Initial 20-case descriptive avoidability probe. No engine or policy tuning."""
import json,sys,time,importlib.util
from pathlib import Path
sys.path.insert(0,'/private/tmp/brilly-research-deps')
import chess
R=Path('research/brilliants-improvement-2026-11-03');O=R/'astra/v5';A=json.loads((R/'validation/analysis-baseline.json').read_text());T={f"{t['game_id']}:{t['ply']}":t for t in A['targets']};P={x['key']:x for x in json.loads((O/'physical-818.json').read_text()) if x['cohort']=='new200'}
s=importlib.util.spec_from_file_location('mp','mute-chess-research/studies/brilliant-moves-2026-11-03/material-features.py');mp=importlib.util.module_from_spec(s);s.loader.exec_module(mp)
class Budget:
 def __init__(self,cap):self.cap=cap;self.used=0
 def tick(self):
  self.used+=1
  if self.used>self.cap:raise TimeoutError()
def raw(b):return sum(mp.VALUES[p.piece_type]*(1 if p.color==b.turn else -1) for p in b.piece_map().values())
def exchange(b,s,budget):
 budget.tick();best=0
 for m in list(b.generate_legal_captures()):
  if m.to_square!=s:continue
  val=mp.gain(b,m);b.push(m)
  try:gain=val-exchange(b,s,budget)
  finally:b.pop()
  best=max(best,gain)
 return best
def hasoffer(before,after,budget):
 budget.tick()
 if after.is_checkmate() or after.is_stalemate() or after.is_insufficient_material():return False
 credit=max(0,-raw(after)-raw(before))
 for square,p in after.piece_map().items():
  if p.color==after.turn or p.piece_type in (1,6):continue
  if exchange(after,square,budget)>credit+100:return True
 return False
def avoid(t,cap):
 b=chess.Board(t['fen_before']);budget=Budget(cap);roots=[]
 try:
  for m in sorted(b.legal_moves,key=lambda m:m.uci()):
   c=b.copy();c.push(m);offered=hasoffer(b,c,budget);roots.append({'uci':m.uci(),'san':b.san(m),'has_offer':offered})
   if not offered:return {'avoidable':True,'witness':roots[-1],'nodes':budget.used,'roots_checked':len(roots)}
 except TimeoutError:return {'avoidable':None,'nodes':budget.used-1,'roots_checked':len(roots),'reason':'shared budget exhausted'}
 return {'avoidable':False,'nodes':budget.used,'roots_checked':len(roots)}
def terminalproof(t,cap=512):
 b=chess.Board(t['fen_after']);before=chess.Board(t['fen_before']);credit=max(0,-raw(b)-raw(before));budget=Budget(cap);proofs=[]
 try:
  for m in list(b.generate_legal_captures()):
   p=b.piece_at(m.to_square)
   if not p or p.piece_type in (1,6):continue
   val=mp.gain(b,m);san=b.san(m);b.push(m)
   try:
    net=val-exchange(b,m.to_square,budget)
    if net<=credit+100:continue
    if b.is_stalemate():proofs.append({'acceptance':san,'uci':m.uci(),'stalemate':True})
   finally:b.pop()
 except TimeoutError:return {'proofs':proofs,'complete':False,'nodes':budget.used-1}
 return {'proofs':proofs,'complete':True,'nodes':budget.used}
def phase(t):return sum({1:0,2:1,3:1,4:2,5:4,6:0}[p.piece_type] for p in chess.Board(t['fen_before']).piece_map().values())
def matchcost(fp,tp):
 f=P[fp];p=P[tp];fm=chess.Board(T[fp]['fen_before']).piece_type_at(chess.Move.from_uci(T[fp]['uci']).from_square);pm=chess.Board(T[tp]['fen_before']).piece_type_at(chess.Move.from_uci(T[tp]['uci']).from_square)
 fv={x['victim'].lower() for x in f['acceptances']};pv={x['victim'].lower() for x in p['acceptances']}
 return (0 if fv&pv else 1000)+(0 if fm==pm else 300)+abs((f['max_debt3'] or 0)-(p['max_debt3'] or 0))+abs(f['raw_before']-p['raw_before'])/2+20*abs(phase(T[fp])-phase(T[tp]))
fps=[k for k,x in P.items() if x['v4']=='!!' and not x['truth']];true=[k for k,x in P.items() if x['v4']=='!!' and x['truth']];used={'169827191694:65'};pairs=[]
for fp in fps:
 if fp=='187780686673:36':tp='169827191694:65'
 else:tp=min((k for k in true if k not in used),key=lambda k:(matchcost(fp,k),k));used.add(tp)
 pairs.append((fp,tp))
out=[]
for fp,tp in pairs:
 for k in [fp,tp]:
  t=T[k];row={'key':k,'san':t['san'],'truth':P[k]['truth'],'matched_pair_false_key':fp,'avoidability128':avoid(t,128),'avoidability512':avoid(t,512),'direct_stalemate_after_acceptance':terminalproof(t)};out.append(row)
(O/'avoidability20.json').write_text(json.dumps({'selection':'Ten fresh v4 false awards; ten distinct v4 true awards matched by offered role, mover role, physical debt, material balance and phase; Qh4/h6 pair fixed by request. All are development. Roots sorted by UCI.','rows':out},indent=2)+'\n')
for x in out:print(x['key'],x['san'],'TP' if x['truth'] else 'FP','128',x['avoidability128'],'512',x['avoidability512'],'stalemate',x['direct_stalemate_after_acceptance']['proofs'])
