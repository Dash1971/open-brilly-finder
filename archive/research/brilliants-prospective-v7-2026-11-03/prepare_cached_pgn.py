"""Reuse existing header-only monthly selection and exact corpus PGN importer."""
import collections
import hashlib
import importlib.util
import io
import json
import pathlib
import re
import sqlite3
import sys
from datetime import datetime, timezone

sys.dont_write_bytecode = True
ROOT = pathlib.Path(__file__).resolve().parent
W = ROOT.parent.parent
def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result
m = module('prospective_v7_corpus', ROOT / 'corpus.py')
chess = m.chess
load = lambda p: json.loads(p.read_text())
save = lambda n, x: (ROOT / n).write_text(json.dumps(x, indent=2) + '\n')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
excluded = set(load(ROOT / 'exclude-games.json')['game_ids'])
known = set(load(ROOT / 'known-position-exclusions.json')['canonical_first_four'])
inventory = load(ROOT / 'INVENTORY.json')
nominees = load(ROOT / 'UNUSED-HISTORICAL-POOL.json')

def objects(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from objects(child)
    elif isinstance(value, list):
        for child in value:
            yield from objects(child)

raw = {}
for path in dict.fromkeys(source for row in nominees for source in row['source_artifacts']):
    for row in objects(load(W / path)):
        gid = str(row.get('game_id', ''))
        if gid in excluded or not isinstance(row.get('ply'), int):
            continue
        key = (gid, row['ply'])
        old = raw.get(key)
        if old is None or (not old.get('captured_at') and row.get('captured_at')):
            raw[key] = dict(row)
for path in sorted(ROOT.glob('*-gallery-topup-raw.json')):
    for row in objects(load(path)):
        gid = str(row.get('game_id', ''))
        if gid.isdigit() and gid not in excluded and isinstance(row.get('ply'), int):
            raw[(gid, row['ply'])] = dict(row) | {'source_artifacts': [str(path.relative_to(W))]}
for row in nominees:
    key = (row['game_id'], row['ply'])
    raw[key] = dict(row) | raw.get(key, {})
for (gid, ply), row in raw.items():
    row.update(game_id=gid, ply=ply, account=next((a for a in m.ACCOUNTS if a.lower() == str(row.get('account', '')).lower()), row.get('account')),
        source_type='gallery', label='!!', current_label='unknown', selected=False)
save('historical-pool-snapshot.json', {'created_at': m.now(), 'rows': list(raw.values()), 'scope': 'Historical nominations only; no new current labels.'})

conn = sqlite3.connect(ROOT / 'corpus.sqlite3')
conn.row_factory = sqlite3.Row
template_path = W / 'mute-chess-research/studies/brilliant-moves/corpus.sqlite3'
template = sqlite3.connect(f'file:{template_path}?mode=ro', uri=True)
for table in ['metadata', 'games', 'positions', 'observations']:
    sql = template.execute('SELECT sql FROM sqlite_master WHERE type="table" AND name=?', (table,)).fetchone()[0]
    conn.execute(sql.replace('CREATE TABLE ', 'CREATE TABLE IF NOT EXISTS ', 1))
conn.execute('''CREATE VIEW IF NOT EXISTS active_observations AS SELECT * FROM observations WHERE rowid IN
 (SELECT MAX(rowid) FROM observations GROUP BY game_id,ply,source_type,captured_at,source_link,account)''')
template.close()
# Metadata stays empty until root freezes PLAN; never call corpus.connect early.
needed = {gid for gid, _ in raw}
for path in inventory['input_sha256']:
    if not path.endswith('corpus.sqlite3'):
        continue
    source = sqlite3.connect(f'file:{W / path}?mode=ro', uri=True)
    source.row_factory = sqlite3.Row
    for game in source.execute('SELECT * FROM games'):
        if game['game_id'] in needed and not conn.execute('SELECT 1 FROM games WHERE game_id=?', (game['game_id'],)).fetchone():
            m.import_pgn(conn, game['pgn'], game['source_link'], game['captured_at'], {game['game_id']})
    source.close()

cache = ROOT / 'original-pgn'
cache.mkdir(exist_ok=True)
monthly = {}
for path in (W / 'research').rglob('original-pgn/*.pgn'):
    if ROOT in path.parents:
        continue
    if path.name not in monthly or path.stat().st_mtime_ns > monthly[path.name].stat().st_mtime_ns:
        monthly[path.name] = path
games_for_panel = {}
cache_receipts = []
for name, path in sorted(monthly.items()):
    meta_path = path.with_suffix('.response.json')
    if not meta_path.exists():
        continue
    meta = load(meta_path)
    destination = cache / name
    if not destination.exists():
        destination.symlink_to(path)
    receipt = {k: meta[k] for k in ['source_link', 'captured_at', 'sha256', 'bytes'] if k in meta}
    receipt.update(reused_local_file=str(path.relative_to(W)), original_manifest_sha256=sha(meta_path))
    destination.with_suffix('.response.json').write_text(json.dumps(receipt, indent=2) + '\n')
    archive_hash = sha(path)
    cache_receipts.append(dict(receipt, name=name, actual_sha256=archive_hash))
    text = path.read_text()
    stream = io.StringIO(text)
    while True:
        start = stream.tell()
        headers = chess.pgn.read_headers(stream)
        end = stream.tell()
        if headers is None:
            break
        gid = m.game_id_from(headers.get('Link')) or m.game_id_from(headers.get('Site'))
        if not gid or gid in excluded:
            continue
        account = next((a for a in m.ACCOUNTS if a.lower() in [headers.get('White', '').lower(), headers.get('Black', '').lower()]), None)
        if not account:
            continue
        rank = hashlib.sha256(f'mute-prospective-v7-panel-games:{gid}'.encode()).hexdigest()
        candidate = {'game_id': gid, 'account': account, 'ordering_hash': rank, 'monthly_artifact': str(path.relative_to(W)),
            'monthly_sha256': archive_hash, 'source_link': meta['source_link'], 'capture_timestamp': meta['captured_at'],
            'date': headers.get('UTCDate') or headers.get('Date'), 'pgn_slice_sha256': hashlib.sha256(text[start:end].encode()).hexdigest()}
        games_for_panel.setdefault(gid, candidate)
        if gid in needed and not conn.execute('SELECT 1 FROM games WHERE game_id=?', (gid,)).fetchone():
            m.import_pgn(conn, text[start:end], meta['source_link'], meta['captured_at'], {gid})
save('MONTHLY-CACHE-SNAPSHOT.json', {'archives': cache_receipts, 'no_downloads_in_this_step': True})
# All cached unused games are ranked; selecting500 waits for main/reserve exclusion.
save('PANEL-PGN-GAME-POOL.json', {'scope': 'Unreviewed public PGN games, no current labels or policy activations. Final500 selected only after primary/reserve game list freezes.',
    'games': sorted(games_for_panel.values(), key=lambda r: r['ordering_hash']), 'all571reviewed_games_excluded': True})
ready = []
pending = []
rejected = []
for (gid, ply), row in raw.items():
    p = conn.execute('SELECT * FROM positions WHERE game_id=? AND ply=?', (gid, ply)).fetchone()
    g = conn.execute('SELECT * FROM games WHERE game_id=?', (gid,)).fetchone()
    if not p or not g:
        pending.append({'game_id': gid, 'ply': ply, 'account': row.get('account')})
        continue
    if any(' '.join(p[k].split()[:4]) in known for k in ['fen_before', 'fen_after']):
        rejected.append({'game_id': gid, 'ply': ply, 'reason': 'known_before_or_after_position'})
        continue
    if (g['white'] if p['fen_before'].split()[1] == 'w' else g['black']).lower() != str(row.get('account', '')).lower():
        rejected.append({'game_id': gid, 'ply': ply, 'reason': 'account_not_mover'})
        continue
    placement = m.observed_board(row)
    if placement and placement != p['fen_after'].split()[0]:
        rejected.append({'game_id': gid, 'ply': ply, 'reason': 'gallery_board_mismatch'})
        continue
    if row.get('san') and row['san'] != p['san'] or row.get('uci') and row['uci'] != p['uci']:
        rejected.append({'game_id': gid, 'ply': ply, 'reason': 'SAN_UCI_mismatch'})
        continue
    headers = json.loads(g['headers_json'])
    namespace = re.search(r'/(live|daily)/', headers.get('Link', '') + ' ' + headers.get('Site', ''))
    if not namespace:
        rejected.append({'game_id': gid, 'ply': ply, 'reason': 'namespace_unknown'})
        continue
    value = dict(row) | {k: p[k] for k in ['san', 'uci', 'fen_before', 'fen_after']}
    value.update(game_type=namespace[1], pgn_sha256=g['pgn_sha256'], pgn_date=g['date'],
        source_link=f'https://www.chess.com/analysis/game/{namespace[1]}/{gid}/review?move={ply-1}')
    ready.append(value)
save('ELIGIBLE-PGN-POOL.json', {'ready': ready, 'pending': pending, 'rejected': rejected})
conn.close()
print(json.dumps({'ready_games': {a: len({r['game_id'] for r in ready if r['account'] == a}) for a in m.ACCOUNTS},
    'pending': pending, 'rejected': rejected, 'cached_panel_unreviewed_games': len(games_for_panel), 'monthly_cache_files': len(monthly)}))
