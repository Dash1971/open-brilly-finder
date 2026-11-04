#!/usr/bin/env python3
"""Frozen fresh-test core evidence only: SF18/300k, full PGN, no lookback warmup.
Adapted from the completed uniform collector; explicit root CORE-FREEZE GO required before preparation/launch.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import sqlite3
import sys
import time
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

try:
    import chess, chess.engine, chess.pgn
except ImportError:
    sys.path.insert(0, '/private/tmp/brilly-research-deps')
    import chess, chess.engine, chess.pgn

ROOT = Path(__file__).resolve().parent
AUTHORIZATION = json.loads((ROOT / 'PLAN.json').read_text())['metadata']
ENGINE = '/opt/homebrew/bin/stockfish'
BUDGETS = {'core': 300000}
SEARCH_SPENT = 0.0
ACTIVE_SEARCH = None
WALL_CAP = 600.0
RUN_STARTED = time.monotonic()
VALUES = {chess.PAWN: 90, chess.KNIGHT: 300, chess.BISHOP: 300,
          chess.ROOK: 500, chess.QUEEN: 1000, chess.KING: 0}


def now():
    return datetime.now(timezone.utc).isoformat()


def guard():
    if (ROOT / 'STOP').exists():
        raise TimeoutError('Stopped by parent marker')
    if time.monotonic() - RUN_STARTED >= WALL_CAP:
        raise TimeoutError('Ten-minute per-worker wall safeguard reached; no automatic retries')
    if not AUTHORIZATION.get('root_core_freeze_sha256'):
        raise RuntimeError('Root core-freeze artifact not bound')
    if AUTHORIZATION.get('quantity_completion_authorized') is not True or AUTHORIZATION.get('tuning_authorized') is not False:
        raise RuntimeError('Frozen quantity-only research authorization missing')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, data):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(data, indent=2) + '\n')
    temporary.replace(path)


def material(board):
    if board.is_checkmate():
        return -10000
    return sum(VALUES[p.piece_type] * (1 if p.color == board.turn else -1)
               for p in board.piece_map().values())


def qsearch(board, alpha, beta):
    guard()
    stand = material(board)
    if stand >= beta:
        return beta
    alpha = max(alpha, stand)
    moves = sorted(board.generate_legal_captures(), reverse=True,
                   key=lambda move: 90 if board.is_en_passant(move)
                   else VALUES[board.piece_at(move.to_square).piece_type])
    for move in moves:
        board.push(move)
        value = -qsearch(board, -beta, -alpha)
        board.pop()
        if value >= beta:
            return beta
        alpha = max(alpha, value)
    return alpha


@lru_cache(maxsize=4000)
def naive(fen):
    """Python translation of pinned EC capture/material reference, not SF eval."""
    board = chess.Board(fen)
    moves = list(board.legal_moves)
    if not moves:
        return -10000 if board.is_checkmate() else 0
    best = -10000
    for move in moves:
        guard()
        board.push(move)
        best = max(best, -qsearch(board, -10000, 10000))
        board.pop()
    return best


def packed(info):
    value = info['score'].white()
    return {('mate' if value.is_mate() else 'cp'):
            value.mate() if value.is_mate() else value.score(),
            'moves': [move.uci() for move in info['pv']]}


def search(engine, board, budget, session):
    global SEARCH_SPENT, ACTIVE_SEARCH
    guard()
    if board.is_checkmate() or board.is_stalemate() or board.is_insufficient_material():
        value = {'mate': -1 if board.turn else 1} if board.is_checkmate() else {'cp': 0}
        return {'current': {'depth': 99, 'lines': [{**value, 'moves': []}]},
                'terminal': True, 'quality': f'frozen-test-sf18-{budget}'}
    count = min(2, board.legal_moves.count())
    pending, completed = [], []
    start = time.monotonic()
    ACTIVE_SEARCH = start
    try:
        with engine.analysis(board, chess.engine.Limit(nodes=budget), multipv=count, game=session) as stream:
            for info in stream:
                guard()
                if not all(key in info for key in ('score', 'pv', 'depth')):
                    continue
                if not info['pv'] or info.get('upperbound') or info.get('lowerbound'):
                    continue
                rank = info.get('multipv', 1)
                if rank != len(pending) + 1:
                    pending = []
                if rank != len(pending) + 1:
                    continue
                if info['pv'][0] not in board.legal_moves:
                    continue
                pending.append(info)
                if rank == count:
                    if (len({line['depth'] for line in pending}) == 1 and
                            len({line['pv'][0] for line in pending}) == count):
                        snap = {'depth': pending[0]['depth'], 'lines': [packed(line) for line in pending],
                                'reported_nodes': pending[-1].get('nodes')}
                        if not completed or snap['depth'] > completed[-1]['depth']:
                            completed.append(snap)
                            completed = completed[-2:]
                        else:
                            completed[-1] = snap
                    pending = []
    finally:
        SEARCH_SPENT += time.monotonic() - start
        ACTIVE_SEARCH = None
    if not completed:
        raise ValueError('No exact complete same-depth comparison at ' + board.fen())
    return {'current': completed[-1], 'previous': completed[-2] if len(completed) > 1 else None,
            'terminal': False, 'quality': f'frozen-test-sf18-{budget}',
            'elapsed_seconds': round(time.monotonic() - start, 6)}


def selected(conn):
    rows = conn.execute('''SELECT o.*,p.san,p.uci,p.fen_before,p.fen_after,g.pgn,g.pgn_sha256,
        g.split,g.white,g.black,g.white_rating,g.black_rating,g.date,g.time_control FROM observations o JOIN positions p USING(game_id,ply) JOIN games g USING(game_id)
        ORDER BY o.game_id,o.ply,o.captured_at''').fetchall()
    primary_rows = json.loads((ROOT / "primary-moves.json").read_text())
    primary_keys = {(str(row["game_id"]), int(row["ply"])) for row in primary_rows}
    if len(primary_keys) != 200 or len(primary_rows) != 200:
        raise ValueError("Frozen fresh test requires exactly200 unique moves")
    valid, rejected = {}, []
    for row in rows:
        row = dict(row)
        if (row['game_id'], row['ply']) not in primary_keys:
            continue
        raw = json.loads(row['raw_json'])
        checks = [(row['observed_san'], row['san']), (row['observed_uci'], row['uci']),
                  (row['observed_fen_before'], row['fen_before']), (row['observed_fen_after'], row['fen_after'])]
        gallery_board = raw.get('board_placement') or raw.get('rawgalleryboard_placement')
        if gallery_board is not None:
            checks.append((gallery_board, row['fen_after'].split()[0]))
        observed_identity = any(a is not None for a, _ in checks)
        mismatched_identity = any(a != b for a, b in checks if a is not None)
        if not observed_identity or mismatched_identity:
            rejected.append({'observation_id': row['observation_id'], 'game_id': row['game_id'],
                             'ply': row['ply'], 'source_type': row['source_type'],
                             'reason': 'observed_identity_mismatch' if mismatched_identity else 'observed_identity_unavailable'})
            continue
        key = (row['game_id'], row['ply'])
        if key not in valid:
            valid[key] = {'game_id': row['game_id'], 'ply': row['ply'], 'san': row['san'], 'uci': row['uci'],
                          'fen_before': row['fen_before'], 'fen_after': row['fen_after'],
                          'pgn': row['pgn'], 'pgn_sha256': row['pgn_sha256'], 'split': row['split'],
                          'white': row['white'], 'black': row['black'],
                          'white_rating': row['white_rating'], 'black_rating': row['black_rating'],
                          'date': row['date'], 'time_control': row['time_control'],
                          'observations': []}
        observation = {k: row[k] for k in
            ('observation_id', 'source_type', 'label', 'label_status', 'account', 'captured_at')}
        observation['categories'] = json.loads(row['categories_json'])
        observation['negative_category'] = raw.get('negative_category')
        valid[key]['observations'].append(observation)
    return list(valid.values()), rejected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=BUDGETS)
    parser.add_argument('--db', type=Path, default=ROOT / 'corpus.sqlite3')
    parser.add_argument('--subset', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    guard()
    conn = sqlite3.connect('file:' + str(args.db.resolve()) + '?mode=ro', uri=True)
    conn.row_factory = sqlite3.Row
    targets, rejected = selected(conn)
    conn.close()
    subset = json.loads(args.subset.read_text()) if args.subset else None
    if subset is not None:
        keys = {(str(row['game_id']), int(row['ply'])) for row in subset}
        targets = [target for target in targets if (target['game_id'], target['ply']) in keys]
        if {(t['game_id'], t['ply']) for t in targets} != keys:
            raise ValueError('Frozen partition identities not fully available')
    output = args.output or ROOT / 'analysis-core.json'
    if output.exists():
        raise ValueError('Clean core run refuses existing output; no automatic cache resume/retry')
    budget = BUDGETS[args.stage]
    result = {'started_at': now(), 'quantity_limit': 200, 'expected_partition_cases': len(targets), 'expected_partition_snapshots': len({(t['game_id'],p) for t in targets for p in range(max(0,t['ply']-2),t['ply']+1)}), 'plan_sha256': digest(ROOT/'PLAN.json'), 'wall_safeguard_seconds': WALL_CAP, 'primary_selection_sha256': digest(ROOT / 'primary-moves.json'), 'stage': args.stage,
              'nodes_per_position': budget, 'engine_path': ENGINE, 'engine_sha256': digest(ENGINE),
              'threads': 1, 'hash_mb': 64, 'script_sha256': digest(__file__),
              'subset_sha256': digest(args.subset) if args.subset else None,
              'rule_tuning': False, 'rejected_identity_rows': rejected, 'targets': [],
              'snapshots': {}, 'status': 'running'}
    write(output, result)
    if not targets:
        result.update(status='no_eligible_identity_validated_PGN_rows', completed_at=now())
        write(output, result)
        print(json.dumps({'status': result['status'], 'output': str(output)}))
        return
    wall_start = time.monotonic()
    engine = chess.engine.SimpleEngine.popen_uci(ENGINE)
    engine.configure({'Threads': 1, 'Hash': 64})
    result['engine_id'] = engine.id
    result['session_policy'] = 'Clean process; Clear Hash and new UCI game per full-PGN game; chronological positions; no cached engine snapshot reuse.'
    result['engine_option_defaults'] = {k: {'default':v.default,'type':v.type} for k,v in engine.options.items()}
    try:
        for game_id in sorted({target['game_id'] for target in targets}):
            guard()
            group = [target for target in targets if target['game_id'] == game_id]
            game = chess.pgn.read_game(io.StringIO(group[0]['pgn']))
            if game is None or game.errors:
                raise ValueError('PGN became unparsable for ' + game_id)
            wanted = sorted({ply for target in group for ply in
                             (max(0, target['ply'] - 2), target['ply'] - 1, target['ply'])})
            boards, board = {0: game.board()}, game.board()
            for ply, move in enumerate(game.mainline_moves(), 1):
                board.push(move)
                if ply in wanted:
                    boards[ply] = board.copy(stack=True)
            engine.configure({'Clear Hash': None})
            session = object()
            for ply in wanted:
                guard()
                cached = result['snapshots'].get(f'{game_id}:{ply}')
                if cached:
                    if cached['pgn_sha256'] != group[0]['pgn_sha256'] or cached['fen'] != boards[ply].fen():
                        raise ValueError('Cached position identity changed')
                    continue
                snap = search(engine, boards[ply], budget, session)
                snap.update(game_id=game_id, position_ply=ply, fen=boards[ply].fen(),
                            pgn_sha256=group[0]['pgn_sha256'], ec_material=naive(boards[ply].fen()))
                result['snapshots'][f'{game_id}:{ply}'] = snap
                result['recorded_search_seconds'] = round(SEARCH_SPENT,6)
                result['wall_seconds'] = round(time.monotonic()-wall_start,6)
                write(output, result)
                n = len(result['snapshots'])
                if n == 8 or n % 60 == 0:
                    progress = {'snapshots':n,'expected':result['expected_partition_snapshots'],'recorded_search_seconds':result['recorded_search_seconds'],'wall_seconds':result['wall_seconds'],'mean_search_seconds':round(SEARCH_SPENT/n,6)}
                    print(json.dumps(progress),flush=True)
            for target in group:
                entry = {key: value for key, value in target.items() if key != 'pgn'}
                entry['snapshot_ids'] = [f'{game_id}:{ply}' for ply in
                    range(max(0, target['ply'] - 2), target['ply'] + 1)]
                result['targets'].append(entry)
            write(output, result)
        result.update(status='complete', completed_at=now())
    except (TimeoutError, KeyboardInterrupt) as error:
        result.update(status='stopped', reason=str(error), completed_at=now())
    except Exception as error:
        result.update(status='failed', reason=str(error), completed_at=now())
        raise
    finally:
        engine.quit()
        result['recorded_search_seconds'] = round(SEARCH_SPENT,6)
        result['wall_seconds'] = round(time.monotonic()-wall_start,6)
        write(output, result)
    print(json.dumps({'status': result['status'], 'targets': len(result['targets']),
                      'snapshots': len(result['snapshots']), 'output': str(output)}))


if __name__ == '__main__':
    main()
