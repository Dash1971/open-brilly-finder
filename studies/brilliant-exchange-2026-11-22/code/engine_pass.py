#!/usr/bin/env python3
"""Engine evidence for every sacrifice candidate (any non-pawn piece capturable with SEE gain after the move).

Per candidate, three fixed-node Stockfish searches (Threads=1, hash cleared):
  before : position before the move, MultiPV 3
  accept : position after the move, root restricted to captures of an offered piece (SEE>0)
  decline: position after the move, root restricted to every other reply
Per-depth scores are kept so shallower budgets can be replayed without re-searching.
Resumable: appends JSON lines to engine/part-<k>.jsonl
"""
import sys, os, json, pickle, subprocess, multiprocessing as mp
import chess

NODES = int(os.environ.get("NODES", 200000))
OUT = os.environ.get("OUT", "engine")
NW = int(os.environ.get("NW", 9))


class SF:
    def __init__(self):
        self.p = subprocess.Popen(["stockfish"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
        self.cmd("uci"); self.wait("uciok")
        self.cmd("setoption name Threads value 1"); self.cmd("setoption name Hash value 64")
        self.cmd("isready"); self.wait("readyok")

    def cmd(self, s):
        self.p.stdin.write(s + "\n"); self.p.stdin.flush()

    def wait(self, tok):
        while True:
            l = self.p.stdout.readline()
            if l.startswith(tok):
                return l

    def search(self, fen, multipv=1, searchmoves=None, nodes=NODES):
        self.cmd("ucinewgame")
        self.cmd(f"setoption name MultiPV value {multipv}")
        self.cmd("isready"); self.wait("readyok")
        self.cmd(f"position fen {fen}")
        go = f"go nodes {nodes}"
        if searchmoves:
            go += " searchmoves " + " ".join(searchmoves)
        self.cmd(go)
        depths = {}
        while True:
            l = self.p.stdout.readline()
            if l.startswith("bestmove"):
                break
            if not l.startswith("info") or " score " not in l or " pv " not in l:
                continue
            if "upperbound" in l or "lowerbound" in l:
                continue
            t = l.split()
            d = int(t[t.index("depth") + 1])
            k = int(t[t.index("multipv") + 1]) if "multipv" in t else 1
            si = t.index("score")
            sc = [t[si + 1], int(t[si + 2])]
            pv = t[t.index("pv") + 1:]
            n = int(t[t.index("nodes") + 1])
            depths.setdefault(d, {})[k] = (sc, pv, n)
        res = {}
        if not depths:
            return res
        dmax = max(depths)
        for d, lines in depths.items():
            res[d] = [[lines[k][0], lines[k][1][:12] if d == dmax else lines[k][1][:1], lines[k][2]] for k in sorted(lines)]
        return res


def worker(args):
    k, items = args
    path = f"{OUT}/part-{k}.jsonl"
    done = set()
    if os.path.exists(path):
        for l in open(path):
            try:
                j = json.loads(l); done.add((j["game_id"], j["ply"]))
            except Exception:
                pass
    sf = SF()
    with open(path, "a") as f:
        for r in items:
            key = (r["game_id"], r["ply"])
            if key in done:
                continue
            b = chess.Board(r["fen_after"])
            hang_sq = {o[0] for o in r["offers"] if o[3] > 0}
            acc = [m.uci() for m in b.legal_moves if m.to_square in hang_sq and b.piece_at(m.to_square) is not None]
            dec = [m.uci() for m in b.legal_moves if m.uci() not in set(acc)]
            out = dict(game_id=r["game_id"], ply=r["ply"])
            out["before"] = sf.search(r["fen_before"], multipv=3)
            out["accept"] = sf.search(r["fen_after"], 1, acc) if acc else {}
            out["decline"] = sf.search(r["fen_after"], 1, dec) if dec else {}
            out["n_acc"] = len(acc); out["n_dec"] = len(dec)
            f.write(json.dumps(out) + "\n"); f.flush()
    sf.cmd("quit")
    return k


if __name__ == "__main__":
    R = pickle.load(open("moves.pkl", "rb"))
    cand = [r for r in R if any(o[3] > 0 for o in r["offers"])]
    lim = int(os.environ.get("LIMIT", 0))
    if lim:
        cand = cand[:lim]
    print(len(cand), "candidates", file=sys.stderr)
    os.makedirs(OUT, exist_ok=True)
    chunks = [(k, cand[k::NW]) for k in range(NW)]
    with mp.Pool(NW) as pool:
        for k in pool.imap_unordered(worker, chunks):
            print("done", k, file=sys.stderr)
