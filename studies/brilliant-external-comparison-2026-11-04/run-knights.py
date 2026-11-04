"""One bounded frozen-policy run; labels are never loaded by this process."""
import sys,json,hashlib,time,subprocess,selectors,collections,signal
from pathlib import Path
sys.path.insert(0,'/private/tmp/brilly-research-deps')
import chess,chess.engine
HERE=Path(__file__).resolve().parent
NODE='/private/tmp/node-v24.22.1-darwin-arm64/bin/node'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(name,obj):(HERE/name).write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n')
def main():
 protocol=json.loads((HERE/'PROTOCOL.json').read_text());freeze=json.loads((HERE/'KNIGHTS-FREEZE.json').read_text())
 for name,h in freeze['files'].items():assert sha(HERE/name)==h,(name,'changed')
 assert sha('/opt/homebrew/bin/stockfish')==protocol['engine_sha256']
 out=HERE/'KNIGHTS-PREDICTIONS.jsonl';assert not out.exists()
 rows=[json.loads(x) for x in (HERE/'INPUTS.jsonl').read_text().splitlines()]
 proc=subprocess.Popen([NODE,str(HERE/'knights-adapter.mjs')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=open(HERE/'knights-stderr.log','w'),text=True,bufsize=1)
 sel=selectors.DefaultSelector();sel.register(proc.stdout,selectors.EVENT_READ)
 engine=chess.engine.SimpleEngine.popen_uci('/opt/homebrew/bin/stockfish',timeout=10);engine.configure({'Threads':1,'Hash':64})
 start=time.monotonic();spent=0.;searches=0;cache={};counts=collections.Counter();deadline=start+1200
 ef=(HERE/'KNIGHTS-ENGINE-EVIDENCE.jsonl').open('x');of=out.open('x');completed=0
 def step(row,w,evidence):
  left=deadline-time.monotonic()
  if left<=0:return {'status':'unavailable','reason':'run_wall_cap'}
  r={**row,'historyUcis':row['historyUcis']+[row['uci']]}
  proc.stdin.write(json.dumps({'row':r,'window':w,'evidence':evidence},separators=(',',':'))+'\n');proc.stdin.flush()
  if not sel.select(min(15,left)):raise TimeoutError('native_step_timeout')
  line=proc.stdout.readline()
  if not line:raise RuntimeError('native_process_stopped')
  return json.loads(line)
 def board_for(row,fen):
  b=chess.Board(row['rootFen']);target=chess.Board(fen).fen();found=None
  if b.fen()==target:found=b.copy(stack=True)
  for u in row['historyUcis']+[row['uci']]:
   b.push_uci(u)
   if b.fen()==target:found=b.copy(stack=True)
  if found is not None:return found
  for m in list(b.legal_moves):
   b.push(m)
   if b.fen()==target:return b.copy(stack=True)
   b.pop()
  raise ValueError('request_not_on_exact_history_or_acceptance')
 def acquisition(row,request):
  nonlocal spent,searches
  board=board_for(row,request['fen']);roots=request.get('rootMoves');depth=request['depth'];mp=request.get('multiPv',2)
  identity=json.dumps([board.root().fen(),[m.uci() for m in board.move_stack],sorted(roots) if roots is not None else None,mp],separators=(',',':'))
  key=hashlib.sha256(identity.encode()).hexdigest()
  if key in cache:
   counts['cache_hits']+=1;record=cache[key]
   if record.get('evidence') and record['evidence']['analysis']['depth']>=depth:return record['evidence'],None
   return None,'cached_insufficient_depth_no_retry'
  if spent>=900 or time.monotonic()>=deadline:return None,'acquisition_budget_exhausted'
  rms=[chess.Move.from_uci(u) for u in roots] if roots is not None else None
  if rms is not None:assert len(set(rms))==len(rms) and all(m in board.legal_moves for m in rms)
  count=min(mp,len(rms) if rms is not None else board.legal_moves.count())
  assert count>=1
  pending=[];best=None;t=time.monotonic();engine.configure({'Clear Hash':None})
  try:
   limit=chess.engine.Limit(nodes=300000,time=max(.001,min(5,900-spent,deadline-time.monotonic())),depth=depth)
   with engine.analysis(board,limit,multipv=count,root_moves=rms,game=object()) as stream:
    for info in stream:
     if not all(k in info for k in ['score','pv','depth']):continue
     if not info['pv'] or info.get('upperbound') or info.get('lowerbound'):continue
     rank=info.get('multipv',1)
     if rank!=len(pending)+1:pending=[]
     if rank!=len(pending)+1:continue
     pending.append(info)
     if rank==count:
      if len({i['depth'] for i in pending})==1 and len({i['pv'][0] for i in pending})==count:
       lines=[]
       for idx,i in enumerate(pending,1):
        b=board.copy(stack=True)
        for m in i['pv']:assert m in b.legal_moves;b.push(m)
        val=i['score'].pov(board.turn)
        lines.append({'multipv':idx,'depth':i['depth'],'scoreCp':None if val.is_mate() else val.score(),'mate':val.mate() if val.is_mate() else None,'pv':[m.uci() for m in i['pv']]})
       first=lines[0]
       candidate={'kind':'live-position','fen':request['fen'],'analysis':{'depth':first['depth'],'bestmove':first['pv'][0],'scoreCp':first['scoreCp'],'mate':first['mate'],'pv':first['pv'],'candidates':lines}}
       if roots is not None:candidate['rootMoves']=roots
       if best is None or candidate['analysis']['depth']>=best['analysis']['depth']:best=candidate
      pending=[]
   reason=None if best and best['analysis']['depth']>=depth else 'node_or_time_cap_before_required_depth'
  except Exception as e:
   reason='engine_error:'+str(e);best=None
  elapsed=time.monotonic()-t;spent+=elapsed;searches+=1
  record={'id':key,'case':row['key'],'request':request,'rootFen':board.root().fen(),'historyUcis':[m.uci() for m in board.move_stack],'evidence':best,'reason':reason,'seconds':elapsed}
  cache[key]=record;ef.write(json.dumps(record,separators=(',',':'))+'\n');ef.flush()
  counts['searches']+=1;counts['search_'+str(reason)]+=1
  return (best,None) if reason is None else (None,reason)
 run_error=None
 try:
  for row in rows:
   windows={}
   for w in ['current','previous']:
    evidence=[];requests=[];result=None
    if time.monotonic()>=deadline:result={'status':'unavailable','reason':'run_wall_cap'}
    else:
     for stage in range(7):
      result=step(row,w,evidence)
      if result['status']=='complete':break
      request=result.get('request')
      if not request:break
      if stage==6:result['reason']='six_request_stage_cap';break
      e,reason=acquisition(row,request);requests.append({'request':request,'failure':reason})
      if reason:result['acquisition_failure']=reason;break
      if any(e['fen']==old['fen'] and e.get('rootMoves')==old.get('rootMoves') for old in evidence):result['reason']='repeated_scope_after_supplied_evidence';break
      evidence.append(e)
    result['award']=result.get('brilliant') if result['status']=='complete' else None
    result['acquisition_requests']=requests;windows[w]=result;counts[w+':'+result['status']+':'+str(result.get('reason'))]+=1
   values=[x['award'] for x in windows.values()];award=False if False in values else True if all(v is True for v in values) else None
   of.write(json.dumps({'key':row['key'],'windows':windows,'award':award},separators=(',',':'))+'\n');completed+=1
   if completed%50==0:
    of.flush();write('KNIGHTS-PROGRESS.json',{'cases':completed,'elapsed_seconds':time.monotonic()-start,'engine_seconds':spent,'searches':searches,'counts':dict(counts)})
    print(json.dumps({'cases':completed,'elapsed_seconds':round(time.monotonic()-start,1),'engine_seconds':round(spent,1),'searches':searches}),flush=True)
 except Exception as e:
  run_error=repr(e)
  # Finish bookkeeping without retries; unattempted cases remain unavailable.
  for row in rows[completed:]:
   windows={w:{'status':'unavailable','reason':'run_stopped','message':run_error,'award':None} for w in ['current','previous']}
   of.write(json.dumps({'key':row['key'],'windows':windows,'award':None})+'\n')
 finally:
  of.close();ef.close();proc.terminate();proc.wait(timeout=5);engine.quit()
  result={'status':'complete' if run_error is None else 'stopped_with_unresolved','cases':len(rows),'attempted_cases':completed,'error':run_error,'elapsed_seconds':time.monotonic()-start,'engine_seconds':spent,'searches':searches,'counts':dict(counts),'output_sha256':sha(out),'evidence_sha256':sha(HERE/'KNIGHTS-ENGINE-EVIDENCE.jsonl'),'freeze_sha256':sha(HERE/'KNIGHTS-FREEZE.json')}
  write('KNIGHTS-RECEIPT.json',result);print(json.dumps(result),flush=True)
if __name__=='__main__':main()
