# SPDX-License-Identifier: AGPL-3.0-only
"""Render Mute Selective's headline metrics from published results."""
from pathlib import Path
import json
import os
os.environ.setdefault('MPLCONFIGDIR', '/private/tmp/mute-research-mpl')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
P = Path(__file__).resolve().parents[1]
DATA_PATH = P / 'data/fresh-results.json'
if DATA_PATH.exists():
    c = json.loads(DATA_PATH.read_text())['counts']['primary']['selective']
else:
    c = json.loads((P / 'data/selective-update-2026-11-06.json').read_text())['metrics']['selective']
tp, fn, fp = c['TP'], c['FN'], c['FP']
INK, MOSS, GOLD, PALE = '#172723', '#668478', '#D9B25F', '#EDF1EA'
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 12, 'svg.fonttype': 'none'})
fig = plt.figure(figsize=(12, 5.7), dpi=140, facecolor='white')
fig.text(.055, .91, 'Chess.com-style Brilliants, measured', color=INK, fontsize=23, weight='bold')
fig.text(.055, .84, 'Mute Selective · 1,000 test games · Witty_Alien', color=INK, fontsize=12)
rows = [(.51, 'Chess.com Brilliants we recognize', tp, tp+fn),
        (.22, 'Our Brilliant badges that match Chess.com', tp, tp+fp)]
for bottom, title, n, total in rows:
    fraction = n / total
    ax = fig.add_axes([.055, bottom, .88, .16])
    ax.barh([0], [100], color=PALE, height=.8)
    ax.barh([0], [fraction * 100], color=MOSS, height=.8)
    ax.text(1.5, 0, f'{fraction:.1%}', va='center', ha='left', color='white', fontsize=23, weight='bold')
    ax.text(101.5, 0, f'{n:,} / {total:,}', va='center', ha='right', color=INK, fontsize=14)
    ax.set_xlim(0, 103)
    ax.set_ylim(-.5, .5)
    ax.axis('off')
    fig.text(.055, bottom+.17, title, color=INK, fontsize=14, weight='bold')
fig.text(.055, .075, '38 extra awards across 30,423 other moves · Stockfish 19 Fast analysis', color=INK, fontsize=12)
fig.text(.055, .025, 'Reference: the player’s complete Brilliant gallery; scores cover own moves in gallery-listed games.', color='#46554f', fontsize=10)
for suffix in ['png', 'svg']:
    fig.savefig(P / f'figures/fresh-results.{suffix}', dpi=140, facecolor='white', metadata={'Creator': 'Open Brilly Finder'})

svg_path = P / 'figures/fresh-results.svg'
svg_path.write_text('\n'.join(line.rstrip() for line in svg_path.read_text().splitlines()) + '\n')
