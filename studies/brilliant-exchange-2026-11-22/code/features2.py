#!/usr/bin/env python3
"""Extra static tactical features for sacrifice candidates (board-only, no engine)."""
import sys, pickle, multiprocessing as mp
import chess
from extract_moves import VAL, offers, see_capture


def best_capture(board):
    """(gain, move) of the side to move's best capture by static exchange, any victim incl. pawns."""
    best = (0, None)
    for m in board.legal_moves:
        if board.is_capture(m):
            g = see_capture(board, m)
            if g > best[0]:
                best = (g, m)
    return best


def mate_in_one(board):
    for m in board.legal_moves:
        board.push(m)
        mate = board.is_checkmate()
        board.pop()
        if mate:
            return True
    return False


def build(r):
    f = {}
    mover = chess.WHITE if r["color"] == "w" else chess.BLACK
    before = chess.Board(r["fen_before"])
    after = chess.Board(r["fen_after"])
    move = chess.Move.from_uci(r["uci"])
    hang = [o for o in r["offers"] if o[3] > 0]
    top = max(hang, key=lambda o: (o[3], o[1]))
    sq = top[0]
    bo = {o[0]: o for o in (r["before_offers"] or [])}

    # attackers / defenders of the offered piece
    f["hang_n_attackers"] = len(after.attackers(not mover, sq))
    f["hang_n_defenders"] = len(after.attackers(mover, sq))
    f["hang_see_before"] = bo[sq][3] if sq in bo else (0 if sq != r["to_sq"] else -1)
    f["hang_worsened"] = int(sq != r["to_sq"] and top[3] > (bo[sq][3] if sq in bo else 0))
    f["from_hang"] = bo[r["from_sq"]][3] if r["from_sq"] in bo else 0
    f["moved_safe"] = int(not any(o[0] == r["to_sq"] and o[3] > 0 for o in r["offers"]))

    # could the offered stationary piece have stepped to safety?
    esc = 0
    if sq != r["to_sq"]:
        for m in before.legal_moves:
            if m.from_square == sq:
                cv = VAL[before.piece_type_at(m.to_square)] if before.piece_at(m.to_square) else 0
                before.push(m)
                lost = max([o[3] for o in offers(before, mover) if o[0] == m.to_square], default=0)
                before.pop()
                if cv - lost >= 0:
                    esc = 1
                    break
    f["hang_could_escape"] = esc

    # mover's threats if the opponent ignores everything (null move)
    thr_gain, thr_move, thr_mate = 0, None, 0
    if not after.is_check():
        nb = after.copy(stack=False)
        nb.turn = mover
        nb.ep_square = None
        if nb.is_valid():
            thr_gain, thr_move = best_capture(nb)
            thr_mate = int(mate_in_one(nb))
    f["threat_gain"] = thr_gain
    f["threat_mate1"] = thr_mate
    f["threat_by_moved"] = int(thr_move is not None and thr_move.from_square == r["to_sq"])
    f["threat_minus_hang"] = thr_gain - top[3]
    # threats that existed before the move (what the mover could simply have taken)
    f["pre_capture_gain"] = best_capture(before)[0]

    # acceptance: opponent takes the offered piece with its least valuable attacker; what does the mover get back at once?
    accs = [m for m in after.legal_moves if m.to_square == sq and after.piece_at(sq) is not None]
    accs = [m for m in accs if see_capture(after, m) > 0]
    f["n_accepting"] = len(accs)
    f["accept_by_king_only"] = int(bool(accs) and all(after.piece_type_at(m.from_square) == chess.KING for m in accs))
    res = []
    for m in accs:
        victim = VAL[after.piece_type_at(sq)]
        after.push(m)
        if after.is_checkmate():
            after.pop()
            continue
        g, bm = best_capture(after)
        same = int(bm is not None and bm.to_square == sq)
        pre = 0  # was that regain capture already available before the acceptance (pure counter-threat)?
        if bm is not None and thr_move is not None and bm.to_square == thr_move.to_square and bm.to_square != sq:
            pre = 1
        m1 = int(mate_in_one(after))
        chk = int(any(after.gives_check(x) for x in after.legal_moves))
        opp_in_check_gain = g
        after.pop()
        res.append(dict(net2=r["cap_val"] - victim + g, regain=g, same=same, pre=pre, mate1=m1, chk=chk,
                        attacker=after.piece_type_at(m.from_square)))
    if res:
        worst = min(res, key=lambda x: x["net2"])  # the acceptance that is statically worst for the mover
        f["acc_net2_min"] = worst["net2"]
        f["acc_net2_max"] = max(x["net2"] for x in res)
        f["acc_regain"] = worst["regain"]
        f["acc_regain_same_sq"] = worst["same"]
        f["acc_regain_pre_threat"] = worst["pre"]
        f["acc_mate1_any"] = max(x["mate1"] for x in res)
        f["acc_mate1_all"] = min(x["mate1"] for x in res)
        f["acc_check_avail"] = worst["chk"]
    else:
        for k in ("acc_net2_min", "acc_net2_max", "acc_regain", "acc_regain_same_sq", "acc_regain_pre_threat",
                  "acc_mate1_any", "acc_mate1_all", "acc_check_avail"):
            f[k] = -9
    # opponent's own counter-chances after the move, unrelated to the offer: can it win material elsewhere / pawns
    f["opp_other_gain"] = max([see_capture(after, m) for m in after.legal_moves
                               if after.is_capture(m) and m.to_square not in {o[0] for o in hang}], default=0)
    f["moved_attacks_higher"] = int(any(
        after.piece_at(t) is not None and after.piece_at(t).color != mover and VAL[after.piece_type_at(t)] > VAL[after.piece_type_at(r["to_sq"])]
        and after.piece_type_at(t) != chess.KING for t in after.attacks(r["to_sq"])))
    f["king_zone_att"] = 0
    ok = after.king(not mover)
    if ok is not None:
        zone = chess.SquareSet(chess.BB_KING_ATTACKS[ok]) | chess.SquareSet.from_square(ok)
        f["king_zone_att"] = sum(1 for z in zone if after.is_attacked_by(mover, z))
        f["hang_dist_opp_king"] = chess.square_distance(sq, ok)
        f["to_dist_opp_king"] = chess.square_distance(r["to_sq"], ok)
    else:
        f["hang_dist_opp_king"] = f["to_dist_opp_king"] = 9
    return (r["game_id"], r["ply"]), f


if __name__ == "__main__":
    R = pickle.load(open("moves.pkl", "rb"))
    cand = [r for r in R if any(o[3] >= 2 for o in r["offers"])]
    print(len(cand), file=sys.stderr)
    with mp.Pool(9) as pool:
        out = dict(pool.imap_unordered(build, cand, chunksize=200))
    pickle.dump(out, open("feats2.pkl", "wb"))
    print("wrote feats2.pkl", len(out))
