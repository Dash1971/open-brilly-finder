"""Parse a saved Chess.com review (schema-less protobuf) into per-ply records."""
import pb, chess, collections
def sq(n): return chess.SQUARE_NAMES[n - 1]
def move(m):
    if m is None: return None
    d = dict((f, v) for f, t, v in m if t == 'v')
    u = sq(d.get(1, 1)) + sq(d.get(2, 1))
    extra = {k: v for k, v in d.items() if k not in (1, 2)}
    return u, extra
def score(s):
    """returns dict(raw fields)"""
    if s is None: return None
    out = {}
    for f, t, v in s:
        if t == 'm': out[f] = [(a, b, c) for a, b, c in v]
        else: out[f] = v
    return out
def plies(path):
    t = pb.load(path); root = pb.get(t, 2, 2)
    r3 = pb.get(root, 3); B = pb.allf(r3, 3); A = pb.allf(pb.get(root, 1), 1)
    out = []
    for i, b in enumerate(B):
        p2 = pb.get(b, 2); p3 = pb.get(b, 3)
        rec = dict(ply=i + 1, f1=dict((f, v) for f, t, v in b if t == 'v'))
        rec['played'] = move(pb.get(p2, 1)); rec['cls'] = dict((f, v) for f, t, v in p2 if t == 'v').get(3)
        rec['score'] = score(pb.get(p2, 4))
        if p3 is not None:
            rec['best'] = move(pb.get(p3, 1)); rec['best_cls'] = dict((f, v) for f, t, v in p3 if t == 'v').get(3); rec['best_score'] = score(pb.get(p3, 4))
        rec['A'] = pb.show(A[i])
        rec['n7'] = len(pb.allf(b, 7)); rec['n9'] = len(pb.allf(b, 9))
        rec['f8'] = move(pb.get(b, 8))
        out.append(rec)
    return out, root
if __name__ == '__main__':
    import sys, pickle
    R = {(r['game_id'], r['ply']): r for r in pickle.load(open('moves.pkl', 'rb'))}
    for gid in sys.argv[1:]:
        P, root = plies(f'ccreview/{gid}.json')
        print(gid, len(P), 'tallies', pb.show(pb.get(root, 2, 4))[:300])
        for p in P:
            r = R.get((gid, p['ply']))
            mark = ('OWN ' + r['san'] + (' !!GALLERY' if r['label'] else '') + (' uci-ok' if r['uci'][:4] == p['played'][0] else ' UCI-MISMATCH ' + r['uci'])) if r else ''
            print(p['ply'], p['f1'], p['played'], 'cls', p['cls'], 'sc', p['score'], '| best', p.get('best'), p.get('best_cls'), p.get('best_score'), '|', mark)
