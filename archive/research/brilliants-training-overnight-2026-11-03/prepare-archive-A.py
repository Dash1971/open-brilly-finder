"""One bounded archive stratum, selected without review labels or model outputs."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, io, json, re, sys
sys.path.insert(0, '/private/tmp/brilly-research-deps')
import chess, chess.pgn

ROOT = Path(__file__).resolve().parent
W = ROOT.parents[1]
load = lambda p: json.loads(p.read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
rank = lambda gid: hashlib.sha256(('mute-overnight-archive-A-01:' + gid).encode()).hexdigest()
canon = lambda fen: ' '.join(chess.Board(fen).fen().split()[:4])
now = lambda: datetime.now(timezone.utc).isoformat()

if len(sys.argv) == 1:
    used = set(load(ROOT / 'EXCLUSIONS-FIRST-WAVE.json')['reviewed_game_ids'])
    for p in ROOT.glob('queue-*.json'):
        used.update(g['game_id'] for g in load(p).get('games', []))
    known = set(load(ROOT / 'ASSESSMENT-POSITION-EXCLUSIONS.json')['canonical_first_four'])
    found = {}
    for path in sorted((W / 'research').rglob('*.pgn')):
        if 'original-pgn' not in path.parts or path.name.split('-')[0].lower() not in {'nelsi', 'knvb'}:
            continue
        account = 'KNVB' if path.name.lower().startswith('knvb-') else 'nelsi'
        for block in re.split(r'(?=\[Event ")', path.read_text()):
            m = re.search(r'\[Link "[^"]*/(live|daily)/(\d+)"\]', block)
            if not m or m[2] in used or m[2] in found:
                continue
            found[m[2]] = (account, block.strip() + '\n', path, m[1])
    chosen = []
    for account in ['nelsi', 'KNVB']:
        chosen.extend(sorted((gid for gid, x in found.items() if x[0] == account), key=rank)[:15])
    games = []
    for gid in chosen:
        account, pgn, path, ns = found[gid]
        game = chess.pgn.read_game(io.StringIO(pgn))
        assert game and not game.errors
        board = game.board(); positions = []
        for ply, node in enumerate(game.mainline(), 1):
            move = node.move; before = board.fen(); san = board.san(move)
            capture = board.is_capture(move); check = board.gives_check(move)
            board.push(move); after = board.fen()
            positions.append(dict(ply=ply, san=san, uci=move.uci(), fen_before=before, fen_after=after,
                                  capture=capture, check=check, current_label='unknown',
                                  known_position_overlap=canon(before) in known or canon(after) in known))
        split = 'assessment' if int(hashlib.sha256(('mute-overnight-2026-11-03-v1:' + gid).encode()).hexdigest(), 16) % 5 == 0 else 'training'
        receipt = path.with_suffix('.response.json')
        source = load(receipt).get('source_link') if receipt.exists() else game.headers.get('Link')
        games.append(dict(account=account, game_id=gid, game_namespace=ns, split=split, split_assigned_at=now(),
                          source_kind='archive_static_offer', gallery_targets=[], anchor_is_assumed_brilliant=False,
                          pgn=pgn, pgn_sha256=hashlib.sha256(pgn.encode()).hexdigest(), pgn_source_link=source,
                          cached_source=str(path.relative_to(W)), pgn_headers=dict(game.headers),
                          total_plies=len(positions), positions=positions, current_review_labels_observed=False))
    output = ROOT / 'archive-A-screen-candidates.json'
    assert not output.exists(), 'Candidate frame already frozen'
    output.write_text(json.dumps(dict(prepared_at=now(), source_kind='archive_static_offer',
        selection='First 15 unassigned official archive games per account by fixed SHA256 rank, before current labels or model outputs.',
        games=games), indent=2) + '\n')
    print(json.dumps(dict(screen_candidates=len(games), available_archive_games=len(found), sha256=sha(output))))
else:
    candidate_path = ROOT / 'archive-A-screen-candidates.json'
    screen_path = ROOT / 'control-offers-A-archive-candidates.json'
    frame = load(candidate_path); screen = load(screen_path)
    assert screen['queue_sha256'] == sha(candidate_path)
    offers = {g['game_id']: [p['ply'] for p in g['positions'] if p['raw_legal_offer']]
              for g in screen['games'] if g['complete']}
    selected = []
    for account in ['nelsi', 'KNVB']:
        eligible = [g for g in frame['games'] if g['account'] == account and offers.get(g['game_id'])]
        assert len(eligible) >= 10, f'Insufficient legal-offer games for {account}'
        selected.extend(eligible[:10])
    selected.sort(key=lambda g: rank(g['game_id']))
    for g in selected:
        ply = offers[g['game_id']][0]; p = g['positions'][ply - 1]
        url = f'https://www.chess.com/analysis/game/{g["game_namespace"]}/{g["game_id"]}/review?move={ply-1}'
        g.update(primary_nomination_ply=ply, primary_nomination_san=p['san'], analysis_anchor_ply=ply,
                 analysis_anchor_san=p['san'], anchor_role='First static legal offer, not a known Brilliant',
                 source_link=url, review_url=url,
                 assessment_position_rule='ASSESSMENT-POSITION-EXCLUSIONS.json governs all assessment labels; split never changes.')
    output = ROOT / 'queue-A-archive-wave1.json'; assert not output.exists()
    counts = dict(games=len(selected), nominees=0, positions=sum(g['total_plies'] for g in selected),
                  training_games=sum(g['split'] == 'training' for g in selected),
                  assessment_games=sum(g['split'] == 'assessment' for g in selected))
    output.write_text(json.dumps(dict(prepared_at=now(), collector='overnight_collector_a',
        source_kind='archive_static_offer', control_sampling_version='static_offer_v3',
        selection='First 10 games per account in the frozen hash-ranked archive frame with at least one static legal offer; all current labels unknown.',
        source_frame_sha256=sha(candidate_path), static_screen_sha256=sha(screen_path),
        script_sha256=sha(Path(__file__)), games=selected, counts=counts), indent=2) + '\n')
    print(json.dumps(dict(file=output.name, sha256=sha(output), counts=counts)))
