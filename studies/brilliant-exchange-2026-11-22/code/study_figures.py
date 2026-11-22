#!/usr/bin/env python3
"""Figures for the Mute Exchange study. Reads study_stats.json; writes PNG and SVG files."""
import json, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import chess, chess.svg

OUT = os.environ.get("FIG_OUT", "../open-brilly-finder/studies/brilliant-exchange-2026-11-22/figures/")
S = json.load(open("study_stats.json"))
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e6e5df"
BLUE, ORANGE, TRACK, BLUE_LIGHT = "#2a78d6", "#eb6834", "#ecebe6", "#a9c8f0"
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 11, "text.color": INK, "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK2, "axes.edgecolor": GRID, "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE, "axes.spines.top": False, "axes.spines.right": False,
})


def bar(ax, y, x0, w, h, color):
    if w <= 0:
        return
    r = min(h / 2, 0.012 * (ax.get_xlim()[1] - ax.get_xlim()[0]))
    ax.add_patch(FancyBboxPatch((x0, y - h / 2), w, h, boxstyle=f"round,pad=0,rounding_size={r}", linewidth=0, facecolor=color, mutation_aspect=h / max(r, 1e-9) * 0 + 1))


def clean(ax, xgrid=False):
    ax.spines["left"].set_visible(False); ax.spines["bottom"].set_visible(False)
    ax.tick_params(length=0)
    if xgrid:
        ax.xaxis.grid(True, color=GRID, linewidth=1); ax.set_axisbelow(True)


def save(fig, name):
    fig.savefig(OUT + name, dpi=200, bbox_inches="tight", pad_inches=0.25); plt.close(fig)


def title(fig, head, sub, y=0.98):
    fig.text(0.02, y, head, fontsize=15, fontweight="bold", va="top", ha="left")
    fig.text(0.02, y - 0.085, sub, fontsize=10.5, color=INK2, va="top", ha="left")


# 1. headline results ---------------------------------------------------------------------------------
rows = {r["name"]: r for r in S["model"]["rows"]}
sel, exc = rows["published Mute Selective"], rows["v6 medium (training precision 95.3%)"]
total = S["model"]["gallery_positives"]
fig, (a, b) = plt.subplots(1, 2, figsize=(11, 3.7), gridspec_kw={"width_ratios": [1.5, 1], "wspace": 0.3})
title(fig, "Mute Exchange finds more Brilliants, with about the same number of wrong badges",
      f"{S['model']['test_games']} Witty_Alien games held out from training, scored on Mute Chess's own Stockfish 19 Fast review output. {total} gallery Brilliants.", y=1.06)
a.set_xlim(0, total); a.set_ylim(-0.7, 1.7)
for y, r, col, name in ((1, exc, BLUE, "Mute Exchange (new)"), (0, sel, ORANGE, "Mute Selective (current)")):
    bar(a, y, 0, total, 0.42, TRACK); bar(a, y, 0, r["found_gallery"], 0.42, col)
    a.text(0, y + 0.36, name, fontsize=11, fontweight="bold", va="bottom")
    a.text(r["found_gallery"] - 6, y, f"{r['found_gallery']}  ({r['found_gallery'] / total:.0%})", color="white", fontweight="bold", va="center", ha="right")
a.set_yticks([]); a.set_xticks([0, 100, 200, 300, total]); a.set_xlabel("Chess.com Brilliants found"); clean(a)
b.set_xlim(0, 24); b.set_ylim(-0.8, 1.7)
for y, r, col, light in ((1, exc, BLUE, BLUE_LIGHT), (0, sel, ORANGE, "#f6c3ad")):
    both = r["false_both"]; today = r["false_gallery"] - both
    bar(b, y, 0, both - 0.12, 0.42, col); bar(b, y, both + 0.12, today - 0.12, 0.42, light)
    b.text(both / 2, y, str(both), color="white", fontweight="bold", va="center", ha="center")
    b.text(both + today / 2 + 0.1, y, str(today), color=INK, fontweight="bold", va="center", ha="center")
    b.text(r["false_gallery"] + 0.6, y, f"{r['false_gallery']} total", color=INK2, va="center")
for yy, col, lab in ((-0.42, "#8f8e88", "dark: Chess.com rejects it today as well"), (-0.62, "#d6d5cf", "light: Chess.com awards Brilliant today")):
    b.add_patch(FancyBboxPatch((0, yy - 0.05), 0.7, 0.1, boxstyle="round,pad=0,rounding_size=0.02", linewidth=0, facecolor=col))
    b.text(1.1, yy, lab, fontsize=9.5, color=INK2, va="center")
b.set_yticks([]); b.set_xticks([0, 5, 10, 15, 20]); b.set_xlabel("Badges on moves not in the gallery"); clean(b)
save(fig, "results.png")

# 2. the offer test -----------------------------------------------------------------------------------
c = S["candidate_test"]; d = S["data"]
fig, ax = plt.subplots(figsize=(10, 3.4))
title(fig, "One simple test finds nearly every Brilliant", "Can the opponent capture a knight, bishop, rook or queen and come out two or more points ahead on that square?", y=1.08)
items = [("All moves by the seven accounts", d["own_moves"], TRACK, INK), (f"Moves that pass the offer test ({c['share_of_moves']:.0%})", c["candidates"], BLUE_LIGHT, INK),
         (f"Chess.com Brilliants that pass ({c['brilliants_covered']:,} of {c['brilliants_total']:,})", c["brilliants_covered"], BLUE, INK)]
ax.set_xlim(0, d["own_moves"] * 1.02); ax.set_ylim(-0.6, 2.75)
for i, (name, v, col, ink) in enumerate(items):
    y = 2 - i
    bar(ax, y, 0, v, 0.4, col); ax.text(0, y + 0.3, name, va="bottom", fontsize=11)
    ax.text(v + d["own_moves"] * 0.01, y, f"{v:,}", va="center", fontweight="bold")
ax.set_yticks([]); ax.set_xticks([]); clean(ax)
save(fig, "offer-test.png")

# 3. what Chess.com's own review says -----------------------------------------------------------------
sit = S["rule"]["situations"]
order = sorted(sit.items(), key=lambda kv: -kv[1]["rate"])
fig, ax = plt.subplots(figsize=(10.5, 4.6))
title(fig, "Which sound sacrifices does Chess.com call Brilliant?",
      f"Chess.com's top move, material on offer, not worse than -0.20 afterwards, not in check: {S['rule']['base']['n']:,} moves in 1,005 reviewed games.", y=1.03)
ax.set_xlim(0, 100); ax.set_ylim(-0.6, len(order) - 0.1)
for i, (name, v) in enumerate(order):
    y = len(order) - 1 - i
    bar(ax, y, 0, 100, 0.34, TRACK); bar(ax, y, 0, v["rate"] * 100, 0.34, BLUE)
    ax.text(0, y + 0.24, name, va="bottom", fontsize=10.5)
    ax.text(v["rate"] * 100 + 1.5, y, f"{v['rate']:.0%}", va="center", fontweight="bold")
    ax.text(100, y + 0.24, f"{v['brilliant']:,} of {v['n']:,}", va="bottom", ha="right", color=INK2, fontsize=9.5)
ax.set_yticks([]); ax.set_xticks([0, 25, 50, 75, 100]); ax.set_xticklabels(["0%", "25%", "50%", "75%", "100%"]); ax.set_xlabel("Share labelled Brilliant by Chess.com"); clean(ax)
save(fig, "situations.png")

# 4. history ------------------------------------------------------------------------------------------
h = S["history"]; ks = sorted(h, key=int)
fig, ax = plt.subplots(figsize=(8, 3.9))
title(fig, "An offer goes stale", "Sound sacrifices where a piece is left where it stands. Share in Chess.com's Brilliant gallery.", y=1.06)
ax.set_ylim(0, 75); ax.set_xlim(-0.6, len(ks) - 0.4)
for i, k in enumerate(ks):
    v = h[k]["rate"] * 100
    ax.add_patch(FancyBboxPatch((i - 0.28, 0), 0.56, v, boxstyle="round,pad=0,rounding_size=0.06", linewidth=0, facecolor=BLUE, mutation_aspect=18))
    ax.text(i, v + 2, f"{v:.0f}%", ha="center", fontweight="bold")
names = ["first move\non offer", "1 move\nalready", "2 moves\nalready", "3 moves\nalready", "4 or more\nalready"]
ax.set_xticks(range(len(ks))); ax.set_xticklabels([f"{n}\n({h[k]['n']:,} moves)" for n, k in zip(names, ks)], fontsize=9.5); ax.set_yticks([]); clean(ax)
save(fig, "stale-offers.png")

# 5. engine agreement by depth ------------------------------------------------------------------------
bd = S["engine"]["by_depth"]; ds = sorted(bd, key=int)
fig, ax = plt.subplots(figsize=(8.5, 4))
title(fig, "Searching deeper does not close the gap with Chess.com's engine",
      f"How often Stockfish 18's top move is Chess.com's top move, on {S['engine']['by_depth_brilliants']} Chess.com Brilliants.", y=1.06)
xs = [int(k) for k in ds]; ys = [bd[k]["brilliants"] * 100 for k in ds]
ax.plot(xs, ys, color=BLUE, linewidth=2, marker="o", markersize=7, markerfacecolor=BLUE, markeredgecolor=SURFACE, markeredgewidth=2)
for x, y in zip(xs, ys):
    if x in (8, 12, 16, 22):
        ax.text(x, y + 3, f"{y:.0f}%", ha="center", fontweight="bold")
ax.set_ylim(40, 100); ax.set_xlim(7, 23); ax.set_xticks(xs); ax.set_xlabel("Stockfish search depth"); ax.set_yticks([40, 60, 80, 100]); ax.set_yticklabels(["40%", "60%", "80%", "100%"])
ax.yaxis.grid(True, color=GRID, linewidth=1); ax.set_axisbelow(True); clean(ax)
ax.annotate("Mute Chess Fast review", xy=(12, ys[xs.index(12)]), xytext=(12, 47), ha="center", color=INK2, fontsize=9.5, arrowprops=dict(arrowstyle="-", color=INK2, linewidth=1))
save(fig, "engine-depth.png")

# 6. trade-off curve ----------------------------------------------------------------------------------
cv = S["curve"]; cut = S["model"]["cutoffs"]
fig, ax = plt.subplots(figsize=(8.5, 4.4))
title(fig, "Choosing the cutoff", "Each point on the line is a possible cutoff for Mute Exchange on the 337 held-out games (native Stockfish 19 Fast evidence).", y=1.05)
xs, ys = [0], [0]
for f_, fa in zip(cv["found"], cv["false_gallery"]):
    xs.append(fa); ys.append(f_)
ax.plot(xs, ys, color=BLUE, linewidth=2)
for name, lab, dx, dy in (("very strict", "very strict", 1.2, -14), ("strict", "strict", -1.2, 22), ("medium", "medium (selected)", 1.2, -15), ("loose", "loose", -1, 9)):
    i = max(j for j, s in enumerate(cv["score"]) if s >= cut[name])
    x, y = cv["false_gallery"][i], cv["found"][i]
    ax.plot([x], [y], marker="o", markersize=9 if name == "medium" else 7, color=BLUE, markeredgecolor=SURFACE, markeredgewidth=2)
    ax.text(x + dx, y + dy, f"{lab}\n{y} found, {x} false", fontsize=9.5, ha="left" if dx > 0 else "right", va="center", fontweight="bold" if name == "medium" else "normal")
ax.plot([sel["false_gallery"]], [sel["found_gallery"]], marker="o", markersize=9, color=ORANGE, markeredgecolor=SURFACE, markeredgewidth=2)
ax.text(sel["false_gallery"] + 1.2, sel["found_gallery"] - 18, f"Mute Selective (current)\n{sel['found_gallery']} found, {sel['false_gallery']} false", fontsize=9.5, ha="left", va="center")
ax.set_xlim(0, 45); ax.set_ylim(120, 360); ax.set_xlabel("Badges on moves not in Chess.com's gallery"); ax.set_ylabel(f"Brilliants found (of {total})")
ax.yaxis.grid(True, color=GRID, linewidth=1); ax.set_axisbelow(True); clean(ax)
save(fig, "cutoff.png")

# 7. what moved the needle ----------------------------------------------------------------------------
lad = list(S["ladder_witty1000_at_38_false"].items())
fig, ax = plt.subplots(figsize=(10.5, 4))
title(fig, "What moved the needle", "Brilliants found among 1,234 on the published 1,000-game test, each held to the same 38 false badges.", y=1.06)
ax.set_xlim(0, 1234); ax.set_ylim(-0.6, len(lad) - 0.15)
for i, (name, v) in enumerate(lad):
    y = len(lad) - 1 - i
    bar(ax, y, 0, 1234, 0.34, TRACK); bar(ax, y, 0, v, 0.34, ORANGE if i == 0 else BLUE)
    ax.text(0, y + 0.24, name, va="bottom", fontsize=10.5); ax.text(v - 12, y, f"{v}  ({v / 1234:.0%})", va="center", ha="right", color="white", fontweight="bold")
ax.set_yticks([]); ax.set_xticks([0, 300, 600, 900, 1234]); ax.set_xlabel("Brilliants found (of 1,234)"); clean(ax)
save(fig, "ladder.png")

# 8. the two owner examples ---------------------------------------------------------------------------
def board(fen, uci, offered, name, flip=False):
    b = chess.Board(fen); m = chess.Move.from_uci(uci)
    svg = chess.svg.board(b, arrows=[chess.svg.Arrow(m.from_square, m.to_square, color="#2a78d6")], fill={chess.parse_square(offered): "#f6c3ad"},
                          orientation=chess.BLACK if flip else chess.WHITE, size=360, colors={"square light": "#eeeee2", "square dark": "#8aa1b5", "margin": "#fcfcfb", "coord": "#52514e"})
    open(OUT + name, "w").write(svg)
board("rn1qkb1r/pp2pppp/2p2n2/8/2B1N1b1/5N2/PPPP1PPP/R1BQK2R w KQkq - 4 6", "f3e5", "d1", "legals-mate.svg")
board("rnbq1rk1/pp4pp/2pb4/8/3Pp3/4P3/PP1N1PPP/R1BQR1K1 b - - 1 12", "d6h2", "h2", "greek-gift.svg", flip=True)
print("figures written to", OUT)
