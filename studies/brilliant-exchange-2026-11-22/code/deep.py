#!/usr/bin/env python3
"""For candidate positions with Chess.com review data: Stockfish best move at each depth up to DEPTH, to compare with Chess.com's best move."""
import os, sys, json, pickle, subprocess, glob, multiprocessing as mp
import pandas as pd
import ccparse
DEPTH = int(os.environ.get('DEPTH', 22))
def worker(args):
    k, items = args
    p = subprocess.Popen(['stockfish'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
    def cmd(s): p.stdin.write(s + '\n'); p.stdin.flush()
    cmd('uci'); cmd('setoption name Threads value 1'); cmd('setoption name Hash value 128'); cmd('isready')
    while not p.stdout.readline().startswith('readyok'): pass
    out = []
    for key, fen in items:
        cmd('ucinewgame'); cmd('isready')
        while not p.stdout.readline().startswith('readyok'): pass
        cmd(f'position fen {fen}'); cmd(f'go depth {DEPTH}')
        best = {}
        while True:
            l = p.stdout.readline()
            if l.startswith('bestmove'): break
            if l.startswith('info') and ' pv ' in l and 'bound' not in l:
                t = l.split(); d = int(t[t.index('depth') + 1]); si = t.index('score')
                best[d] = (t[t.index('pv') + 1], t[si + 1], int(t[si + 2]), int(t[t.index('nodes') + 1]))
        out.append((key, best))
    cmd('quit'); return out
if __name__ == '__main__':
    R = {(r['game_id'], r['ply']): r for r in pickle.load(open('moves.pkl', 'rb'))}
    done = pickle.load(open('deep.pkl', 'rb')) if os.path.exists('deep.pkl') else {}
    items = []; ccbest = {}
    for path in glob.glob('ccreview/*.json'):
        gid = os.path.basename(path)[:-5]
        try: P, _ = ccparse.plies(path)
        except Exception: continue
        for pl in P:
            r = R.get((gid, pl['ply']))
            if r is None or not any(o[3] >= 2 for o in r['offers']): continue
            ccbest[(gid, pl['ply'])] = (pl['best'][0] if pl.get('best') else pl['played'][0])
            if (gid, pl['ply']) not in done: items.append(((gid, pl['ply']), r['fen_before']))
    lim = int(os.environ.get('LIMIT', 0))
    if lim: items = items[:lim]
    print(len(items), 'positions to search', file=sys.stderr)
    NW = 8
    with mp.Pool(NW) as pool:
        for res in pool.imap_unordered(worker, [(k, items[k::NW]) for k in range(NW)]):
            done.update(dict(res))
    pickle.dump(done, open('deep.pkl', 'wb')); pickle.dump(ccbest, open('ccbest.pkl', 'wb'))
    print('saved', len(done))
