#!/usr/bin/env python3
"""Independent200 pre-label descriptors; fixed raw-v2 selection, no engine."""
import sys,importlib.util,json,re
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('validation_corpus',ROOT/'corpus.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);chess=m.chess
c=m.connect(ROOT/'corpus.sqlite3');known={x['canonical_first_four'] for x in json.loads((ROOT/'known-regression-fens.json').read_text())['positions']};out=[]
values={1:90,2:300,3:300,4:500,5:1000,6:0}
def canon(f):return ' '.join(chess.Board(f).fen().split()[:4])
def material(b,color):return sum(values[p.piece_type]*(1 if p.color==color else -1) for p in b.piece_map().values())
prior={}
for old in ('brilliants-600-2026-11-03','brilliants-additional-300-2026-11-03'):
 for p in (ROOT.parents[1]/old).glob('control-candidates-v2-*.json'):
  payload=json.loads(p.read_text())
  for x in payload.get('rows',[]):prior[(x['game_id'],x['ply'])]=x
for account in m.ACCOUNTS:
 q=json.loads((ROOT/f'{account.lower()}-ui-queue.json').read_text());pool=json.loads((ROOT/f'{account.lower()}-candidate-pool.json').read_text());gallery={(x['game_id'],x['ply']) for x in pool}
 for gid in sorted({x['game_id'] for x in q['targets']+q['reserves']}):
  g=c.execute('SELECT * FROM games WHERE game_id=?',(gid,)).fetchone();color=g['white'].lower()==account.lower();link=json.loads(g['headers_json']).get('Link','');namespace=re.search(r'/(live|daily)/',link)[1]
  for p in c.execute('SELECT * FROM positions WHERE game_id=? ORDER BY ply',(gid,)):
   b=chess.Board(p['fen_before']);after=chess.Board(p['fen_after'])
   if b.turn!=color or (gid,p['ply']) in gallery or canon(p['fen_before']) in known or canon(p['fen_after']) in known or after.is_game_over():continue
   move=chess.Move.from_uci(p['uci']);piece=b.piece_at(move.from_square);capture=b.is_capture(move);previous=c.execute('SELECT * FROM positions WHERE game_id=? AND ply=?',(gid,p['ply']-1)).fetchone();recap=bool(capture and previous and previous['uci'][2:4]==p['uci'][2:4] and chess.Board(previous['fen_before']).is_capture(chess.Move.from_uci(previous['uci'])))
   x={k:p[k] for k in ('game_id','ply','san','uci','fen_before','fen_after')}|{'account':account,'game_type':namespace,'expected_game_type':namespace,'source_link':f'https://www.chess.com/analysis/game/{namespace}/{gid}/review?move={p["ply"]-1}','capture':capture,'recapture_same_square':recap,'moved_piece':piece.symbol(),'raw_material_before_mover':material(b,color),'raw_material_after_mover':material(after,color),'immediate_material_gain':material(after,color)-material(b,color),'moved_piece_attacked':after.is_attacked_by(not color,move.to_square),'moved_piece_defended':after.is_attacked_by(color,move.to_square),'selected':False,'label':'unknown'}
   saved=prior.get((gid,p['ply']))
   if saved and saved['fen_before']==x['fen_before'] and saved['fen_after']==x['fen_after']:x['current_v2_legal_piece_offer']=saved['current_v2_legal_piece_offer'];x['offer_source']='unchanged pinned raw-v2 saved descriptor'
   out.append(x)
assert len(out)<=20000
(ROOT/'control-preparation-input.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'positions':len(out),'need_pinned_predicate':sum('current_v2_legal_piece_offer' not in x for x in out)}));c.close()
