"""Fixed-forest study extractor: legal PGN + saved engine windows ->75 features.
No fitting, labels, identities, old-case lookups, network or engine searches.
"""
import io,json,math,subprocess,sys
from pathlib import Path
sys.dont_write_bytecode=True
from feature_kernel import chess,extract_features
import chess.pgn
HERE=Path(__file__).resolve().parent
IMPROVE=HERE.parents[2]
NODE='/private/tmp/node-v24.22.1-darwin-arm64/bin/node'
LOADER=IMPROVE/'root/frozen-v4/node_modules/tsx/dist/loader.mjs'
MODEL_PATH=IMPROVE/'learning-v5/forest-diagnostic/forest-full.json'

def prepare(pgn,ply,snapshots):
 """Validate exact PGN history and ordered [prior-own-after,before,after] snapshots.
 Snapshot quality is explicit provenance, not inferred from score/depth. Earlier
 targets may have only two snapshots; previous iterations may be absent.
 """
 game=chess.pgn.read_game(io.StringIO(pgn))
 if game is None or game.errors:raise ValueError('Invalid PGN')
 if not isinstance(ply,int) or ply<1:raise ValueError('Invalid one-based target ply')
 board=game.board();fens=[board.fen()];moves=list(game.mainline_moves())
 if ply>len(moves):raise ValueError('Target beyond PGN')
 for m in moves[:ply]:
  if m not in board.legal_moves:raise ValueError('Illegal PGN move')
  board.push(m);fens.append(board.fen())
 indices=list(dict.fromkeys([max(0,ply-2),ply-1,ply]))
 if len(snapshots)!=len(indices):raise ValueError('Wrong snapshot count/order')
 for s,i in zip(snapshots,indices):
  if s['fen']!=fens[i]:raise ValueError('PGN/snapshot FEN mismatch')
  if not isinstance(s.get('quality'),str) or not s['quality']:raise ValueError('Explicit engine quality provenance required')
  for which in ['current','previous']:
   w=s.get(which)
   if w is None:continue
   if not isinstance(w.get('lines'),list) or not w['lines']:raise ValueError('Empty engine window')
   for line in w['lines']:
    if not isinstance(line.get('moves'),list) or not any(line.get(k) is not None for k in ['cp','mate']):raise ValueError('Malformed engine score/PV')
    pv=chess.Board(s['fen'])
    for uci in line['moves']:
     move=chess.Move.from_uci(uci)
     if move not in pv.legal_moves:raise ValueError('Illegal engine PV')
     pv.push(move)
 return {'fen_before':fens[ply-1],'fen_after':fens[ply],'uci':moves[ply-1].uci(),'snaps':[{**s,'current':s.get('current'),'previous':s.get('previous'),'terminal':bool(s.get('terminal',False))} for s in snapshots]}

def extract_batch(requests):
 inputs=[prepare(r['pgn'],r['ply'],r['snapshots']) for r in requests]
 proc=subprocess.run([NODE,'--no-warnings','--import',str(LOADER),str(HERE/'context.mts')],input=json.dumps(inputs),text=True,capture_output=True,check=True)
 contexts=json.loads(proc.stdout)
 return [extract_features(t,c) for t,c in zip(inputs,contexts)]

def score_fixed_forest(case,model):
 names=model['features'];base=names[:75]
 if len(names)!=150 or names[75:]!=[n+'__missing' for n in base] or len(model['trees'])!=64:raise ValueError('Unexpected frozen forest schema')
 scores={}
 for which in ['current','previous']:
  fs=case['windows'][which]['features']
  if sorted(fs)!=base:raise ValueError('Predictor schema/order mismatch')
  values=[float(fs[n]) if fs[n] is not None else None for n in base]+[float(fs[n] is None) for n in base]
  if any(v is not None and not math.isfinite(v) for v in values):raise ValueError('Nonfinite feature')
  probabilities=[]
  for tree in model['trees']:
   node=tree
   while node['kind']=='split':
    value=values[node['feature_index']]
    node=node['left' if value is None or value<=node['threshold'] else 'right']
   probabilities.append(node['raw_p'])
  scores[which]=sum(probabilities)/64
 award=all(scores[w]>=5/6 and case['windows'][w]['eligible'] for w in scores) and case['confidence_sufficient']
 return {'award':bool(award),'window_scores':scores,'threshold':5/6}

if __name__=='__main__':
 requests=json.load(sys.stdin);cases=extract_batch(requests);model=json.loads(MODEL_PATH.read_text())
 json.dump([{'features':c,'forest':score_fixed_forest(c,model)} for c in cases],sys.stdout,allow_nan=False)
