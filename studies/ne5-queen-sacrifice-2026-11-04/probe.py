"""One-game diagnostic: six local searches, no fitting or application changes."""
import ast,hashlib,io,json,sys,time
from pathlib import Path
sys.path.insert(0,'/private/tmp/brilly-research-deps')
import chess,chess.engine,chess.pgn
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
START=time.monotonic();SEARCH_SPENT=0.;ACTIVE_SEARCH=None
def guard():
    if time.monotonic()-START>90:raise TimeoutError('One-game90second cap')
source=ROOT/'research/brilliants-prospective-v7-2026-11-03/adapter/sf18-collect.py'
funcs=[n for n in ast.parse(source.read_text()).body if isinstance(n,ast.FunctionDef) and n.name in ['packed','search']]
exec(compile(ast.Module(body=funcs,type_ignores=[]),str(source),'exec'),globals())
pgn='[White "Dash"]\n[Black "Indigo Flint"]\n[Result "1-0"]\n[TimeControl "900+10"]\n\n1. e4 c6 2. Nf3 d5 3. Nc3 dxe4 4. Nxe4 Bg4 5. Bc4 Nf6 6. Ne5 Bxd1 7. Bxf7# 1-0\n'
(HERE/'game.pgn').write_text(pgn)
g=chess.pgn.read_game(io.StringIO(pgn));assert not g.errors
b=g.board();boards=[b.copy(stack=True)]
for m in g.mainline_moves():b.push(m);boards.append(b.copy(stack=True))
assert boards[11].peek().uci()=='f3e5' and boards[13].is_checkmate()
engine='/opt/homebrew/bin/stockfish';engine_sha=hashlib.sha256(Path(engine).read_bytes()).hexdigest()
assert engine_sha=='ae4c93fa9676ca7750d0714342fd8a5b1d018000fc6e0f6cedf112067b5ef374'
result={'scope':'Local SF18 reproduction of deployed classifier; not captured browser SF19 internal evidence. Two fixed search budgets; no model tuning.','game_url':'https://mutechess.org/game/tjxdTRho','played_uci':'f3e5','engine_sha256':engine_sha,'threads':1,'hash_mb':64,'multipv':2,'full_history':True,'profiles':[]}
sf=chess.engine.SimpleEngine.popen_uci(engine);sf.configure({'Threads':1,'Hash':64})
try:
    for budget in [300000,3000000]:
        snapshots=[]
        for ply in [9,10,11]:
            guard();sf.configure({'Clear Hash':None});s=search(sf,boards[ply],budget,object());s.update(fen=boards[ply].fen(),ply=ply);snapshots.append(s)
        result['profiles'].append({'budget':budget,'input':{'positions':[s['fen'] for s in snapshots],'reviews':snapshots,'move':'f3e5'}})
finally:sf.quit()
result['elapsed_seconds']=time.monotonic()-START
(HERE/'SNAPSHOTS.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'searches':6,'elapsed_seconds':result['elapsed_seconds']}))
