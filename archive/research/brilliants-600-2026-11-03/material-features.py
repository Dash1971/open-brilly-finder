#!/usr/bin/env python3
"""Descriptive capture-recovery features; never a production classification rule.

No engine, network, browser, tuning, or app changes. Each position shares a
strict one-second / 100,000-call budget across same-square SEE and all-square
capture search. Incomplete positions return UNKNOWN, never a negative finding.
"""
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, '/private/tmp/brilly-research-deps')
import chess

ROOT = Path(__file__).resolve().parent
VALUES = {chess.PAWN: 90, chess.KNIGHT: 300, chess.BISHOP: 300,
          chess.ROOK: 500, chess.QUEEN: 1000, chess.KING: 0}
SECONDS, MAX_CALLS, INF = 1.0, 100_000, 1_000_000_000


class Budget:
    def __init__(self):
        self.start = time.monotonic()
        self.calls = self.see = self.capture = self.checked = self.quiet_evasions = 0

    def tick(self, kind):
        self.calls += 1
        if kind == 'see':
            self.see += 1
        else:
            self.capture += 1
        if self.calls > MAX_CALLS:
            raise TimeoutError('100000-call cap')
        if time.monotonic() - self.start >= SECONDS:
            raise TimeoutError('one-second cap')

    def checked_node(self, board):
        if board.is_check():
            self.checked += 1
            if any(not board.is_capture(move) for move in board.legal_moves):
                self.quiet_evasions += 1


def material(board):
    # Physical material only, including at checkmate: no mate score or sentinel.
    return sum(VALUES[p.piece_type] * (1 if p.color == board.turn else -1)
               for p in board.piece_map().values())


def gain(board, move):
    victim = board.piece_at(move.to_square)
    value = 90 if board.is_en_passant(move) else VALUES[victim.piece_type] if victim else 0
    return value + (VALUES[move.promotion] - 90 if move.promotion else 0)


def same_square(board, square, budget):
    budget.tick('see')
    budget.checked_node(board)
    best = 0
    for move in list(board.generate_legal_captures()):
        if move.to_square != square:
            continue
        value = gain(board, move)
        board.push(move)
        try:
            best = max(best, value - same_square(board, square, budget))
        finally:
            board.pop()
    return best


def captures(board, alpha, beta, budget):
    budget.tick('capture')
    budget.checked_node(board)
    # Stand-pat remains heuristic in check. Quiet evasions are NOT searched.
    best, line = material(board), []
    if best >= beta:
        return best, line
    alpha = max(alpha, best)
    for move in sorted(board.generate_legal_captures(), key=lambda m: gain(board, m), reverse=True):
        uci = move.uci()
        board.push(move)
        try:
            child, continuation = captures(board, -beta, -alpha, budget)
        finally:
            board.pop()
        score = -child
        if score > best:
            best, line = score, [uci] + continuation
        alpha = max(alpha, best)
        if alpha >= beta:
            break
    return best, line


def line_san(board, ucis):
    result, position = [], board.copy()
    for uci in ucis:
        move = chess.Move.from_uci(uci)
        result.append(position.san(move))
        position.push(move)
    return result


def probe(before, after):
    budget, acceptances, reasons = Budget(), [], []
    original, board = chess.Board(before), chess.Board(after)
    baseline = material(original)
    credit = max(0, -material(board) - baseline)
    try:
        for move in list(board.generate_legal_captures()):
            budget.tick('see')
            victim = board.piece_at(move.to_square)
            if not victim or victim.piece_type in (chess.PAWN, chess.KING):
                continue
            value, san, uci = gain(board, move), board.san(move), move.uci()
            board.push(move)
            try:
                local = value - same_square(board, move.to_square, budget)
                if local <= credit + 100:
                    continue
                outcome, continuation = captures(board, -INF, INF, budget)
                conditional = [uci] + continuation
                acceptances.append({'san': san, 'uci': uci, 'same_square_gain': local,
                    'capture_only_outcome_mover': outcome,
                    'loss_from_raw_premove_material': baseline - outcome,
                    'conditional_line_uci': conditional})
            finally:
                board.pop()
            acceptances[-1]['conditional_line_san'] = line_san(board, conditional)
        if time.monotonic() - budget.start >= SECONDS:
            raise TimeoutError('one-second cap')
    except TimeoutError as error:
        reasons.append(str(error))
    losses = [a['loss_from_raw_premove_material'] for a in acceptances]
    complete = not reasons
    maxloss = max(losses) if losses and complete else None
    return {'raw_premove_material_mover': baseline,
        'immediate_capture_promotion_credit': credit,
        'qualifying_legal_acceptances': acceptances,
        'outcome': 'UNKNOWN' if reasons else 'complete' if losses else 'no_qualifying_acceptance',
        'maxloss': maxloss, 'recoup': maxloss <= 100 if maxloss is not None else None,
        'unknown_reasons': reasons,
        'checked_nodes_with_heuristic_stand_pat': budget.checked,
        'checked_nodes_with_omitted_quiet_evasions': budget.quiet_evasions,
        'check_search_is_heuristic': bool(budget.checked),
        'calls': budget.calls, 'same_square_calls': budget.see,
        'capture_search_calls': budget.capture,
        'elapsed_seconds': round(time.monotonic() - budget.start, 6)}


def verification_examples():
    cases = json.loads((ROOT / 'illustrative-cases.json').read_text())
    results = []
    for case in cases:
        board, steps = chess.Board(case['fen_before']), []
        color, baseline = board.turn, material(board)
        for san in case['moves']:
            move = board.parse_san(san)
            board.push(move)
            physical = material(board) * (1 if board.turn == color else -1)
            steps.append({'san': san, 'uci': move.uci(), 'material_mover': physical})
        assert physical - baseline == 90, (case['id'], physical - baseline)
        after = chess.Board(case['fen_before'])
        after.push_san(case['moves'][0])
        results.append({'id': case['id'], 'outside_primary': True,
            'conditional_not_claimed_played_or_forced': True, 'verified_steps': steps,
            'physical_line_gain': physical - baseline,
            **probe(case['fen_before'], after.fen())})
    old = json.loads((ROOT.parent / 'brilliants-2026-11-02/results.json').read_text())
    bb2 = next(x for x in old['samples'] if x['game'] == '172016241890')
    result = probe(bb2['fen_before'], bb2['fen_after'])
    assert result['maxloss'] == 200, result
    results.append({'id': 'Ju Wenjun 19.Bb2', 'outside_primary': True,
                    'expected_capture_only_material_cost': 200, **result})
    return results


def main():
    source = ROOT / 'primary-moves.json'
    rows = json.loads(source.read_text())
    if len(rows) > 600:
        raise ValueError('Primary snapshot exceeds agreed 600 moves')
    result = {'generated_at': datetime.now(timezone.utc).isoformat(),
        'scope': 'Descriptive physical-material features on this saved primary snapshot; not a rule proposal or classifier result.',
        'primary_input_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'per_position_caps': {'seconds': SECONDS, 'combined_calls': MAX_CALLS},
        'material_units': VALUES,
        'specific_acceptance_qualification': 'Legal nonpawn capture; its forced same-square exchange gain must exceed immediate capture/promotion credit +100.',
        'recoup_definition': 'For completed cases with at least one qualifying acceptance: maxloss <=100, relative to RAW physical material before the sampled move.',
        'limitations': ['No engine evaluation or tactical soundness test.',
            'Both sides may stand pat, even in check. Quiet evasions and other quiet moves are omitted.',
            'Conditional capture-only lines are neither claimed to be played nor forced.',
            'Physical material at checkmate has no mate-score sentinel.',
            'Python acceptance qualification needs a later cross-check against the frozen TypeScript legal-offer feature.',
            'No production policy, threshold tuning, or held-out predictive claim.'],
        'rows': [{**{key: row.get(key) for key in ('game_id', 'ply', 'account', 'san', 'uci', 'fresh_label', 'split', 'sampling_category')},
                  **probe(row['fen_before'], row['fen_after'])} for row in rows],
        'verification_outside_primary': verification_examples()}
    (ROOT / 'material-features.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'positions': len(result['rows']),
        'unknown': sum(r['outcome'] == 'UNKNOWN' for r in result['rows']),
        'elapsed_seconds': sum(r['elapsed_seconds'] for r in result['rows']),
        'verification': [(r['id'], r['maxloss']) for r in result['verification_outside_primary']]}))


if __name__ == '__main__':
    main()
