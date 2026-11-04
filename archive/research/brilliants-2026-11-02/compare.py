"""One-off comparison of selected Safari gallery examples with the pinned EC oracle.

Run with PYTHONPATH=/private/tmp/brilly-research-deps python3 compare.py.
No application changes; SF18 evidence is different from Chess.com's private engine run.
"""
import io, json, math, pathlib, subprocess
from functools import lru_cache
import chess, chess.pgn, chess.engine

HERE = pathlib.Path(__file__).parent
NODE = '/Users/da/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node'
ORACLE = pathlib.Path('/Users/da/Documents/ChatGPT/Mobile Maia/preview/tool/hardening/classification/reference/annotate.mjs')
VALUES = {chess.PAWN:90, chess.KNIGHT:300, chess.BISHOP:300, chess.ROOK:500, chess.QUEEN:1000, chess.KING:0}
def material(b):
    if b.is_checkmate(): return -10000
    return sum(VALUES[p.piece_type] * (1 if p.color == b.turn else -1) for p in b.piece_map().values())
def qsearch(b, alpha, beta):
    stand = material(b)
    if stand >= beta: return beta
    alpha = max(alpha, stand)
    captures = list(b.generate_legal_captures())
    captures.sort(key=lambda m: 90 if b.is_en_passant(m) else VALUES[b.piece_at(m.to_square).piece_type], reverse=True)
    for m in captures:
        b.push(m)
        score = -qsearch(b, -beta, -alpha)
        b.pop()
        if score >= beta: return beta
        alpha = max(alpha, score)
    return alpha
@lru_cache(None)
def naive(fen):
    b = chess.Board(fen)
    if not b.legal_moves: return -10000 if b.is_checkmate() else 0
    best = -10000
    for m in list(b.legal_moves):
        b.push(m)
        best = max(best, -qsearch(b,-10000,10000))
        b.pop()
    return best
def wc(cp): return 100 / (1 + math.exp(-0.00368208 * max(-1000,min(1000,cp))))
def score(info):
    s = info['score'].white()
    return {'type':'mate','value':s.mate()} if s.is_mate() else {'type':'cp','value':s.score()}
def norm(s, turn): return (1000 * (1 if s['value'] > 0 else -1) if s['type']=='mate' else max(-1000,min(1000,s['value']))) * (1 if turn else -1)
def complete_search(board, nodes, multipv=1):
    pending=[]
    completed=None
    with engine.analysis(board,chess.engine.Limit(nodes=nodes),multipv=multipv) as search:
      for info in search:
        if not all(k in info for k in ('depth','score','pv')) or info.get('upperbound') or info.get('lowerbound'): continue
        rank=info.get('multipv',1)
        if rank != len(pending)+1: pending=[]
        if rank != len(pending)+1: continue
        pending.append(info)
        if rank == multipv:
          if len({i['depth'] for i in pending})==1 and len({i['pv'][0] for i in pending})==multipv:
            completed=pending
          pending=[]
    if completed is None: raise ValueError('No complete exact iteration')
    return completed

samples = json.loads((HERE/'samples.json').read_text())
samples = [dict(s,ply=ply,chesscom_cp_white=s.get('chesscom_cp_white') if ply==s['ply'] else None)
           for s in samples for ply in [s['ply']]+s.get('additional_brilliant_plies',[])]
engine = chess.engine.SimpleEngine.popen_uci('/opt/homebrew/bin/stockfish')
engine.configure({'Threads':1,'Hash':64})
output=[]
try:
  for sample in samples:
    game = chess.pgn.read_game(io.StringIO(sample['moves']))
    if game.errors: raise ValueError(game.errors)
    moves = list(game.mainline_moves())
    b=game.board()
    for m in moves[:sample['ply']-1]: b.push(m)
    move = moves[sample['ply']-1]
    san=b.san(move)
    before=b.copy()
    preceding=before.copy()
    preceding.pop()
    b.push(move)
    after=b.copy()
    mb, ma=naive(before.fen()),-naive(after.fen())
    sac=not after.is_game_over() and mb > ma+100
    runs=[]
    for nodes in (300000,1500000):
      # Clear engine hash for each independently bounded comparison.
      engine.configure({'Clear Hash':None})
      previousinfo=complete_search(preceding,nodes,multipv=2)[0]
      infos=complete_search(before,nodes,multipv=2)
      afterinfo=complete_search(after,nodes)[0]
      case={'prevprev':score(previousinfo),'prev':score(infos[0]),'next':score(afterinfo),'color':'white' if before.turn else 'black',
          'prevMoves':[{'score':{'value':score(i)},'sanMoves':[m.uci() for m in i['pv']]} for i in infos],
          'is_sacrifice':sac,'move':move.uci()}
      award=json.loads(subprocess.check_output([NODE,str(ORACLE)],input=json.dumps([case]).encode()))[0]
      best, second=[norm(score(i),before.turn) for i in infos]
      nextcp=norm(score(afterinfo),before.turn)
      runs.append({'nodes_per_position':nodes,'depth_before':infos[0]['depth'],'depth_after':afterinfo['depth'],
          'best':before.san(infos[0]['pv'][0]),'second':before.san(infos[1]['pv'][0]),
          'best_cp_mover':best,'second_cp_mover':second,'after_cp_mover':nextcp,
          'best_second_wc_gap':round(wc(best)-wc(second),3),'wc_loss':round(wc(best)-wc(nextcp),3),'ec_label':award,
          'oracle_input':case})
    result={**sample,'san':san,'fen_before':before.fen(),'fen_after':after.fen(),
      'material_before':mb,'material_after_mover':ma,'ec_sacrifice':sac,'runs':runs}
    output.append(result)
    print(json.dumps({k:result[k] for k in ('player','san','ec_sacrifice','material_before','material_after_mover')}),flush=True)
    print(json.dumps([{k:r[k] for k in ('nodes_per_position','best','second','best_cp_mover','second_cp_mover','best_second_wc_gap','ec_label')} for r in runs]),flush=True)
    (HERE/'results.json').write_text(json.dumps({'engine':engine.id,'method':'SF18 one thread, 64MB hash, 300k and 1.5m nodes per position; unchanged EC TS oracle; Python translation of pinned capture/material reference; no app confidence-policy replay','samples':output},indent=2)+'\n')
finally: engine.quit()
