#!/usr/bin/env python3
"""Study-local prospective-v7 precision assessment corpus; unchanged independent200 identity/import method. Offline PGN reuse and explicit UI evidence only; no engine or network commands."""
from __future__ import annotations
import argparse,hashlib,io,json,re,sqlite3,sys
from urllib.parse import parse_qs,urlparse
from datetime import datetime,timezone
from pathlib import Path
try:
 import chess.pgn
except ImportError:
 sys.path.insert(0,'/private/tmp/brilly-research-deps');import chess.pgn
ROOT=Path(__file__).resolve().parent
TARGET_PER_ACCOUNT=20
RESERVE_MOVES=60
ACCOUNTS=('nelsi','hansen','KNVB','GothamChess','Hikaru')
GAME_ID=re.compile(r'(?:game|games)/(?:live|daily)/(\d+)|(?:live|daily)/(\d+)')
_selection_cache={}
def split_for(game,headers):
 return ('validation','Prospective unchanged-v7 assessment; all1048 previous labels are unblinded development')

def now():
    return datetime.now(timezone.utc).isoformat()

def guard():
    if (ROOT / 'STOP_COLLECTION').exists():
        raise RuntimeError('Collection stopped by owner/parent marker')
    return 20

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
    plan = json.loads((ROOT / 'PLAN.json').read_text())
    metadata = {'study_id':plan['study_id'], 'started_at':plan.get('prepared_at_utc',plan['frozen_at_utc']),
        'plan_sha256':sha((ROOT / 'PLAN.json').read_bytes()), 'quantity_completion_authorized':True,
        'tuning_authorized':False, 'accounts':list(ACCOUNTS),
        'target':{'fresh_brilliant':100,'fresh_non_brilliant':100,'total_primary_cap':200,'soft_per_account_per_class':20},
        'split_policy':plan['selection']['partitions'], 'split_frozen_before_tuning':True,
        'baseline_sources':plan['baseline_sources'], 'label_absence_means':'unknown',
        'excluded_game_ids':json.loads((ROOT / 'exclude-games.json').read_text())['game_ids']}
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
               'good': 'good', 'book': 'book', 'forced': 'forced', 'miss': 'miss', 'unknown': 'unknown'}
    return mapping.get(value.lower(), value if value in ('!!', '!', '!?', '?!', '?', '??') else 'unknown')

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
        if selected(raw) and unit not in selected_units and len(selected_units) >= 200 + RESERVE_MOVES:
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

def validate(conn):
    problems, missing = [], []
    board_checks, review_board_checks, index_checks = 0, 0, 0
    board_verified = set()
    observations = conn.execute('SELECT * FROM active_observations').fetchall()
    for observation in observations:
        raw = json.loads(observation['raw_json'])
        source_game = game_id_from(observation['source_link'])
        if source_game != observation['game_id']:
            problems.append({'observation_id':observation['observation_id'], 'field':'source_game_id',
                             'observed':observation['game_id'], 'derived':source_game})
        expected_game = conn.execute('SELECT headers_json FROM games WHERE game_id=?',(observation['game_id'],)).fetchone()
        if expected_game:
            expected_url = json.loads(expected_game[0]).get('Link','')
            expected_ns = re.search(r'/(live|daily)/',expected_url)
            observed_ns = re.search(r'/(live|daily)/',observation['source_link'])
            if expected_ns and (not observed_ns or expected_ns[1]!=observed_ns[1]):
                problems.append({'observation_id':observation['observation_id'],'field':'source_namespace','expected':expected_ns[1],'observed':observed_ns[1] if observed_ns else None})
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
    allocation_file = ROOT / 'quota-allocations.json'
    quotas = json.loads(allocation_file.read_text())['account_class_quotas'] if allocation_file.exists() else {}
    rows, pending, conflicts = [], [], []
    positive_identities = set()
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
        identity = (' '.join(chess.Board(position['fen_before']).fen().split()[:4]), position['uci'])
        if positive and identity in positive_identities:
            conflicts.append({'game_id': key[0], 'ply': key[1], 'reason': 'Repeated positive before-position plus move across games; excluded by additional300 plan'})
            continue
        if sum(v[label_class] for v in per_account.values()) >=100: continue
        if per_account[account][label_class] >= quotas.get(account,{}).get(label_class,TARGET_PER_ACCOUNT): continue
        per_account[account][label_class] += 1
        if positive: positive_identities.add(identity)
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
            'target_complete': all(sum(v[label] for v in per_account.values())==100 for label in ('fresh_brilliant','fresh_non_brilliant')),
            'moves': rows}

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
    assert len(primary)<=200
    (ROOT / 'primary-moves.json').write_text(json.dumps(primary, indent=2) + '\n')
    for partition in ('validation',):
        (ROOT / ('primary-'+partition+'-moves.json')).write_text(json.dumps([m for m in primary if m['split']==partition],indent=2)+'\n')
    primary_keys = {(m['game_id'], m['ply']) for m in primary}
    fresh_primary = [r for r in rows if (r['game_id'], r['ply']) in primary_keys
                     and r['source_type'] == 'fresh_review' and selected(r['original_observation'])]
    before_positions = {}
    all_positions = {}
    for move in primary:
        position = ' '.join(chess.Board(move['fen_before']).fen().split()[:4])
        identity = {'game_id':move['game_id'], 'ply':move['ply'], 'account':move['account'], 'split':move['split']}
        before_positions.setdefault(position, []).append(identity)
        for phase in ('fen_before','fen_after'):
            key = ' '.join(chess.Board(move[phase]).fen().split()[:4])
            all_positions.setdefault(key, []).append(identity | {'phase':phase})
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
             'repeated_before_or_after_positions': [{'canonical_first_four':k,'occurrences':v} for k,v in all_positions.items() if len(v)>1],
             'cross_partition_position_overlap': [{'canonical_first_four':k,'occurrences':v} for k,v in all_positions.items() if len({x['split'] for x in v})>1],
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
 p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='command',required=True)
 for name in ('init','validate','export'):s.add_parser(name)
 e=s.add_parser('import-evidence');e.add_argument('file',type=Path)
 g=s.add_parser('import-pgn');g.add_argument('file',type=Path);g.add_argument('--source',required=True);g.add_argument('--only-games',required=True)
 a=p.parse_args();c=connect(ROOT/'corpus.sqlite3')
 try:
  if a.command=='import-evidence':result=import_evidence(c,a.file)
  elif a.command=='import-pgn':result=import_pgn(c,a.file.read_text(),a.source,now(),set(a.only_games.split(',')))
  elif a.command=='validate':result=validate(c)
  else:result=export(c)
  print(json.dumps(result,indent=2))
 finally:c.close()
if __name__=='__main__':main()
