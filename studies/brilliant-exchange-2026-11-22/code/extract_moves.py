#!/usr/bin/env python3
"""Parse the seven-account PGN into one row per own move with board-only features.

Own move = a move played by an account listed in the game's BrilliantAccounts header
(the account whose complete gallery defines the labels for that game).
"""
import io, re, sys, pickle, multiprocessing as mp
import chess, chess.pgn

PGN = "../open-brilly-finder/studies/brilliant-selective-2026-11-06/data/seven-accounts-last-12-months-chesscom-brilliants.pgn"
INVERT = False
VAL = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 100}


def see_after(board, sq):
    """Best material gain for side to move by capturing on sq (may decline => 0)."""
    best = None
    for m in board.legal_moves:
        if m.to_square == sq and board.piece_at(sq) is not None:
            v = VAL[board.piece_type_at(m.from_square)]
            if best is None or v < best[0]:
                best = (v, m)
    if best is None:
        return 0
    return max(0, see_capture(board, best[1]))


def see_capture(board, move):
    """Material gain for side to move from playing this capture, opponent replying optimally on the same square."""
    victim = board.piece_type_at(move.to_square)
    gain = VAL[victim] if victim else (1 if board.is_en_passant(move) else 0)
    if move.promotion:
        gain += VAL[move.promotion] - 1
    board.push(move)
    try:
        if board.is_checkmate():
            return gain
        return gain - see_after(board, move.to_square)
    finally:
        board.pop()


def offers(board, color):
    """Captures available to the side to move against `color`'s non-pawn pieces.
    Returns list of (victim_sq, victim_type, attacker_type, see_gain) keeping the best capture per victim."""
    out = {}
    for m in board.legal_moves:
        t = board.piece_at(m.to_square)
        if t is None or t.color != color or t.piece_type == chess.PAWN:
            continue
        g = see_capture(board, m)
        a = board.piece_type_at(m.from_square)
        cur = out.get(m.to_square)
        if cur is None or g > cur[3]:
            out[m.to_square] = (m.to_square, t.piece_type, a, g)
    return list(out.values())


def material(board, color):
    return sum(VAL[pt] * len(board.pieces(pt, color)) for pt in (1, 2, 3, 4, 5))


def game_rows(text):
    g = chess.pgn.read_game(io.StringIO(text))
    h = g.headers
    accounts = set(a.strip().lower() for a in h.get("BrilliantAccounts", "").split(",") if a.strip())
    gid = h["Link"].rsplit("/", 1)[-1]
    white, black = h["White"], h["Black"]
    rows = []
    board = g.board()
    node = g
    ply = 0
    prev_capture_value = 0  # value the opponent just captured on its last move
    prev_to = None
    while node.variations:
        nxt = node.variation(0)
        move = nxt.move
        ply += 1
        mover = board.turn
        name = white if mover else black
        own = (name.lower() in accounts) != INVERT
        cap_piece = board.piece_type_at(move.to_square)
        cap_val = VAL[cap_piece] if cap_piece else (1 if board.is_en_passant(move) else 0)
        if own:
            label = 3 in nxt.nags
            cat = None
            mcat = re.search(r"Category: ([^.]+)\.", nxt.comment or "")
            if mcat:
                cat = mcat.group(1)
            clk = nxt.clock()
            prev_clk = node.parent.clock() if node.parent is not None else None
            fen_before = board.fen()
            moved_type = board.piece_type_at(move.from_square)
            in_check_before = board.is_check()
            # offers standing before the move (if it were opponent's turn)
            before_off = None
            if not in_check_before:
                b2 = board.copy(stack=False)
                b2.turn = not mover
                b2.ep_square = None
                if b2.is_valid():
                    before_off = offers(b2, mover)
            mat_own_b, mat_opp_b = material(board, mover), material(board, not mover)
            san = board.san(move)
            n_legal = board.legal_moves.count()
            board.push(move)
            gives_check = board.is_check()
            mate = board.is_checkmate()
            off = offers(board, mover) if not mate else []
            # number of opponent legal replies
            n_replies = board.legal_moves.count()
            rows.append(dict(
                game_id=gid, ply=ply, account=name, color="w" if mover else "b",
                elo=int(h["WhiteElo"] if mover else h["BlackElo"]), opp_elo=int(h["BlackElo"] if mover else h["WhiteElo"]),
                tc=h.get("TimeControl"), date=h.get("Date"), result=h.get("Result"),
                label=label, category=cat, san=san, uci=move.uci(), fen_before=fen_before, fen_after=board.fen(),
                clk=clk, prev_clk=prev_clk,
                moved_type=moved_type, cap_val=cap_val, promo=move.promotion, gives_check=gives_check, mate=mate,
                in_check_before=in_check_before, n_legal=n_legal, n_replies=n_replies,
                to_sq=move.to_square, from_sq=move.from_square,
                offers=off, before_offers=before_off,
                mat_own=mat_own_b, mat_opp=mat_opp_b,
                opp_prev_cap_val=prev_capture_value, recapture=(prev_to == move.to_square and cap_val > 0),
                total_plies=None,
            ))
        else:
            board.push(move)
        prev_capture_value = cap_val
        prev_to = move.to_square
        node = nxt
    for r in rows:
        r["total_plies"] = ply
    return rows


def split_games(path):
    buf = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.startswith("[Event ") and buf:
                yield "".join(buf)
                buf = []
            buf.append(line)
    if buf:
        yield "".join(buf)


if __name__ == "__main__":
    games = list(split_games(PGN))
    print(len(games), "games", file=sys.stderr)
    with mp.Pool(9) as pool:
        out = []
        for i, rows in enumerate(pool.imap(game_rows, games, chunksize=20)):
            out.extend(rows)
            if i % 1000 == 0:
                print(i, len(out), file=sys.stderr)
    pickle.dump(out, open("moves.pkl", "wb"))
    print(len(out), "own moves;", sum(r["label"] for r in out), "brilliant")
