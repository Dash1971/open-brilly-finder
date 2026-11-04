"""One fixed, authorized repeat-award snapshot completion; no selection or tuning.
Uses the existing final-study search implementation unchanged. Never overwrites
baseline evidence. Full PGN stack, one SF process/thread,64MB,300k nodes.
"""
import json,sys,sqlite3,io,hashlib,importlib.util
from pathlib import Path
sys.path.insert(0,'/private/tmp/brilly-research-deps')
import chess,chess.engine,chess.pgn
SOURCE=Path('research/brilliants-final-2026-11-03/analysis.py')
s=importlib.util.spec_from_file_location('existing_collector',SOURCE);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
planfile=Path(sys.argv[1]);output=Path(sys.argv[2]);plan=json.loads(planfile.read_text());wanted=sorted(set(plan['snapshot_ids']));cap=plan['authorized_snapshot_cap'];assert cap<=1200 and len(wanted)<=cap
assert not output.exists(),'Never overwrite prior evidence'
conn=sqlite3.connect('file:research/brilliants-improvement-2026-11-03/future-validation-v5/corpus.sqlite3?mode=ro',uri=True);conn.row_factory=sqlite3.Row
result={'scope':plan['scope'],'started_at':m.now(),'status':'running','fixed_snapshot_ids':wanted,'nodes_per_position':300000,'threads':1,'hash_mb':64,'full_pgn_history':True,'hash_session_policy':'ClearHash and new game session per game; increasing ply order; no baseline replacement.','plan_sha256':m.digest(planfile),'collector_source_sha256':m.digest(SOURCE),'runner_sha256':m.digest(__file__),'engine_path':m.ENGINE,'engine_sha256':m.digest(m.ENGINE),'snapshots':{}}
m.write(output,result);engine=chess.engine.SimpleEngine.popen_uci(m.ENGINE);engine.configure({'Threads':1,'Hash':64});result['engine_id']=engine.id
try:
 for gid in sorted({x.split(':')[0] for x in wanted}):
  game=conn.execute('select pgn,pgn_sha256 from games where game_id=?',(gid,)).fetchone();assert game
  pgn=chess.pgn.read_game(io.StringIO(game['pgn']));assert pgn and not pgn.errors
  plies={int(x.split(':')[1]) for x in wanted if x.split(':')[0]==gid};board=pgn.board();boards={}
  for ply,move in enumerate(pgn.mainline_moves(),1):
   board.push(move)
   if ply in plies:boards[ply]=board.copy(stack=True)
  assert set(boards)==plies
  engine.configure({'Clear Hash':None});session=object()
  for ply in sorted(plies):
   expected=conn.execute('select fen_after from positions where game_id=? and ply=?',(gid,ply)).fetchone();assert expected and boards[ply].fen()==chess.Board(expected['fen_after']).fen()
   snap=m.search(engine,boards[ply],300000,session);snap.update(game_id=gid,position_ply=ply,fen=boards[ply].fen(),pgn_sha256=game['pgn_sha256'],ec_material=m.naive(boards[ply].fen()),quality='repeat-award-sf18-300000')
   result['snapshots'][f'{gid}:{ply}']=snap;m.write(output,result)
 result.update(status='complete',completed_at=m.now());m.write(output,result)
except Exception as e:
 result.update(status='failed',reason=str(e),completed_at=m.now());m.write(output,result);raise
finally:engine.quit();conn.close()
print(json.dumps({'status':result['status'],'snapshots':len(result['snapshots']),'elapsed_search_seconds':sum(s.get('elapsed_seconds',0) for s in result['snapshots'].values())}))
