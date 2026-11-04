"""Exact bounded physical kernel copied from the recorded v5 probe; no top-level818-case job."""
import sys,time,importlib.util
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,'/private/tmp/brilly-research-deps')
import chess
WORKSPACE=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('physical_reference',WORKSPACE/'mute-chess-research/studies/brilliant-moves-2026-11-03/material-features.py')
mp=importlib.util.module_from_spec(spec);spec.loader.exec_module(mp)
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
