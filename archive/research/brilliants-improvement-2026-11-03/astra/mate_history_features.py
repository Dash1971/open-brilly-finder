"""Bounded descriptive board features on the 618 already-unblinded development cases.
No engine or policy scoring. Legal same-square offers use the frozen 90/300/300/500/1000
values and > current capture/promotion credit+100 qualification. Previous raw vulnerability
is not reduced by the preceding own move's capture credit. Mate witnesses are exact legal
mate-in-one replies after a qualifying capture. UNKNOWN remains explicit on budget failure.
"""
import sys,json,importlib.util,hashlib,time
from pathlib import Path
sys.path.insert(0,'/private/tmp/brilly-research-deps')
import chess
P=Path('mute-chess-research/studies/brilliant-moves');O=Path('research/brilliants-improvement-2026-11-03/astra')
s=importlib.util.spec_from_file_location('mp','mute-chess-research/studies/brilliant-moves-2026-11-03/material-features.py');mp=importlib.util.module_from_spec(s);s.loader.exec_module(mp)
a=json.loads((P/'analysis-baseline.json').read_text());rs={f"{r['game_id']}:{r['ply']}":r for r in json.loads((P/'comparison-v3.json').read_text())['rows']}
def mates(b):
 result=[]
 for m in list(b.legal_moves):
  b.push(m);yes=b.is_checkmate();b.pop()
  if yes:result.append({'uci':m.uci(),'san':b.san(m)})
 return result
def acceptances(b,square):
 result=[];budget=mp.Budget()
 for m in list(b.generate_legal_captures()):
  if m.to_square!=square:continue
  san=b.san(m);value=mp.gain(b,m);b.push(m)
  try:g=value-mp.same_square(b,square,budget);reply_count=b.legal_moves.count();proof=mates(b)
  finally:b.pop()
  result.append({'uci':m.uci(),'san':san,'exchange_gain':g,'mate_in_one_replies':proof,'mate_candidate_count':reply_count})
 return result
t0=time.monotonic();out=[]
for t in a['targets']:
 key=f"{t['game_id']}:{t['ply']}";r=rs[key];b=chess.Board(t['fen_before']);c=chess.Board(t['fen_after']);m=chess.Move.from_uci(t['uci']);prev=chess.Board(a['snapshots'][t['snapshot_ids'][-3]]['fen']) if len(t['snapshot_ids'])>=3 else None
 credit=max(0,-mp.material(c)-mp.material(b));row={'key':key,'san':t['san'],'label':r['primary_fresh_binary_label'],'v3_symbol':r['mute_v3']['symbol'],'check_evasion':b.is_check(),'gives_check':c.is_check(),'capture_promotion_credit':credit,'history_available':prev is not None,'offers':[],'unknown':[]}
 try:
  if c.is_game_over(claim_draw=False):
   # Match classifier terminal semantics: do not infer automatic draw by game history.
   terminal=not any(c.legal_moves) or c.is_insufficient_material()
  else:terminal=False
  if not terminal:
   for square,piece in c.piece_map().items():
    if piece.color==c.turn or piece.piece_type in (1,6):continue
    acceptance=acceptances(c,square);qualified=[z for z in acceptance if z['exchange_gain']>credit+100]
    if not qualified:continue
    old=m.from_square if square==m.to_square else square
    if b.is_castling(m) and piece.piece_type==chess.ROOK:
     rank=chess.square_rank(m.from_square)
     if square==chess.square(5 if m.to_square>m.from_square else 3,rank):old=chess.square(7 if m.to_square>m.from_square else 0,rank)
    oldpiece=prev.piece_at(old) if prev else None
    oldacc=acceptances(prev,old) if oldpiece and oldpiece.color==piece.color else []
    row['offers'].append({'piece':piece.symbol(),'square':chess.square_name(square),'piece_moved_this_ply':square!=old,'previous_square':chess.square_name(old) if prev else None,'previous_piece_type':oldpiece.symbol() if oldpiece else None,'previous_exchange_gain':max([z['exchange_gain'] for z in oldacc]+[0]) if prev else None,'previous_legal_acceptances':oldacc,'qualifying_acceptances':qualified,'current_exchange_gain':max(z['exchange_gain'] for z in qualified)})
 except TimeoutError as e:row['unknown'].append(str(e))
 for offer in row['offers']:
  offer['any_acceptance_mate_in_one']=any(z['mate_in_one_replies'] for z in offer['qualifying_acceptances'])
  offer['all_acceptances_mate_in_one']=all(z['mate_in_one_replies'] for z in offer['qualifying_acceptances'])
 row['has_piece_with_all_acceptances_mate_in_one']=any(z['all_acceptances_mate_in_one'] for z in row['offers']) if not row['unknown'] else None
 row['all_qualifying_acceptances_mate_in_one']=bool(row['offers']) and all(z['all_acceptances_mate_in_one'] for z in row['offers']) if not row['unknown'] else None
 row['qualifying_mate_probe_child_positions_upper_bound']=sum(1+z['mate_candidate_count'] for o in row['offers'] for z in o['qualifying_acceptances'])
 row['published_raw_offer']=r['mute_piece_offer']
 row['raw_offer_parity']=bool(row['offers'])==r['mute_piece_offer'] if not row['unknown'] else None
 row['acceptance_mate_in_one']=any(z['mate_in_one_replies'] for offer in row['offers'] for z in offer['qualifying_acceptances']) if not row['unknown'] else None
 row['unchanged_offer_check_evasion']=bool(row['check_evasion'] and prev and row['offers'] and all(not z['piece_moved_this_ply'] and z['previous_exchange_gain']==z['current_exchange_gain'] for z in row['offers'])) if not row['unknown'] else None
 out.append(row)
result={'scope':'All 618 cases are now development. Descriptive board features only; no new classifier replay or validation.','source_analysis_sha256':hashlib.sha256((P/'analysis-baseline.json').read_bytes()).hexdigest(),'elapsed_seconds':time.monotonic()-t0,'rows':out}
(O/'all-618-mate-history-features.json').write_text(json.dumps(result,indent=2)+'\n')
print('rows',len(out),'unknown',sum(bool(x['unknown']) for x in out),'seconds',result['elapsed_seconds'])
for label in ['brilliant','non_brilliant']:
 z=[x for x in out if x['label']==label];print(label,'matewitness',sum(x['acceptance_mate_in_one'] is True for x in z),'continuation',sum(x['unchanged_offer_check_evasion'] is True for x in z))
