#!/usr/bin/env python3
"""Every move Chess.com classified in a review: the played moves AND every move inside its suggested lines.
For each: position, move, Chess.com class, Chess.com score, plus our static features. Engine-free."""
import os, glob, sys, pickle, collections, multiprocessing as mp
import chess
import pb
from extract_moves import VAL, offers, material
import features2, features5, features6
from ccjoin import CLS

def mv(node):
    d = dict((f, v) for f, t, v in node if t == 'v')
    return d.get(1), d.get(2), {k: v for k, v in d.items() if k not in (1, 2)}

def to_move(board, node):
    a, b, extra = mv(node)
    if not a or not b: return None
    m = chess.Move(a - 1, b - 1)
    if m in board.legal_moves: return m
    for promo in (chess.QUEEN, chess.KNIGHT, chess.ROOK, chess.BISHOP):
        m2 = chess.Move(a - 1, b - 1, promotion=promo)
        if m2 in board.legal_moves: return m2      # promotion piece is not decoded; queen assumed first
    return None

def row_for(board, move, ply, prev_cap, prev_to):
    mover = board.turn
    cap_piece = board.piece_type_at(move.to_square)
    cap_val = VAL[cap_piece] if cap_piece else (1 if board.is_en_passant(move) else 0)
    in_check = board.is_check(); before_off = None
    if not in_check:
        b2 = board.copy(stack=False); b2.turn = not mover; b2.ep_square = None
        if b2.is_valid(): before_off = offers(b2, mover)
    r = dict(ply=ply, color='w' if mover else 'b', uci=move.uci(), fen_before=board.fen(),
             moved_type=board.piece_type_at(move.from_square), cap_val=cap_val, promo=move.promotion,
             in_check_before=in_check, n_legal=board.legal_moves.count(), to_sq=move.to_square, from_sq=move.from_square,
             before_offers=before_off, mat_own=material(board, mover), mat_opp=material(board, not mover),
             opp_prev_cap_val=prev_cap, recapture=(prev_to == move.to_square and cap_val > 0))
    board.push(move)
    r['fen_after'] = board.fen(); r['gives_check'] = board.is_check(); r['mate'] = board.is_checkmate()
    r['offers'] = offers(board, mover) if not r['mate'] else []; r['n_replies'] = board.legal_moves.count()
    return r

def score_of(p2, white):
    s = pb.get(p2, 4)
    if s is None: return None, None
    inner = pb.get(s, 1); d = {f: v for f, t, v in (inner or [])}
    sign = 1 if white else -1
    depth = dict((f, v) for f, t, v in s if t == 'v').get(2)
    if 1 in d: return sign * pb.zz(d[1]), depth
    if 2 in d: return sign * 100000, depth
    if 3 in d: return -sign * 100000, depth
    return 0, depth

def base_feats(r):
    """board-only part of features.build"""
    f = {}
    hang = [o for o in r['offers'] if o[3] > 0]; top = max(hang, key=lambda o: (o[3], o[1]))
    bo = {o[0]: o for o in (r['before_offers'] or [])}
    mover = chess.WHITE if r['color'] == 'w' else chess.BLACK
    f['net'] = r['cap_val'] - top[3]; f['hang_see'] = top[3]; f['hang_type'] = top[1]; f['hang_attacker'] = top[2]
    f['hang_is_moved'] = int(top[0] == r['to_sq'])
    f['hang_already_attacked'] = int(top[0] != r['to_sq'] and top[0] in bo)
    f['hang_already_hanging'] = int(top[0] != r['to_sq'] and top[0] in bo and bo[top[0]][3] > 0)
    f['before_hang_max'] = max([o[3] for o in bo.values()], default=0) if r['before_offers'] is not None else -1
    f['n_hang'] = len(hang); f['hang_sum'] = sum(o[3] for o in hang); f['n_capturable'] = len(r['offers'])
    f['moved_type'] = r['moved_type']; f['cap_val'] = r['cap_val']; f['gives_check'] = int(r['gives_check']); f['in_check'] = int(r['in_check_before'])
    f['promo'] = r['promo'] or 0; f['matdiff'] = r['mat_own'] - r['mat_opp']; f['mat_total'] = r['mat_own'] + r['mat_opp']; f['mat_own'] = r['mat_own']
    f['opp_prev_cap'] = r['opp_prev_cap_val']; f['recapture'] = int(r['recapture']); f['n_legal'] = r['n_legal']; f['n_replies'] = r['n_replies']
    b = chess.Board(r['fen_before']); played = chess.Move.from_uci(r['uci']); alt = []
    for m in list(b.legal_moves):
        if m == played: continue
        cv = VAL[b.piece_type_at(m.to_square)] if b.piece_at(m.to_square) else (1 if b.is_en_passant(m) else 0)
        b.push(m)
        alt.append(99 if b.is_checkmate() else cv - max([o[3] for o in offers(b, mover)], default=0))
        b.pop()
    f['alt_best_net'] = max(alt, default=-99); f['alt_safe_frac'] = (sum(1 for v in alt if v >= 0) / len(alt)) if alt else 0
    f['alt_n_better_net'] = sum(1 for v in alt if v > f['net'])
    return f

def hist_feats(r, rows):
    """features4 logic; rows: ply -> row (same game context incl. line)"""
    ply = r['ply']; hang = [o for o in r['offers'] if o[3] >= 2]; top = max(hang, key=lambda o: (o[3], o[1])); sq, typ = top[0], top[1]
    f = {}; age = 0; p = ply - 2; moved = (sq == r['to_sq'])
    while not moved and p in rows:
        pr = rows[p]
        has = any(o[0] == sq and o[1] == typ and o[3] > 0 for o in pr['offers'])
        if has and pr['to_sq'] != sq: age += 1; p -= 2
        elif has: age += 1; break
        else: break
    f['hang_age'] = age; prev = rows.get(ply - 2)
    f['prev_hang_max'] = max([o[3] for o in prev['offers']], default=0) if prev else -1
    f['prev_net'] = (prev['cap_val'] - max([o[3] for o in prev['offers'] if o[3] > 0], default=0)) if prev else 0
    f['prev_cap_val'] = prev['cap_val'] if prev else 0
    f['prev_same_piece_moved'] = int(bool(prev) and prev['to_sq'] == r['from_sq'])
    f['origin_offered_prev'] = int(bool(prev) and any(o[0] == r['from_sq'] and o[3] > 0 for o in prev['offers']))
    f['origin_offered_prev_see'] = max([o[3] for o in prev['offers'] if o[0] == r['from_sq']], default=0) if prev else 0
    f['prev_n_hang'] = sum(1 for o in prev['offers'] if o[3] > 0) if prev else 0
    p4 = rows.get(ply - 4); f['prev2_hang_max'] = max([o[3] for o in p4['offers']], default=0) if p4 else -1
    f['mat_change_2ply'] = (r['mat_own'] - r['mat_opp']) - ((prev['mat_own'] - prev['mat_opp']) if prev else (r['mat_own'] - r['mat_opp']))
    f['prev_gives_check'] = int(bool(prev) and prev['gives_check'])
    return f

def game(path):
    gid = os.path.basename(path)[:-5]
    try:
        t = pb.load(path); root = pb.get(t, 2, 2); r3 = pb.get(root, 3); B = pb.allf(r3, 3)
        start = [v for f, ty, v in r3 if f == 2 and ty == 's'][0]
    except Exception:
        return []
    board = chess.Board(start); grows = {}; out = []; prev_cap, prev_to = 0, None
    def emit(r, rows, node, src, j):
        if not any(o[3] >= 2 for o in r['offers']): return
        d = dict((f, v) for f, tt, v in node if tt == 'v'); cp, depth = score_of(node, r['color'] == 'w')
        f = dict(game_id=gid, src_ply=src, line_idx=j, ply=r['ply'], kind=('played' if j == 0 and src == r['ply'] and rows is grows else 'line'),
                 cls=CLS.get(d.get(3), str(d.get(3))), cc_cp=cp, cc_depth=depth, fen_before=r['fen_before'], uci=r['uci'])
        f.update(base_feats(r)); r2 = dict(r, game_id=gid)
        f.update(features2.build(r2)[1]); f.update(hist_feats(r, rows)); f.update(features5.build((r2, rows.get(r['ply'] - 2)))[1]); f.update(features6.build(r2)[1])
        out.append(f)
    for i, b in enumerate(B):
        ply = i + 1; p2 = pb.get(b, 2)
        m = to_move(board, pb.get(p2, 1))
        if m is None: break
        lines = []
        for fld in (7, 9):
            L = pb.allf(b, fld)
            if L: lines.append((fld, L))
        # hypothetical lines from the position before this ply
        for fld, L in lines:
            lb = board.copy(stack=False); rows = dict(grows); pc, pt = prev_cap, prev_to
            for j, e in enumerate(L):
                node = pb.get(e, 2)
                if node is None: break
                lm = to_move(lb, pb.get(node, 1))
                if lm is None: break
                r = row_for(lb, lm, ply + j, pc, pt); rows[ply + j] = r
                if not (fld == 7 and j == 0): emit(r, rows, node, ply, j)      # the played move itself is emitted below
                pc, pt = r['cap_val'], lm.to_square
        r = row_for(board, m, ply, prev_cap, prev_to); grows[ply] = r
        # is the played move Chess.com's best? (no field 3 = yes)
        emit(r, grows, p2, ply, 0)
        if out and out[-1]['ply'] == ply and out[-1]['kind'] == 'played': out[-1]['cc_is_best'] = int(pb.get(b, 3) is None)
        prev_cap, prev_to = r['cap_val'], m.to_square
    return out

if __name__ == '__main__':
    paths = sorted(glob.glob('ccreview/*.json'))
    with mp.Pool(9) as pool:
        out = [x for g in pool.imap_unordered(game, paths, chunksize=4) for x in g]
    pickle.dump(out, open('lines.pkl', 'wb')); print('games', len(paths), 'examples', len(out))
