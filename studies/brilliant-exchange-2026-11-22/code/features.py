#!/usr/bin/env python3
"""Build a feature table for sacrifice candidates from moves.pkl + engine/*.jsonl.

DEPTH env var (optional) caps the engine depth used, to emulate a shallower budget.
"""
import os, sys, json, glob, math, pickle, multiprocessing as mp
import chess
from extract_moves import VAL, offers, see_capture

DEPTH = int(os.environ.get("DEPTH", 0))
ENG = os.environ.get("ENG", "engine")


def cp_of(sc):
    kind, v = sc
    if kind == "cp":
        return max(-9000, min(9000, v))
    return (10000 - min(abs(v), 99) * 10) * (1 if v > 0 else -1) if v != 0 else -10000


def wc(cp):
    return 100.0 / (1.0 + math.exp(-0.00368208 * cp))


def pick(res, cap=DEPTH):
    """res: {depth(str): [[score, pv, nodes], ...]} -> lines at the deepest depth <= cap (complete multipv set preferred)."""
    if not res:
        return None, None
    ds = sorted(int(d) for d in res)
    if cap:
        ok = [d for d in ds if d <= cap]
        ds = ok if ok else ds[:1]
    d = ds[-1]
    # prefer the deepest depth having the max number of lines
    nmax = max(len(res[str(x)]) for x in ds)
    for x in reversed(ds):
        if len(res[str(x)]) == nmax:
            d = x
            break
    return d, res[str(d)]


def material_bal(board, color):
    s = 0
    for pt in (1, 2, 3, 4, 5):
        s += VAL[pt] * (len(board.pieces(pt, color)) - len(board.pieces(pt, not color)))
    return s


def build(args):
    r, e = args
    f = {}
    key = (r["game_id"], r["ply"])
    hang = [o for o in r["offers"] if o[3] > 0]
    top = max(hang, key=lambda o: (o[3], o[1]))
    bo = {o[0]: o for o in (r["before_offers"] or [])}
    mover = chess.WHITE if r["color"] == "w" else chess.BLACK
    f["label"] = int(r["label"])
    f["net"] = r["cap_val"] - top[3]
    f["hang_see"] = top[3]
    f["hang_type"] = top[1]
    f["hang_attacker"] = top[2]
    f["hang_is_moved"] = int(top[0] == r["to_sq"])
    f["hang_already_attacked"] = int(top[0] != r["to_sq"] and top[0] in bo)
    f["hang_already_hanging"] = int(top[0] != r["to_sq"] and top[0] in bo and bo[top[0]][3] > 0)
    f["before_hang_max"] = max([o[3] for o in bo.values()], default=0) if r["before_offers"] is not None else -1
    f["n_hang"] = len(hang)
    f["hang_sum"] = sum(o[3] for o in hang)
    f["n_capturable"] = len(r["offers"])
    f["moved_type"] = r["moved_type"]
    f["cap_val"] = r["cap_val"]
    f["gives_check"] = int(r["gives_check"])
    f["in_check"] = int(r["in_check_before"])
    f["promo"] = r["promo"] or 0
    f["matdiff"] = r["mat_own"] - r["mat_opp"]
    f["mat_total"] = r["mat_own"] + r["mat_opp"]
    f["mat_own"] = r["mat_own"]
    f["opp_prev_cap"] = r["opp_prev_cap_val"]
    f["recapture"] = int(r["recapture"])
    f["n_legal"] = r["n_legal"]
    f["n_replies"] = r["n_replies"]
    f["ply"] = r["ply"]
    f["elo"] = r["elo"]
    f["elo_diff"] = r["elo"] - r["opp_elo"]
    f["clk"] = r["clk"] if r["clk"] is not None else -1
    f["spent"] = (r["prev_clk"] - r["clk"]) if (r["clk"] is not None and r["prev_clk"] is not None) else -1
    try:
        f["tc_base"] = int(str(r["tc"]).split("+")[0]) if "/" not in str(r["tc"]) else 86400
    except Exception:
        f["tc_base"] = -1

    # --- alternatives: could the mover have kept material? (board-only)
    b = chess.Board(r["fen_before"])
    played = chess.Move.from_uci(r["uci"])
    alt_nets = {}
    for m in list(b.legal_moves):
        if m == played:
            continue
        cv = VAL[b.piece_type_at(m.to_square)] if b.piece_at(m.to_square) else (1 if b.is_en_passant(m) else 0)
        b.push(m)
        if b.is_checkmate():
            net = 99
        else:
            offs = [o[3] for o in offers(b, mover)]
            net = cv - max(offs, default=0)
        b.pop()
        alt_nets[m.uci()] = net
    f["alt_best_net"] = max(alt_nets.values(), default=-99)
    f["alt_safe_frac"] = (sum(1 for v in alt_nets.values() if v >= 0) / len(alt_nets)) if alt_nets else 0
    f["alt_n_better_net"] = sum(1 for v in alt_nets.values() if v > f["net"])

    # --- engine: before position
    d, lines = pick(e["before"])
    f["depth_before"] = d or 0
    cps = [cp_of(l[0]) for l in lines] if lines else []
    mvs = [l[1][0] for l in lines] if lines else []
    f["best_cp"] = cps[0] if cps else 0
    f["best_is_mate"] = int(bool(lines) and lines[0][0][0] == "mate" and lines[0][0][1] > 0)
    f["rank"] = (mvs.index(r["uci"]) + 1) if r["uci"] in mvs else 4
    alts = [(c, m) for c, m in zip(cps, mvs) if m != r["uci"]]
    f["alt_cp"] = alts[0][0] if alts else -9999
    f["alt2_cp"] = alts[1][0] if len(alts) > 1 else -9999
    f["alt_net"] = alt_nets.get(alts[0][1], 0) if alts else 0  # does the engine's best alternative also give material?
    f["played_cp_before"] = cps[mvs.index(r["uci"])] if r["uci"] in mvs else -9999

    # --- engine: after position (accept / decline), scores from the opponent's POV -> negate
    da, la = pick(e["accept"]); dd, ld = pick(e["decline"])
    acc = -cp_of(la[0][0]) if la else None
    dec = -cp_of(ld[0][0]) if ld else None
    f["has_decline"] = int(dec is not None)
    f["accept_cp"] = acc if acc is not None else 9999
    f["decline_cp"] = dec if dec is not None else 9999
    cands = [x for x in (acc, dec) if x is not None]
    played_cp = min(cands) if cands else f["best_cp"]
    f["played_cp"] = played_cp
    f["accept_is_best"] = int(acc is not None and (dec is None or acc <= dec))
    f["acc_minus_dec"] = (acc - dec) if (acc is not None and dec is not None) else 0
    f["accept_mate_for_mover"] = int(bool(la) and la[0][0][0] == "mate" and la[0][0][1] < 0)
    f["played_mate"] = int(played_cp >= 9000)
    best = max(f["best_cp"], played_cp)
    f["cp_loss"] = best - played_cp
    f["wc_best"] = wc(best)
    f["wc_played"] = wc(played_cp)
    f["wc_loss"] = wc(best) - wc(played_cp)
    f["wc_alt"] = wc(f["alt_cp"]) if alts else 0
    f["wc_gain_vs_alt"] = wc(played_cp) - (wc(f["alt_cp"]) if alts else 0)
    f["wc_alt2"] = wc(f["alt2_cp"]) if len(alts) > 1 else 0
    f["wc_accept"] = wc(acc) if acc is not None else 100
    f["wc_decline"] = wc(dec) if dec is not None else 100

    # --- material trajectory along the acceptance PV
    traj = []
    if la:
        _, lfull = pick(e["accept"], 0)  # full PV only stored at max depth
        pv = lfull[0][1]
        b = chess.Board(r["fen_after"])
        base = material_bal(chess.Board(r["fen_before"]), mover)
        for u in pv:
            try:
                m = chess.Move.from_uci(u)
                if m not in b.legal_moves:
                    break
                b.push(m)
            except Exception:
                break
            traj.append(material_bal(b, mover) - base)
        f["pv_len"] = len(traj)
        f["pv_mate"] = int(b.is_checkmate())
    else:
        f["pv_len"] = 0
        f["pv_mate"] = 0
    def at(i):
        return traj[min(i, len(traj) - 1)] if traj else 0
    f["mat_after_accept"] = at(0)      # after opponent captures
    f["mat_pv2"] = at(1)               # after mover's reply
    f["mat_pv3"] = at(2)
    f["mat_pv4"] = at(3)
    f["mat_pv6"] = at(5)
    f["mat_pv8"] = at(7)
    f["mat_pv_end"] = traj[-1] if traj else 0
    f["mat_pv_min"] = min(traj) if traj else 0
    f["mat_pv_max_mover_turn"] = max(traj[1::2]) if len(traj) > 1 else at(0)
    rec = next((i for i, v in enumerate(traj) if v >= 0), -1)
    f["recover_ply"] = rec
    return key, f


def load():
    R = pickle.load(open("moves.pkl", "rb"))
    idx = {(r["game_id"], r["ply"]): r for r in R}
    E = {}
    for p in glob.glob(f"{ENG}/part-*.jsonl"):
        for l in open(p):
            try:
                j = json.loads(l)
            except Exception:
                continue
            E[(j["game_id"], j["ply"])] = j
    return idx, E


if __name__ == "__main__":
    idx, E = load()
    items = [(idx[k], e) for k, e in E.items()]
    print(len(items), "candidates with engine evidence", file=sys.stderr)
    with mp.Pool(int(os.environ.get("NP", 3))) as pool:
        out = dict(pool.imap_unordered(build, items, chunksize=200))
    name = f"feats{'-d%d' % DEPTH if DEPTH else ''}.pkl"
    pickle.dump(out, open(name, "wb"))
    print("wrote", name, len(out))
