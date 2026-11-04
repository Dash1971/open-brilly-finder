"""One bounded, read-only-source consolidation; no predictions or engine work."""
import collections
import csv
import hashlib
import io
import json
import pathlib
import re
import sqlite3
from datetime import datetime, timezone

import chess
import chess.pgn

HERE = pathlib.Path(__file__).resolve().parent
WORKSPACE = HERE.parent.parent
OLD = HERE.parent / 'brilliants-final-2026-11-03'
NEW = HERE / 'future-validation-v5'
OUT = HERE / 'publication-data-v5'
assert not OUT.exists(), 'Do not overwrite a staged dataset silently'
OUT.mkdir()
(OUT / 'protocol').mkdir()
load = lambda p: json.loads(p.read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
textsha = lambda s: hashlib.sha256(s.encode()).hexdigest()

def write(name, value):
    path = OUT / name
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')

def relative(path):
    return str(path.resolve().relative_to(WORKSPACE))

def sanitize(value):
    # Only provenance copies use this function. Observation evidence stays exact.
    if isinstance(value, dict):
        return {sanitize(k): sanitize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize(v) for v in value]
    if isinstance(value, str):
        return value.replace(str(WORKSPACE) + '/', '')
    return value

def observed_board(raw):
    placement = raw.get('board_placement') or raw.get('rawgalleryboard_placement')
    pieces = raw.get('review_board_pieces') or raw.get('gallery_board_pieces') or raw.get('board_piece_classes')
    if placement is not None or not pieces:
        return placement
    board = chess.Board(None)
    for value in pieces:
        role = re.search(r'\b([wb][pnbrqk])\b', value)
        square = re.search(r'\bsquare-([1-8])([1-8])\b', value)
        assert role and square
        target = chess.square(int(square[1]) - 1, int(square[2]) - 1)
        assert not board.piece_at(target)
        symbol = role[1][1].upper() if role[1][0] == 'w' else role[1][1]
        board.set_piece_at(target, chess.Piece.from_symbol(symbol))
    return board.board_fen()

inputs = [OLD / 'primary-moves.json', OLD / 'panel-moves.json', NEW / 'primary-moves.json']
originals = [load(p) for p in inputs]
assert [len(v) for v in originals] == [818, 30, 200]
dev_ids = {str(r['game_id']) for r in originals[0] + originals[1]}
test_ids = {str(r['game_id']) for r in originals[2]}
assert (len(dev_ids), len(test_ids)) == (439, 106) and not dev_ids & test_ids
ids = dev_ids | test_ids
sources = [sqlite3.connect(f'file:{p / "corpus.sqlite3"}?mode=ro', uri=True) for p in [OLD, NEW]]
for db in sources:
    db.row_factory = sqlite3.Row
source_db_hashes = {relative(p / 'corpus.sqlite3'): sha(p / 'corpus.sqlite3') for p in [OLD, NEW]}

db = sqlite3.connect(OUT / 'corpus.sqlite3')
db.row_factory = sqlite3.Row
db.execute('PRAGMA foreign_keys=ON')
for table in ['metadata', 'games', 'positions', 'observations']:
    db.execute(sources[0].execute('SELECT sql FROM sqlite_master WHERE type="table" AND name=?', (table,)).fetchone()[0])
db.execute('''CREATE VIEW active_observations AS SELECT * FROM observations WHERE rowid IN
 (SELECT MAX(rowid) FROM observations GROUP BY game_id,ply,source_type,captured_at,source_link,account)''')
db.execute('''CREATE TABLE labeled_moves (game_id TEXT,ply INTEGER,role TEXT,cohort TEXT,
 fresh_observation_id TEXT,fresh_label TEXT,is_brilliant INTEGER,record_json TEXT,
 PRIMARY KEY(game_id,ply),FOREIGN KEY(game_id) REFERENCES games(game_id))''')
archive_games = []
for table in ['games', 'positions', 'observations']:
    columns = [r[1] for r in sources[0].execute(f'PRAGMA table_info({table})')]
    insert = f'INSERT INTO {table} ({",".join(columns)}) VALUES ({",".join("?" for _ in columns)})'
    for index, source in enumerate(sources):
        selected = dev_ids if index == 0 else test_ids
        for source_row in source.execute(f'SELECT * FROM {table} ORDER BY rowid'):
            row = dict(source_row)
            if row['game_id'] not in selected:
                continue
            if table == 'games':
                archive_games.append({'game_id': row['game_id'], 'source_database': relative([OLD, NEW][index] / 'corpus.sqlite3'),
                    'archived_split': row['split'], 'archived_split_reason': row['split_reason']})
                row['split'] = 'development' if index == 0 else 'test'
                row['split_reason'] = 'Current v5 role; prior split names are archival metadata only. All848 prior moves are development; the frozen200 are the prospective test.'
            db.execute(insert, [row[c] for c in columns])

moves = []
archive_fields = ['split', 'original_split', 'source_cohort', 'source_split_before_consolidation',
    'source_cohort_before_consolidation', 'historical_v4_evaluation_role', 'future_v5_role']
for index, rows in enumerate(originals):
    for raw in rows:
        role = 'test' if index == 2 else 'development'
        game = db.execute('SELECT * FROM games WHERE game_id=?', (str(raw['game_id']),)).fetchone()
        namespace = 'daily' if '/daily/' in raw['fresh_source_link'] else 'live'
        row = {k: raw[k] for k in ['game_id', 'ply', 'account', 'label_class', 'fresh_label', 'san', 'uci',
            'fen_before', 'fen_after', 'fresh_observation_id', 'fresh_captured_at', 'fresh_source_link',
            'identity_basis', 'board_identity_captured', 'board_missing']}
        row.update(role=role, cohort=['development_core', 'development_mechanism_panel', 'prospective_test'][index],
            game_namespace=namespace, move_id=f'{namespace}:{raw["game_id"]}:{raw["ply"]}',
            is_brilliant=raw['fresh_label'] == '!!', gallery_observation_ids=raw.get('gallery_observation_ids', []),
            sampling_category=raw.get('sampling_category') or raw.get('category'), categories=raw.get('categories', []),
            date=game['date'], white=game['white'], black=game['black'], white_rating=game['white_rating'],
            black_rating=game['black_rating'], time_control=game['time_control'], pgn_sha256=game['pgn_sha256'],
            source_primary_artifact=relative(inputs[index]), archive_metadata={k: raw[k] for k in archive_fields if k in raw})
        moves.append(row)
        db.execute('INSERT INTO labeled_moves VALUES(?,?,?,?,?,?,?,?)', (row['game_id'], row['ply'], role,
            row['cohort'], row['fresh_observation_id'], row['fresh_label'], int(row['is_brilliant']), json.dumps(row, sort_keys=True)))
assert len({r['move_id'] for r in moves}) == 1048

# Check every complete PGN, stored position, fresh label, and captured rendered board.
by_game = collections.defaultdict(list)
for row in moves:
    by_game[row['game_id']].append(row)
positions_checked = 0
proofs = collections.Counter()
missing = []
for game in db.execute('SELECT * FROM games ORDER BY game_id'):
    assert textsha(game['pgn']) == game['pgn_sha256']
    parsed = chess.pgn.read_game(io.StringIO(game['pgn']))
    assert parsed and not parsed.errors
    board = parsed.board()
    saved = {r['ply']: r for r in db.execute('SELECT * FROM positions WHERE game_id=?', (game['game_id'],))}
    for ply, move in enumerate(parsed.mainline_moves(), 1):
        assert move in board.legal_moves
        p = saved[ply]
        assert (p['san'], p['uci'], p['fen_before']) == (board.san(move), move.uci(), board.fen())
        board.push(move)
        assert p['fen_after'] == board.fen()
        positions_checked += 1
    assert len(saved) == game['total_plies']
    for row in by_game[game['game_id']]:
        p = saved[row['ply']]
        assert all(row[k] == p[k] for k in ['san', 'uci', 'fen_before', 'fen_after'])
        observation = db.execute('SELECT * FROM observations WHERE observation_id=?', (row['fresh_observation_id'],)).fetchone()
        assert observation and observation['source_type'] == 'fresh_review' and observation['label'] == row['fresh_label']
        assert (observation['game_id'], observation['ply']) == (row['game_id'], row['ply'])
        board_sources = [observation]
        for ident in row['gallery_observation_ids']:
            gallery = db.execute('SELECT * FROM observations WHERE observation_id=?', (ident,)).fetchone()
            assert gallery and gallery['source_type'] == 'gallery'
            board_sources.append(gallery)
        rendered = [observed_board(json.loads(o['raw_json'])) for o in board_sources]
        for placement in rendered:
            if placement:
                assert placement == row['fen_after'].split()[0], row['move_id']
        # Preserve the original capture-coverage flags, rather than upgrade old evidence.
        if row['board_identity_captured']:
            assert any(rendered), row['move_id']
            proofs[row['role']] += 1
        else:
            missing.append(row['move_id'])
assert dict(proofs) == {'development': 841, 'test': 200} and len(missing) == 7

# Freeze/source audit: exact original hashes, sanitized provenance copies, no predictions.
queue = load(NEW / 'QUEUE-FREEZE.json')
core = load(NEW / 'CORE-FREEZE.json')
hash_checks = []
def check(path, expected, kind):
    actual = sha(path)
    assert actual == expected, relative(path)
    hash_checks.append({'artifact': relative(path), 'sha256': actual, 'kind': kind, 'matches': True})
for name, expected in queue['source_model_executable_sha256'].items():
    check(WORKSPACE / name, expected, 'prelabel_frozen_source_or_model')
for name, expected in queue['file_sha256'].items():
    check(NEW / name, expected, 'prelabel_queue_or_protocol')
for name, meta in queue['source_freeze_artifact_sha256'].items():
    check(HERE / name, meta['sha256'], 'prelabel_source_freeze')
for name, expected in core['files_sha256'].items():
    check(NEW / name, expected, 'final_primary_identity_freeze')
protocol_paths = [NEW / 'PLAN.json', NEW / 'QUEUE-FREEZE.json', NEW / 'CORE-FREEZE.json',
    NEW / 'exclude-games.json', NEW / 'known-regression-fens.json', NEW / 'gallery-reserve-activations.json',
    HERE / 'astra/v5/fresh-extractor/FREEZE.json', HERE / 'astra/v5/sequence-reference/source-freeze.json',
    HERE / 'astra/v5/sequence-reference/source-freeze-castling-addendum.json', OLD / 'CANDIDATE-FREEZE.json']
copies = []
for index, path in enumerate(protocol_paths):
    name = f'protocol/{index:02d}-{path.name}'
    write(name, sanitize(load(path)))
    copies.append({'source_artifact': relative(path), 'source_sha256': sha(path), 'staged_artifact': name,
        'staged_sha256': sha(OUT / name), 'local_path_normalization_only': True})
write('source-hash-audit.json', {'all_checked_hashes_match': True, 'checks': hash_checks, 'protocol_copies': copies})
write('archival-game-metadata.json', archive_games)
write('moves.json', moves)
fields = ['move_id', 'role', 'cohort', 'game_namespace', 'game_id', 'ply', 'account', 'is_brilliant', 'fresh_label',
    'san', 'uci', 'fen_before', 'fen_after', 'board_identity_captured', 'board_missing', 'fresh_observation_id',
    'fresh_captured_at', 'fresh_source_link', 'gallery_observation_ids', 'sampling_category', 'categories',
    'pgn_sha256', 'date', 'white', 'black', 'white_rating', 'black_rating', 'time_control', 'archive_metadata']
with (OUT / 'moves.csv').open('w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    for row in moves:
        writer.writerow({k: json.dumps(row[k], sort_keys=True) if isinstance(row[k], (dict, list)) else row[k] for k in fields})
observations = [dict(r) for r in db.execute('SELECT * FROM observations ORDER BY game_id,ply,captured_at,observation_id')]
write('observations-export.json', observations)
games = list(db.execute('SELECT * FROM games ORDER BY game_id'))
(OUT / 'selected-games.pgn').write_text('\n\n'.join(r['pgn'].strip() for r in games) + '\n')
write('pgn-provenance.json', {'selected_games': len(games), 'http_headers_included': False,
    'games': [{k: r[k] for k in ['game_id', 'pgn_sha256', 'source_link', 'captured_at', 'total_plies', 'split']} for r in games]})
fresh_ids = {r['fresh_observation_id'] for r in moves}
new_fresh = [r for r in observations if r['game_id'] in test_ids and r['source_type'] == 'fresh_review']
new_secondary = [r['observation_id'] for r in new_fresh if r['observation_id'] not in fresh_ids]
assert len(new_fresh) == 210 and len(new_secondary) == 10
counts = {t: db.execute(f'SELECT count(*) FROM {t}').fetchone()[0] for t in ['games', 'positions', 'observations', 'labeled_moves']}
assert counts['games'] == 545 and counts['labeled_moves'] == 1048
manifest = {'study_id': 'brilliant-moves-v5-private-staging', 'staged_at_utc': datetime.now(timezone.utc).isoformat(),
    'publication_status': 'private_parent_review_required', 'predictions_included': False,
    'roles': {'development': {'moves': 848, 'games': 439, 'brilliant': 413, 'explicit_non_brilliant': 435},
        'test': {'moves': 200, 'games': 106, 'brilliant': 100, 'explicit_non_brilliant': 100}},
    'role_note': 'All848 prior core/panel labels are training/development. Historical split names are archive metadata only; the frozen200 form the new prospective test.',
    'counts': counts, 'observation_source_counts': dict(collections.Counter(r['source_type'] for r in observations)),
    'new_fresh_observations': 210, 'new_secondary_fresh_observations': 10, 'new_secondary_observation_ids': new_secondary,
    'secondary_note': 'All raw gallery/current observations and revisions for included games are retained. Gallery labels are separate from explicit fresh-review labels; absence is not negative.',
    'identity_validation': {'full_pgn_positions_legally_replayed': positions_checked, 'all1048_exact_game_ply_SAN_UCI_FEN_and_fresh_labels_match': True,
        'rendered_board_proofs': 1041, 'development_rendered_board_proofs': 841, 'test_rendered_board_proofs': 200,
        'without_rendered_board_proof': missing, 'missing_note': 'Seven retained development records have exact PGN/SAN/ply identity but no captured rendered-board proof. Do not describe all1048 as board verified.'},
    'inputs': [{'artifact': relative(p), 'sha256': sha(p)} for p in inputs], 'source_database_sha256': source_db_hashes,
    'candidate_and_exclusion_provenance': 'source-hash-audit.json and protocol/; effective S castling addendum supersedes the initial executable hash.',
    'privacy': {'raw_http_headers_included': False, 'cookies_or_auth_material_included': False,
        'private_absolute_paths_included': False, 'raw_observation_json_preserved_exactly': True},
    'artifact_scope': 'Selected545games only; full PGNs once per game. Source corpora unchanged. No monthly archives, engine binaries, node_modules, predictions, or scores.'}
for key, value in manifest.items():
    db.execute('INSERT INTO metadata VALUES (?,?)', (key, json.dumps(value, sort_keys=True)))
db.commit()
assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
assert not db.execute('PRAGMA foreign_key_check').fetchall()
# Privacy guard across every textual SQL cell and every staged text artifact.
bad_path = re.compile(r'/(?:Users|private|var/folders|home|tmp)/')
bad_key = re.compile(r'"(?:cookies?|set-cookie|authorization|request_headers|response_headers|http_headers)"\s*:', re.I)
def clean(value):
    assert not bad_path.search(value), 'Private absolute path in staging'
    assert not bad_key.search(value), 'HTTP/auth field in staging'
    assert 'coffeechessandpizza' not in value.lower(), 'Logged-in owner identity in staging'
for table in ['metadata', 'games', 'positions', 'observations', 'labeled_moves']:
    for row in db.execute(f'SELECT * FROM {table}'):
        for value in row:
            if isinstance(value, str):
                clean(value)
db.close()
for path in OUT.rglob('*'):
    if path.is_file() and path.suffix != '.sqlite3':
        clean(path.read_text())
for p, expected in source_db_hashes.items():
    assert sha(WORKSPACE / p) == expected, 'Source database changed during read-only staging'
for source in sources:
    source.close()
manifest['artifact_sha256'] = {str(p.relative_to(OUT)): sha(p) for p in OUT.rglob('*') if p.is_file()}
write('manifest.json', manifest)
print(json.dumps({'complete': True, 'counts': counts, 'rendered_board_proofs': 1041, 'without_board_proof': 7,
    'new_secondary_fresh': 10, 'source_hash_checks': len(hash_checks), 'predictions_joined': False}))
