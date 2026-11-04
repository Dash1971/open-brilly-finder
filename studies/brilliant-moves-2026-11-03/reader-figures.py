#!/usr/bin/env python3
"""Reader figures for this study. Saved evidence only; no collection or tuning."""
import io
import json
import sys
from pathlib import Path

try:
    import chess
except ImportError:
    sys.path.insert(0, '/private/tmp/brilly-research-deps')
    import chess
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.patches import Rectangle, FancyBboxPatch
from PIL import Image

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'figures'
BG, INK, MUTED = '#f7f8f5', '#203a36', '#60726d'
MINT, BLUE, CORAL = '#61bda3', '#8195ae', '#db9567'
plt.rcParams.update({'font.family': 'DejaVu Sans', 'svg.fonttype': 'none',
                     'text.color': INK, 'axes.labelcolor': INK,
                     'xtick.color': MUTED, 'ytick.color': INK,
                     'svg.hashsalt': 'mute-chess-brilliants-318'})


def save(fig, name):
    fig.savefig(OUT / f'{name}.png', dpi=150, facecolor=BG, bbox_inches='tight')
    fig.savefig(OUT / f'{name}.svg', facecolor=BG, bbox_inches='tight', metadata={'Date': None})
    plt.close(fig)


def board_panel(ax, board, move=None, title='', arrow_color='#bd704c'):
    ax.set(xlim=(-.35, 8.05), ylim=(-.35, 8.05), aspect='equal')
    ax.axis('off')
    for rank in range(8):
        for file in range(8):
            ax.add_patch(Rectangle((file, rank), 1, 1,
                facecolor='#cadbd1' if (file + rank) % 2 else '#78998b'))
            piece = board.piece_at(chess.square(file, rank))
            if piece:
                ax.text(file + .5, rank + .49,
                    piece.unicode_symbol(invert_color=piece.color == chess.WHITE),
                    ha='center', va='center', fontsize=40,
                    color='#172e29' if piece.color == chess.BLACK else '#fcfffa',
                    path_effects=[pe.withStroke(linewidth=1.4, foreground='#172e29')])
        ax.text(-.17, rank + .5, str(rank + 1), ha='center', va='center', fontsize=9, color=MUTED)
        ax.text(rank + .5, -.17, 'abcdefgh'[rank], ha='center', va='center', fontsize=9, color=MUTED)
    if move:
        ax.annotate('', xy=(chess.square_file(move.to_square) + .5, chess.square_rank(move.to_square) + .5),
            xytext=(chess.square_file(move.from_square) + .5, chess.square_rank(move.from_square) + .5),
            arrowprops={'arrowstyle': '-|>', 'lw': 5, 'color': arrow_color, 'alpha': .8})
    if title:
        ax.set_title(title, fontsize=16, fontweight='bold', pad=12)


def reference_illustrations():
    cases = json.loads((ROOT / 'illustrative-cases.json').read_text())
    for case in cases:
        board = chess.Board(case['fen_before'])
        stages = [(board.copy(), None, 'Before the combination')]
        for san, caption in zip(case['moves'], case['captions']):
            move = board.parse_san(san)
            board.push(move)
            stages.append((board.copy(), move, caption))
        frames = []
        for i, (position, move, caption) in enumerate(stages):
            fig = plt.figure(figsize=(7.4, 8.4), facecolor=BG)
            ax = fig.add_axes([.08, .17, .84, .73])
            board_panel(ax, position, move)
            fig.text(.5, .96, case['title'], ha='center', va='top', fontsize=19, weight='bold')
            fig.text(.5, .915, 'Chess.com: ' + case['label'], ha='center', fontsize=14,
                     color='#267b66' if case['label'] == 'Brilliant' else MUTED)
            fig.text(.5, .12, caption, ha='center', fontsize=12, wrap=True)
            fig.text(.5, .073, f'{i} / 5  •  Illustrative legal continuation', ha='center', fontsize=10, color=MUTED)
            fig.text(.5, .035, case['conclusion'] if i == 5 else 'Watch the material come back on a different square.',
                     ha='center', fontsize=10, color=MUTED)
            buf = io.BytesIO()
            fig.savefig(buf, format='png', dpi=110, facecolor=BG)
            plt.close(fig)
            frame = Image.open(buf).convert('RGB')
            frames.append(frame.copy())
            if i in (0, 5):
                frame.save(OUT / f'{case["id"]}-{"before" if i == 0 else "after"}.png')
        frames[0].save(OUT / f'{case["id"]}.gif', save_all=True, append_images=frames[1:],
                       duration=[1800, 1400, 1400, 1400, 1400, 3500], loop=0, disposal=2)
    fig, axes = plt.subplots(1, 2, figsize=(12.4, 6.8), facecolor=BG)
    for ax, case in zip(axes, cases):
        b = chess.Board(case['fen_before'])
        move = b.parse_san(case['moves'][0])
        board_panel(ax, b, move, 'Chess.com: ' + case['label'])
    fig.suptitle('Similar material trades, different labels', fontsize=23, weight='bold', y=.98)
    fig.text(.5, .055, 'Both illustrated continuations trade equal-valued pieces and finish one pawn up.',
             ha='center', fontsize=12, color=MUTED)
    fig.text(.5, .017, 'Supplemental examples outside the 318-move comparison. The positions themselves are different.',
             ha='center', fontsize=10, color=MUTED)
    fig.tight_layout(rect=(0, .08, 1, .94))
    save(fig, 'similar-trades')


def current_rules():
    fig, ax = plt.subplots(figsize=(16, 3.65), facecolor=BG)
    ax.axis('off')
    steps = [('Good enough?', 'The move stays close\nto the engine’s best\nand remains playable.'),
             ('A real offer?', 'The opponent can take a\npiece and finish that\nexchange ahead.'),
             ('Material agrees?', 'En Croissant’s material\ncheck agrees, OR the mover\nhas an explicit winning mate.'),
             ('Offer matters?', 'Other checked moves\nwithout an offer don’t\nalready win comfortably.'),
             ('Checks agree?', 'Complete engine checks\nagree on the award.')]
    for i, (title, body) in enumerate(steps):
        left = .015 + i * .198
        ax.add_patch(FancyBboxPatch((left, .21), .174, .57, boxstyle='round,pad=.009',
            facecolor='#e2f2e9' if i == 2 else 'white', edgecolor='#dce5dc', transform=ax.transAxes))
        ax.text(left + .01, .67, f'{i+1}  {title}', fontsize=13, weight='bold', transform=ax.transAxes)
        ax.text(left + .01, .35, body, fontsize=10.2, linespacing=1.5, transform=ax.transAxes)
        if i < 4:
            ax.text(left + .186, .5, '→', ha='center', va='center', fontsize=21, color=MUTED, transform=ax.transAxes)
    ax.text(.015, .96, 'How the proposed Mute award works', fontsize=23, weight='bold', transform=ax.transAxes)
    ax.text(.015, .055, 'All five checks must pass. The highlighted material guard is new; exact thresholds are in the methods.',
            fontsize=11, color=MUTED, transform=ax.transAxes)
    save(fig, 'current-rules')


def quiet_offer():
    case = json.loads((ROOT / 'hero-case.json').read_text())
    before = chess.Board(case['fen_before'])
    move = chess.Move.from_uci(case['uci'])
    offered = chess.Board(case['fen_after'])
    accepted = offered.copy()
    for san in case['acceptance']:
        accepted.push_san(san)
    fig, axes = plt.subplots(1, 2, figsize=(12.4, 7.1), facecolor=BG)
    board_panel(axes[0], offered, move, 'A quiet bishop move leaves a rook offered', arrow_color='#3f9dcc')
    square = chess.parse_square(case['offered_square'])
    axes[0].add_patch(Rectangle((chess.square_file(square), chess.square_rank(square)), 1, 1,
        fill=False, edgecolor=CORAL, linewidth=4))
    axes[0].annotate('', xy=(1.5, .5), xytext=(6.5, 5.5),
        arrowprops={'arrowstyle': '-|>', 'lw': 3, 'color': CORAL, 'linestyle': '--'})
    board_panel(axes[1], accepted, title='If accepted: a rook traded for a bishop')
    fig.suptitle('A Brilliant can be a quiet move', fontsize=25, weight='bold', y=.99)
    fig.text(.5, .065, 'Chess.com: Brilliant   •   White plays Bg2 instead of moving the attacked rook.',
             ha='center', fontsize=12, color=MUTED)
    fig.text(.5, .022, 'The offer is real: White gives up more material than it receives, while keeping a playable position.',
             ha='center', fontsize=11, color=MUTED)
    fig.tight_layout(rect=(0, .09, 1, .94))
    save(fig, 'quiet-offer')


def comparison():
    data = json.loads((ROOT / 'comparison-rules.json').read_text())
    proposed = json.loads((ROOT / 'comparison-v3.json').read_text())
    keys = lambda source: {(r['game_id'], r['ply']) for r in source['rows']}
    if len(data['rows']) != 318 or keys(data) != keys(proposed):
        raise ValueError('Reader chart requires the same frozen 318 moves in both replays')
    metrics = [data['summaries']['ec']['all_fresh'],
               data['summaries']['mute_v2']['all_fresh'],
               proposed['summaries']['mute_v3']['all_fresh']]
    labels = ['En Croissant', 'Mute before guard', 'Mute with guard (proposed)']
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.6), facecolor=BG)
    for ax, kind, title in zip(axes, ['TP', 'FP'], ['Confirmed Brilliants found', 'Other moves also given Brilliant']):
        denominator = metrics[0]['positive_n' if kind == 'TP' else 'negative_n']
        if denominator != 159 or any(m['positive_n' if kind == 'TP' else 'negative_n'] != denominator for m in metrics):
            raise ValueError('Expected 159 confirmed examples in each comparison group')
        values = [m[kind] for m in metrics]
        ax.set_facecolor('white')
        ax.barh(labels, values,
                color=[BLUE, '#b3beb8', MINT if kind == 'TP' else CORAL], height=.48)
        ax.invert_yaxis()
        ax.set_xlim(0, denominator * 1.22)
        ax.set_xticks([0, 40, 80, 120, 159])
        ax.set_title(title, fontsize=14, weight='bold', pad=18)
        ax.set_xlabel(f'Out of {denominator} checked moves')
        ax.spines[['top', 'right', 'left']].set_visible(False)
        for y, value in enumerate(values):
            ax.text(value + denominator * .016, y, f'{value} / {denominator}', va='center', fontsize=14)
    fig.suptitle('Same 318 moves, three award rules', fontsize=24, weight='bold', y=.99)
    fig.text(.025, .045, '159 confirmed Brilliants + 159 comparison moves from strong players. Deliberately difficult examples.',
             fontsize=10.5, color=MUTED)
    fig.text(.025, .009, 'The guard was chosen after inspecting this sample. These are retrospective counts, not population error rates.',
             fontsize=10.5, color=MUTED)
    fig.tight_layout(rect=(0, .09, 1, .94))
    save(fig, 'rule-comparison')


if __name__ == '__main__':
    OUT.mkdir(exist_ok=True)
    reference_illustrations()
    current_rules()
    quiet_offer()
    comparison()
