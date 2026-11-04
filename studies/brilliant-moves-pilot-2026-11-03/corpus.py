#!/usr/bin/env python3
"""Study-specific Chess.com pilot corpus. Public monthly PGNs; labels come from UI evidence.

Examples:
  python3 corpus.py init
  python3 corpus.py import-evidence evidence.json
  python3 corpus.py import-pgn selected-games.pgn --source https://... --only-games 123,456
  python3 corpus.py fetch-month Hikaru 2026 10 --only-games 123,456
  python3 corpus.py validate
  python3 corpus.py export

No app changes, authenticated HTTP, private endpoints, rule tuning or bulk crawl.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import re
import sqlite3
import sys
import urllib.request
from urllib.parse import parse_qs, urlparse
from datetime import datetime, timezone
from pathlib import Path

try:
    import chess.pgn
except ImportError:
    sys.path.insert(0, '/private/tmp/brilly-research-deps')
    import chess.pgn

ROOT = Path(__file__).resolve().parent
START = '2026-11-03T00:02:02+00:00'
DEADLINE = '2026-11-03T00:47:02+00:00'
ACCOUNTS = ('nelsi', 'hansen', 'KNVB', 'GothamChess', 'Hikaru')
DOCS = [
    'https://www.chess.com/news/view/published-data-api',
    'https://support.chess.com/en/articles/8705305-how-do-i-get-a-pgn-of-my-game',
]
GAME_ID = re.compile(r'(?:game|games)/(?:live|daily)/(\d+)|(?:live|daily)/(\d+)')


def now():
    return datetime.now(timezone.utc).isoformat()


def guard():
    remaining = (datetime.fromisoformat(DEADLINE) - datetime.now(timezone.utc)).total_seconds()
    if remaining <= 0:
        raise RuntimeError('Pilot collection deadline has passed; no collection extension is authorized.')
    return remaining


def sha(value):
    return hashlib.sha256(value.encode('utf8') if isinstance(value, str) else value).hexdigest()


def connect(db):
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    conn.executescript('''
      CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS games(
        game_id TEXT PRIMARY KEY, pgn TEXT NOT NULL, pgn_sha256 TEXT NOT NULL,
        source_link TEXT NOT NULL, captured_at TEXT NOT NULL, headers_json TEXT NOT NULL,
        white TEXT, black TEXT, white_rating INTEGER, black_rating INTEGER,
        date TEXT, utc_time TEXT, time_control TEXT, result TEXT,
        split TEXT NOT NULL, split_reason TEXT NOT NULL, total_plies INTEGER NOT NULL
      );
      CREATE TABLE IF NOT EXISTS positions(
        game_id TEXT NOT NULL REFERENCES games(game_id), ply INTEGER NOT NULL,
        san TEXT NOT NULL, uci TEXT NOT NULL, fen_before TEXT NOT NULL, fen_after TEXT NOT NULL,
        clock_seconds REAL, PRIMARY KEY(game_id,ply)
      );
      CREATE TABLE IF NOT EXISTS observations(
        observation_id TEXT PRIMARY KEY, game_id TEXT NOT NULL, ply INTEGER NOT NULL,
        source_type TEXT NOT NULL CHECK(source_type IN ('gallery','fresh_review')),
        label TEXT NOT NULL, label_status TEXT NOT NULL, account TEXT,
        observed_san TEXT, observed_uci TEXT, observed_fen_before TEXT, observed_fen_after TEXT,
        categories_json TEXT NOT NULL, displayed_evaluation TEXT, coach_explanation TEXT,
        source_link TEXT NOT NULL, captured_at TEXT NOT NULL, evidence_file TEXT,
        raw_json TEXT NOT NULL
      );
    ''')
    metadata = {
        'started_at': START, 'collection_deadline': DEADLINE,
        'accounts': list(ACCOUNTS), 'target': {'gallery_positives': 20, 'fresh_negatives': 20},
        'split_policy': 'Hikaru games -> player_holdout; other SHA256(game_id)%5==0 -> game_holdout; rest development. Never split positions from a game.',
        'split_frozen_before_tuning': True, 'tuning_authorized': False,
        'official_pgn_documentation': DOCS, 'label_absence_means': 'unknown',
    }
    for key, value in metadata.items():
        packed = json.dumps(value, sort_keys=True)
        old = conn.execute('SELECT value FROM metadata WHERE key=?', (key,)).fetchone()
        if old and old[0] != packed:
            raise ValueError('Immutable pilot metadata differs: ' + key)
        conn.execute('INSERT OR IGNORE INTO metadata VALUES(?,?)', (key, packed))
    conn.commit()
    return conn


def game_id_from(text):
    match = GAME_ID.search(text or '')
    return next((v for v in match.groups() if v), None) if match else None


def canonical_label(value):
    value = str(value or '').strip()
    mapping = {'brilliant': '!!', 'brilliant!': '!!', 'great': '!', 'inaccuracy': '?!',
               'mistake': '?', 'blunder': '??', 'best': 'best', 'excellent': 'excellent',
               'good': 'good', 'book': 'book', 'miss': 'miss', 'unknown': 'unknown'}
    return mapping.get(value.lower(), value if value in ('!!', '!', '!?', '?!', '?', '??') else 'unknown')


def import_evidence(conn, path):
    guard()
    payload = json.loads(path.read_text())
    observations = payload if isinstance(payload, list) else payload.get('observations', [payload])
    count = 0
    for raw in observations:
        guard()
        source = raw.get('source_link') or raw.get('source_url') or raw.get('url')
        captured = raw.get('captured_at') or raw.get('capture_timestamp')
        source_type = raw.get('source_type')
        if source_type not in ('gallery', 'fresh_review'):
            raise ValueError('source_type must explicitly be gallery or fresh_review')
        if not source or not captured:
            raise ValueError('Every observation needs source_link and captured_at')
        datetime.fromisoformat(captured.replace('Z', '+00:00'))
        game = str(raw.get('game_id') or raw.get('game') or game_id_from(source) or '')
        if not game.isdigit():
            raise ValueError('Exact numeric Chess.com game_id required')
        ply = raw.get('ply')
        if not isinstance(ply, int) or ply < 1:
            raise ValueError('Exact 1-based ply required; source move-index conversion must be verified')
        label = canonical_label(raw.get('label'))
        # A missing gallery entry never becomes a negative. Only a visible fresh label can.
        status = ('fresh_confirmed_brilliant' if label == '!!' else
                  'fresh_confirmed_non_brilliant' if label != 'unknown' else 'unknown') if source_type == 'fresh_review' else (
                      'gallery_brilliant' if label == '!!' else 'unknown')
        ident = str(raw.get('observation_id') or sha(json.dumps(raw, sort_keys=True)))
        categories = raw.get('categories')
        if categories is None:
            categories = []  # Raw JSON preserves whether categories were unobserved.
        values = (
            ident, game, ply, source_type, label, status, raw.get('account'),
            raw.get('san'), raw.get('uci'), raw.get('fen_before'), raw.get('fen_after'),
            json.dumps(categories), None if raw.get('displayed_evaluation') is None else str(raw['displayed_evaluation']),
            raw.get('coach_explanation'), source, captured, raw.get('evidence_file'),
            json.dumps(raw, sort_keys=True),
        )
        old = conn.execute('SELECT raw_json FROM observations WHERE observation_id=?', (ident,)).fetchone()
        if old and old[0] != values[-1]:
            raise ValueError('Observation IDs are immutable; use a new ID for a fresh capture')
        conn.execute('INSERT OR IGNORE INTO observations VALUES(' + ','.join('?' for _ in values) + ')', values)
        count += 1
    conn.commit()
    return {'observations_processed': count}


def split_for(game, headers):
    if any(headers.get(color, '').lower() == 'hikaru' for color in ('White', 'Black')):
        return 'player_holdout', 'Hikaru reserved before any rule tuning'
    if int(sha(game), 16) % 5 == 0:
        return 'game_holdout', 'Deterministic SHA256(game_id) modulo 5'
    return 'development', 'Remaining games; no rule tuning in feasibility pilot'


def integer(value):
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def import_pgn(conn, text, source, captured_at, only_games):
    guard()
    stream = io.StringIO(text)
    imported, skipped = [], 0
    while True:
        guard()
        start = stream.tell()
        game = chess.pgn.read_game(stream)
        end = stream.tell()
        if game is None:
            break
        # Preserve this game's source PGN slice, not a normalized re-export.
        raw_pgn = text[start:end].strip() + '\n'
        headers = dict(game.headers)
        game_id = game_id_from(headers.get('Link')) or game_id_from(headers.get('Site'))
        if not game_id or (only_games and game_id not in only_games):
            skipped += 1
            continue
        if game.errors:
            raise ValueError(f'PGN parsing errors in game {game_id}: {game.errors}')
        board = game.board()
        positions = []
        for ply, node in enumerate(game.mainline(), 1):
            if ply % 25 == 0:
                guard()
            move = node.move
            before = board.fen()
            san = board.san(move)
            board.push(move)
            positions.append((game_id, ply, san, move.uci(), before, board.fen(), node.clock()))
        digest = sha(raw_pgn)
        old = conn.execute('SELECT pgn_sha256 FROM games WHERE game_id=?', (game_id,)).fetchone()
        if old:
            if old[0] != digest:
                raise ValueError(f'Different PGN bytes for existing game {game_id}; retain separately and resolve provenance')
            imported.append(game_id)
            continue
        split, reason = split_for(game_id, headers)
        conn.execute('INSERT INTO games VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', (
            game_id, raw_pgn, digest, source, captured_at, json.dumps(headers, sort_keys=True),
            headers.get('White'), headers.get('Black'), integer(headers.get('WhiteElo')), integer(headers.get('BlackElo')),
            headers.get('UTCDate') or headers.get('Date'), headers.get('UTCTime'), headers.get('TimeControl'), headers.get('Result'),
            split, reason, len(positions),
        ))
        conn.executemany('INSERT INTO positions VALUES(?,?,?,?,?,?,?)', positions)
        imported.append(game_id)
    conn.commit()
    return {'games_imported_or_matched': imported, 'archive_games_skipped': skipped,
            'requested_not_found': sorted(only_games - set(imported))}


def fetch_month(conn, account, year, month, only_games):
    if not only_games:
        raise ValueError('fetch-month requires --only-games; pilot is not a broad archive crawl')
    if account.lower() not in [a.lower() for a in ACCOUNTS] or not 1 <= month <= 12:
        raise ValueError('Account/month outside pilot scope')
    remaining = guard()
    url = f'https://api.chess.com/pub/player/{account}/games/{year:04}/{month:02}/pgn'
    request = urllib.request.Request(url, headers={'User-Agent': 'MuteChess-brilliants-feasibility/1.0 (public research; https://github.com/Dash1971/mute-chess)'})
    chunks = []
    with urllib.request.urlopen(request, timeout=min(30, remaining)) as response:
        while True:
            guard()
            chunk = response.read(262144)
            if not chunk:
                break
            chunks.append(chunk)
            if sum(map(len, chunks)) > 50 * 1024 * 1024:
                raise ValueError('Monthly archive exceeded the 50 MiB pilot transfer cap')
        response_headers = dict(response.headers)
    guard()
    content = b''.join(chunks)
    captured = now()
    folder = ROOT / 'original-pgn'
    folder.mkdir(exist_ok=True)
    destination = folder / f'{account.lower()}-{year:04}-{month:02}.pgn'
    if destination.exists() and destination.read_bytes() != content:
        raise ValueError('Monthly archive bytes changed; refusing to overwrite original evidence')
    destination.write_bytes(content)
    destination.with_suffix('.response.json').write_text(json.dumps({
        'source_link': url, 'captured_at': captured, 'sha256': sha(content),
        'bytes': len(content), 'headers': response_headers, 'documentation': DOCS,
    }, indent=2) + '\n')
    return import_pgn(conn, content.decode('utf8'), url, captured, only_games)


def validate(conn):
    problems, missing = [], []
    board_checks, index_checks = 0, 0
    observations = conn.execute('SELECT * FROM observations').fetchall()
    for observation in observations:
        raw = json.loads(observation['raw_json'])
        source_move = parse_qs(urlparse(observation['source_link']).query).get('move')
        if source_move and len(source_move) == 1 and source_move[0].isdigit():
            index_checks += 1
            source_ply = int(source_move[0]) + 1
            if source_ply != observation['ply']:
                problems.append({'observation_id': observation['observation_id'], 'field': 'source_move_index',
                                 'observed': observation['ply'], 'derived': source_ply})
        position = conn.execute('SELECT * FROM positions WHERE game_id=? AND ply=?',
                                (observation['game_id'], observation['ply'])).fetchone()
        if not position:
            missing.append({'observation_id': observation['observation_id'], 'game_id': observation['game_id'], 'ply': observation['ply']})
            continue
        for observed, derived in [('observed_san', 'san'), ('observed_uci', 'uci'),
                                   ('observed_fen_before', 'fen_before'), ('observed_fen_after', 'fen_after')]:
            if observation[observed] is not None and observation[observed] != position[derived]:
                problems.append({'observation_id': observation['observation_id'], 'field': observed,
                                 'observed': observation[observed], 'derived': position[derived]})
        gallery_board = raw.get('board_placement') or raw.get('rawgalleryboard_placement')
        if observation['source_type'] == 'gallery' and gallery_board is not None:
            board_checks += 1
            derived_board = position['fen_after'].split()[0]
            if gallery_board != derived_board:
                problems.append({'observation_id': observation['observation_id'], 'field': 'gallery_board_placement',
                                 'observed': gallery_board, 'derived': derived_board})
    disagreements = [dict(r) for r in conn.execute('''
      SELECT game_id,ply,GROUP_CONCAT(DISTINCT label_status) AS statuses
      FROM observations GROUP BY game_id,ply HAVING
      SUM(label_status='gallery_brilliant')>0 AND SUM(label_status='fresh_confirmed_non_brilliant')>0
    ''')]
    return {'games': conn.execute('SELECT COUNT(*) FROM games').fetchone()[0],
            'positions': conn.execute('SELECT COUNT(*) FROM positions').fetchone()[0],
            'observations': len(observations), 'indexing_mismatches': problems,
            'gallery_board_placements_checked': board_checks,
            'source_move_indices_checked': index_checks,
            'observations_waiting_for_pgn': missing, 'gallery_fresh_disagreements': disagreements,
            'label_counts': [dict(r) for r in conn.execute('SELECT label_status,COUNT(*) AS n FROM observations GROUP BY label_status')],
            'split_counts': [dict(r) for r in conn.execute('SELECT split,COUNT(*) AS n FROM games GROUP BY split')]}


def export(conn):
    rows = []
    for row in conn.execute('''SELECT o.*,p.san,p.uci,p.fen_before,p.fen_after,p.clock_seconds,
        g.white,g.black,g.white_rating,g.black_rating,g.date,g.time_control,g.split
        FROM observations o LEFT JOIN positions p ON p.game_id=o.game_id AND p.ply=o.ply
        LEFT JOIN games g ON g.game_id=o.game_id ORDER BY o.game_id,o.ply,o.source_type'''):
        item = dict(row)
        item['categories'] = json.loads(item.pop('categories_json'))
        item['original_observation'] = json.loads(item.pop('raw_json'))
        item['missing_fields'] = [k for k, v in item.items() if v is None]
        rows.append(item)
    (ROOT / 'observations-export.json').write_text(json.dumps(rows, indent=2) + '\n')
    manifest = {'metadata': {r['key']: json.loads(r['value']) for r in conn.execute('SELECT * FROM metadata')},
                'exported_at': now(), 'validation': validate(conn)}
    (ROOT / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', type=Path, default=ROOT / 'corpus.sqlite3')
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('init')
    evidence = commands.add_parser('import-evidence'); evidence.add_argument('file', type=Path)
    pgn = commands.add_parser('import-pgn'); pgn.add_argument('file', type=Path)
    pgn.add_argument('--source', required=True); pgn.add_argument('--captured-at', default=now())
    pgn.add_argument('--only-games', default='')
    fetch = commands.add_parser('fetch-month'); fetch.add_argument('account'); fetch.add_argument('year', type=int); fetch.add_argument('month', type=int)
    fetch.add_argument('--only-games', required=True)
    commands.add_parser('validate'); commands.add_parser('export')
    args = parser.parse_args()
    ROOT.mkdir(parents=True, exist_ok=True)
    conn = connect(args.db)
    try:
        if args.command == 'init': result = export(conn)
        elif args.command == 'import-evidence': result = import_evidence(conn, args.file)
        elif args.command == 'import-pgn': result = import_pgn(conn, args.file.read_text(), args.source, args.captured_at, set(filter(None, args.only_games.split(','))))
        elif args.command == 'fetch-month': result = fetch_month(conn, args.account, args.year, args.month, set(filter(None, args.only_games.split(','))))
        elif args.command == 'validate': result = validate(conn)
        else: result = export(conn)
        print(json.dumps(result, indent=2))
    finally:
        conn.close()


if __name__ == '__main__':
    main()
