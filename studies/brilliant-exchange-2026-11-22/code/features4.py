#!/usr/bin/env python3
"""History features: has this offer already been standing (and been declined) on earlier moves?"""
import pickle, collections
R = pickle.load(open('moves.pkl', 'rb'))
games = collections.defaultdict(dict)
for r in R: games[(r['game_id'], r['color'])][r['ply']] = r
import chess
out = {}
for (gid, col), plies in games.items():
    seen_after = collections.Counter(); seen_move = collections.Counter()
    for ply in sorted(plies):
        r = plies[ply]
        hang = [o for o in r['offers'] if o[3] >= 2]
        ka = ' '.join(r['fen_after'].split()[:4]); km = (' '.join(r['fen_before'].split()[:4]), r['uci'])
        if hang:
            top = max(hang, key=lambda o: (o[3], o[1])); sq, typ = top[0], top[1]
            f = {}
            # how many consecutive earlier own moves already left this same piece on this square capturable with gain
            age = 0; p = ply - 2
            moved = (sq == r['to_sq'])
            while not moved and p in plies:
                pr = plies[p]
                if any(o[0] == sq and o[1] == typ and o[3] > 0 for o in pr['offers']) and pr['to_sq'] != sq: age += 1; p -= 2
                elif any(o[0] == sq and o[1] == typ and o[3] > 0 for o in pr['offers']) and pr['to_sq'] == sq: age += 1; break   # it was placed there last move and declined
                else: break
            f['hang_age'] = age
            prev = plies.get(ply - 2)
            f['prev_hang_max'] = max([o[3] for o in prev['offers']], default=0) if prev else -1
            f['prev_net'] = (prev['cap_val'] - max([o[3] for o in prev['offers'] if o[3] > 0], default=0)) if prev else 0
            f['prev_cap_val'] = prev['cap_val'] if prev else 0
            f['prev_same_piece_moved'] = int(bool(prev) and prev['to_sq'] == r['from_sq'])
            # the moved piece was already offered on its origin square after the previous move (offer repeated elsewhere)
            f['origin_offered_prev'] = int(bool(prev) and any(o[0] == r['from_sq'] and o[3] > 0 for o in prev['offers']))
            f['origin_offered_prev_see'] = max([o[3] for o in prev['offers'] if o[0] == r['from_sq']], default=0) if prev else 0
            f['prev_n_hang'] = sum(1 for o in prev['offers'] if o[3] > 0) if prev else 0
            f['prev2_hang_max'] = max([o[3] for o in plies[ply - 4]['offers']], default=0) if (ply - 4) in plies else -1
            f['rep_after'] = seen_after[ka]; f['rep_move'] = seen_move[km]
            # material swing over the last two plies (mid-exchange context)
            f['mat_change_2ply'] = (r['mat_own'] - r['mat_opp']) - ((prev['mat_own'] - prev['mat_opp']) if prev else (r['mat_own'] - r['mat_opp']))
            f['prev_gives_check'] = int(bool(prev) and prev['gives_check'])
            out[(gid, ply)] = f
        seen_after[ka] += 1; seen_move[km] += 1
pickle.dump(out, open('feats4.pkl', 'wb')); print('wrote', len(out))
