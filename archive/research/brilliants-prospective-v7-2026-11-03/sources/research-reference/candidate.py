"""Frozen narrow recovery guard diagnostic; no labels in classify_guard()."""
import json,time,hashlib
from pathlib import Path
from probe import chess,ROOT,PUBLIC,Budget,physical,gain,see,probe
def classify_guard(row,snapshot):
 before=chess.Board(row['fen_before']);played=chess.Move.from_uci(row['uci'])
 if before.is_check() or not before.is_capture(played) or played.promotion or before.gives_check(played):return {'veto':False,'status':'ineligible'}
 if not snapshot or not snapshot.get('current') or not snapshot.get('previous'):return {'veto':False,'status':'missing-window'}
 try:roots=[chess.Move.from_uci(snapshot[w]['lines'][0]['moves'][0]) for w in ['current','previous']]
 except (KeyError,IndexError,ValueError):return {'veto':False,'status':'missing-root'}
 after=chess.Board(row['fen_after']);color=before.turn;baseline=physical(before,color);credit=max(0,physical(after,color)-baseline);budget=Budget();accepted=[]
 static=before.copy();static.turn=not color;static.ep_square=None
 try:
  for m in list(after.generate_legal_captures()):
   p=after.piece_at(m.to_square)
   if not p or p.piece_type in (chess.PAWN,chess.KING):continue
   g=gain(after,m);after.push(m)
   try:cost=g-see(after,m.to_square,budget)
   finally:after.pop()
   if cost<=credit+100:continue
   if m.to_square==played.to_square:return {'veto':False,'status':'new-moved-offer'}
   if m not in static.legal_moves or static.piece_at(m.from_square)!=after.piece_at(m.from_square) or static.piece_at(m.to_square)!=p:return {'veto':False,'status':'new-capture-lane'}
   oldgain=gain(static,m);static.push(m)
   try:oldcost=oldgain-see(static,m.to_square,budget)
   finally:static.pop()
   if oldcost!=cost:return {'veto':False,'status':'changed-exchange-liability'}
   accepted.append(m.uci())
  if not accepted or any(m.uci() not in accepted for m in roots):return {'veto':False,'status':'best-defense-declines-offer','roots':[m.uci() for m in roots]}
  return {**probe(row,budget),'best_reply_roots':[m.uci() for m in roots],'existing_acceptances':accepted}
 except TimeoutError:return {'veto':False,'status':'unknown','nodes':budget.nodes}
def main():
 snapshots={}
 for fn in ['development-baseline.json','development-panel.json','test-baseline.json']:snapshots.update(json.loads((PUBLIC/'data'/fn).read_text())['snapshots'])
 rows=json.loads((PUBLIC/'moves.json').read_text());out=[];start=time.monotonic()
 for row in rows:
  if not row['S_award']:continue
  key=f"{row['game_id']}:{row['ply']}";result=classify_guard(row,snapshots.get(key));out.append({'key':key,'san':row['san'],'role':row['role'],'truth':row['is_brilliant'],**result})
 changes=[r for r in out if r['veto']]
 summary={'cases':len(rows),'S_awards':len(out),'removed_true':sum(r['truth'] for r in changes),'removed_false':sum(not r['truth'] for r in changes),'unknown':sum(r['status']=='unknown' for r in out),'elapsed_seconds':time.monotonic()-start,'source_hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),ROOT/'probe.py',ROOT/'CANDIDATE-PLAN.json']},'rows':out}
 (ROOT/'candidate-results.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({k:v for k,v in summary.items() if k!='rows'}));print(json.dumps(changes))
if __name__=='__main__':main()
