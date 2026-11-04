#!/usr/bin/env python3
"""Study-specific Chess.com 600-move study corpus. Public monthly PGNs; labels come from UI evidence.

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
START = '2026-11-03T00:58:30+00:00'
TARGET_PER_ACCOUNT = 60
RESERVE_MOVES = 60
ACCOUNTS = ('nelsi', 'hansen', 'KNVB', 'GothamChess', 'Hikaru')
DOCS = [
    'https://www.chess.com/news/view/published-data-api',
    'https://support.chess.com/en/articles/8705305-how-do-i-get-a-pgn-of-my-game',
]
GAME_ID = re.compile(r'(?:game|games)/(?:live|daily)/(\d+)|(?:live|daily)/(\d+)')


def now():
    return datetime.now(timezone.utc).isoformat()


def guard():
    if (ROOT / 'STOP_COLLECTION').exists():
        raise RuntimeError('Collection stopped by owner/parent marker')
    return 30  # Per-request timeout, not a study duration cap.


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
      CREATE VIEW IF NOT EXISTS active_observations AS
        SELECT * FROM observations WHERE rowid IN (
          SELECT MAX(rowid) FROM observations
          GROUP BY game_id,ply,source_type,captured_at,source_link,account
        );
    ''')
    metadata = {
        'started_at': START, 'collection_deadline': None, 'quantity_completion_authorized': True,
        'accounts': list(ACCOUNTS), 'target': {'fresh_brilliant': 300, 'fresh_non_brilliant': 300, 'per_account_per_class': TARGET_PER_ACCOUNT, 'preferred_positive_per_sacrifice_category': 15, 'reserve_unique_moves': RESERVE_MOVES},
        'split_policy': 'Hikaru games -> player_holdout; other SHA256(game_id)%5==0 -> game_holdout; rest development. Never split positions from a game.',
        'split_frozen_before_tuning': True, 'tuning_authorized': False,
        'official_pgn_documentation': DOCS, 'label_absence_means': 'unknown',
        'excluded_game_ids': json.loads((ROOT / 'exclude-games.json').read_text())['game_ids'],
        'pilot_source_immutable': str(ROOT.parent / 'brilliants-pilot-2026-11-03'),
    }
    for key, value in metadata.items():
        packed = json.dumps(value, sort_keys=True)
        old = conn.execute('SELECT value FROM metadata WHERE key=?', (key,)).fetchone()
        if old and old[0] != packed:
            raise ValueError('Immutable study metadata differs: ' + key)
        conn.execute('INSERT OR IGNORE INTO metadata VALUES(?,?)', (key, packed))
    conn.commit()
    return conn


def game_id_from(text):
    match = GAME_ID.search(text or '')
    return next((v for v in match.groups() if v), None) if match else None


def canonical_label(value):
    value = str(value or '').strip()
    if value in ('!!', '!', '!?', '?!', '?', '??'):
        return value
    value = re.sub(r'^is\s+', '', value.lower()).rstrip('!.')
    value = re.sub(r'^(?:a|an|the)\s+', '', value)
    value = re.sub(r'\s+move$', '', value)
    mapping = {'brilliant': '!!', 'brilliant!': '!!', 'great': '!', 'inaccuracy': '?!',
               'mistake': '?', 'blunder': '??', 'best': 'best', 'excellent': 'excellent',
               'good': 'good', 'book': 'book', 'miss': 'miss', 'unknown': 'unknown'}
    return mapping.get(value.lower(), value if value in ('!!', '!', '!?', '?!', '?', '??') else 'unknown')


_selection_cache = {}


def selected(raw):
    if raw.get('selected') is False:
        return False
    chosen = raw.get('selected') is True or raw.get('selection_status') in ('primary', 'selected', 'reserve_selected')
    if chosen and raw.get('source_type') == 'gallery':
        path = ROOT / 'evidence' / f"{str(raw.get('account', '')).lower()}-gallery-selected.json"
        if path.exists():
            modified = path.stat().st_mtime_ns
            cached = _selection_cache.get(path)
            if not cached or cached[0] != modified:
                records = json.loads(path.read_text())
                keys = {(str(r['game_id']), r['ply']) for r in records if r.get('selected') is not False}
                _selection_cache[path] = (modified, keys)
            chosen = (str(raw.get('game_id')), raw.get('ply')) in _selection_cache[path][1]
    return chosen


def observed_board(raw):
    placement = raw.get('board_placement') or raw.get('rawgalleryboard_placement')
    pieces = raw.get('review_board_pieces') or raw.get('gallery_board_pieces') or raw.get('board_piece_classes')
    if placement is not None or not pieces:
        return placement
    board = chess.Board(None)
    for piece_class in pieces:
        role = re.search(r'\b([wb][pnbrqk])\b', piece_class)
        square = re.search(r'\bsquare-([1-8])([1-8])\b', piece_class)
        if not role or not square:
            raise ValueError('Malformed observed board-piece class')
        target = chess.square(int(square[1]) - 1, int(square[2]) - 1)
        if board.piece_at(target):
            raise ValueError('Duplicate square in observed rendered board')
        symbol = role[1][1].upper() if role[1][0] == 'w' else role[1][1]
        board.set_piece_at(target, chess.Piece.from_symbol(symbol))
    return board.board_fen()


def import_evidence(conn, path):
    guard()
    payload = json.loads(path.read_text())
    observations = payload if isinstance(payload, list) else payload.get('observations', [payload])
    count = 0
    skipped = 0
    excluded_skipped = []
    selected_units = {(r['game_id'],r['ply']) for r in conn.execute('SELECT game_id,ply,raw_json FROM active_observations') if selected(json.loads(r['raw_json']))}
    for raw in observations:
        guard()
        if not selected(raw) and raw.get('source_type') != 'fresh_review':
            skipped += 1
            continue
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
        excluded = json.loads((ROOT / 'exclude-games.json').read_text())['game_ids']
        if game in excluded:
            excluded_skipped.append(game)
            continue
        unit = (game, raw.get('ply'))
        if selected(raw) and unit not in selected_units and len(selected_units) >= 600 + RESERVE_MOVES:
            raise ValueError('Study unique-move reserve cap reached; no expansion authorized')
        ply = raw.get('ply')
        if not isinstance(ply, int) or ply < 1:
            raise ValueError('Exact 1-based ply required; source move-index conversion must be verified')
        label = canonical_label(raw.get('label'))
        if source_type == 'fresh_review' and label == 'unknown':
            raise ValueError('Unrecognized fresh-review label; fix observed-label extraction rather than guessing: ' + str(raw.get('label')))
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
        if selected(raw): selected_units.add(unit)
        count += 1
    conn.commit()
    return {'observations_processed': count, 'unselected_records_skipped': skipped,
            'excluded_known_games_skipped': sorted(set(excluded_skipped))}


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
        excluded = json.loads((ROOT / 'exclude-games.json').read_text())['game_ids']
        if not game_id or game_id in excluded or (only_games and game_id not in only_games):
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
        raise ValueError('fetch-month requires --only-games; study is not a broad archive crawl')
    if account.lower() not in [a.lower() for a in ACCOUNTS] or not 1 <= month <= 12:
        raise ValueError('Account/month outside study scope')
    remaining = guard()
    url = f'https://api.chess.com/pub/player/{account}/games/{year:04}/{month:02}/pgn'
    request = urllib.request.Request(url, headers={'User-Agent': 'MuteChess-brilliants-600-study/1.0 (public research; https://github.com/Dash1971/mute-chess)'})
    chunks = []
    with urllib.request.urlopen(request, timeout=min(30, remaining)) as response:
        while True:
            guard()
            chunk = response.read(262144)
            if not chunk:
                break
            chunks.append(chunk)
            if sum(map(len, chunks)) > 50 * 1024 * 1024:
                raise ValueError('Monthly archive exceeded the 50 MiB per-request study transfer cap')
        allowed_headers = {'content-type','content-length','content-disposition','etag','last-modified','cache-control','date'}
        response_headers = {k.lower():v for k,v in response.headers.items() if k.lower() in allowed_headers}
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
    board_checks, review_board_checks, index_checks = 0, 0, 0
    board_verified = set()
    observations = conn.execute('SELECT * FROM active_observations').fetchall()
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
        game = conn.execute('SELECT white,black FROM games WHERE game_id=?', (observation['game_id'],)).fetchone()
        mover = game['white'] if position['fen_before'].split()[1] == 'w' else game['black']
        if observation['account'] and observation['account'].lower() != mover.lower():
            problems.append({'observation_id':observation['observation_id'], 'field':'account_to_move',
                             'observed':observation['account'], 'derived':mover})
        for observed, derived in [('observed_san', 'san'), ('observed_uci', 'uci'),
                                   ('observed_fen_before', 'fen_before'), ('observed_fen_after', 'fen_after')]:
            if observation[observed] is not None and observation[observed] != position[derived]:
                problems.append({'observation_id': observation['observation_id'], 'field': observed,
                                 'observed': observation[observed], 'derived': position[derived]})
        gallery_board = observed_board(raw)
        if gallery_board is not None:
            if observation['source_type'] == 'gallery': board_checks += 1
            else: review_board_checks += 1
            derived_board = position['fen_after'].split()[0]
            if gallery_board != derived_board:
                problems.append({'observation_id': observation['observation_id'], 'field': 'observed_board_placement',
                                 'observed': gallery_board, 'derived': derived_board})
            else:
                board_verified.add((observation['game_id'], observation['ply']))
    disagreements = [dict(r) for r in conn.execute('''
      SELECT game_id,ply,GROUP_CONCAT(DISTINCT label_status) AS statuses
      FROM active_observations GROUP BY game_id,ply HAVING
      SUM(label_status='gallery_brilliant')>0 AND SUM(label_status='fresh_confirmed_non_brilliant')>0
    ''')]
    fresh_conflicts = []
    for conflict in conn.execute('''SELECT game_id,ply FROM active_observations WHERE source_type='fresh_review'
        GROUP BY game_id,ply HAVING COUNT(DISTINCT label_status)>1'''):
        captures = [dict(r) for r in conn.execute('''SELECT label,label_status,captured_at,source_link,observation_id
            FROM active_observations WHERE source_type='fresh_review' AND game_id=? AND ply=? ORDER BY captured_at''',
            (conflict['game_id'], conflict['ply']))]
        fresh_conflicts.append({'game_id': conflict['game_id'], 'ply': conflict['ply'], 'captures': captures})
    regression_file = ROOT / 'known-regression-fens.json'
    regression_fens = {p['canonical_first_four'] for p in json.loads(regression_file.read_text())['positions']} if regression_file.exists() else set()
    regression_matches = []
    for row in conn.execute('SELECT DISTINCT p.* FROM positions p JOIN active_observations o USING(game_id,ply)'):
        matching = [field for field in ('fen_before', 'fen_after')
                    if ' '.join(chess.Board(row[field]).fen().split()[:4]) in regression_fens]
        if matching:
            current = any(selected(json.loads(o['raw_json'])) for o in observations
                          if o['game_id'] == row['game_id'] and o['ply'] == row['ply'])
            regression_matches.append({'game_id': row['game_id'], 'ply': row['ply'], 'san': row['san'],
                                       'matching_positions': matching, 'currently_selected': current})
    return {'games': conn.execute('SELECT COUNT(*) FROM games').fetchone()[0],
            'positions': conn.execute('SELECT COUNT(*) FROM positions').fetchone()[0],
            'observations': len(observations), 'indexing_mismatches': problems,
            'raw_evidence_versions': conn.execute('SELECT COUNT(*) FROM observations').fetchone()[0],
            'metadata_enrichment_revisions': conn.execute('SELECT COUNT(*) FROM observations').fetchone()[0] - len(observations),
            'gallery_board_placements_checked': board_checks,
            'fresh_review_board_placements_checked': review_board_checks,
            'unique_moves_with_board_identity': len(board_verified),
            'source_move_indices_checked': index_checks,
            'known_regression_fen_positions': len(regression_fens),
            'known_regression_fen_matches': regression_matches,
            'observations_waiting_for_pgn': missing, 'gallery_fresh_disagreements': disagreements,
            'fresh_binary_label_conflicts': fresh_conflicts,
            'label_counts': [dict(r) for r in conn.execute('SELECT label_status,COUNT(*) AS n FROM active_observations GROUP BY label_status')],
            'split_counts': [dict(r) for r in conn.execute('SELECT split,COUNT(*) AS n FROM games GROUP BY split')]}


def primary_progress(conn, validation):
    groups = {}
    invalid = {item['observation_id'] for item in validation['indexing_mismatches']}
    known_positions = {(item['game_id'], item['ply']) for item in validation.get('known_regression_fen_matches', [])}
    conflicting_captures = {(item['game_id'], item['ply']) for item in validation.get('fresh_binary_label_conflicts', [])}
    for row in conn.execute('SELECT * FROM active_observations ORDER BY captured_at,observation_id'):
        groups.setdefault((row['game_id'], row['ply']), []).append(row)
    per_account = {a: {'fresh_brilliant': 0, 'fresh_non_brilliant': 0} for a in ACCOUNTS}
    rows, pending, conflicts = [], [], []
    for key, observations in groups.items():
        relevant = [r for r in observations if selected(json.loads(r['raw_json']))]
        fresh = [r for r in relevant if r['source_type'] == 'fresh_review']
        if not fresh: continue
        if key in conflicting_captures:
            conflicts.append({'game_id': key[0], 'ply': key[1], 'reason': 'Conflicting explicit fresh binary labels across captures, including secondary evidence; excluded pending review'})
            continue
        if key in known_positions:
            conflicts.append({'game_id': key[0], 'ply': key[1], 'reason': 'Known development/regression FEN; excluded from new primary sample'})
            continue
        labels = {r['label'] == '!!' for r in fresh if r['label'] != 'unknown'}
        if len(labels) != 1 or any(r['observation_id'] in invalid for r in relevant):
            conflicts.append({'game_id': key[0], 'ply': key[1], 'reason': 'Conflicting fresh labels or identity mismatch'})
            continue
        latest = fresh[-1]
        account = next((a for a in ACCOUNTS if a.lower() == str(latest['account']).lower()), None)
        if not account: continue
        position = conn.execute('SELECT * FROM positions WHERE game_id=? AND ply=?', key).fetchone()
        if not position or not latest['observed_san']:
            pending.append({'game_id': key[0], 'ply': key[1], 'reason': 'Missing PGN or visible fresh SAN'})
            continue
        has_board_identity = any(observed_board(json.loads(r['raw_json'])) == position['fen_after'].split()[0] for r in relevant)
        gallery = [r for r in relevant if r['label_status'] == 'gallery_brilliant']
        positive = latest['label'] == '!!'
        role = json.loads(latest['raw_json']).get('sample_role')
        if role not in (('positive_target', 'positive_candidate') if positive else ('negative_control',)):
            conflicts.append({'game_id': key[0], 'ply': key[1], 'reason': 'Not the planned positive/control role; reserve only'})
            continue
        if (positive and not gallery) or (not positive and gallery):
            conflicts.append({'game_id': key[0], 'ply': key[1], 'reason': 'Unexpected control-positive or gallery/fresh disagreement; reserve only'})
            continue
        label_class = 'fresh_brilliant' if positive else 'fresh_non_brilliant'
        if per_account[account][label_class] >= TARGET_PER_ACCOUNT: continue
        per_account[account][label_class] += 1
        game = conn.execute('SELECT split,date FROM games WHERE game_id=?', (key[0],)).fetchone()
        rows.append({'game_id': key[0], 'ply': key[1], 'account': account, 'label_class': label_class,
                     'fresh_label': latest['label'], 'san': position['san'], 'uci': position['uci'],
                     'fresh_observation_id': latest['observation_id'], 'fresh_captured_at': latest['captured_at'],
                     'fresh_source_link': latest['source_link'],
                     'gallery_observation_ids': [r['observation_id'] for r in gallery],
                     'fen_before': position['fen_before'], 'fen_after': position['fen_after'],
                     'split': game['split'], 'date': game['date'],
                     'identity_basis': 'visible SAN plus game ID and verified one-based ply; board checked when captured',
                     'board_identity_captured': has_board_identity, 'board_missing': not has_board_identity,
                     'sampling_category': (json.loads(gallery[0]['raw_json']).get('sampling_category') or json.loads(gallery[0]['categories_json'])[0]) if gallery and json.loads(gallery[0]['categories_json']) else None,
                     'categories': json.loads(gallery[0]['categories_json']) if gallery else []})
    return {'per_account': per_account, 'primary_unique_moves': len(rows),
            'primary_fresh_brilliant': sum(v['fresh_brilliant'] for v in per_account.values()),
            'primary_fresh_non_brilliant': sum(v['fresh_non_brilliant'] for v in per_account.values()),
            'primary_moves_with_captured_board_identity': sum(r['board_identity_captured'] for r in rows),
            'primary_moves_with_board_missing': sum(r['board_missing'] for r in rows),
            'pending_identity_or_pgn': pending, 'reserve_or_conflicting_moves': conflicts,
            'target_complete': all(v == TARGET_PER_ACCOUNT for counts in per_account.values() for v in counts.values()),
            'moves': rows}


def reuse_cache(conn):
    """Read only the already-downloaded pilot months, selecting pending study IDs."""
    pending = {r[0] for r in conn.execute('SELECT DISTINCT o.game_id FROM observations o LEFT JOIN games g ON g.game_id=o.game_id WHERE g.game_id IS NULL')}
    pilot = ROOT.parent / 'brilliants-pilot-2026-11-03' / 'original-pgn'
    reused = []
    for path in sorted(pilot.glob('*.pgn')):
        if not pending: break
        metadata = json.loads(path.with_suffix('.response.json').read_text())
        result = import_pgn(conn, path.read_text(), metadata['source_link'], metadata['captured_at'], pending)
        found = set(result['games_imported_or_matched'])
        if found:
            pending -= found
            reused.append({'source_link': metadata['source_link'], 'captured_at': metadata['captured_at'],
                           'sha256': metadata['sha256'], 'bytes': metadata['bytes'], 'selected_game_ids': sorted(found),
                           'reused_local_pilot_archive': True})
    history_file = ROOT / 'reused-pilot-archives.json'
    history = json.loads(history_file.read_text()) if history_file.exists() else []
    history.extend(reused)
    history_file.write_text(json.dumps(history, indent=2) + '\n')
    return {'local_archives_reused': reused, 'pending_game_ids': sorted(pending)}


def fetch_selected(conn, accounts):
    """Resolve a frozen selected-ID snapshot from at most 13 published months/account."""
    guard()
    requests = ROOT / 'pgn-request-snapshots'
    requests.mkdir(exist_ok=True)
    snapshot = {account: sorted({r[0] for r in conn.execute(
        'SELECT DISTINCT o.game_id FROM observations o LEFT JOIN games g ON g.game_id=o.game_id WHERE LOWER(o.account)=LOWER(?) AND g.game_id IS NULL', (account,))}) for account in accounts}
    (requests / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '.json')).write_text(json.dumps({'captured_at':now(),'selected_pending_ids':snapshot,'max_published_months_per_account':13,'earliest_month':'2025/11'},indent=2)+'\n')
    folder = ROOT / 'original-pgn'
    folder.mkdir(exist_ok=True)
    results = []
    allow = {'content-type','content-length','content-disposition','etag','last-modified','cache-control','date'}
    for account, ids in snapshot.items():
        pending = set(ids)
        if not pending: continue
        if account.lower() not in [a.lower() for a in ACCOUNTS]: raise ValueError('Unknown study account')
        url = f'https://api.chess.com/pub/player/{account}/games/archives'
        list_file = folder / f'{account.lower()}-archive-list.json'
        if list_file.exists():
            payload = json.loads(list_file.read_text())
        else:
            old = ROOT.parent / 'brilliants-pilot-2026-11-03' / 'original-pgn' / list_file.name
            if old.exists():
                body = old.read_bytes();metadata = json.loads(old.with_suffix('.response.json').read_text())
                metadata = {k:metadata[k] for k in ('source_link','captured_at','sha256','bytes')}
                metadata['reused_local_pilot_archive_list'] = True
            else:
                req = urllib.request.Request(url,headers={'User-Agent':'MuteChess-brilliants-600-study/1.0 (https://github.com/Dash1971/mute-chess)'})
                with urllib.request.urlopen(req,timeout=guard()) as response:
                    body = response.read(262144)
                    if response.read(1): raise ValueError('Archive list exceeds 256 KiB')
                    metadata = {'source_link':url,'captured_at':now(),'sha256':sha(body),'bytes':len(body),'headers':{k.lower():v for k,v in response.headers.items() if k.lower() in allow}}
            list_file.write_bytes(body)
            list_file.with_suffix('.response.json').write_text(json.dumps(metadata,indent=2)+'\n')
            payload = json.loads(body)
        published = []
        for archive in reversed(payload['archives']):
            match = re.fullmatch(r'https://api\.chess\.com/pub/player/([^/]+)/games/(\d{4})/(\d{2})',archive)
            if not match or match[1].lower()!=account.lower(): raise ValueError('Unexpected published archive URL')
            if (int(match[2]),int(match[3])) < (2025,11): continue
            published.append((int(match[2]),int(match[3])))
        attempts = 0
        for year,month in published[:13]:
            if not pending: break
            guard();attempts += 1
            filename = f'{account.lower()}-{year:04}-{month:02}.pgn'
            local = folder / filename
            if not local.exists(): local = ROOT.parent / 'brilliants-pilot-2026-11-03' / 'original-pgn' / filename
            if local.exists():
                meta = json.loads(local.with_suffix('.response.json').read_text())
                found = import_pgn(conn,local.read_text(),meta['source_link'],meta['captured_at'],pending)
            else:
                found = fetch_month(conn,account,year,month,pending)
            pending -= set(found['games_imported_or_matched'])
            print(json.dumps({'account':account,'month':f'{year:04}/{month:02}','found':found['games_imported_or_matched'],'pending':len(pending)}),flush=True)
        results.append({'account':account,'selected_id_count':len(ids),'published_months_examined':attempts,'unresolved_ids':sorted(pending)})
    return results


def prepare_controls(conn):
    """PGN facts only; every suggestion remains label-unknown until UI review."""
    targets = [r for r in conn.execute("SELECT * FROM active_observations WHERE source_type='gallery'") if selected(json.loads(r['raw_json']))]
    candidates = {a: [] for a in ACCOUNTS}
    for target in targets:
        game = conn.execute('SELECT white,black FROM games WHERE game_id=?', (target['game_id'],)).fetchone()
        if not game: continue
        account = next((a for a in ACCOUNTS if a.lower() == str(target['account']).lower()), None)
        if not account: continue
        parity = 1 if game['white'].lower() == account.lower() else 0
        suggestions = []
        for row in conn.execute('SELECT * FROM positions WHERE game_id=? ORDER BY ply', (target['game_id'],)):
            if row['ply'] % 2 != parity or row['ply'] == target['ply']: continue
            if conn.execute("SELECT 1 FROM observations WHERE game_id=? AND ply=? AND source_type='gallery'", (row['game_id'],row['ply'])).fetchone(): continue
            board = chess.Board(row['fen_before']);move = chess.Move.from_uci(row['uci']);capture = board.is_capture(move)
            if not capture and abs(row['ply'] - target['ply']) > 12: continue
            previous = conn.execute('SELECT * FROM positions WHERE game_id=? AND ply=?', (row['game_id'],row['ply']-1)).fetchone()
            recapture = bool(capture and previous and previous['uci'][2:4] == row['uci'][2:4] and chess.Board(previous['fen_before']).is_capture(chess.Move.from_uci(previous['uci'])))
            victim = board.piece_at(move.to_square)
            suggestions.append(dict(row) | {'is_capture':capture,'captured_role':'pawn' if board.is_en_passant(move) else chess.piece_name(victim.piece_type) if capture and victim else None,'immediate_same_square_recapture':recapture,'label':'unknown','distance_from_target_plies':abs(row['ply'] - target['ply'])})
        suggestions.sort(key=lambda r:(not r['is_capture'],r['distance_from_target_plies'],r['ply']))
        candidates[account].append({'game_id':target['game_id'],'target_ply':target['ply'],'suggestions':suggestions})
    for account, rows in candidates.items():
        (ROOT / f'control-candidates-{account.lower()}.json').write_text(json.dumps(rows,indent=2)+'\n')
    return {account:len(rows) for account,rows in candidates.items()}


def export(conn):
    selected_games = conn.execute('''SELECT g.* FROM games g WHERE EXISTS (
        SELECT 1 FROM active_observations o WHERE o.game_id=g.game_id) ORDER BY game_id''').fetchall()
    selected_pgn = '\n\n'.join(g['pgn'].strip() for g in selected_games) + ('\n' if selected_games else '')
    (ROOT / 'selected-games.pgn').write_text(selected_pgn)
    provenance = {'exported_at': now(), 'selected_games': len(selected_games),
                  'selected_pgn_sha256': sha(selected_pgn), 'selected_pgn_bytes': len(selected_pgn.encode()),
                  'scope': 'Only games referenced by current study observations; full monthly downloads remain local. No HTTP headers, cookies or credentials included.',
                  'games': [{'game_id': g['game_id'], 'pgn_sha256': g['pgn_sha256'],
                             'source_link': g['source_link'], 'captured_at': g['captured_at'],
                             'total_plies': g['total_plies'], 'split': g['split']} for g in selected_games]}
    (ROOT / 'public-pgn-provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    rows = []
    for row in conn.execute('''SELECT o.*,p.san,p.uci,p.fen_before,p.fen_after,p.clock_seconds,
        g.white,g.black,g.white_rating,g.black_rating,g.date,g.time_control,g.split
        FROM active_observations o LEFT JOIN positions p ON p.game_id=o.game_id AND p.ply=o.ply
        LEFT JOIN games g ON g.game_id=o.game_id ORDER BY o.game_id,o.ply,o.source_type'''):
        item = dict(row)
        item['categories'] = json.loads(item.pop('categories_json'))
        item['original_observation'] = json.loads(item.pop('raw_json'))
        item['selection_status'] = 'active_selected' if selected(item['original_observation']) else 'secondary_audit_only'
        item['category_membership_status'] = ('current_verified_selection' if selected(item['original_observation']) else 'superseded_or_secondary_gallery') if item['source_type'] == 'gallery' else 'not_a_gallery_membership_observation'
        item['missing_fields'] = [k for k, v in item.items() if v is None]
        rows.append(item)
    (ROOT / 'observations-export.json').write_text(json.dumps(rows, indent=2) + '\n')
    validation = validate(conn)
    (ROOT / 'known-regression-fen-matches.json').write_text(json.dumps({
        'checked_at': now(), 'policy_source': 'known-regression-fens.json',
        'observed_moves_matching': validation['known_regression_fen_matches']}, indent=2) + '\n')
    progress = primary_progress(conn, validation)
    primary = progress.pop('moves')
    (ROOT / 'primary-moves.json').write_text(json.dumps(primary, indent=2) + '\n')
    primary_keys = {(m['game_id'], m['ply']) for m in primary}
    fresh_primary = [r for r in rows if (r['game_id'], r['ply']) in primary_keys
                     and r['source_type'] == 'fresh_review' and selected(r['original_observation'])]
    before_positions = {}
    for move in primary:
        position = ' '.join(chess.Board(move['fen_before']).fen().split()[:4])
        before_positions.setdefault(position, []).append({'game_id': move['game_id'], 'ply': move['ply'], 'account': move['account']})
    metadata_fields = ['observed_san', 'displayed_evaluation', 'coach_explanation', 'white_rating', 'black_rating', 'date', 'time_control', 'clock_seconds']
    coach_audit = []
    for row in fresh_primary:
        text = (row.get('coach_explanation') or '').strip()
        original = row['original_observation']
        explicit_status = original.get('coach_completeness') or original.get('coach_capture_status') or original.get('coach_explanation_capture_status')
        coach_audit.append({'game_id': row['game_id'], 'ply': row['ply'], 'account': row['account'],
                            'text_present': bool(text), 'characters': len(text),
                            'ends_with_sentence_punctuation': bool(re.search(r'[.!?][\"\u201d\u2019\']?$', text)),
                            'explicit_capture_status': explicit_status,
                            'extraction_method': original.get('coach_extraction', 'not_recorded'),
                            'completeness': 'explicitly_recorded_visible_complete' if explicit_status == 'verified_visible_complete' else 'partial_or_unverified',
                            'raw_text_preserved_in_observations_export': True})
    audit = {'exported_at': now(), 'primary_game_moves': len(primary),
             'authoritative_gallery_selection_files': {p.name: sha(p.read_bytes()) for p in sorted((ROOT / 'evidence').glob('*-gallery-selected.json'))},
             'primary_games': len({m['game_id'] for m in primary}),
             'per_account': progress['per_account'],
             'primary_fresh_capture_rows': len(fresh_primary),
             'fresh_metadata_present': {field: sum(r.get(field) not in (None, '') for r in fresh_primary) for field in metadata_fields},
             'fresh_metadata_missing': {field: sum(r.get(field) in (None, '') for r in fresh_primary) for field in metadata_fields},
             'coach_text_quality': {'text_present': sum(r['text_present'] for r in coach_audit),
                                    'ends_with_sentence_punctuation': sum(r['ends_with_sentence_punctuation'] for r in coach_audit),
                                    'has_explicit_capture_status': sum(r['explicit_capture_status'] is not None for r in coach_audit),
                                    'explicitly_recorded_visible_complete': sum(r['completeness'] == 'explicitly_recorded_visible_complete' for r in coach_audit),
                                    'note': 'Nonempty text and terminal punctuation do not prove completeness. Legacy typewriter-animation captures may be partial; raw text and capture timestamps are unchanged.',
                                    'per_move': coach_audit},
             'primary_moves_with_captured_board_identity': progress['primary_moves_with_captured_board_identity'],
             'primary_moves_with_board_missing': progress['primary_moves_with_board_missing'],
             'primary_exact_before_position_duplicate_groups': [v for v in before_positions.values() if len(v) > 1],
             'known_regression_fen_matches': validation['known_regression_fen_matches'],
             'gallery_fresh_disagreements': validation['gallery_fresh_disagreements'],
             'fresh_binary_label_conflicts': validation['fresh_binary_label_conflicts'],
             'note': 'Counts describe current validated primary game-moves; raw secondary observations and metadata enrichment revisions remain separate audit evidence. Repeated positions across distinct games remain visible; they are not independent positions.'}
    (ROOT / 'cohort-audit.json').write_text(json.dumps(audit, indent=2) + '\n')
    manifest = {'metadata': {r['key']: json.loads(r['value']) for r in conn.execute('SELECT * FROM metadata')},
                'exported_at': now(), 'validation': validation, 'progress': progress}
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
    commands.add_parser('reuse-cache'); commands.add_parser('prepare-controls')
    resolve = commands.add_parser('fetch-selected'); resolve.add_argument('--accounts',required=True)
    args = parser.parse_args()
    ROOT.mkdir(parents=True, exist_ok=True)
    conn = connect(args.db)
    try:
        if args.command == 'init': result = export(conn)
        elif args.command == 'import-evidence': result = import_evidence(conn, args.file)
        elif args.command == 'import-pgn': result = import_pgn(conn, args.file.read_text(), args.source, args.captured_at, set(filter(None, args.only_games.split(','))))
        elif args.command == 'fetch-month': result = fetch_month(conn, args.account, args.year, args.month, set(filter(None, args.only_games.split(','))))
        elif args.command == 'validate': result = validate(conn)
        elif args.command == 'reuse-cache': result = reuse_cache(conn)
        elif args.command == 'prepare-controls': result = prepare_controls(conn)
        elif args.command == 'fetch-selected': result = fetch_selected(conn,args.accounts.split(','))
        else: result = export(conn)
        print(json.dumps(result, indent=2))
    finally:
        conn.close()


if __name__ == '__main__':
    main()
