"""Frozen, label-blind raw mating-offer miner; no engine or model calls.

Raw means any qualifying legal nonpawn capture after an actual played move that
allows its original mover an immediate mate. New-offer attribution is deliberately
left to the frozen downstream rule using exact previous-own-after history.
Run only after the parent freezes this script and INPUTS.json. No automatic retry.
"""
import collections
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import re
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
PV_PATH = ROOT / 'research/brilliants-training-overnight-2026-11-03/adapter/augment-pv.py'
spec = importlib.util.spec_from_file_location('prospective_pv', PV_PATH)
pv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pv)
chess = pv.chess
import chess.pgn

MAX_GAMES = 4000
MAX_SECONDS = 600
MAX_CANDIDATES = 400
SALT = 'mute-mating-prospective-20261104:'


def normalize_fen(fen):
    return ' '.join(fen.split()[:4])


def game_id(link):
    # Chess.com gameLink headers identify the game by the final numeric path part.
    match = re.search(r'(?:^|/)(\d+)(?:[/?#].*)?$', link.strip())
    return match.group(1) if match else link.strip().rstrip('/').split('/')[-1].split('?')[0]


class IdentityHeaders(chess.pgn.HeadersBuilder):
    def visit_header(self, tag, value):
        if tag in ('gameLink', 'Link'):
            self.headers[tag] = value


class BlindGame(chess.pgn.GameBuilder):
    def begin_game(self):
        super().begin_game()
        self.game.headers.clear()

    def visit_header(self, tag, value):
        if tag in ('gameLink', 'Link', 'FEN'):
            self.game.headers[tag] = value

    def visit_result(self, result):
        pass

    def visit_comment(self, comment):
        pass

    def visit_nag(self, nag):
        pass


def main():
    started = time.monotonic()
    counts = collections.Counter()
    candidates = []
    reason = 'input_exhausted'
    stage = 'index'
    records = {}
    seen_positions = set()
    output = HERE / 'MINED.json'
    if output.exists():
        raise FileExistsError('MINED.json already exists; no overwrite or automatic retry')
    inputs_path = HERE / 'INPUTS.json'
    inputs_bytes = inputs_path.read_bytes()
    inputs = json.loads(inputs_bytes)
    excluded_ids = set(map(str, inputs['excluded_game_ids']))
    excluded_positions = {normalize_fen(f) for f in inputs['excluded_positions']}

    def guard():
        if time.monotonic() - started >= MAX_SECONDS:
            raise TimeoutError('600_second_limit')

    try:
        # Text-stream seek cookies preserve exact raw PGN without retaining the pool.
        # Only gameLink is retained by the indexing visitor; no ratings/results read.
        for name in sorted(set(inputs['pgn_files'])):
            path = Path(name)
            if not path.is_absolute():
                raise ValueError('Every pgn_files entry must be absolute')
            with path.open(encoding='utf-8-sig') as stream:
                while True:
                    guard()
                    start = stream.tell()
                    headers = chess.pgn.read_game(stream, Visitor=IdentityHeaders)
                    end = stream.tell()
                    if headers is None:
                        break
                    counts['indexed_game_records'] += 1
                    link = headers.get('gameLink') or headers.get('Link', '')
                    if not link:
                        counts['missing_game_id'] += 1
                        continue
                    gid = game_id(link)
                    if gid in excluded_ids:
                        counts['excluded_game_records'] += 1
                        continue
                    if gid in records:
                        counts['duplicate_game_records'] += 1
                        continue
                    records[gid] = (str(path), start, end)
        counts['unique_fresh_games_indexed'] = len(records)
        stage = 'scan'
        ordered = sorted(records, key=lambda gid: (hashlib.sha256((SALT + gid).encode()).hexdigest(), gid))
        for gid in ordered:
            guard()
            if counts['fresh_games_scanned'] >= MAX_GAMES:
                reason = '4000_game_limit'
                break
            counts['fresh_games_scanned'] += 1
            path, start, end = records[gid]
            with open(path, encoding='utf-8-sig') as stream:
                stream.seek(start)
                chunks = []
                while stream.tell() < end:
                    chunks.append(stream.readline())
                pgn = ''.join(chunks)
            game = chess.pgn.read_game(io.StringIO(pgn), Visitor=BlindGame)
            if game is None or game.errors:
                counts['invalid_games'] += 1
                continue
            board = game.board()
            history = [board.fen()]
            for ply, move in enumerate(game.mainline_moves(), 1):
                guard()
                before = board.copy(stack=True)
                san = board.san(move)
                board.push(move)
                after = board.copy(stack=True)
                history.append(after.fen())
                counts['played_moves_scanned'] += 1
                if ply < 3:
                    continue
                before_key, after_key = normalize_fen(before.fen()), normalize_fen(after.fen())
                if before_key in excluded_positions or after_key in excluded_positions:
                    counts['excluded_position_moves'] += 1
                    continue
                if after_key in seen_positions:
                    counts['duplicate_candidate_position_moves'] += 1
                    continue
                witnesses = {}
                for acceptance in sorted(after.generate_legal_captures(), key=lambda m: m.uci()):
                    guard()
                    victim = after.piece_at(acceptance.to_square)
                    if victim is None or victim.piece_type in (chess.PAWN, chess.KING):
                        continue
                    accepted = after.copy(stack=True)
                    acceptance_san = accepted.san(acceptance)
                    accepted.push(acceptance)
                    mates = []
                    for reply in sorted(accepted.legal_moves, key=lambda m: m.uci()):
                        guard()
                        if not accepted.gives_check(reply):
                            continue
                        reply_san = accepted.san(reply)
                        accepted.push(reply)
                        if accepted.is_checkmate():
                            mates.append({'uci': reply.uci(), 'san': reply_san, 'fen_after_mate': accepted.fen()})
                        accepted.pop()
                    if mates:
                        witnesses[acceptance.uci()] = {
                            'acceptance_uci': acceptance.uci(), 'acceptance_san': acceptance_san,
                            'fen_after_acceptance': accepted.fen(), 'mate_replies': mates,
                        }
                if not witnesses:
                    continue
                counts['moves_with_structural_mate_witness'] += 1
                guard()
                offers, unknown, nodes = pv.qualify(before, after)
                counts['qualifier_calls'] += 1
                counts['qualifier_nodes'] += nodes
                if unknown:
                    counts['qualifier_unknown_moves'] += 1
                    continue
                mating_offers = {u: offers[u] for u in sorted(witnesses) if u in offers}
                if not mating_offers:
                    continue
                seen_positions.add(after_key)
                candidates.append({
                    'key': f'{gid}:{ply}', 'game_id': gid, 'ply': ply,
                    'uci': move.uci(), 'san': san,
                    'fen_before': before.fen(), 'fen_after': after.fen(),
                    'previous_own_after': history[ply - 2],
                    'fen_previous_own_after': history[ply - 2],
                    'previous_own_after_ply': ply - 2,
                    'pgn': pgn, 'pgn_sha256': hashlib.sha256(pgn.encode()).hexdigest(),
                    'source_pgn_file': path,
                    'offers': {u: offers[u] for u in sorted(offers)},
                    'mating_offers': mating_offers,
                    'witnesses': {u: witnesses[u] for u in mating_offers},
                })
                if len(candidates) >= MAX_CANDIDATES:
                    reason = '400_candidate_limit'
                    break
            if len(candidates) >= MAX_CANDIDATES:
                break
            if counts['fresh_games_scanned'] % 200 == 0:
                print(json.dumps({'games': counts['fresh_games_scanned'], 'candidates': len(candidates), 'elapsed_seconds': time.monotonic() - started}), flush=True)
    except TimeoutError as exc:
        reason = str(exc)
    except Exception as exc:
        reason = f'error:{type(exc).__name__}:{exc}'
    counts['unique_fresh_games_indexed'] = len(records)
    result = {
        'status': 'complete' if reason == 'input_exhausted' else 'partial',
        'stop_reason': reason, 'stop_stage': stage, 'no_automatic_retry': True,
        'elapsed_seconds': time.monotonic() - started,
        'limits': {'games': MAX_GAMES, 'seconds': MAX_SECONDS, 'candidates': MAX_CANDIDATES},
        'inputs_sha256': hashlib.sha256(inputs_bytes).hexdigest(),
        'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'qualifier_sha256': hashlib.sha256(PV_PATH.read_bytes()).hexdigest(),
        'excluded_game_ids_count': len(excluded_ids),
        'excluded_positions_count': len(excluded_positions),
        'counts': dict(counts), 'candidate_count': len(candidates), 'candidates': candidates,
    }
    with output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'status': result['status'], 'stop_reason': reason, 'counts': dict(counts), 'candidates': len(candidates)}), flush=True)


if __name__ == '__main__':
    main()
