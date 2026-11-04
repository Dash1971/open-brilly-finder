import sys,json,importlib.util
from pathlib import Path
sys.path.insert(0,'/private/tmp/brilly-research-deps')
import chess,chess.pgn
P=Path('mute-chess-research/studies/brilliant-moves'); OUT=Path('research/brilliants-improvement-2026-11-03/astra')
spec=importlib.util.spec_from_file_location('material_probe','mute-chess-research/studies/brilliant-moves-2026-11-03/material-features.py');mp=importlib.util.module_from_spec(spec);spec.loader.exec_module(mp)
v2={(r['game_id'],r['ply']):r for r in json.loads((P/'comparison-v2.json').read_text())['rows']};v3=json.loads((P/'comparison-v3.json').read_text())['rows'];a=json.loads((P/'analysis-baseline.json').read_text());targets={(t['game_id'],t['ply']):t for t in a['targets']}
games={};f=(P/'selected-games.pgn').open()
while (g:=chess.pgn.read_game(f)) is not None:games[g.headers['Link'].split('/')[-1]]=g
out=[]
for r in v3:
 key=r['game_id'],r['ply'];pos=r['primary_fresh_binary_label']=='brilliant';s2=v2[key]['mute_v2']['symbol'];s3=r['mute_v3']['symbol']
 if not ((s3=='!!' and not pos) or(s2=='!!' and s3!='!!')):continue
 t=targets[key];b=games[key[0]].board();seq=[];hist=[b.copy()]
 for m in games[key[0]].mainline_moves():
  seq.append(b.san(m));b.push(m);hist.append(b.copy())
  if len(seq)==key[1]:break
 prev=hist[-3];before=hist[-2];after=hist[-1];move=chess.Move.from_uci(r['uci']);probe=mp.probe(before.fen(),after.fen());offers=[]
 for s,p in after.piece_map().items():
  if p.color==after.turn or p.piece_type in (1,6):continue
  loss=mp.same_square(after,s,mp.Budget())
  if loss<=probe['immediate_capture_promotion_credit']+100:continue
  oldsquare=move.from_square if s==move.to_square else s
  # Our move is only mover relocation between these two opponent-to-move states;
  # current targets survived the intervening enemy move. No target castle cases here.
  oldloss=mp.same_square(prev,oldsquare,mp.Budget()) if prev.piece_at(oldsquare) and prev.piece_at(oldsquare).color==p.color else None
  offers.append({'piece':p.symbol()+chess.square_name(s),'moved':s==move.to_square,'gain':loss,'previous_square':chess.square_name(oldsquare),'previous_gain':oldloss})
 snaps=[a['snapshots'][i] for i in t['snapshot_ids']];lines=[]
 for line in snaps[-1]['current']['lines']:
  q=after.copy();sans=[];mats=[];baseline=mp.material(before)
  for uci in line['moves'][:10]:
   m=chess.Move.from_uci(uci)
   if m not in q.legal_moves:break
   sans.append(q.san(m));q.push(m);mats.append(mp.material(q)*(1 if q.turn==before.turn else -1)-baseline)
  lines.append({'cp':line.get('cp'),'mate':line.get('mate'),'san':sans,'material_delta':mats})
 out.append({'key':f'{key[0]}:{key[1]}','kind':'LOST' if pos else ('FP' if s3=='!!' else 'REMOVED_FP'),'san':r['san'],'label':r['observations'][0]['label'],'history':seq[-7:],'check_evasion':before.is_check(),'gives_check':after.is_check(),'gates':r['baseline_gates'],'offers':offers,'physical_probe':probe,'ec_before':snaps[-2]['ec_material'],'ec_after':snaps[-1]['ec_material'],'reply_lines':lines,'fen_before':before.fen(),'fen_after':after.fen()})
for x in out:
 proofs=[]
 for z in x['physical_probe']['qualifying_legal_acceptances']:
  b=chess.Board(x['fen_after']);b.push_uci(z['uci'])
  for m in list(b.legal_moves):
   b.push(m);mate=b.is_checkmate();b.pop()
   if mate:proofs.append([z['san'],b.san(m)])
 x['acceptance_mate_in_one']=proofs
(OUT/'error-features.json').write_text(json.dumps(out,indent=2)+'\n')
print('saved',len(out),'unknown',sum(x['physical_probe']['outcome']=='UNKNOWN' for x in out),'seconds',sum(x['physical_probe']['elapsed_seconds'] for x in out))
