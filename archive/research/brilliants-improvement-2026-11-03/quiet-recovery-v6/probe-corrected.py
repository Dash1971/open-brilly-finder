"""One finite recovery diagnostic; labels never enter probe()."""
import sys,json,time,hashlib
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,'/private/tmp/brilly-research-deps')
import chess
ROOT=Path(__file__).resolve().parent
PUBLIC=ROOT.parents[2]/'mute-chess-research/studies/brilliant-moves'
V={chess.PAWN:90,chess.KNIGHT:300,chess.BISHOP:300,chess.ROOK:500,chess.QUEEN:1000,chess.KING:0}
class Budget:
 def __init__(self):self.nodes=0;self.start=time.monotonic()
 def tick(self):
  self.nodes+=1
  if self.nodes>100000 or time.monotonic()-self.start>1:raise TimeoutError
def physical(b,color):return sum(V[p.piece_type]*(1 if p.color==color else -1) for p in b.piece_map().values())
def gain(b,m):
 p=b.piece_at(m.to_square)
 return (90 if b.is_en_passant(m) else V[p.piece_type] if p else 0)+(V[m.promotion]-90 if m.promotion else 0)
def see(b,s,budget):
 budget.tick();best=0
 for m in list(b.generate_legal_captures()):
  if m.to_square!=s:continue
  g=gain(b,m);b.push(m)
  try:v=g-see(b,s,budget)
  finally:b.pop()
  best=max(best,v)
 return best
def recovered(b,color,baseline,budget):
 budget.tick()
 if b.is_game_over():return None
 for m in list(b.generate_legal_captures()):
  san=b.san(m);b.push(m)
  try:
   if b.is_game_over() or b.is_check():continue
   value=physical(b,color)-see(b,m.to_square,budget)
   if value>=baseline-100:return [san]
  finally:b.pop()
 return None
def response(b,color,baseline,budget):
 choices=[m for m in b.legal_moves if not b.is_capture(m) and not m.promotion]
 choices.sort(key=lambda m:(not b.gives_check(m),m.uci()))
 for m in choices:
  budget.tick();san=b.san(m);b.push(m)
  try:
   replies=list(b.legal_moves)
   if not replies:continue
   witnesses=[]
   for reply in replies:
    budget.tick();rsan=b.san(reply);b.push(reply)
    try:rec=recovered(b,color,baseline,budget)
    finally:b.pop()
    if rec is None:break
    witnesses.append({'reply':rsan,'recoup':rec})
   else:return {'quiet':san,'all_legal_replies':len(replies),'witnesses':witnesses}
  finally:b.pop()
 return None
def probe(row):
 before=chess.Board(row['fen_before']);played=chess.Move.from_uci(row['uci'])
 if not before.is_capture(played) or played.promotion or before.gives_check(played):return {'status':'ineligible','veto':False}
 color=before.turn;baseline=physical(before,color);after=chess.Board(row['fen_after']);credit=max(0,physical(after,color)-baseline);budget=Budget();accepted=[]
 try:
  for m in list(after.generate_legal_captures()):
   p=after.piece_at(m.to_square)
   if not p or p.piece_type in (chess.PAWN,chess.KING):continue
   g=gain(after,m);san=after.san(m);after.push(m)
   try:
    cost=g-see(after,m.to_square,budget)
    if cost<=credit+100:continue
    if m.to_square==played.to_square:return {'status':'moved-offer','veto':False,'nodes':budget.nodes}
    result=response(after,color,baseline,budget)
    accepted.append({'acceptance':san,'cost':cost,'response':result})
   finally:after.pop()
  return {'status':'complete' if accepted else 'no-offer','veto':bool(accepted) and all(a['response'] is not None for a in accepted),'nodes':budget.nodes,'acceptances':accepted}
 except TimeoutError:return {'status':'unknown','veto':False,'nodes':budget.nodes,'acceptances':accepted}
def main():
 rows=json.loads((PUBLIC/'moves.json').read_text());out=[];start=time.monotonic()
 for row in rows:
  if not row['S_award']:continue
  result=probe(row);out.append({'key':f"{row['game_id']}:{row['ply']}",'san':row['san'],'role':row['role'],'truth':row['is_brilliant'],**result})
  if result['veto'] or result['status']=='unknown':print(json.dumps({k:out[-1][k] for k in ['key','san','truth','status','veto','nodes']}),flush=True)
 summary={'applied_to_S_awards':len(out),'removed_true':sum(r['veto'] and r['truth'] for r in out),'removed_false':sum(r['veto'] and not r['truth'] for r in out),'unknown':sum(r['status']=='unknown' for r in out),'elapsed_seconds':time.monotonic()-start,'rows':out,'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'plan_sha256':hashlib.sha256((ROOT/'PLAN.json').read_bytes()).hexdigest()}
 (ROOT/'results.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({k:v for k,v in summary.items() if k!='rows'}))
if __name__=='__main__':main()
