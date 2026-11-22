# SPDX-License-Identifier: AGPL-3.0-only
"""Turn a PGN game into one row of board facts per move of the chosen player(s)."""
import io, re
import chess, chess.pgn
from .chesslogic import VAL, offers, material


def game_rows(game, players=None, colors=(chess.WHITE, chess.BLACK)):
    """players: optional set of lowercase names; if given, only their moves are returned."""
    if isinstance(game, str):
        game = chess.pgn.read_game(io.StringIO(game))
    h = game.headers
    gid = h.get("Link", h.get("Site", "game")).rsplit("/", 1)[-1]
    names = {chess.WHITE: h.get("White", "White"), chess.BLACK: h.get("Black", "Black")}
    rows, board, node, ply = [], game.board(), game, 0
    prev_cap, prev_to = 0, None
    while node.variations:
        nxt = node.variation(0)
        move = nxt.move
        ply += 1
        mover = board.turn
        want = mover in colors and (players is None or names[mover].lower() in players)
        cap_piece = board.piece_type_at(move.to_square)
        cap_val = VAL[cap_piece] if cap_piece else (1 if board.is_en_passant(move) else 0)
        if want:
            mcat = re.search(r"Category: ([^.]+)\.", nxt.comment or "")
            fen_before = board.fen()
            in_check = board.is_check()
            before_off = None
            if not in_check:
                b2 = board.copy(stack=False)
                b2.turn = not mover
                b2.ep_square = None
                if b2.is_valid():
                    before_off = offers(b2, mover)
            row = dict(
                game_id=gid, ply=ply, account=names[mover], color="w" if mover else "b",
                label=3 in nxt.nags, category=mcat.group(1) if mcat else None,
                san=board.san(move), uci=move.uci(), fen_before=fen_before,
                moved_type=board.piece_type_at(move.from_square), cap_val=cap_val, promo=move.promotion,
                in_check_before=in_check, n_legal=board.legal_moves.count(),
                to_sq=move.to_square, from_sq=move.from_square, before_offers=before_off,
                mat_own=material(board, mover), mat_opp=material(board, not mover),
                opp_prev_cap_val=prev_cap, recapture=(prev_to == move.to_square and cap_val > 0),
            )
            board.push(move)
            row["fen_after"] = board.fen()
            row["gives_check"] = board.is_check()
            row["mate"] = board.is_checkmate()
            row["offers"] = offers(board, mover) if not row["mate"] else []
            row["n_replies"] = board.legal_moves.count()
            rows.append(row)
        else:
            board.push(move)
        prev_cap, prev_to, node = cap_val, move.to_square, nxt
    return rows
