"""Frozen training-only saved-PV material trajectories. No engines or physical search."""
import sys,json,hashlib,io,sqlite3,time,resource,subprocess,collections,copy
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];E=ROOT.parent/'brilliants-improvement-2026-11-03/astra/v5/fresh-extractor'
sys.path.insert(0,str(E));import feature_kernel as fk
chess=fk.chess
import chess.pgn
VALUES=fk.VALUES
FEATURES=['pv_mapping_unknown','pv_best_accepts','pv_any_saved_accepts','pv_accepted_lines','pv_min_saved_plies','pv_any_terminal6','pv_horizon3_known','pv_horizon6_known','pv_debt3_min','pv_debt3_max','pv_debt6_min','pv_debt6_max','pv_recoup_by6_any','pv_first_recoup_ply_min','pv_cross_square_recoup_any','pv_victim_value_max','pv_accept_net_max']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def material(b,color):return sum(VALUES[p.piece_type]*(1 if p.color==color else -1) for p in b.piece_map().values())
def terminal(b):return b.is_checkmate() or b.is_stalemate() or b.is_insufficient_material()
def qualify(before,after):
 color=before.turn;credit=max(0,material(after,color)-material(before,color));budget=fk.OfferBudget();offers={}
 try:
  for m in list(after.generate_legal_captures()):
   victim=after.piece_at(m.to_square)
   if not victim or victim.piece_type in [1,6]:continue
   gain=fk.pk.mp.gain(after,m);a=after.copy(stack=True);a.push(m);net=gain-fk.exchange(a,m.to_square,budget)
   if net>credit+100:offers[m.uci()]={'victim_value':VALUES[victim.piece_type],'net':net,'square':m.to_square}
  return offers,False,budget.nodes
 except TimeoutError:return {},True,budget.nodes

def window_features(before,after,snapshot,offers,unknown):
 out={n:None for n in FEATURES};out['pv_mapping_unknown']=unknown
 if unknown or not snapshot or not snapshot.get('lines'):return out
 lines=snapshot['lines'][:2];accepted=[l for l in lines if l.get('moves') and l['moves'][0] in offers]
 out.update(pv_best_accepts=bool(lines[0].get('moves') and lines[0]['moves'][0] in offers),pv_any_saved_accepts=bool(accepted),pv_accepted_lines=len(accepted))
 if not accepted:return out
 color=before.turn;base=material(before,color);traces=[]
 for line in accepted:
  a=after.copy(stack=True);trajectory=[];first=None;cross=False;accept=offers[line['moves'][0]]
  for ply,u in enumerate(line['moves'][:6],1):
   m=chess.Move.from_uci(u)
   if m not in a.legal_moves:raise ValueError('Illegal savedPV:'+u)
   originalturn=a.turn==color;capture=a.is_capture(m);previousdebt=base-material(a,color);a.push(m);debt=base-material(a,color);trajectory.append(debt)
   if originalturn and previousdebt>0 and debt<=0:
    if first is None:first=ply
    cross=cross or (capture and m.to_square!=accept['square'])
   if terminal(a):break
  term=terminal(a);traces.append({'trajectory':trajectory,'terminal':term,'first':first,'cross':cross,'accept':accept})
 out.update(pv_min_saved_plies=min(len(t['trajectory']) for t in traces),pv_any_terminal6=any(t['terminal'] for t in traces),pv_victim_value_max=max(t['accept']['victim_value'] for t in traces),pv_accept_net_max=max(t['accept']['net'] for t in traces))
 for h in [3,6]:
  known=all(len(t['trajectory'])>=h or t['terminal'] for t in traces);out['pv_horizon'+str(h)+'_known']=known
  if known:
   debts=[t['trajectory'][min(h,len(t['trajectory']))-1] for t in traces];out['pv_debt'+str(h)+'_min']=min(debts);out['pv_debt'+str(h)+'_max']=max(debts)
 witnesses=[t['first'] for t in traces if t['first'] is not None];cross=any(t['cross'] for t in traces)
 out.update(pv_recoup_by6_any=True if witnesses else False if out['pv_horizon6_known'] else None,pv_first_recoup_ply_min=min(witnesses) if witnesses else None,pv_cross_square_recoup_any=True if cross else False if out['pv_horizon6_known'] else None)
 return out

def main():
 schema_path,expected,out=Path(sys.argv[1]),sys.argv[2],Path(sys.argv[3]);assert sha(schema_path)==expected;schema=json.loads(schema_path.read_text());assert FEATURES==schema['new_features'];assert not out.exists();out.mkdir(parents=True);start=time.monotonic();last=0.
 def guard():
  nonlocal last
  rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform=='darwin' else 1024)
  if time.monotonic()-start>=300 or rss>=512*1024*1024 or (ROOT/'STOP').exists():raise RuntimeError('Fixed augmentation time/memory/STOP limit')
  if time.monotonic()-last>=1:
   p=subprocess.run(['sysctl','-n','kern.memorystatus_vm_pressure_level'],capture_output=True,text=True,check=True);last=time.monotonic()
   if int(p.stdout)!=1:raise RuntimeError('Memory pressure not normal')
 def write(name,d):(out/name).write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')
 try:
  guard()
  for p,h in json.loads((E/'FREEZE.json').read_text())['sha256'].items():assert sha(p)==h
  assert sha(schema['input_path'])==schema['input_sha256']
  for p,h in schema['source_sha256'].items():guard();assert sha(p)==h
  data=json.loads(Path(schema['input_path']).read_text());original_names=list(data['predictors']);assert len(data['cases'])==3724 and len(original_names)==75;coverage=collections.Counter();cohorts=collections.defaultdict(list);pgn_hashes={};source_map={}
  for c in data['cases']:cohorts[c['cohort']].append(c)
  for cohort,cc in cohorts.items():
   mapping=schema['mapping'][cohort];snaps={}
   for p in mapping['banks']:snaps.update(json.loads(Path(p).read_text())['snapshots'])
   db=sqlite3.connect('file:'+mapping['pgn_database']+'?mode=ro',uri=True);bygame=collections.defaultdict(list)
   for c in cc:bygame[c['game_id']].append(c)
   for gid,targets in bygame.items():
    guard();row=db.execute('select pgn from games where game_id=?',(gid,)).fetchone();assert row;pgn=row[0];pgn_hashes[gid]=hashlib.sha256(pgn.encode()).hexdigest();game=chess.pgn.read_game(io.StringIO(pgn));assert game and not game.errors
    wanted={n for c in targets for n in [int(c['key'].split(':')[1])-1,int(c['key'].split(':')[1])]};b=game.board();boards={0:b.copy(stack=True)};moves={}
    for ply,m in enumerate(game.mainline_moves(),1):b.push(m);moves[ply]=m.uci();boards.update({ply:b.copy(stack=True)} if ply in wanted else {})
    for c in targets:
     guard();ply=int(c['key'].split(':')[1]);before,after=boards[ply-1],boards[ply];assert before.fen()==c['fen_before'] and after.fen()==c['fen_after'] and moves[ply]==c['uci'];snap=snaps[c['key']];assert snap['fen']==after.fen();offers,unknown,nodes=qualify(before,after);coverage['cases']+=1;coverage['mapping_unknown']+=unknown;coverage['qualifier_nodes']+=nodes;source_map[c['key']]={'cohort':cohort,'after_snapshot':c['key'],'pgn_sha256':pgn_hashes[gid]}
     for w in ['current','previous']:
      ss=snap.get(w) or (snap['current'] if snap.get('terminal') else None);fs=window_features(before,after,ss,offers,unknown);assert not set(fs)&set(c['windows'][w]['features']);c['windows'][w]['features'].update(fs)
      for n in ['pv_best_accepts','pv_any_saved_accepts','pv_horizon3_known','pv_horizon6_known','pv_recoup_by6_any']:coverage[w+':'+n+':'+str(fs[n])]+=1
   db.close();del snaps
  data['base_predictors']=original_names;data['predictors']=sorted(original_names+FEATURES);data['pv_schema_sha256']=expected
  # Explicitly verify untouched case metadata, guards and every old predictor.
  original=json.loads(Path(schema['input_path']).read_text())
  for a,b in zip(data['cases'],original['cases']):
   restored=copy.deepcopy(a)
   for w in ['current','previous']:
    for n in FEATURES:restored['windows'][w]['features'].pop(n)
   assert restored==b
  guard();write('training-augmented.json',data);write('COVERAGE.json',dict(coverage));write('SOURCE-MAP.json',source_map);guard();write('FREEZE.json',{'status':'complete','schema_sha256':expected,'script_sha256':sha(__file__),'input_sha256':schema['input_sha256'],'augmented_sha256':sha(out/'training-augmented.json'),'source_map_sha256':sha(out/'SOURCE-MAP.json'),'coverage_sha256':sha(out/'COVERAGE.json'),'case_order_metadata_and_base_features_unchanged':True,'elapsed_seconds':time.monotonic()-start,'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform=='darwin' else 1024)});print(json.dumps(dict(coverage)))
 except Exception as e:
  (out/'training-augmented.json').unlink(missing_ok=True);write('STOPPED.json',{'reason':str(e),'no_automatic_retry':True});raise
if __name__=='__main__':main()
