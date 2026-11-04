import json,gzip,hashlib,sys,io,collections,time
from pathlib import Path
sys.path.insert(0,'/private/tmp/brilly-research-deps')
import chess,chess.pgn
HERE=Path(__file__).resolve().parent;WORK=HERE.parents[1]
STUDY=WORK/'mute-chess-research-overnight-2026-11-03/studies/brilliant-training-2026-11-03'
PACK=STUDY/'pv-trajectory-experiment/source-pack'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 start=time.monotonic();data=json.loads((STUDY/'data/training.json').read_text());cases={c['key']:c for c in data['cases']}
 preds={c['key']:c for c in json.loads((WORK/'research/brilliant-standard-learners-2026-11-04/PREDICTIONS.json').read_text())}
 assert len(cases)==len(preds)==3724 and cases.keys()==preds.keys()
 games={json.loads(l)['pgn_key']:json.loads(l) for l in gzip.open(PACK/'games.jsonl.gz','rt')}
 source=[json.loads(l) for l in gzip.open(PACK/'after-snapshots.jsonl.gz','rt')];assert len(source)==3724
 bybanks=collections.defaultdict(list)
 for x in source:bybanks[tuple(x['source_banks'])].append(x)
 output=[];metadata=[];bankhash={};counts=collections.Counter();pvcount=0
 for paths,rows in bybanks.items():
  snapshots={}
  for path in paths:
   bank=json.loads(Path(path).read_text());bankhash[path]=sha(path);snapshots.update(bank['snapshots'])
  bygame=collections.defaultdict(list)
  for x in rows:bygame[x['pgn_key']].append(x)
  for gamekey,items in bygame.items():
   g=games[gamekey];assert hashlib.sha256(g['pgn'].encode()).hexdigest()==g['pgn_sha256']
   game=chess.pgn.read_game(io.StringIO(g['pgn']));assert not game.errors
   board=game.board();initial=board.fen();boards=[board.copy()];history=[]
   for m in game.mainline_moves():history.append(m.uci());board.push(m);boards.append(board.copy())
   for x in items:
    c=cases[x['key']];pred=preds[c['key']];ply=int(c['key'].rsplit(':',1)[1]);gid=c['game_id']
    assert boards[ply-1].fen()==c['fen_before'] and boards[ply].fen()==c['fen_after'] and history[ply-1]==c['uci']
    ss={name:snapshots.get(f'{gid}:{p}') for name,p in [('before',ply-1),('after',ply),('prior',ply-2)]}
    assert ss['after']==x['after_snapshot']
    windows={}
    for w in ['current','previous']:
     windows[w]={}
     for name,p in [('before',ply-1),('after',ply),('prior',ply-2)]:
      snap=ss[name]
      if snap is None:windows[w][name]=None;counts[name+'_missing']+=1;continue
      assert snap['fen']==boards[p].fen()
      s=snap.get(w) or (snap.get('current') if snap.get('terminal') else None)
      windows[w][name]=({**s,"fen":boards[p].fen()} if s else None)
      if not s:counts[name+'_'+w+'_missing']+=1;continue
      roots=[]
      for line in s['lines']:
       b=boards[p].copy()
       for u in line['moves']:b.push_uci(u)
       pvcount+=1
       if line['moves']:roots.append(line['moves'][0])
      assert len(roots)==len(set(roots))
     for name in ['before','after']:
      s=windows[w][name]
      if not s:continue
      f=c['windows'][w]['features'];first=s['lines'][0];sign=1 if boards[ply-1].turn else -1;prefix='best' if name=='before' else 'after'
      for field in ['cp','mate']:
       actual=None if first.get(field) is None else sign*first[field]
       assert actual==f[prefix+'_'+field],(c['key'],w,name,field)
    output.append({'key':c['key'],'fen_before':c['fen_before'],'fen_after':c['fen_after'],'uci':c['uci'],'rootFen':initial,'historyUcis':history[:ply-1], 'priorFen':boards[ply-2].fen() if ply>=2 else None,'priorOwnBeforeFen':boards[ply-3].fen() if ply>=3 else None,'previousMove':history[ply-2] if ply>=2 else None,'windows':windows,'pgn_sha256':g['pgn_sha256']})
    assert c['truth']==pred['truth'] and c['group']==pred['group']
    metadata.append({'key':c['key'],'group':c['group'],'outer_fold':pred['outer_fold'],'truth':c['truth'],'cohort':c['cohort'],'negative_bucket':c['negative_bucket'],'eligible':pred['eligible'],'ec_sacrifice':c['windows']['current']['features']['ec_sacrifice'],'original_429_miss':bool(c['truth'] and pred['eligible'] and not pred['outer_awards']['custom_retuned']),'baseline_awards':pred['outer_awards']})
 order=lambda x:hashlib.sha256(('external-fixed-v1:'+x['key']).encode()).hexdigest()
 output.sort(key=order);metadata.sort(key=order)
 (HERE/'INPUTS.jsonl').write_text(''.join(json.dumps(x,separators=(',',':'))+'\n' for x in output))
 (HERE/'LABELS-AND-GROUPS.json').write_text(json.dumps(metadata,indent=2)+'\n')
 result={'status':'complete','cases':len(output),'groups':len({x['group'] for x in metadata}),'positives':sum(x['truth'] for x in metadata),'original_429_misses':sum(x['original_429_miss'] for x in metadata),'legal_pvs_verified':pvcount,'coverage':dict(counts),'training_sha256':sha(STUDY/'data/training.json'),'baseline_predictions_sha256':sha(WORK/'research/brilliant-standard-learners-2026-11-04/PREDICTIONS.json'),'bank_sha256':bankhash,'input_sha256':sha(HERE/'INPUTS.jsonl'),'metadata_sha256':sha(HERE/'LABELS-AND-GROUPS.json'),'script_sha256':sha(__file__),'elapsed_seconds':time.monotonic()-start}
 assert result['original_429_misses']==429
 (HERE/'INPUT-VERIFICATION.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='bank_sha256'}))
if __name__=='__main__':main()
