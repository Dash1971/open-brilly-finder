#!/usr/bin/env python3
"""Unified-study figures from frozen saved evidence; no collection or analysis.

Run with Python 3 and matplotlib, Pillow and python-chess installed:
    python3 reader-figures.py
Required adjacent inputs: SUMMARY.json, hero-case.json, illustrative-cases.json.
SUMMARY must have completed:true and combined/validation groups, each with
n, positive_n, negative_n, games and policies.ec_raw / policies.mute_v3.
Policy fields: TP,FN,FP,TN and agreement (fraction, not percentage).
Only direct EC and confirmed Mute v3 appear in the headline chart.
The optional prospective group is validated if present, but not mixed into
combined or reserved-validation results. Run only after the cohort is frozen.
"""
import io
import json
from pathlib import Path

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
                     'svg.hashsalt': 'mute-chess-unified-brilliants'})


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
    if len(cases) != 2:
        raise ValueError('Expected two supplemental reference combinations')
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
            fig.text(.5, .073, f'{i} / {len(case["moves"])}  •  Illustrative legal continuation', ha='center', fontsize=10, color=MUTED)
            fig.text(.5, .035, case['conclusion'] if i == len(case['moves']) else 'Watch the material come back on a different square.',
                     ha='center', fontsize=10, color=MUTED)
            buf = io.BytesIO()
            fig.savefig(buf, format='png', dpi=110, facecolor=BG)
            plt.close(fig)
            frame = Image.open(buf).convert('RGB')
            frames.append(frame.copy())
            if i in (0, len(case['moves'])):
                frame.save(OUT / f'{case["id"]}-{"before" if i == 0 else "after"}.png')
        frames[0].save(OUT / f'{case["id"]}.gif', save_all=True, append_images=frames[1:],
                       duration=[1800] + [1400] * (len(stages) - 2) + [3500], loop=0, disposal=2)
    fig, axes = plt.subplots(1, 2, figsize=(12.4, 6.8), facecolor=BG)
    for ax, case in zip(axes, cases):
        b = chess.Board(case['fen_before'])
        move = b.parse_san(case['moves'][0])
        board_panel(ax, b, move, 'Chess.com: ' + case['label'])
    fig.suptitle('Similar material trades, different labels', fontsize=23, weight='bold', y=.98)
    fig.text(.5, .055, 'Both illustrated continuations trade equal-valued pieces and finish one pawn up.',
             ha='center', fontsize=12, color=MUTED)
    fig.text(.5, .017, 'Supplemental reference positions excluded from the benchmark. These are different positions.',
             ha='center', fontsize=10, color=MUTED)
    fig.tight_layout(rect=(0, .08, 1, .94))
    save(fig, 'similar-trades')


def current_rules():
    fig, ax = plt.subplots(figsize=(16, 3.65), facecolor=BG)
    ax.axis('off')
    steps = [('Strong enough?', 'At most 5 mapped points\nlost; resulting score\nat least −1.00 pawns.'),
             ('A legal piece offer?', 'Captures on one square\nbeat immediate gains\nplus the material margin.'),
             ('Material agrees?', 'En Croissant’s material\ncheck agrees, OR the mover\nhas an explicit winning mate.'),
             ('Offer matters?', 'Other checked moves\nwithout an offer don’t\nalready win comfortably.'),
             ('Checks agree?', 'Complete analysis windows\ncorroborate the award;\notherwise withhold it.')]
    for i, (title, body) in enumerate(steps):
        left = .015 + i * .198
        ax.add_patch(FancyBboxPatch((left, .21), .174, .57, boxstyle='round,pad=.009',
            facecolor='#e2f2e9' if i == 2 else 'white', edgecolor='#dce5dc', transform=ax.transAxes))
        ax.text(left + .01, .67, f'{i+1}  {title}', fontsize=12, weight='bold', transform=ax.transAxes)
        ax.text(left + .01, .35, body, fontsize=10.2, linespacing=1.5, transform=ax.transAxes)
        if i < 4:
            ax.text(left + .186, .5, '→', ha='center', va='center', fontsize=21, color=MUTED, transform=ax.transAxes)
    ax.text(.015, .96, 'How Mute’s open Brilliant rule works', fontsize=23, weight='bold', transform=ax.transAxes)
    ax.text(.015, .055, 'All five checks must pass. At least two candidate moves must be evaluated; exact formulas are in the methods.',
            fontsize=11, color=MUTED, transform=ax.transAxes)
    save(fig, 'current-rules')


def quiet_offer():
    case = json.loads((ROOT / 'hero-case.json').read_text())
    before = chess.Board(case['fen_before'])
    move = chess.Move.from_uci(case['uci'])
    if move not in before.legal_moves:
        raise ValueError('Hero move must be legal')
    before.push(move)
    offered = chess.Board(case['fen_after'])
    if before.fen().split()[:4] != offered.fen().split()[:4]:
        raise ValueError('Hero before/move/after identity mismatch')
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


def read_summary():
    summary = json.loads((ROOT / 'SUMMARY.json').read_text())
    if summary.get('completed') is not True:
        raise ValueError('No reader figures until SUMMARY.completed is true')
    for name in ('combined', 'validation', 'prospective'):
        if name not in summary:
            if name == 'prospective':
                continue
            raise ValueError(f'Missing summary group: {name}')
        group = summary[name]
        for key in ('n', 'positive_n', 'negative_n', 'games'):
            if type(group[key]) is not int or group[key] <= 0:
                raise ValueError(f'{name}.{key} must be a positive integer')
        if group['n'] != group['positive_n'] + group['negative_n']:
            raise ValueError(f'{name}: sample denominators disagree')
        if group['games'] > group['n']:
            raise ValueError(f'{name}: more games than observed moves')
        for policy in ('ec_raw', 'mute_v3'):
            metric = group['policies'][policy]
            if any(type(metric[k]) is not int or metric[k] < 0
                   for k in ('TP', 'FN', 'FP', 'TN')):
                raise ValueError(f'{name}.{policy}: invalid confusion counts')
            if (metric['TP'] + metric['FN'] != group['positive_n'] or
                    metric['FP'] + metric['TN'] != group['negative_n']):
                raise ValueError(f'{name}.{policy}: confusion counts disagree with cohort')
            agreement = metric['agreement']
            expected = (metric['TP'] + metric['TN']) / group['n']
            if (type(agreement) not in (float, int) or not 0 <= agreement <= 1 or
                    abs(agreement - expected) > 1e-6):
                raise ValueError(f'{name}.{policy}: agreement must be an accurate fraction')
    if summary['validation']['n'] > summary['combined']['n']:
        raise ValueError('Validation cannot exceed the combined cohort')
    return summary


def comparison(summary):
    policies = [('ec_raw', 'En Croissant (direct)', BLUE),
                ('mute_v3', 'Mute Chess (confirmed)', MINT)]
    columns = [('agreement', 'Agreement with Chess.com', 'Higher means closer agreement'),
               ('TP', 'Chess.com Brilliants found', 'Higher recognizes more Brilliants'),
               ('FP', 'Extra awards on comparison moves', 'Lower avoids more disagreements')]
    fig, axes = plt.subplots(2, 3, figsize=(17, 9.2), facecolor=BG)
    for row, (group_key, title) in enumerate(
            [('combined', 'Full challenge set'), ('validation', 'Reserved-game validation')]):
        group = summary[group_key]
        for col, (kind, heading, explanation) in enumerate(columns):
            ax = axes[row, col]
            ax.set_facecolor('white')
            for y, (policy, label, color) in enumerate(policies):
                metric = group['policies'][policy]
                if kind == 'agreement':
                    numerator, denominator = metric['TP'] + metric['TN'], group['n']
                    value = 100 * metric['agreement']
                else:
                    numerator = metric[kind]
                    denominator = group['positive_n' if kind == 'TP' else 'negative_n']
                    value = 100 * numerator / denominator
                ax.barh(y, value, color=color, height=.45)
                ax.text(value + 1.5, y, f'{value:.1f}%  ({numerator}/{denominator})',
                        va='center', fontsize=11, color=INK)
            ax.set_yticks([0, 1], [p[1] for p in policies] if col == 0 else ['', ''])
            ax.invert_yaxis()
            ax.set_ylim(1.65, -.65)
            ax.set_xlim(0, 139)
            ax.set_xticks([0, 25, 50, 75, 100], ['0%', '25%', '50%', '75%', '100%'])
            ax.spines[['top', 'right', 'left']].set_visible(False)
            ax.tick_params(axis='y', length=0, labelsize=11)
            if row == 0:
                ax.set_title(heading + '\n' + explanation, fontsize=12, weight='bold', pad=18)
            ax.text(0, -.22,
                    f"{title} · {group['n']} moves · {group['games']} games" if col == 0 else
                    (f"{group['positive_n']} observed Brilliants" if kind == 'TP' else
                     f"{group['negative_n']} explicit non-Brilliants"),
                    transform=ax.transAxes, fontsize=10, color=MUTED)
    fig.suptitle('How closely do open rules agree with Chess.com?',
                 fontsize=24, weight='bold', y=.985)
    fig.text(.02, .062, 'Reserved games were excluded from the examples used to choose the fixed Mute rule.',
             fontsize=11, color=MUTED)
    fig.text(.02, .027, 'A deliberately enriched challenge set. These rates do not describe ordinary-game prevalence or awards per game.',
             fontsize=11, color=MUTED)
    fig.tight_layout(rect=(0, .10, 1, .92), h_pad=4.5, w_pad=2)
    save(fig, 'rule-comparison')


if __name__ == '__main__':
    summary = read_summary()
    OUT.mkdir(exist_ok=True)
    reference_illustrations()
    current_rules()
    quiet_offer()
    comparison(summary)
