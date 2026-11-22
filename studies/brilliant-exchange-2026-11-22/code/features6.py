#!/usr/bin/env python3
"""Capture-only material search: after the move, how much material can the opponent win by force through captures alone?
qs_net_d = (what the move captured) - (opponent's best capture-only outcome within d plies). Negative => material really given up."""
import pickle, sys, multiprocessing as mp
import chess
from extract_moves import VAL

def gain_of(board, m):
    v = board.piece_type_at(m.to_square)
    g = VAL[v] if v else (1 if board.is_en_passant(m) else 0)
    if m.promotion: g += VAL[m.promotion] - 1
    return g

def qs(board, depth, alpha, beta):
    """Material the side to move can win (>=0 unless in check) using captures/promotions only; stand pat allowed when not in check."""
    in_check = board.is_check()
    if depth == 0: return 0
    best = -99 if in_check else 0
    if best >= beta: return best
    alpha = max(alpha, best)
    moves = list(board.legal_moves) if in_check else [m for m in board.legal_moves if board.is_capture(m) or m.promotion]
    if in_check and not moves: return -99          # mated
    moves.sort(key=lambda m: -gain_of(board, m))
    for m in moves:
        g = gain_of(board, m)
        board.push(m)
        v = g - qs(board, depth - 1, -beta + g, -alpha + g)
        board.pop()
        if v > best:
            best = v
            if v > alpha: alpha = v
            if alpha >= beta: break
    return best

def build(r):
    b = chess.Board(r['fen_after'])
    f = {}
    for d in (2, 4, 6, 10):
        v = qs(b, d, -200, 200)
        f[f'qs_net{d}'] = max(-30, min(30, r['cap_val'] - v))
    # same question before the move: was the mover already losing material by force (if it were the opponent's turn)?
    bb = chess.Board(r['fen_before'])
    if not bb.is_check():
        bb.turn = not bb.turn; bb.ep_square = None
        f['qs_before6'] = max(-30, min(30, -qs(bb, 6, -200, 200))) if bb.is_valid() else 0
    else:
        f['qs_before6'] = 0
    f['qs_delta6'] = f['qs_net6'] - f['qs_before6']
    # what could the mover simply have won by captures instead (alternative greed)
    b0 = chess.Board(r['fen_before'])
    f['qs_own_before6'] = max(-30, min(30, qs(b0, 6, -200, 200)))
    return (r['game_id'], r['ply']), f

if __name__ == '__main__':
    R = pickle.load(open('moves.pkl', 'rb'))
    cand = [r for r in R if any(o[3] >= 2 for o in r['offers'])]
    with mp.Pool(9) as pool: out = dict(pool.imap_unordered(build, cand, chunksize=200))
    pickle.dump(out, open('feats6.pkl', 'wb')); print('wrote', len(out))
