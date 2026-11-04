import io,json
from pathlib import Path
from extractor import chess,extract_batch,score_fixed_forest,MODEL_PATH
import chess.pgn
samples=[('move_castling','1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. O-O *',7),('move_en_passant','1. e4 a6 2. e5 d5 3. exd6 *',5),('move_promotion','[SetUp "1"]\n[FEN "7k/P7/8/8/8/8/8/4K3 w - - 0 1"]\n\n1. a8=Q+ *',1)]
requests=[]
for flag,pgn,ply in samples:
 game=chess.pgn.read_game(io.StringIO(pgn));b=game.board();fens=[b.fen()]
 for m in list(game.mainline_moves())[:ply]:b.push(m);fens.append(b.fen())
 requests.append({'pgn':pgn,'ply':ply,'snapshots':[{'fen':fens[i],'current':None,'previous':None,'terminal':False,'quality':'explicit-no-engine-test'} for i in dict.fromkeys([max(0,ply-2),ply-1,ply])]})
cases=extract_batch(requests);model=json.loads(MODEL_PATH.read_text())
for (flag,_,_),case in zip(samples,cases):
 assert case['windows']['current']['features'][flag] is True
 assert case['windows']['current']['eligible'] is False
 assert score_fixed_forest(case,model)['award'] is False
out={'scope':'Legal synthetic special-move fixtures with explicitly absent engine evidence; validates board flags and abstention, not calibrated forest decisions.','passed':[x[0] for x in samples]}
Path(__file__).with_name('special-move-checks.json').write_text(json.dumps(out,indent=2)+'\n');print(out)
