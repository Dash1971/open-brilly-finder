#!/usr/bin/env python3
"""Reference implementation of the v6 ("Mute Exchange") Brilliant features.

Everything is computed from what the Mute Chess review window already holds:
  fen_prev   position before the opponent's last move (may be None)
  fen_before position before the move
  uci        the move
  before     up to two engine lines for fen_before: [(uci, cp from the mover's side)]
  after      best engine line for the position after the move: (cp from the mover's side, first reply uci or None)
The TypeScript port must reproduce these numbers exactly (see fixtures).
"""
import math
import chess
from extract_moves import VAL, offers, material
from lines import base_feats
import features2, features6

CP_CLIP = 9000


def wc(cp):
    return 100.0 / (1.0 + math.exp(-0.00368208 * cp))


def score_cp(cp=None, mate=None):
    """Engine score (already from the mover's side) -> clipped centipawns."""
    if mate is not None:
        if mate == 0:
            return -10000
        return (10000 - min(abs(mate), 99) * 10) * (1 if mate > 0 else -1)
    return max(-CP_CLIP, min(CP_CLIP, cp or 0))


def make_row(fen_prev, fen_before, uci):
    board = chess.Board(fen_before)
    move = chess.Move.from_uci(uci)
    mover = board.turn
    opp_cap, opp_to, opp_move = 0, None, None
    if fen_prev:
        pb = chess.Board(fen_prev)
        target = board.board_fen()
        for m in pb.legal_moves:
            cp = pb.piece_type_at(m.to_square)
            cv = VAL[cp] if cp else (1 if pb.is_en_passant(m) else 0)
            pb.push(m)
            hit = pb.board_fen() == target
            pb.pop()
            if hit:
                opp_cap, opp_to, opp_move = cv, m.to_square, m
                break
    cap_piece = board.piece_type_at(move.to_square)
    cap_val = VAL[cap_piece] if cap_piece else (1 if board.is_en_passant(move) else 0)
    in_check = board.is_check()
    before_off = None
    if not in_check:
        b2 = board.copy(stack=False); b2.turn = not mover; b2.ep_square = None
        if b2.is_valid():
            before_off = offers(b2, mover)
    r = dict(game_id='', ply=0, color='w' if mover else 'b', uci=uci, fen_before=fen_before,
             moved_type=board.piece_type_at(move.from_square), cap_val=cap_val, promo=move.promotion,
             in_check_before=in_check, n_legal=board.legal_moves.count(), to_sq=move.to_square, from_sq=move.from_square,
             before_offers=before_off, mat_own=material(board, mover), mat_opp=material(board, not mover),
             opp_prev_cap_val=opp_cap, recapture=(opp_to == move.to_square and cap_val > 0))
    board.push(move)
    r['fen_after'] = board.fen(); r['gives_check'] = board.is_check(); r['mate'] = board.is_checkmate()
    r['offers'] = offers(board, mover) if not r['mate'] else []
    r['n_replies'] = board.legal_moves.count()
    return r, opp_move


def history_feats(r, fen_prev, opp_move):
    """What the previous position says about this offer (was it already standing? what did the opponent just do?)."""
    mover = chess.WHITE if r['color'] == 'w' else chess.BLACK
    hang = [o for o in r['offers'] if o[3] >= 2]
    top = max(hang, key=lambda o: (o[3], o[1])); sq, typ = top[0], top[1]
    f = dict(has_prev=0, hang_age=0, prev_hang_max=-1, prev_n_hang=0, origin_offered_prev=0, origin_offered_prev_see=0,
             prev_gives_check=0, hang_see_prev=0, hung_was_there_prev=-1,
             opp_last_attacks_hung=-1, opp_last_cap=-1, opp_last_piece=0, opp_last_to_hung_sq=0,
             opp_last_attacks_origin=-1, opp_last_see_loss=0, opp_last_discovers_hung=-1)
    if not fen_prev or opp_move is None:
        return f
    pb = chess.Board(fen_prev)
    po = offers(pb, mover)
    f['has_prev'] = 1
    f['prev_hang_max'] = max([o[3] for o in po], default=0)
    f['prev_n_hang'] = sum(1 for o in po if o[3] > 0)
    f['hang_age'] = int(sq != r['to_sq'] and any(o[0] == sq and o[1] == typ and o[3] > 0 for o in po))
    f['origin_offered_prev'] = int(any(o[0] == r['from_sq'] and o[3] > 0 for o in po))
    f['origin_offered_prev_see'] = max([o[3] for o in po if o[0] == r['from_sq']], default=0)
    f['prev_gives_check'] = int(pb.is_check())
    f['hang_see_prev'] = max([o[3] for o in po if o[0] == sq and o[1] == typ], default=0)
    p0 = pb.piece_at(sq)
    f['hung_was_there_prev'] = int(p0 is not None and p0.color == mover and p0.piece_type == typ)
    lm = opp_move
    f['opp_last_piece'] = pb.piece_type_at(lm.from_square)
    f['opp_last_cap'] = VAL[pb.piece_type_at(lm.to_square)] if pb.piece_at(lm.to_square) else (1 if pb.is_en_passant(lm) else 0)
    att_before = pb.attackers(not mover, sq)
    pb.push(lm)
    att_after = pb.attackers(not mover, sq)
    f['opp_last_attacks_hung'] = int(lm.to_square in att_after)
    f['opp_last_discovers_hung'] = int(len(att_after - att_before - chess.SquareSet.from_square(lm.to_square)) > 0)
    f['opp_last_attacks_origin'] = int(lm.to_square in pb.attackers(not mover, r['from_sq']))
    f['opp_last_to_hung_sq'] = int(lm.to_square == sq)
    f['opp_last_see_loss'] = max([o[3] for o in offers(pb, not mover)], default=0)
    return f


def engine_feats(r, before, after):
    f = {}
    uci = r['uci']
    cps = [c for _, c in before]; mvs = [m for m, _ in before]
    best_cp = cps[0]
    played_cp, reply = after
    f['best_cp'] = best_cp
    f['best_is_mate'] = int(best_cp >= 9000)
    f['rank'] = (mvs.index(uci) + 1) if uci in mvs else 3
    alts = [(c, m) for c, m in zip(cps, mvs) if m != uci]
    f['alt_cp'] = alts[0][0] if alts else -9999
    f['played_cp_before'] = cps[mvs.index(uci)] if uci in mvs else -9999
    f['played_cp'] = played_cp
    f['played_mate'] = int(played_cp >= 9000)
    best = max(best_cp, played_cp)
    f['cp_loss'] = best - played_cp
    f['wc_best'] = wc(best); f['wc_played'] = wc(played_cp); f['wc_loss'] = wc(best) - wc(played_cp)
    f['wc_alt'] = wc(f['alt_cp']) if alts else 0
    f['wc_gain_vs_alt'] = wc(played_cp) - (wc(f['alt_cp']) if alts else 0)
    hang_sq = {o[0] for o in r['offers'] if o[3] > 0}
    f['reply_is_accept'] = int(bool(reply) and chess.Move.from_uci(reply).to_square in hang_sq)
    # does the engine's best alternative also give up material?
    f['alt_net'] = 0
    if alts:
        b = chess.Board(r['fen_before']); m = chess.Move.from_uci(alts[0][1]); mover = b.turn
        if m in b.legal_moves:
            cv = VAL[b.piece_type_at(m.to_square)] if b.piece_at(m.to_square) else (1 if b.is_en_passant(m) else 0)
            b.push(m)
            f['alt_net'] = 99 if b.is_checkmate() else cv - max([o[3] for o in offers(b, mover)], default=0)
    return f


def v6_features(fen_prev, fen_before, uci, before, after):
    """Returns None when the move is not a sacrifice candidate, else an ordered feature dict."""
    r, opp_move = make_row(fen_prev, fen_before, uci)
    if not any(o[3] >= 2 for o in r['offers']):
        return None
    f = {}
    f.update(base_feats(r))
    f.update(features2.build(r)[1])
    f.update(features6.build(r)[1])
    f.update(history_feats(r, fen_prev, opp_move))
    f.update(engine_feats(r, before, after))
    return f
