#!/usr/bin/env python3
"""One bounded offline selection-descriptor input for additional300; no engine or network."""
import importlib.util,json,sqlite3,resource
from pathlib import Path
ROOT=Path(__file__).resolve().parent;OLD=ROOT.parent/'brilliants-600-2026-11-03'
s=importlib.util.spec_from_file_location('corpus',ROOT/'corpus.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);chess=m.chess
c=m.connect(ROOT/'corpus.sqlite3');known={x['canonical_first_four'] for x in json.loads((ROOT/'known-regression-fens.json').read_text())['positions']};out=[];targetkeys=set()
queues={}
for account in m.ACCOUNTS:
 q=json.loads((ROOT/f'{account.lower()}-ui-queue.json').read_text());queues[account]=q
 targetkeys.update((x['game_id'],x['ply']) for x in q['targets'])
values={chess.PAWN:90,chess.KNIGHT:300,chess.BISHOP:300,chess.ROOK:500,chess.QUEEN:1000,chess.KING:0}
def canon(f):return ' '.join(chess.Board(f).fen().split()[:4])
def material(b,color):return sum(values[p.piece_type]*(1 if p.color==color else -1) for p in b.piece_map().values())
for account,q in queues.items():
 games={x['game_id'] for x in q['targets']};old=json.loads((OLD/f'control-candidates-v2-{account.lower()}.json').read_text());saved={(x['game_id'],x['ply']):x for x in old['rows'] if x['game_id'] in games}
 for gid in sorted(games):
  g=c.execute('SELECT white,black FROM games WHERE game_id=?',(gid,)).fetchone();color=g['white'].lower()==account.lower()
  for p in c.execute('SELECT * FROM positions WHERE game_id=? ORDER BY ply',(gid,)):
   if p['ply']<11 or (gid,p['ply']) in targetkeys:continue
   b=chess.Board(p['fen_before'])
   if b.turn!=color or canon(p['fen_before']) in known or canon(p['fen_after']) in known:continue
   move=chess.Move.from_uci(p['uci']);piece=b.piece_at(move.from_square);capture=b.is_capture(move);before=material(b,color);previous=c.execute('SELECT * FROM positions WHERE game_id=? AND ply=?',(gid,p['ply']-1)).fetchone();recapture=bool(capture and previous and previous['uci'][2:4]==p['uci'][2:4] and chess.Board(previous['fen_before']).is_capture(chess.Move.from_uci(previous['uci'])))
   b.push(move);after=material(b,color)
   x={k:p[k] for k in ('game_id','ply','san','uci','fen_before','fen_after')}|{'account':account,'capture':capture,'recapture_same_square':recapture,'moved_piece':piece.symbol(),'raw_material_before_mover':before,'raw_material_after_mover':after,'immediate_material_gain':after-before,'moved_piece_attacked':b.is_attacked_by(not color,move.to_square),'moved_piece_defended':b.is_attacked_by(color,move.to_square),'selected':False,'label':'unknown'}
   prior=saved.get((gid,p['ply']))
   if prior and prior['fen_before']==x['fen_before'] and prior['fen_after']==x['fen_after']:x['current_v2_legal_piece_offer']=prior['current_v2_legal_piece_offer'];x['offer_source']='unchanged saved raw-v2 predicate'
   out.append(x)
assert len(out)<=20000
(ROOT/'control-preparation-input.json').write_text(json.dumps(out,indent=2)+'\n');c.close();print(json.dumps({'positions':len(out),'need_new_predicate':sum('current_v2_legal_piece_offer' not in x for x in out),'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}))
