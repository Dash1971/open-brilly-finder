#!/usr/bin/env python3
"""Retrospective material-gate screen, NOT a classifier change or new study run.

Uses only saved pilot FENs and owner/known-positive controls. No browser,
network, engine, threshold tuning or application edits. The necessary-gate
screen is not a full hypothetical classifier replay: alternative-root relevance
and confidence behavior are not recomputed with a replacement predicate.
"""
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    import chess
except ImportError:
    sys.path.insert(0, '/private/tmp/brilly-research-deps')
    import chess

ROOT = Path(__file__).resolve().parent
VALUES = {chess.PAWN: 90, chess.KNIGHT: 300, chess.BISHOP: 300,
          chess.ROOK: 500, chess.QUEEN: 1000, chess.KING: 0}
ALPHA, BETA = -10000, 10000
START = time.monotonic()
QSEARCH_CALLS = 0
SEE_CALLS = 0


def material(board):
    # Deliberately no checkmate bonus/sentinel: this is physical material only.
    return sum(VALUES[p.piece_type] * (1 if p.color == board.turn else -1)
               for p in board.piece_map().values())


def gain(board, move):
    captured = (90 if board.is_en_passant(move) else
                VALUES[board.piece_at(move.to_square).piece_type]
                if board.piece_at(move.to_square) else 0)
    return captured + (VALUES[move.promotion] - 90 if move.promotion else 0)


def qsearch(board, alpha, beta, stand):
    global QSEARCH_CALLS
    QSEARCH_CALLS += 1
    if QSEARCH_CALLS % 256 == 0 and time.monotonic() - START > 35:
        raise TimeoutError('35-second exploratory probe cap reached')
    # Either side may stop exchanging, even when the real game would require a
    # quiet check response. No quiet responses are searched; this is a heuristic.
    if stand >= beta:
        return beta
    alpha = max(alpha, stand)
    captures = sorted(board.generate_legal_captures(), key=lambda move: gain(board, move), reverse=True)
    for move in captures:
        value = gain(board, move)
        board.push(move)
        score = -qsearch(board, -beta, -alpha, -stand - value)
        board.pop()
        if score >= beta:
            return beta
        alpha = max(alpha, score)
    return alpha


def see(board, square):
    global SEE_CALLS
    SEE_CALLS += 1
    best = 0
    for move in list(board.generate_legal_captures()):
        if move.to_square != square:
            continue
        value = gain(board, move)
        board.push(move)
        score = value - see(board, square)
        board.pop()
        best = max(best, score)
    return best


def probe(before, after):
    original, board = chess.Board(before), chess.Board(after)
    original_material = material(original)
    credit = max(0, -material(board) - original_material)
    acceptances = []
    for move in list(board.generate_legal_captures()):
        victim = board.piece_at(move.to_square)
        if not victim or victim.piece_type in (chess.PAWN, chess.KING):
            continue
        value, san, uci = gain(board, move), board.san(move), move.uci()
        board.push(move)
        local_gain = value - see(board, move.to_square)
        # The specific acceptance, not merely some capture of that square,
        # must satisfy the existing legal-offer exchange/credit condition.
        if local_gain > credit + 100:
            outcome = qsearch(board, ALPHA, BETA, material(board))
            acceptances.append({'san': san, 'uci': uci, 'same_square_gain': local_gain,
                                'capture_only_outcome_mover': outcome,
                                'loss_from_raw_premove_material': original_material - outcome})
        board.pop()
    return {'raw_premove_material_mover': original_material, 'immediate_capture_promotion_credit': credit,
            'qualifying_legal_acceptances': acceptances,
            'necessary_material_gate_passes': any(a['loss_from_raw_premove_material'] > 100 for a in acceptances)}


def read(name):
    return json.loads((ROOT / name).read_text())


def main():
    comparison, baseline = read('comparison-rules.json'), read('analysis-baseline.json')
    rows = []
    for row in comparison['rows']:
        target = next(t for t in baseline['targets'] if
                      t['game_id'] == row['game_id'] and t['ply'] == row['ply'])
        rows.append({'game_id': row['game_id'], 'ply': row['ply'], 'san': row['san'],
                     'fresh_binary_label': row['primary_fresh_binary_label'],
                     'current_v2_symbol': row['mute_v2']['symbol'],
                     'existing_ec_material_sacrifice': row['ec_sacrifice'],
                     'legal_piece_offer': row['mute_piece_offer'],
                     'offer_AND_ec_material_gate': row['ec_sacrifice'] and row['mute_piece_offer'],
                     **probe(target['fen_before'], target['fen_after'])})
    controls = []
    for control in comparison['owner_controls_separate_from_chesscom_labels']:
        controls.append({'name': control['name'], 'label_provenance': 'owner_expected_not_brilliant',
                         'fresh_chesscom_label': 'unknown',
                         **probe(control['fen_before'], control['derived_fen_after'])})
    old = json.loads((ROOT.parent / 'brilliants-2026-11-02/results.json').read_text())
    bb2 = next(sample for sample in old['samples'] if sample['game'] == '172016241890')
    controls.append({'name': 'Ju Wenjun 19.Bb2', 'label_provenance': 'previously used known positive',
                     **probe(bb2['fen_before'], bb2['fen_after'])})
    target = next(t for t in baseline['targets'] if t['game_id'] == '186305472636' and t['ply'] == 18)
    board = chess.Board(target['fen_before'])
    line = []
    for san in ['Nxd5', 'Nxd5', 'Bxd5', 'cxd5', 'Bxg5']:
        move = board.parse_san(san)  # Raises if this proposed explanatory line is illegal.
        captured = board.piece_at(move.to_square)
        board.push(move)
        raw_black = sum(VALUES[p.piece_type] * (1 if p.color == chess.BLACK else -1)
                        for p in board.piece_map().values())
        line.append({'san': san, 'uci': move.uci(), 'captured_piece': captured.symbol() if captured else None,
                     'black_minus_white_material': raw_black})
    current_positives = [row for row in rows if row['fresh_binary_label'] == 'brilliant' and row['current_v2_symbol'] == '!!']
    result = {
        'run_at_utc': datetime.now(timezone.utc).isoformat(),
        'scope': 'Retrospective exploratory gate screen on the completed pilot; no held-out validation claim.',
        'no_collection_engine_or_rule_changes': True,
        'source_classifier_commit': comparison['source_provenance']['commit'],
        'input_hashes': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                         for name in ('comparison-rules.json', 'analysis-baseline.json')},
        'algorithm': 'Retain a specific legal nonpawn offer acceptance with same-square exchange gain > credit+100; force it, then perform all-square capture-only material negamax from the mover. Require at least one such acceptance to leave >100 physical material units below RAW pre-move balance.',
        'alpha_beta_root_bounds': [ALPHA, BETA], 'material_units': VALUES,
        'checkmate_scoring': 'Physical material only; no mate bonus or -10000 terminal sentinel.',
        'stopping_semantics': 'Either side may stand pat; quiet moves/check responses not searched. Legal captures only.',
        'rows': rows, 'separate_known_controls': controls,
        'AND_gate_loses_current_fresh_positives': [{'game_id': row['game_id'], 'ply': row['ply'], 'san': row['san']}
            for row in current_positives if not row['offer_AND_ec_material_gate']],
        'counterfactual_gate_loses_current_fresh_positives': [{'game_id': row['game_id'], 'ply': row['ply'], 'san': row['san']}
            for row in current_positives if not row['necessary_material_gate_passes']],
        'gotham_legal_recoup_counterexample': {'game_id': '186305472636', 'ply': 18,
            'fresh_chesscom_label': 'Brilliant', 'conditional_line': '9...Nxd5 10.Nxd5 Bxd5 11.cxd5 Bxg5',
            'not_claimed_as_played_game_continuation': True, 'verified_steps': line},
        'qsearch_calls': QSEARCH_CALLS, 'same_square_see_calls': SEE_CALLS,
        'elapsed_seconds': time.monotonic() - START,
        'limitations': ['Necessary-gate screen, not full modified-policy evaluation.',
            'These pilot examples were inspected retrospectively; future candidate tuning would consume them as development data.',
            'Capture-only material minimax is not complete chess search or an account of human perception.',
            'Root bounds are finite; all observed material values remained strictly inside them.'],
    }
    path = ROOT / 'exploratory-material-probe.json'
    path.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: result[key] for key in ('AND_gate_loses_current_fresh_positives',
          'counterfactual_gate_loses_current_fresh_positives', 'qsearch_calls', 'same_square_see_calls', 'elapsed_seconds')}, indent=2))


if __name__ == '__main__':
    main()
