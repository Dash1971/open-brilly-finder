"""Separate fixed300k accepting-branch diagnostic; never enters grouped evaluation."""
import ast,hashlib,importlib.util,io,json,sys,time
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,'/private/tmp/brilly-research-deps')
import chess,chess.engine,chess.pgn
H=Path(__file__).resolve().parent;W=H.parents[1]
START=time.monotonic();SEARCH_SPENT=0.;ACTIVE_SEARCH=None
def guard():
 if time.monotonic()-START>90:raise TimeoutError('90second diagnostic cap, no retry')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
protocol=json.loads((H/'NE5-PROBE-PROTOCOL.json').read_text())
for p,digest in protocol['sources'].items():assert sha(Path(p))==digest
assert not (H/'NE5-ACCEPTANCE.json').exists()
source=W/'research/brilliants-prospective-v7-2026-11-03/adapter/sf18-collect.py'
funcs=[n for n in ast.parse(source.read_text()).body if isinstance(n,ast.FunctionDef) and n.name in ['packed','search']]
exec(compile(ast.Module(body=funcs,type_ignores=[]),str(source),'exec'),globals())
spec=importlib.util.spec_from_file_location('savedpv',W/'research/brilliants-training-overnight-2026-11-03/adapter/augment-pv.py');pv=importlib.util.module_from_spec(spec);spec.loader.exec_module(pv)
pgn=(W/'research/ne5-queen-sacrifice-2026-11-04/game.pgn').read_text();g=chess.pgn.read_game(io.StringIO(pgn));assert not g.errors
b=g.board();boards=[b.copy(stack=True)]
for m in g.mainline_moves():b.push(m);boards.append(b.copy(stack=True))
before,after=boards[10],boards[11];assert after.peek().uci()=='f3e5'
offers,unknown,nodes=pv.qualify(before,after);assert not unknown and len(offers)<=4
found=[];sf=chess.engine.SimpleEngine.popen_uci('/opt/homebrew/bin/stockfish');sf.configure({'Threads':1,'Hash':64})
try:
 for u,offer in sorted(offers.items()):
  guard();a=after.copy(stack=True);a.push_uci(u);sf.configure({'Clear Hash':None});snapshot=search(sf,a,300000,object())
  found.append({'uci':u,'accepted_fen':a.fen(),'snapshot':snapshot,'source':'new_ne5_diagnostic_only'})
finally:sf.quit()
out={'scope':protocol['scope'],'key':'ne5-diagnostic-only','pgn_sha256':sha(W/'research/ne5-queen-sacrifice-2026-11-04/game.pgn'),'fen_before':before.fen(),'fen_after':after.fen(),'offers':found,'searches':len(found),'elapsed_seconds':time.monotonic()-START,'protocol_sha256':sha(H/'NE5-PROBE-PROTOCOL.json')}
(H/'NE5-ACCEPTANCE.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'searches':len(found),'elapsed_seconds':out['elapsed_seconds']}))
