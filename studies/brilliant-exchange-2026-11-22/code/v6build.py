#!/usr/bin/env python3
"""Build the v6 feature table for every candidate (own + opponents + Dash) from cached Stockfish evidence, capped at DEPTH."""
import os, sys, json, glob, pickle, multiprocessing as mp
import v6ref
from features import cp_of, pick
DEPTH = int(os.environ.get('DEPTH', 12))

def one(args):
    key, fen_prev, r, e = args
    d, lines = pick(e['before'], DEPTH)
    if not lines: return key, None
    before = [(l[1][0], cp_of(l[0])) for l in lines[:2]]
    da, la = pick(e['accept'], DEPTH); dd, ld = pick(e['decline'], DEPTH)
    cands = []
    if la: cands.append((-cp_of(la[0][0]), la[0][1][0]))
    if ld: cands.append((-cp_of(ld[0][0]), ld[0][1][0]))
    if not cands: return key, None
    after = min(cands)            # opponent picks the reply that is worst for the mover
    f = v6ref.v6_features(fen_prev, r['fen_before'], r['uci'], before, after)
    return key, f

def load(prefix):
    R = pickle.load(open(prefix + 'moves.pkl', 'rb'))
    byc = {}
    for r in R: byc[(r['game_id'], r['color'], r['ply'])] = r
    E = {}
    for p in glob.glob(prefix + 'engine/part-*.jsonl'):
        for l in open(p):
            try: j = json.loads(l); E[(j['game_id'], j['ply'])] = j
            except Exception: pass
    items = []
    for r in R:
        k = (r['game_id'], r['ply'])
        if k in E and any(o[3] >= 2 for o in r['offers']):
            prev = byc.get((r['game_id'], r['color'], r['ply'] - 2))
            items.append((k, prev['fen_after'] if prev else None, r, E[k]))
    return items

if __name__ == '__main__':
    for prefix in ('', 'opp/', 'dash/'):
        items = load(prefix)
        with mp.Pool(int(os.environ.get('NP', 8))) as pool:
            out = {k: f for k, f in pool.imap_unordered(one, items, chunksize=100) if f is not None}
        pickle.dump(out, open(f'{prefix}v6-d{DEPTH}.pkl', 'wb'))
        print(prefix or 'own/', 'candidates', len(items), 'rows', len(out), flush=True)
