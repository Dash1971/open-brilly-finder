"""Freeze this study's reserved cases only after an explicit candidate-bound root GO."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, io, json, re, shutil, sqlite3, sys
sys.path.insert(0, '/private/tmp/brilly-research-deps')
import chess, chess.pgn

ROOT = Path(__file__).resolve().parent
sha = lambda data: hashlib.sha256(data).hexdigest()
read_json = lambda path: json.loads(path.read_text())
encoded = lambda value: (json.dumps(value, indent=2, ensure_ascii=False) + '\n').encode()
canonical = lambda fen: ' '.join(chess.Board(fen).fen().split()[:4])

def reserved(game_id):
    return int(sha(('mute-overnight-2026-11-03-v1:' + game_id).encode()), 16) % 5 == 0

def select_labels(rows, game_id):
    chosen = [r for r in rows if r['is_brilliant'] == 1 or r['negative_bucket'] == 'hard_ordinary']
    errors = [r for r in rows if r['negative_bucket'] == 'easy_error']
    if errors:
        chosen.append(min(errors, key=lambda r: sha(f'mute-overnight-assessment-v1:error:{game_id}:{r["ply"]}'.encode())))
    return sorted(chosen, key=lambda r: r['ply'])

def unique_keys(targets):
    keys = [(t['game_id'], t['ply']) for t in targets]
    assert len(keys) == len(set(keys)), 'Duplicate game/ply target'
    examples = [t['example_key'] for t in targets]
    assert len(examples) == len(set(examples)), 'Duplicate canonical position/move target'

def self_test():
    rows = [dict(ply=p, is_brilliant=int(p == 1), negative_bucket=b) for p, b in
            [(1, 'positive'), (2, 'hard_ordinary'), (3, 'easy_error'), (4, 'easy_error'), (5, 'other_explicit')]]
    picked = select_labels(rows, 'synthetic')
    assert [r['ply'] for r in picked[:2]] == [1, 2] and len(picked) == 3
    assert select_labels(rows[::-1], 'synthetic') == picked
    assert reserved('100') == (int(hashlib.sha256(b'mute-overnight-2026-11-03-v1:100').hexdigest(), 16) % 5 == 0)
    try:
        unique_keys([dict(game_id='1', ply=1, example_key='x')] * 2)
    except AssertionError:
        pass
    else:
        raise AssertionError('Duplicate guard failed')
    print(json.dumps({'self_test': 'PASS', 'reserved_data_read': False, 'engines_or_models_run': False}))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root-go', action='store_true')
    parser.add_argument('--candidate-freeze', type=Path)
    parser.add_argument('--candidate-sha256')
    parser.add_argument('--output-dir', type=Path)
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        self_test(); return
    if not args.root_go or not all([args.candidate_freeze, args.candidate_sha256, args.output_dir]):
        parser.error('Root GO, candidate freeze path/hash, and a NEW output directory are required before reading reserved data.')
    assert sha(args.candidate_freeze.read_bytes()) == args.candidate_sha256, 'Candidate freeze hash mismatch'
    output = args.output_dir.resolve()
    assert not output.exists(), 'Output directory already exists; never overwrite a frozen assessment'
    exclusion_paths = [ROOT / 'ASSESSMENT-POSITION-EXCLUSIONS.json', ROOT / 'EXCLUSIONS-FIRST-WAVE.json']
    exclusion_hashes = {p.name: sha(p.read_bytes()) for p in exclusion_paths}
    old_positions = set(read_json(exclusion_paths[0])['canonical_first_four'])
    old_games = set(read_json(exclusion_paths[1])['reviewed_game_ids'])
    cx = sqlite3.connect('file:' + str(ROOT / 'dataset.sqlite3') + '?mode=ro', uri=True)
    cx.row_factory = sqlite3.Row
    cx.execute('BEGIN')
    games = [dict(r) for r in cx.execute("SELECT g.*,s.source_kind,s.sampling_version FROM games g LEFT JOIN game_strata s USING(game_id) WHERE split='assessment' ORDER BY imported_at,game_id")]
    training_positions = {r[0] for r in cx.execute("SELECT before_key FROM positions JOIN games USING(game_id) WHERE split='training' UNION SELECT after_key FROM positions JOIN games USING(game_id) WHERE split='training'")}
    quarantined = {r[0] for r in cx.execute('SELECT game_id FROM quarantines')}
    packed = []; targets = []; excluded = []; sources = {}; selected_examples = set()
    for g in games:
        gid = g['game_id']; assert reserved(gid), 'Assessment split differs from original pre-label hash'
        rows = [dict(r) for r in cx.execute('SELECT l.*,p.san,p.uci,p.fen_before,p.fen_after,p.before_key,p.after_key FROM labels l JOIN positions p USING(game_id,ply) WHERE game_id=? ORDER BY ply', (gid,))]
        if gid in old_games or gid in quarantined:
            excluded.append(dict(game_id=gid, reason='old_reviewed_game' if gid in old_games else 'quarantined_game', labels=len(rows))); continue
        eligible = []
        for row in rows:
            reason = None
            if row['dataset_use'] != 'assessment': reason = row['dataset_use']
            elif row['before_key'] in old_positions or row['after_key'] in old_positions: reason = 'old_full_game_position_overlap'
            elif row['before_key'] in training_positions or row['after_key'] in training_positions: reason = 'new_training_full_game_position_overlap'
            elif row['is_brilliant'] not in (0, 1): reason = 'unknown_or_conflicting_binary_label'
            if reason: excluded.append(dict(game_id=gid, ply=row['ply'], reason=reason))
            else: eligible.append(row)
        sampled = select_labels(eligible, gid); selected = []
        for row in sampled:
            if row['example_key'] in selected_examples:
                excluded.append(dict(game_id=gid, ply=row['ply'], reason='duplicate_reserved_position_move_no_replacement'))
            else:
                selected.append(row); selected_examples.add(row['example_key'])
        selected_plies = {r['ply'] for r in sampled}
        excluded.extend(dict(game_id=gid, ply=r['ply'], reason='prespecified_label_stratum_or_error_subsample') for r in eligible if r['ply'] not in selected_plies)
        if not selected:
            excluded.append(dict(game_id=gid, reason='zero_eligible_selected_labels', labels=len(rows))); continue
        assert sha(g['pgn'].encode()) == g['pgn_sha256'], 'Full PGN hash mismatch'
        game = chess.pgn.read_game(io.StringIO(g['pgn'])); assert game and not game.errors
        header = dict(game.headers)
        assert g['source_account'].lower() in [header.get('White', '').lower(), header.get('Black', '').lower()]
        link = header.get('Link', g['source_link']); match = re.search(r'/(live|daily)/(\d+)', link)
        assert match and match[2] == gid, 'PGN game identity mismatch'
        board = game.board(); positions = {}
        for ply, node in enumerate(game.mainline(), 1):
            before = board.fen(); san = board.san(node.move); board.push(node.move)
            positions[ply] = (san, node.move.uci(), before, board.fen())
        stored = [dict(r) for r in cx.execute('SELECT * FROM positions WHERE game_id=? ORDER BY ply', (gid,))]
        assert len(stored) == len(positions) == g['total_plies']
        for row in stored:
            assert positions[row['ply']] == tuple(row[k] for k in ['san', 'uci', 'fen_before', 'fen_after']), 'Full mainline identity mismatch'
        for row in selected:
            assert positions[row['ply']] == tuple(row[k] for k in ['san', 'uci', 'fen_before', 'fen_after'])
            assert row['example_key'] == sha((canonical(row['fen_before']) + '\n' + row['uci']).encode())
            targets.append(dict(game_id=gid, ply=row['ply'], split='assessment', san=row['san'], uci=row['uci'], fen_before=row['fen_before'], fen_after=row['fen_after'], label=row['label'], is_brilliant=bool(row['is_brilliant']), negative_bucket=row['negative_bucket'], source_account=g['source_account'], source_kind=g['source_kind'], actual_mover=row['mover'], actual_mover_rating=row['mover_rating'], individual_rendered_board_verified=bool(row['rendered_board_verified']), source_types=json.loads(row['source_types']), example_key=row['example_key']))
        for source in cx.execute('SELECT DISTINCT source_file,source_sha256 FROM observations WHERE game_id=?', (gid,)):
            assert sha((ROOT / source[0]).read_bytes()) == source[1], 'Raw source changed'
            sources[source[0]] = source[1]
        assert sha((ROOT / g['complete_file']).read_bytes()) == g['complete_sha256']
        sources[g['complete_file']] = g['complete_sha256']
        packed.append(dict(game_id=gid, split='assessment', pgn=g['pgn'], pgn_sha256=g['pgn_sha256'], source_account=g['source_account'], source_kind=g['source_kind'], control_sampling_version=g['sampling_version'], game_namespace=match[1]))
    unique_keys(targets)
    assert len({g['game_id'] for g in packed}) == len(packed)
    journal = cx.execute('PRAGMA journal_mode').fetchone()[0]
    cx.rollback(); cx.close()
    for p in exclusion_paths:
        assert sha(p.read_bytes()) == exclusion_hashes[p.name], 'Exclusions changed during preparation'
    assert sha(args.candidate_freeze.read_bytes()) == args.candidate_sha256, 'Candidate freeze changed'
    snapshot_sha = sha(encoded(dict(games=packed, targets=targets, exclusions=excluded)))
    sampling_receipts = {name: sha((ROOT / name).read_bytes()) for name in ['PLAN.json', 'CONTROL-SAMPLING-AMENDMENT.json', 'ASSESSMENT-OVERLAP-AMENDMENT.json'] if (ROOT / name).exists()}
    freeze = dict(sampling_receipts_sha256=sampling_receipts, training_full_position_count=len(training_positions), training_full_positions_sha256=sha(encoded(sorted(training_positions))), frozen_at_utc=datetime.now(timezone.utc).isoformat(), candidate_freeze_sha256=args.candidate_sha256, script_sha256=sha(Path(__file__).read_bytes()), input_exclusion_sha256=exclusion_hashes, source_files_sha256=sources, sqlite_journal_mode=journal, logical_read_transaction_sha256=snapshot_sha, database_live_path_not_an_engine_input=True, selection='All Brilliant and hard ordinary labels currently eligible for assessment, plus one deterministic hashed error per game. Original game split; no quotas, replacements or model outputs.', counts=dict(completed_assessment_games=len(games), embedded_games=len(packed), targets=len(targets), excluded_records=len(excluded)))
    output.mkdir(parents=True); (output / 'source').mkdir()
    shutil.copyfile(Path(__file__), output / 'source' / Path(__file__).name)
    (output / 'INPUT-FREEZE.json').write_bytes(encoded(freeze))
    (output / 'EXCLUDED.json').write_bytes(encoded(excluded))
    receipts = []
    for start in range(0, len(packed), 20):
        chunk = packed[start:start + 20]; ids = {g['game_id'] for g in chunk}; chosen = [t for t in targets if t['game_id'] in ids]
        value = dict(split='assessment', input_freeze_sha256=sha(encoded(freeze)), games=chunk, targets=chosen, counts=dict(games=len(chunk), targets=len(chosen), brilliant=sum(t['is_brilliant'] for t in chosen), hard_ordinary=sum(t['negative_bucket']=='hard_ordinary' for t in chosen), error=sum(t['negative_bucket']=='easy_error' for t in chosen), unique_core_positions=len({(t['game_id'],p) for t in chosen for p in range(max(0,t['ply']-2),t['ply']+1)})))
        name = f'assessment-batch-{start // 20 + 1:02d}.json'; data = encoded(value)
        (output / name).write_bytes(data); receipts.append(dict(file=name, sha256=sha(data), games=len(chunk), targets=len(chosen)))
    (output / 'MANIFEST.json').write_bytes(encoded(dict(input_freeze_sha256=sha(encoded(freeze)), batches=receipts)))
    print(json.dumps(dict(output_dir=str(output), counts=freeze['counts'], batches=len(receipts), manifest_sha256=sha((output / 'MANIFEST.json').read_bytes()))))

if __name__ == '__main__':
    main()
