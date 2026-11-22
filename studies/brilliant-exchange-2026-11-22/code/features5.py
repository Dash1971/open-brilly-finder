#!/usr/bin/env python3
"""What did the opponent's last move do to the offered piece? (needs the previous own-move row)"""
import pickle, collections, multiprocessing as mp
import chess
from extract_moves import VAL, offers
R = pickle.load(open('moves.pkl', 'rb'))
games = collections.defaultdict(dict)
for r in R: games[(r['game_id'], r['color'])][r['ply']] = r

def build(item):
    r, prev = item
    hang = [o for o in r['offers'] if o[3] >= 2]
    top = max(hang, key=lambda o: (o[3], o[1])); sq, typ = top[0], top[1]
    mover = chess.WHITE if r['color'] == 'w' else chess.BLACK
    f = dict(opp_last_attacks_hung=-1, opp_last_cap=-1, opp_last_check=int(r['in_check_before']), opp_last_piece=0, opp_last_to_hung_sq=0,
             hang_see_prev=0, hang_placed_prev=0, opp_last_attacks_origin=-1, opp_last_see_loss=0, opp_last_discovers_hung=-1, hung_was_there_prev=-1)
    if prev is None: return (r['game_id'], r['ply']), f
    pb = chess.Board(prev['fen_after']); target = chess.Board(r['fen_before']).board_fen()
    lm = None
    for m in pb.legal_moves:
        pb.push(m)
        if pb.board_fen() == target: lm = m; pb.pop(); break
        pb.pop()
    f['hang_see_prev'] = max([o[3] for o in prev['offers'] if o[0] == sq and o[1] == typ], default=0)
    f['hang_placed_prev'] = int(prev['to_sq'] == sq)
    p0 = pb.piece_at(sq)
    f['hung_was_there_prev'] = int(p0 is not None and p0.color == mover and p0.piece_type == typ)
    if lm is None: return (r['game_id'], r['ply']), f
    f['opp_last_piece'] = pb.piece_type_at(lm.from_square)
    f['opp_last_cap'] = VAL[pb.piece_type_at(lm.to_square)] if pb.piece_at(lm.to_square) else (1 if pb.is_en_passant(lm) else 0)
    att_before = pb.attackers(not mover, sq)
    pb.push(lm)
    att_after = pb.attackers(not mover, sq)
    f['opp_last_attacks_hung'] = int(lm.to_square in att_after)
    f['opp_last_discovers_hung'] = int(len(att_after - att_before - chess.SquareSet.from_square(lm.to_square)) > 0)
    f['opp_last_attacks_origin'] = int(lm.to_square in pb.attackers(not mover, r['from_sq']))
    f['opp_last_to_hung_sq'] = int(lm.to_square == sq)
    # was the opponent's own last move itself leaving material en prise (did the mover have a free capture)?
    f['opp_last_see_loss'] = max([o[3] for o in offers(pb, not mover)], default=0)
    return (r['game_id'], r['ply']), f

if __name__ == '__main__':
    items = []
    for (gid, col), plies in games.items():
        for ply, r in plies.items():
            if any(o[3] >= 2 for o in r['offers']): items.append((r, plies.get(ply - 2)))
    with mp.Pool(9) as pool: out = dict(pool.imap_unordered(build, items, chunksize=300))
    pickle.dump(out, open('feats5.pkl', 'wb')); print('wrote', len(out))
