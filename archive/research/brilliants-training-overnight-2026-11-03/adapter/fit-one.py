"""One fixed forest, trusted Tree AST only. Hash-bound root GO; no assessment I/O."""
import os
for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','VECLIB_MAXIMUM_THREADS','MKL_NUM_THREADS']:os.environ[k]='1'
import sys,json,hashlib,ast,math,time,resource,subprocess,datetime
from pathlib import Path
sys.dont_write_bytecode=True;sys.path.insert(0,'/private/tmp/mute-research-plot');import numpy as np
ROOT=Path(__file__).resolve().parents[1];KERNEL=ROOT.parent/'brilliants-improvement-2026-11-03/learning-v5/forest-diagnostic/fit.py';KH='005050c4c2f9d90178464e007de7112fc77a9f4c2b8bd10c4a8058655c73c18f'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
input_path,go_path,out=map(Path,sys.argv[1:]);go=json.loads(go_path.read_text());plan=ROOT/'EXPERIMENT-PLAN.json'
assert go['fit_authorized'] and go['all_research_browser_tabs_closed'] and go['candidate_count']==1
assert go['training_sha256']==sha(input_path) and go['script_sha256']==sha(__file__) and go['plan_sha256']==sha(plan) and sha(KERNEL)==KH
assert not out.exists();out.mkdir(parents=True);start=time.monotonic();last=0.;deadline=datetime.datetime.fromisoformat(json.loads(plan.read_text())['deadline_utc'].replace('Z','+00:00')).timestamp()
def guard():
 global last
 if time.monotonic()-start>=180 or resource.getrusage(resource.RUSAGE_SELF).ru_maxrss>=512*1024*1024 or time.time()>=deadline or (ROOT/'STOP').exists():raise RuntimeError('Fixed fit time/memory/deadline/STOP limit')
 if time.monotonic()-last>=1:
  p=subprocess.run(['sysctl','-n','kern.memorystatus_vm_pressure_level'],capture_output=True,text=True,check=True);last=time.monotonic()
  if int(p.stdout)!=1:raise RuntimeError('Memory pressure not normal')
try:
 guard();assert subprocess.run(['pgrep','-x','stockfish'],capture_output=True).returncode!=0
 source=ast.parse(KERNEL.read_text());tree=next(n for n in source.body if isinstance(n,ast.ClassDef) and n.name=='Tree');exec(compile(ast.Module(body=[tree],type_ignores=[]),str(KERNEL),'exec'),globals())
 data=json.loads(input_path.read_text());cases=data['cases'];base=data['predictors'];names=base+[n+'__missing' for n in base];assert len(names)==150
 windows=[c['windows'][w] for c in cases for w in ['current','previous']]
 X=np.array([[float(r['features'][n]) if r['features'][n] is not None else np.nan for n in base]+[float(r['features'][n] is None) for n in base] for r in windows]);assert not np.isinf(X).any()
 y=np.repeat(np.array([c['truth'] for c in cases],dtype=bool),2);ids=np.repeat(np.arange(len(cases)),2);eligible=np.array([r['eligible'] for r in windows],dtype=bool)
 group_order=sorted({c['group'] for c in cases});index={g:i for i,g in enumerate(group_order)};groups=np.repeat(np.array([index[c['group']] for c in cases]),2)
 eligible_counts=np.bincount(ids[eligible],minlength=len(cases));weights=np.array([(5 if not y[i] else 1)/max(1,eligible_counts[ids[i]]) for i in range(len(windows))]);train=np.flatnonzero(eligible);trees=[];boots=[]
 for number in range(64):
  guard();rng=np.random.default_rng(np.random.SeedSequence([20261103,5,number]));draws=rng.choice(np.arange(len(group_order)),size=len(group_order),replace=True);mult=np.bincount(draws,minlength=len(group_order));ix=np.repeat(train,mult[groups[train]])
  assert np.array_equal(np.bincount(ix,minlength=len(windows))[train],mult[groups[train]])
  trees.append(Tree(X,y,ids,weights,names,groups,rng).fit(ix));boots.append(mult.tolist())
 def inspect(n,depth=0):
  if n['kind']=='leaf':assert n['distinct_moves']>=8 and 0<=n['raw_p']<=1
  else:
   assert depth<6 and 0<=n['feature_index']<150;inspect(n['left'],depth+1);inspect(n['right'],depth+1)
 for t in trees:inspect(t)
 guard();model={'features':names,'trees':trees};mp=out/'forest-candidate.json';mp.write_text(json.dumps(model,indent=2,allow_nan=False)+'\n')
 receipt={'scope':'One experimental fullfit; no assessment predictions or promotion','training_sha256':sha(input_path),'kernel_sha256':KH,'script_sha256':sha(__file__),'go_sha256':sha(go_path),'plan_sha256':sha(plan),'model_sha256':sha(mp),'cases':len(cases),'eligible_windows':len(train),'groups':len(group_order),'trees':64,'threshold':5/6,'elapsed_seconds':time.monotonic()-start,'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss};(out/'MODEL-FREEZE.json').write_text(json.dumps(receipt,indent=2)+'\n');(out/'bootstrap.json').write_text(json.dumps({'group_order':group_order,'multiplicities':boots})+'\n');print(json.dumps(receipt))
except Exception as e:
 (out/'STOPPED.json').write_text(json.dumps({'reason':str(e),'no_automatic_retry':True})+'\n');raise
