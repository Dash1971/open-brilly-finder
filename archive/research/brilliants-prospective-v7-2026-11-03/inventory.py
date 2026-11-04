"""One bounded offline inventory. No labels, engines, network, or selection by outcomes."""
import collections
import hashlib
import json
import pathlib
import re
import sqlite3
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parent
W = ROOT.parent.parent
I = W / 'research/brilliants-improvement-2026-11-03'
OLD = [W / 'research' / n for n in ['brilliants-pilot-2026-11-03', 'brilliants-600-2026-11-03',
    'brilliants-additional-300-2026-11-03', 'brilliants-final-2026-11-03']]
OLD += [I / 'validation', I / 'future-validation-v5']
load = lambda p: json.loads(p.read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
rel = lambda p: str(p.relative_to(W))
inputs = {}

def read(p):
    inputs[rel(p)] = sha(p)
    return load(p)

def objects(v):
    if isinstance(v, dict):
        yield v
        for child in v.values():
            yield from objects(child)
    elif isinstance(v, list):
        for child in v:
            yield from objects(child)

def game(row):
    gid = row.get('game_id')
    if gid is None:
        source = row.get('source_link') or row.get('review_url') or row.get('game_url') or ''
        m = re.search(r'/game/(?:live|daily)/(\d+)', source)
        gid = m[1] if m else None
    return str(gid) if str(gid).isdigit() else None

excluded = collections.defaultdict(set)
fen_excluded = set()
canonical = lambda fen: ' '.join(fen.split()[:4])
for root in OLD:
    for p in root.glob('*exclude*games*.json'):
        d = read(p)
        for gid in d.get('game_ids', []):
            excluded[str(gid)].add('previous_exclusion_or_regression_list')
    for p in root.glob('*ui-queue.json'):
        d = read(p)
        for key in ['targets', 'reserves']:
            for row in d.get(key, []):
                gid = game(row)
                if gid:
                    excluded[gid].add('previous_frozen_target_or_reserved_game')
    for p in root.rglob('*panel-queue.json'):
        for row in objects(read(p)):
            gid = game(row)
            if gid:
                excluded[gid].add('previous_fixed_mechanism_panel')
    for p in (root / 'evidence').glob('*.json'):
        for row in objects(read(p)):
            if row.get('source_type') == 'fresh_review':
                gid = game(row)
                if gid:
                    excluded[gid].add('previous_explicit_fresh_review_including_secondary')
    known = root / 'known-regression-fens.json'
    if known.exists():
        for row in read(known).get('positions', []):
            if row.get('canonical_first_four'):
                fen_excluded.add(canonical(row['canonical_first_four']))

public = W / 'mute-chess-research/studies/brilliant-moves'
primary = read(public / 'moves.json')
assert len(primary) == 1048
for row in primary:
    excluded[str(row['game_id'])].add('previous1048_labeled_development_moves')
    for key in ['fen_before', 'fen_after']:
        fen_excluded.add(canonical(row[key]))
strict_excluded = excluded
observed_excluded = {gid: reasons - {'previous_frozen_target_or_reserved_game'} for gid, reasons in excluded.items()
    if reasons - {'previous_frozen_target_or_reserved_game'}}
strict_fen_excluded = set(fen_excluded)
excluded = observed_excluded
db_paths = list(dict.fromkeys([r / 'corpus.sqlite3' for r in OLD] + [public / 'corpus.sqlite3']))
cached = {}
positions = {}
for path in db_paths:
    if not path.exists():
        continue
    inputs[rel(path)] = sha(path)
    conn = sqlite3.connect(f'file:{path}?mode=ro', uri=True)
    conn.row_factory = sqlite3.Row
    for row in conn.execute('SELECT game_id,pgn_sha256,date,white,black,total_plies FROM games'):
        cached.setdefault(row['game_id'], {**dict(row), 'source_database': rel(path)})
    # Exclude every cached position in previously reviewed or reserved games.
    for row in conn.execute('SELECT game_id,ply,san,uci,fen_before,fen_after FROM positions'):
        if row['game_id'] in excluded:
            fen_excluded.update([canonical(row['fen_before']), canonical(row['fen_after'])])
        if row['game_id'] in strict_excluded:
            strict_fen_excluded.update([canonical(row['fen_before']), canonical(row['fen_after'])])
        positions.setdefault((row['game_id'], row['ply']), dict(row))
    conn.close()

pool = {}
for root in OLD:
    paths = set((root / 'evidence').glob('*gallery*.json')) | set(root.glob('*gallery*raw.json'))
    paths |= set(root.glob('*-candidate-pool.json'))
    if (root / 'cached-candidates-COLLECTOR-ONLY.json').exists():
        paths.add(root / 'cached-candidates-COLLECTOR-ONLY.json')
    for n in ['historical-pool-snapshot.json', 'ELIGIBLE-PGN-POOL.json']:
        if (root / n).exists():
            paths.add(root / n)
    for path in sorted(paths):
        for row in objects(read(path)):
            gid = game(row)
            account = row.get('account')
            ply = row.get('ply')
            if not gid or not account or not isinstance(ply, int):
                continue
            account = {'knvb': 'KNVB', 'gothamchess': 'GothamChess', 'hikaru': 'Hikaru'}.get(str(account).lower(), str(account).lower())
            if account not in ['nelsi', 'hansen', 'KNVB', 'GothamChess', 'Hikaru']:
                continue
            key = (account, gid, ply)
            if key not in pool:
                pool[key] = {'account': account, 'game_id': gid, 'ply': ply,
                    'category': row.get('sampling_category') or row.get('category') or row.get('categories'),
                    'source_artifacts': [], 'label_status': 'historical_gallery_nomination_only_current_label_unknown'}
            pool[key]['source_artifacts'].append(rel(path))

eligible = []
rejections = collections.Counter()
for key, row in pool.items():
    gid, ply = row['game_id'], row['ply']
    if gid in excluded:
        rejections['previous_game_or_frozen_reserve'] += 1
        continue
    position = positions.get((gid, ply))
    if position and any(canonical(position[k]) in fen_excluded for k in ['fen_before', 'fen_after']):
        rejections['known_before_or_after_position'] += 1
        continue
    row['cached_full_PGN_available'] = gid in cached
    row['PGN_move_identity_available'] = position is not None
    row['also_eligible_under_strict_never_use_prior_reserves'] = gid not in strict_excluded and not (position and any(canonical(position[k]) in strict_fen_excluded for k in ['fen_before', 'fen_after']))
    if position:
        row.update({k: position[k] for k in ['san', 'uci', 'fen_before', 'fen_after']})
    row['ordering_hash'] = hashlib.sha256(f'mute-prospective-v7:{gid}:{ply}'.encode()).hexdigest()
    eligible.append(row)
eligible.sort(key=lambda r: r['ordering_hash'])
counts = {}
strict_counts = {}
for account in ['nelsi', 'hansen', 'KNVB', 'GothamChess', 'Hikaru']:
    rows = [r for r in eligible if r['account'] == account]
    ready = [r for r in rows if r['cached_full_PGN_available'] and r['PGN_move_identity_available']]
    counts[account] = {'unused_historical_moves': len(rows), 'unused_unique_games': len({r['game_id'] for r in rows}),
        'cached_PGN_identity_ready_games': len({r['game_id'] for r in ready}),
        'missing_cached_PGN_games': len({r['game_id'] for r in rows if not r['cached_full_PGN_available']}),
        'shortfall_to20_cached_games': max(0, 20-len({r['game_id'] for r in ready})),
        'categories': dict(collections.Counter(str(r['category']) for r in rows))}
    strict = [r for r in rows if r['also_eligible_under_strict_never_use_prior_reserves']]
    strict_counts[account] = {'unused_unique_games':len({r['game_id'] for r in strict}),
        'cached_PGN_identity_ready_games':len({r['game_id'] for r in strict if r['cached_full_PGN_available'] and r['PGN_move_identity_available']})}
out = {'prepared_at_utc': datetime.now(timezone.utc).isoformat(), 'status': 'Offline inventory only; no plan freeze, fresh labels, engine searches, or policy predictions.',
    'proposed_main_cohort': '200primarymoves,100explicitBrilliant+100explicitnon,20/class/account, one positive nominee/game with matched controls; ranked reserves preselected before current labels.',
    'exclusion_policy': 'Observed union: explicit fresh-review records including secondary, old regression/exclusion lists, all1048moves/games, and all cached positions of excluded games. Never-opened prior frozen reserves and gallery-only unused nominations remain eligible; their strict alternative counts are separate.',
    'exclusion_games': len(excluded), 'exclusion_canonical_positions': len(fen_excluded),
    'cached_games_total': len(cached), 'historical_nomination_moves_total': len(pool), 'eligible_moves_total': len(eligible),
    'accounts': counts, 'strict_prior_reserved_also_excluded':{'games':len(strict_excluded),'positions':len(strict_fen_excluded),'accounts':strict_counts}, 'rejections': dict(rejections),
    'direct_change_panel': {'maximum_games': 30, 'separate_from_primary': True, 'status': 'Not selected: needs frozen-v6/v7 activation evidence on unreviewed games before Chess.com labels; no engine or activation scoring in this inventory.', 'quota_policy': 'Retain all explicit labels; no class quota or replacement by outcome.'},
    'coverage_limit': 'Only saved evidence/queue records can be audited offline. Root must confirm any opened-but-unsaved browser games are included before final freeze.',
    'input_sha256': inputs}
for name,value in [('INVENTORY.json',out),('exclude-games.json',{'game_ids': sorted(excluded), 'reasons': {k:sorted(v) for k,v in sorted(excluded.items())}}),('exclude-games-strict-including-unopened-reserves.json',{'game_ids':sorted(strict_excluded),'reasons':{k:sorted(v) for k,v in sorted(strict_excluded.items())}}),('known-position-exclusions.json',{'count':len(fen_excluded),'canonical_first_four':sorted(fen_excluded)}),('UNUSED-HISTORICAL-POOL.json',eligible)]:
    (ROOT/name).write_text(json.dumps(value,indent=2)+'\n')
print(json.dumps({'accounts':counts,'excluded_games':len(excluded),'excluded_positions':len(fen_excluded),'eligible_moves':len(eligible)}))
