#!/usr/bin/env python3
"""Figures for this pilot only; read saved observations/rule results, never collect or tune."""
import json
import sqlite3
from pathlib import Path

import chess
import chess.svg
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.patches import FancyBboxPatch, Rectangle

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'figures'
BG, INK, MUTED, MINT, BLUE, ORANGE = '#f7f8f5', '#203a36', '#60726d', '#61bda3', '#8195ae', '#db9567'
plt.rcParams.update({'font.family': 'DejaVu Sans', 'svg.fonttype': 'none', 'text.color': INK,
                     'axes.labelcolor': INK, 'xtick.color': MUTED, 'ytick.color': INK,
                     'svg.hashsalt': 'mute-brilliants-pilot-v1'})


def save(fig, name):
    fig.savefig(OUT / (name + '.png'), dpi=140, facecolor=BG, bbox_inches='tight')
    fig.savefig(OUT / (name + '.svg'), facecolor=BG, bbox_inches='tight', metadata={'Date': None})
    plt.close(fig)


def board_panel(ax, board, title, move=None):
    ax.set(xlim=(0, 8), ylim=(0, 8), aspect='equal'); ax.axis('off')
    for rank in range(8):
        for file in range(8):
            ax.add_patch(Rectangle((file, rank), 1, 1, facecolor='#cadbd1' if (file + rank) % 2 else '#78998b'))
            piece = board.piece_at(chess.square(file, rank))
            if piece:
                ax.text(file + .5, rank + .49, piece.unicode_symbol(invert_color=piece.color == chess.WHITE),
                        ha='center', va='center', fontsize=43, color='#172e29' if piece.color == chess.BLACK else '#fcfffa',
                        path_effects=[pe.withStroke(linewidth=1.4, foreground='#172e29')])
    if move:
        start, end = move.from_square, move.to_square
        ax.annotate('', xy=(chess.square_file(end)+.5, chess.square_rank(end)+.5),
                    xytext=(chess.square_file(start)+.5, chess.square_rank(start)+.5),
                    arrowprops={'arrowstyle': '-|>', 'lw': 6, 'color': '#c1734c', 'alpha': .72})
    ax.set_title(title, fontsize=15, pad=12, fontweight='bold')


def main():
    OUT.mkdir(exist_ok=True)
    db = sqlite3.connect(ROOT / 'corpus.sqlite3'); db.row_factory = sqlite3.Row
    result = json.loads((ROOT / 'comparison-rules.json').read_text())
    games = db.execute('SELECT count(*) FROM games').fetchone()[0]
    obs = db.execute('SELECT game_id,ply,source_type,label_status FROM observations').fetchall()
    gallery = {(o['game_id'], o['ply']) for o in obs if o['source_type'] == 'gallery'}
    pos = {(o['game_id'], o['ply']) for o in obs if o['label_status'] == 'fresh_confirmed_brilliant'}
    neg = {(o['game_id'], o['ply']) for o in obs if o['label_status'] == 'fresh_confirmed_non_brilliant'}
    fig, ax = plt.subplots(figsize=(12, 6)); fig.patch.set_facecolor(BG); ax.axis('off')
    ax.text(.02, .94, 'A small, traceable pilot', fontsize=25, weight='bold', transform=ax.transAxes)
    for i, (value, label) in enumerate([(games, 'unique games'), (len(gallery), 'gallery entries'), (len(pos|neg), 'fresh move labels')]):
        left = .02+i*.33
        ax.add_patch(FancyBboxPatch((left, .48), .29, .32, boxstyle='round,pad=.012', facecolor='white', edgecolor='#e1e7e0', transform=ax.transAxes))
        ax.text(left+.025, .64, str(value), fontsize=39, weight='bold', transform=ax.transAxes)
        ax.text(left+.025, .54, label, fontsize=14, color=MUTED, transform=ax.transAxes)
    total = len(pos|neg); width = .94
    ax.add_patch(Rectangle((.02, .24), width*len(pos)/total, .12, color=MINT, transform=ax.transAxes))
    ax.add_patch(Rectangle((.02+width*len(pos)/total, .24), width*len(neg)/total, .12, color=BLUE, transform=ax.transAxes))
    ax.text(.02, .15, f'{len(pos)} fresh Brilliants', fontsize=15, transform=ax.transAxes)
    ax.text(.52, .15, f'{len(neg)} confirmed non-Brilliants', fontsize=15, transform=ax.transAxes)
    ax.text(.02, .04, f'{len(gallery & neg)} gallery label changed in fresh review. Gallery absence is never a negative label.', fontsize=11, color=MUTED, transform=ax.transAxes)
    save(fig, 'pilot-cohort')
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.3)); fig.patch.set_facecolor(BG)
    for ax, kind, title in zip(axes, ['TP', 'FP'], ['Detected fresh Brilliants', 'False awards on sampled non-Brilliants']):
        metrics = [result['summaries'][p]['all_fresh'] for p in ['ec', 'mute_v2']]
        denominator = metrics[0]['positive_n' if kind == 'TP' else 'negative_n']
        values = [m[kind] for m in metrics]
        ax.set_facecolor('white'); ax.barh(['En Croissant', 'Mute v2'], values, color=[BLUE, MINT if kind == 'TP' else ORANGE], height=.48)
        ax.invert_yaxis(); ax.set_xlim(0, max(1, denominator)*1.2); ax.set_title(title, fontsize=14, weight='bold', pad=18)
        ax.set_xlabel(f'Count out of {denominator} sampled moves'); ax.spines[['top', 'right', 'left']].set_visible(False)
        for y, value in enumerate(values): ax.text(value+.3, y, f'{value}/{denominator} ({value/denominator:.0%})', va='center', fontsize=13)
    fig.suptitle('Same positions, different award rules', fontsize=24, fontweight='bold', y=1.03)
    fig.text(.03, -.035, f'SAMPLED pilot • {len(result["rows"])} analyzed moves • SF18 / 300k nodes • Mute v2 @ b3585f2\nPublished-label comparison with whole-window checks; not a population accuracy estimate.', fontsize=10, color=MUTED)
    fig.tight_layout(); save(fig, 'rule-comparison')
    selected = [('hansen-qxe4', '184403311373', 59), ('knvb-bxd5', '186066679548', 103), ('nelsi-qxd6', '186405804254', 51)]
    labels = {'??': 'Blunder', '?': 'Mistake', '?!': 'Dubious', '!?': 'Interesting', '!!': 'Brilliant', '!': 'Good', '': 'Unannotated'}
    for name, game_id, ply in selected:
        row = db.execute('SELECT * FROM positions WHERE game_id=? AND ply=?', (game_id, ply)).fetchone()
        if not row: continue
        evaluated = next((r for r in result['rows'] if r['game_id'] == game_id and r['ply'] == ply), None)
        if not evaluated: continue
        fresh = next((o['label'] for o in evaluated['observations'] if o['source_type'] == 'fresh_review'), 'unknown')
        caption = f'Fresh review: {labels.get(fresh, fresh.title())} · Mute v2: {labels.get(evaluated["mute_v2"]["symbol"], "Unknown")}'
        before, after = chess.Board(row['fen_before']), chess.Board(row['fen_after']); move = chess.Move.from_uci(row['uci'])
        fig, axes = plt.subplots(1, 2, figsize=(12, 6.6)); fig.patch.set_facecolor(BG)
        board_panel(axes[0], before, 'Before ' + row['san'], move); board_panel(axes[1], after, 'After ' + row['san'])
        fig.suptitle(caption, fontsize=17, weight='bold'); fig.text(.05, .015, f'Observed move, not a suggested continuation · game {game_id} · ply {ply}', color=MUTED, fontsize=10)
        fig.tight_layout(rect=(0, .04, 1, .92)); save(fig, name)
        for suffix, board, arrows in [('before', before, [chess.svg.Arrow(move.from_square, move.to_square)]), ('after', after, [])]:
            (OUT/(name+'-'+suffix+'.svg')).write_text(chess.svg.board(board, arrows=arrows, size=560,
                colors={'square light': '#cadbd1', 'square dark': '#78998b', 'arrow green': '#c1734ccc'}))
    (OUT/'figure-sources.json').write_text(json.dumps({'games': games, 'gallery_entries': len(gallery), 'fresh_positive': len(pos),
        'fresh_negative': len(neg), 'comparison_rows': len(result['rows']), 'summaries': {k: result['summaries'][k]['all_fresh'] for k in ['ec', 'mute_v2']},
        'notes': 'Read from corpus.sqlite3 and comparison-rules.json; no collection, tuning or model inference. Board panels show the recorded played move.'}, indent=2)+'\n')


if __name__ == '__main__': main()
