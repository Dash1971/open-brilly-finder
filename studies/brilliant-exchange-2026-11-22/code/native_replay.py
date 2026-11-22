#!/usr/bin/env python3
"""Run the Mute Exchange model on the archived NATIVE Stockfish 19 Fast review evidence of the 1,000-game Witty_Alien test.

The archive holds, per game, the review snapshot for every position (two root lines, depth 12 / 500 ms, plus the
previous completed iteration) and Mute Selective's native decision for every move. No engine is run here."""
import glob, json, os, pickle, sys, multiprocessing as mp
import chess
import v6ref
ROOT = 'native/research/brilliant-fresh-witty-2026-11-06'

def cp_of(line, white_mover):
    pov = 1 if white_mover else -1
    if line.get('mate') is not None: return v6ref.score_cp(mate=line['mate'] * pov)
    return v6ref.score_cp(cp=(line.get('cp') or 0) * pov)

def evidence(snap_before, snap_after, white):
    before = [(l['moves'][0], cp_of(l, white)) for l in snap_before['lines'][:2] if l.get('moves')]
    la = snap_after['lines'][0]
    after = (cp_of(la, white), la['moves'][0] if la.get('moves') else None)
    return before, after

def game(path):
    d = json.load(open(path))
    if not d.get('complete'): return []
    mo = d['move_outcomes']; init = d['initial']; out = []
    for i, m in enumerate(mo):
        if not (m['account_own_move'] and m['scored_player']): continue
        white = chess.Board(m['fen_before']).turn
        row = dict(game_id=d['game_id'], ply=m['ply'], san=m['san'], uci=m['uci'], gallery=bool(m['gallery_positive']), excluded=bool(m['position_overlap_excluded']),
                   selective=m['selective'] == '!!', production=m['production'] == '!!')
        fen_prev = mo[i - 1]['fen_before'] if i >= 1 else None
        for tag, key in (('cur', 'current'), ('prev', 'previous')):
            sb, sa = init[i].get(key), init[i + 1].get(key)
            row['f_' + tag] = None
            if not sb or not sa or not sb.get('lines') or not sa.get('lines'): continue
            before, after = evidence(sb, sa, white)
            if not before: continue
            try: row['f_' + tag] = v6ref.v6_features(fen_prev, m['fen_before'], m['uci'], before, after)
            except Exception as e: row['err'] = repr(e)[:80]
        row['depth_before'] = init[i]['current']['depth']; row['depth_after'] = init[i + 1]['current']['depth']
        out.append(row)
    return out

if __name__ == '__main__':
    files = {}
    for p in sorted(glob.glob(ROOT + '/assessment-*/*.json')) + sorted(glob.glob(ROOT + '/full/segment-*/assessment-*/*.json')):
        gid = os.path.basename(p)[:-5]
        if gid.isdigit(): files[gid] = p        # the continuation run reuses the original 200 byte for byte; later path wins
    print(len(files), 'games', file=sys.stderr)
    with mp.Pool(9) as pool:
        rows = [r for g in pool.imap_unordered(game, list(files.values()), chunksize=8) for r in g]
    pickle.dump(rows, open('native_rows.pkl', 'wb'))
    prim = [r for r in rows if not r['excluded']]
    print('own moves', len(rows), 'primary', len(prim), 'gallery positives', sum(r['gallery'] for r in prim), 'selective TP', sum(r['gallery'] and r['selective'] for r in prim), 'FP', sum((not r['gallery']) and r['selective'] for r in prim),
          '| candidates', sum(r['f_cur'] is not None for r in prim), 'errors', sum('err' in r for r in rows))
