"""Only tiny synthetic arrays; no study data, fitted artifacts, or engine access."""
import os
for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','VECLIB_MAXIMUM_THREADS','MKL_NUM_THREADS']:os.environ[k]='1'
import sys,ast,json,math,hashlib,pathlib,datetime
sys.path.insert(0,'/private/tmp/mute-research-plot');import numpy as np
ROOT=pathlib.Path(__file__).resolve().parents[1];S=ROOT/'adapter/optimize-boosting.py';ns={'np':np,'math':math,'hashlib':hashlib};parsed=ast.parse(S.read_text());functions=[n for n in parsed.body if isinstance(n,ast.FunctionDef) and n.name!='main'];exec(compile(ast.Module(body=functions,type_ignores=[]),str(S),'exec'),ns);checks=[]
w=np.full(4,.25);y=np.array([1.,1.,-1.,-1.]);h=np.array([1.,-1.,-1.,-1.]);a,new,r=ns['boost_step'](w,y,h);expected=.25*math.log(3);assert a==expected and r['error']==.25;manual=np.array([.25*math.exp(-expected),.25*math.exp(expected),.25*math.exp(-expected),.25*math.exp(-expected)]);manual/=manual.sum();assert np.array_equal(new,manual) and new[1]>w[1];checks.append('signed update increases misclassifiedpositive weight; exact manual alpha/update')
nh=np.array([1.,1.,1.,-1.]);na,nw,nr=ns['boost_step'](w,y,nh);assert nr['error']==.25 and nw[2]>w[2] and na==expected;checks.append('misclassifiednegative weight increases with correct sign')
h=np.array([-1.,1.,1.,-1.]);assert ns['boost_step'](w,y,h)[0] is None;checks.append('errorhalf rejects and terminates without update')
a,new,r=ns['boost_step'](w,y,y);assert math.isfinite(a) and a>0 and r['stop']=='zero_error' and np.allclose(new,w);checks.append('zeroerror finiteclipped alpha accepted then terminate')
assert (ns['normalized_vote']([],np.zeros((2,150)),np.arange(2))==0).all();checks.append('zeroensemble finitezero score abstains')
leaf={'kind':'leaf','weighted_positive':1.,'weighted_negative':1.};assert ns['weak_sign'](leaf,np.zeros((1,150)),[0])[0]==-1;checks.append('weightedmajority tie negative')
def load(p):
 t=next(n for n in ast.parse(p.read_text()).body if isinstance(n,ast.ClassDef) and n.name=='Tree');scope={'np':np,'math':math,'guard':lambda:None};exec(compile(ast.Module(body=[t],type_ignores=[]),str(p),'exec'),scope);return scope['Tree']
Old=load(ROOT.parent/'brilliants-improvement-2026-11-03/learning-v5/forest-diagnostic/fit.py');Tree=load(ROOT/'adapter/capacity-tree.py');rng=np.random.default_rng(9147);base=['physical_unknown']+['f'+str(i) for i in range(74)];names=base+[n+'__missing' for n in base];raw=rng.normal(size=(192,75));raw[:,0]=0;X=np.column_stack([raw,np.zeros_like(raw)]);ids=np.repeat(np.arange(96),2);groups=np.repeat(np.arange(24),8);truth=raw[:,1]+raw[:,2]>0;y=np.where(truth,1.,-1.);ix=np.arange(192)
weights=np.where(truth,1.,5.)/2;old=Old(X,truth,ids,weights,names,groups,np.random.default_rng(52));new=Tree(X,truth,ids,weights,names,groups,np.random.default_rng(52),6,8,12);ot=old.fit(ix);nt=new.fit(ix);assert json.dumps(ot,sort_keys=True)==json.dumps(nt,sort_keys=True);checks.append('unchangedRF bitwise originalkernel parity')
adaptive=np.full(192,1/192);learners=[]
for n in range(4):
 trainer=Tree(X,truth,ids,adaptive,names,groups,np.random.default_rng(52+n),2,8,24);t=trainer.fit(ix);signs=ns['weak_sign'](t,X,ix);a,adaptive,rec=ns['boost_step'](adaptive,y,signs)
 if a is None:break
 learners.append({'alpha':a,'tree':t})
 if rec['stop']=='zero_error':break
assert learners
model=json.loads(json.dumps({'kind':'boosting','features':names,'learners':learners}));scores=ns['normalized_vote'](learners,X,ix)
for i in range(6):
 case={'windows':{w:{'features':{name:float(raw[2*i+j,k]) for k,name in enumerate(base)},'eligible':True} for j,w in enumerate(['current','previous'])},'confidence_sufficient':True};got=ns['score_model'](model,case,.8);assert np.array_equal(np.array(list(got['window_scores'].values())),scores[2*i:2*i+2]);assert got['award']==bool((scores[2*i:2*i+2]>=.8).all())
checks.append('synthetictraining votes equal JSONserialized inference/window decision')
case['windows']['current']['features']['physical_unknown']=True;assert not ns['score_model'](model,case,0)['award'];case['windows']['current']['features']['physical_unknown']=False;case['confidence_sufficient']=False;assert not ns['score_model'](model,case,0)['award'];checks.append('physicalunknown and confidence guard inference')
case['confidence_sufficient']=True;rf={'features':names,'trees':[nt]*64};sc=ns['score_model'](rf,case,.8);assert np.allclose(list(sc['window_scores'].values()),new.predict(nt,np.array([10,11])),atol=1e-14,rtol=0);checks.append('originalforest schema fallback inference parity')
# Execute the actual training/test isolation assertion extracted from nested boosting.
main=next(n for n in parsed.body if isinstance(n,ast.FunctionDef) and n.name=='main');boost=next(n for n in ast.walk(main) if isinstance(n,ast.FunctionDef) and n.name=='boosting');assertion=next(n for n in boost.body if isinstance(n,ast.Assert));guard=compile(ast.Module(body=[assertion],type_ignores=[]),'actualgroupguard','exec')
try:exec(guard,{'cg':np.array([0,0,1]),'train_cases':np.array([0]),'test_cases':np.array([1])});raise RuntimeError('Leakage guard failed')
except AssertionError:pass
exec(guard,{'cg':np.array([0,0,1]),'train_cases':np.array([0,1]),'test_cases':np.array([2])});checks.append('actualgroup guard rejects alias-group leakage')
hashfile=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();receipt={'created_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Tiny synthetic arithmetic and trees only; no real training optimization or seen654 access','passed':True,'checks':checks,'script_sha256':hashfile(S),'protocol_sha256':hashfile(ROOT/'boosting-optimization/PROTOCOL.json'),'test_sha256':hashfile(pathlib.Path(__file__))};(ROOT/'boosting-optimization/PREP-CHECKS.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
