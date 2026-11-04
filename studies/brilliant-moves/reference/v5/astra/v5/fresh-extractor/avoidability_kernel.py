import sys
import chess
from feature_kernel import pk
mp=pk.mp
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
