"""Two known external pawn-combination regressions; never fresh-test metrics."""
import hashlib, importlib.util, io, json, re, sqlite3, sys, time
from pathlib import Path
sys.dont_write_bytecode = True
sys.path.insert(0, '/private/tmp/brilly-research-deps')
import chess.engine, chess.pgn
HERE = Path(__file__).resolve().parent
IMPROVE = HERE.parent
ROOT = IMPROVE.parent.parent
OUT = HERE / 'fixture-forest-results.json'
assert not OUT.exists(), 'No automatic overwrite/retry'
spec = importlib.util.spec_from_file_location('saved_collector', ROOT / 'research/brilliants-final-2026-11-03/analysis.py')
collector = importlib.util.module_from_spec(spec); spec.loader.exec_module(collector)
sys.path.insert(0, str(IMPROVE / 'astra/v5/fresh-extractor'))
from extractor import extract_batch, score_fixed_forest, MODEL_PATH
definitions = json.loads((ROOT / 'mute-chess-research/studies/brilliant-moves/illustrative-cases.json').read_text())
monthly = ROOT / 'research/brilliants-600-2026-11-03/original-pgn/nelsi-2026-10.pgn'
chunks = re.split(r'(?=^\[Event )', monthly.read_text(), flags=re.M)
db = sqlite3.connect('file:' + str(ROOT / 'research/brilliants-pilot-2026-11-03/corpus.sqlite3') + '?mode=ro', uri=True)
cases = []
for d in definitions:
    gid = d['game_id']; pgn = next((p.strip() + '\n\n' for p in chunks if f'/live/{gid}' in p), None)
    source = str(monthly)
    if pgn is None:
        row = db.execute('SELECT pgn FROM games WHERE game_id=?', (gid,)).fetchone()
        assert row, 'Missing known fixture PGN'
        pgn = row[0]; source = 'pilot corpus game ' + gid
    game = chess.pgn.read_game(io.StringIO(pgn)); assert game and not game.errors
    board = game.board(); boards = {0: board.copy(stack=True)}
    for ply, move in enumerate(game.mainline_moves(), 1):
        if ply == d['ply']:
            assert board.fen() == d['fen_before'] and board.san(move) == d['moves'][0]
        board.push(move); boards[ply] = board.copy(stack=True)
        if ply >= d['ply']: break
    cases.append({'definition': d, 'pgn': pgn, 'pgn_sha256': hashlib.sha256(pgn.encode()).hexdigest(), 'pgn_source': source, 'boards': boards})
db.close()
plan = {'scope': 'Exactly two already-known outside-benchmark pawn-combination fixtures; not fresh or included in benchmark totals.', 'frozen_before_search_at': collector.now(), 'script_sha256': collector.digest(__file__), 'engine_sha256': collector.digest(collector.ENGINE), 'nodes': 300000, 'Threads': 1, 'Hash_MB': 64, 'maximum_positions': 6, 'forest_sha256': collector.digest(MODEL_PATH), 'cases': [{k: c[k] for k in ('definition','pgn_sha256','pgn_source')} for c in cases]}
(HERE / 'fixture-forest-plan.json').write_text(json.dumps(plan, indent=2) + '\n')
engine = chess.engine.SimpleEngine.popen_uci(collector.ENGINE)
engine.configure({'Threads': 1, 'Hash': 64})
requests = []; evidence = []
try:
    for case in cases:
        engine.configure({'Clear Hash': None}); session = object(); snapshots = []
        ply = case['definition']['ply']
        for index in [ply-2, ply-1, ply]:
            b = case['boards'][index]
            s = collector.search(engine, b, 300000, session)
            s.update(fen=b.fen(), position_ply=index, ec_material=collector.naive(b.fen()), pgn_sha256=case['pgn_sha256'])
            snapshots.append(s)
        requests.append({'pgn': case['pgn'], 'ply': ply, 'snapshots': snapshots})
        evidence.append({'game_id': case['definition']['game_id'], 'pgn': case['pgn'], 'pgn_sha256':case['pgn_sha256'], 'snapshots':snapshots})
finally:
    engine.quit()
model = json.loads(MODEL_PATH.read_text())
features = extract_batch(requests)
results = [{'game_id': case['definition']['game_id'], 'san':case['definition']['moves'][0], 'known_label':case['definition']['label'], 'forest':score_fixed_forest(f,model), 'features':f} for case,f in zip(cases, features)]
report = {'plan':plan,'evidence':evidence,'results':results,'completed_at':collector.now()}
OUT.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps([{k:r[k] for k in ('game_id','san','known_label','forest')} for r in results]))
