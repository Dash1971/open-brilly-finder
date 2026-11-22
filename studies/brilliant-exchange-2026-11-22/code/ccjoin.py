"""Join Chess.com review records with our own-move rows -> one table for sacrifice candidates and all own moves."""
import os, glob, pickle, collections, sys
import pandas as pd, numpy as np
import pb, ccparse
CLS = {1:'book',2:'brilliant',3:'great',4:'best',5:'excellent',6:'good',7:'inaccuracy',8:'mistake',9:'miss',10:'blunder',11:'forced'}
def mover_score(s, white):
    """Chess.com score dict -> (cp from mover POV, mate from mover POV or None). cp is zigzag white-POV."""
    if not s or 1 not in s: return None, None
    d = {f: v for f, t, v in s[1]}
    sign = 1 if white else -1
    if 1 in d: return sign * pb.zz(d[1]), None
    if 2 in d: return sign * 100000, sign * d[2]       # white mates
    if 3 in d: return -sign * 100000, -sign * d[3]     # black mates
    return 0, None   # empty message = 0.00
def build(moves_path='moves.pkl'):
    R = pickle.load(open(moves_path, 'rb'))
    byg = collections.defaultdict(dict)
    for r in R: byg[r['game_id']][r['ply']] = r
    rows = []; bad = 0
    for path in glob.glob('ccreview/*.json'):
        gid = os.path.basename(path)[:-5]
        try: P, root = ccparse.plies(path)
        except Exception as e: bad += 1; continue
        own = byg.get(gid, {})
        for p in P:
            r = own.get(p['ply'])
            if r is None: continue
            if r['uci'][:4] != p['played'][0]: bad += 1; continue
            white = r['color'] == 'w'
            cp, mate = mover_score(p['score'], white)
            bcp, bmate = mover_score(p.get('best_score'), white) if p.get('best') else (cp, mate)
            hang = max([o[3] for o in r['offers']], default=0)
            rows.append(dict(game_id=gid, ply=p['ply'], account=r['account'], gallery=int(r['label']), cls=CLS.get(p['cls'], str(p['cls'])),
                             cc_cp=cp, cc_mate=mate, cc_best_cp=bcp, cc_best_mate=bmate, cc_is_best=int(not p.get('best')),
                             cc_depth=(p['score'] or {}).get(2), f5=p['f1'].get(5), key=p['f1'].get(1, 0), hang_see=hang, cand=int(hang >= 2),
                             n7=p['n7'], n9=p['n9']))
    df = pd.DataFrame(rows).set_index(['game_id', 'ply'])
    return df, bad
if __name__ == '__main__':
    df, bad = build()
    df.to_pickle('cc.pkl')
    print('games', df.index.get_level_values(0).nunique(), 'own moves', len(df), 'unparsed/mismatch', bad)
    print('gallery brilliant vs review class:'); print(pd.crosstab(df.gallery, df.cls))
    c = df[df.cand == 1]
    print('candidates:', len(c)); print(pd.crosstab(c.gallery, c.cls))
