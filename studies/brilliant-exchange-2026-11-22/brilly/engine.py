# SPDX-License-Identifier: AGPL-3.0-only
"""Fixed-node Stockfish evidence for one candidate: before (MultiPV 3), accept and decline replies."""
import subprocess
import chess


class Engine:
    def __init__(self, path="stockfish", nodes=200000, hash_mb=64):
        self.nodes = nodes
        self.p = subprocess.Popen([path], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
        self._cmd("uci"); self._wait("uciok")
        self._cmd("setoption name Threads value 1"); self._cmd(f"setoption name Hash value {hash_mb}")
        self._cmd("isready"); self._wait("readyok")

    def _cmd(self, s):
        self.p.stdin.write(s + "\n"); self.p.stdin.flush()

    def _wait(self, tok):
        while True:
            line = self.p.stdout.readline()
            if line.startswith(tok):
                return line

    def close(self):
        try:
            self._cmd("quit")
        except Exception:
            pass

    def search(self, fen, multipv=1, searchmoves=None):
        """{depth(str): [[score, pv, nodes], ...]}; full PV kept only at the last depth."""
        self._cmd("ucinewgame")
        self._cmd(f"setoption name MultiPV value {multipv}")
        self._cmd("isready"); self._wait("readyok")
        self._cmd(f"position fen {fen}")
        go = f"go nodes {self.nodes}"
        if searchmoves:
            go += " searchmoves " + " ".join(searchmoves)
        self._cmd(go)
        depths = {}
        while True:
            line = self.p.stdout.readline()
            if line.startswith("bestmove"):
                break
            if not line.startswith("info") or " score " not in line or " pv " not in line:
                continue
            if "upperbound" in line or "lowerbound" in line:
                continue
            t = line.split()
            d = int(t[t.index("depth") + 1])
            k = int(t[t.index("multipv") + 1]) if "multipv" in t else 1
            si = t.index("score")
            depths.setdefault(d, {})[k] = ([t[si + 1], int(t[si + 2])], t[t.index("pv") + 1:], int(t[t.index("nodes") + 1]))
        if not depths:
            return {}
        dmax = max(depths)
        return {str(d): [[lines[k][0], lines[k][1][:12] if d == dmax else lines[k][1][:1], lines[k][2]] for k in sorted(lines)]
                for d, lines in depths.items()}

    def evidence(self, row):
        b = chess.Board(row["fen_after"])
        hang_sq = {o[0] for o in row["offers"] if o[3] > 0}
        acc = [m.uci() for m in b.legal_moves if m.to_square in hang_sq and b.piece_at(m.to_square) is not None]
        accset = set(acc)
        dec = [m.uci() for m in b.legal_moves if m.uci() not in accset]
        return dict(game_id=row["game_id"], ply=row["ply"],
                    before=self.search(row["fen_before"], multipv=3),
                    accept=self.search(row["fen_after"], 1, acc) if acc else {},
                    decline=self.search(row["fen_after"], 1, dec) if dec else {},
                    n_acc=len(acc), n_dec=len(dec))
