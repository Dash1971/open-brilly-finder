# SPDX-License-Identifier: AGPL-3.0-only
"""Static chess logic: legal static exchange evaluation and piece offers."""
import chess

VAL = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 100}


def see_after(board, sq):
    """Best material gain for the side to move by capturing on sq (it may decline: never below 0)."""
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
    """Material gain for the side to move from this capture, with optimal legal recaptures on the same square."""
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
    """Captures the side to move has against `color`'s non-pawn pieces.
    Returns (victim_sq, victim_type, attacker_type, exchange_gain), best capture per victim."""
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


def material_bal(board, color):
    return material(board, color) - material(board, not color)


def best_capture(board):
    """(gain, move) of the side to move's best capture by static exchange (any victim)."""
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


def is_candidate(row):
    """Chess.com-style piece offer: some non-pawn piece can be captured for an exchange gain of at least 2."""
    return any(o[3] >= 2 for o in row["offers"])
