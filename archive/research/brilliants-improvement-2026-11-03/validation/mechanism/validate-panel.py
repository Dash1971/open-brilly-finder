"""Study-only independent legal replay of proposed, still-unlabeled panel."""
import hashlib
import io
import json
import pathlib
import sqlite3
import sys

sys.path.insert(0, '/private/tmp/brilly-research-deps')
import chess
import chess.pgn

ROOT = pathlib.Path(__file__).resolve().parent
VAL = ROOT.parent
panel = json.loads((ROOT / 'panel-proposed.json').read_text())
selection = json.loads((ROOT / 'selection-input.json').read_text())
canon = lambda fen: ' '.join(chess.Board(fen).fen().split()[:4])
known = {x['canonical_first_four'] for x in json.loads((VAL / 'known-regression-fens.json').read_text())['positions']}
gallery = set()
protected, core = set(), set()
queue_hashes = {}
for account in ['nelsi', 'hansen', 'knvb', 'gothamchess', 'hikaru']:
    path = VAL / f'{account}-ui-queue.json'
    content = path.read_bytes()
    q = json.loads(content)
    queue_hashes[path.name] = hashlib.sha256(content).hexdigest()
    core.update(str(r['game_id']) for r in q['targets'])
    protected.update(str(r['game_id']) for r in q['reserves'][:8])
    for row in q['targets'] + q['reserves']:
        for key in ['fen_before', 'fen_after']:
            if row.get(key):
                gallery.add(canon(row[key]))
assert sorted(queue_hashes.values()) == sorted(selection['queue_sha256'].values())
old_ids = set(selection.get('old_games', []))
exclude_document = json.loads((VAL / 'exclude-games.json').read_text())
if isinstance(exclude_document, dict):
    old_ids.update(str(x) for x in exclude_document.get('game_ids', []))
else:
    old_ids.update(str(x) for x in exclude_document)
assert len(old_ids) == 325
db = sqlite3.connect(f'file:{VAL / "corpus.sqlite3"}?mode=ro', uri=True)
seen = set()
VALUES = {chess.PAWN:90, chess.KNIGHT:300, chess.BISHOP:300, chess.ROOK:500, chess.QUEEN:1000, chess.KING:0}
def physical(board, mover):
    return sum(VALUES[p.piece_type] * (1 if p.color == mover else -1) for p in board.piece_map().values())

counts = {category: 0 for category in panel['counts']}
for row in panel['cases']:
    gid = row['game_id']
    assert gid not in seen
    seen.add(gid)
    assert gid not in core | protected | old_ids | set(selection['already_opened_extra_games'])
    assert canon(row['fen_before']) not in known | gallery
    assert canon(row['fen_after']) not in known | gallery
    pgn, pgn_hash = db.execute('select pgn,pgn_sha256 from games where game_id=?', (gid,)).fetchone()
    assert hashlib.sha256(pgn.encode()).hexdigest() == pgn_hash == row['pgn_sha256']
    game = chess.pgn.read_game(io.StringIO(pgn))
    board = game.board()
    afters = {0:board.fen()}
    target = None
    for ply, move in enumerate(game.mainline_moves(), 1):
        assert move in board.legal_moves
        if ply == row['ply']:
            assert board.fen() == row['fen_before']
            assert board.san(move) == row['san']
            assert move.uci() == row['uci']
            target = board.turn
        board.push(move)
        afters[ply] = board.fen()
        if ply == row['ply']:
            assert board.fen() == row['fen_after']
            assert afters.get(ply - 2) == row['previous_own_after_fen']
            break
    assert target is not None
    row['mover_color'] = 'white' if target else 'black'
    row['label_status'] = 'unknown_not_yet_reviewed'
    row['pgn_and_witness_legally_validated'] = True
    features = row['features']
    for feature in ['mating_acceptance', 'cross_square_material_recoup']:
        proof = features.get(feature)
        if not proof or proof['status'] != 'witness':
            continue
        witness = chess.Board(row['fen_after'])
        line_san, trajectory = [], [physical(witness, target)]
        accepted_square = None
        for index, uci in enumerate(proof['line']):
            move = chess.Move.from_uci(uci)
            assert move in witness.legal_moves
            if index == 0:
                victim = witness.piece_at(move.to_square)
                assert victim and victim.color == target and victim.piece_type not in [chess.PAWN, chess.KING]
                accepted_square = move.to_square
            if feature == 'cross_square_material_recoup':
                assert witness.is_capture(move)
            line_san.append(witness.san(move))
            witness.push(move)
            trajectory.append(physical(witness, target))
        if feature == 'mating_acceptance':
            assert len(proof['line']) == 2 and witness.is_checkmate() and witness.turn != target
        else:
            assert trajectory == proof['material_trajectory']
            assert proof['initial_material'] == physical(chess.Board(row['fen_before']), target)
            assert trajectory[-1] >= proof['initial_material']
            assert all(amount < proof['initial_material'] for amount in trajectory[1:-1])
            assert move.to_square != accepted_square and witness.turn != target
        proof['line_san_ascii'] = line_san
        assert proof['probes'] <= 512
    counts[row['category']] += 1
assert counts == panel['counts']
panel['validation'] = {'all_selected_pgn_identities_valid': True, 'all_saved_conditional_lines_legal': True,
    'old_games_excluded':len(old_ids), 'old_canonical_positions_excluded':len(known),
    'core_games_excluded':len(core), 'protected_reserve_games_excluded':len(protected),
    'gallery_candidate_before_after_positions_excluded':len(gallery), 'one_case_per_game':True,
    'observations_tables_read':False, 'current_label_evidence_files_read':False}
(ROOT / 'panel-validated.json').write_text(json.dumps(panel, indent=2)+'\n')
print(json.dumps({'counts':counts,'validation':panel['validation']}))
