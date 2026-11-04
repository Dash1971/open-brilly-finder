// Study-only adapter: unchanged FullGameClassifier and SearchSnapshots, native UCI contract.
import {readFileSync,writeFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {FullGameClassifier} from '../sources/native/ui/analyse/src/noSweatFullReview.ts';
import {classify,annotation,isSacrifice,naiveMaterial} from '../sources/native/ui/analyse/src/noSweatClassify.ts';
import {SearchSnapshots} from '../sources/native/ui/analyse/src/noSweatSnapshots.ts';
import {legalUcis,position,terminalScore,after} from '../sources/native/ui/analyse/src/noSweatCore.ts';
const root=new URL('../',import.meta.url);const load=(url:URL)=>JSON.parse(readFileSync(url,'utf8'));
const hash=(url:URL)=>createHash('sha256').update(readFileSync(url)).digest('hex');
const smoke=process.argv[2]==='--smoke';
const inputUrl=smoke?undefined:new URL(process.argv[2],new URL('file://'+process.cwd()+'/'));
const outputUrl=smoke?new URL('adapter/SMOKE.json',root):new URL(process.argv[3],new URL('file://'+process.cwd()+'/'));
if(!smoke){const go=load(new URL('ENGINE-GO.json',root));if(!go.native_balanced || !go.browsers_closed || go.native_input_sha256!==hash(inputUrl!) || go.native_adapter_sha256!==hash(new URL(import.meta.url)))throw Error('Root native GO/hash binding absent');}
const freeze=load(new URL('FREEZE.json',root));for(const [path,entry]of Object.entries(freeze.files) as any)if(hash(new URL(path,root))!==entry.sha256)throw Error('Frozen source changed: '+path);
let games:any[];
if(smoke){const fen='rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';const nodes:any[]=[{ply:0,fen}];for(const uci of ['e2e4','e7e5'])nodes.push({ply:nodes.length,fen:after(nodes.at(-1).fen,uci),uci});games=[{game_id:'synthetic-start-e4-e5',account:'synthetic',nodes}];}
else games=load(inputUrl!).games;
if(games.length>(smoke?1:10))throw Error('Frozen whole-game cap exceeded');
const searchRows:any[]=[],gameRows:any[]=[];let totalPositions=0,engineMs=0;const started=Date.now();
const startedUTC=new Date().toISOString();let engineName='';
const assetUrl=new URL('sources/native-assets/',root);
const moduleFactory=(await import(new URL('sf_19_smallnet.js',assetUrl).href)).default;
const net=readFileSync(new URL('nn-61e7af4bb97d.nnue',assetUrl));if(createHash('sha256').update(net).digest('hex')!=='61e7af4bb97d51eeeb25d322916f86513b5cd3a827ce189c98c6e31946f99e5b')throw Error('NNUE hash mismatch');
const materialCache=new Map<string,number>();const material=(f:string)=>{if(materialCache.has(f))return materialCache.get(f)!;const n=naiveMaterial(f);materialCache.set(f,n);if(materialCache.size>4000)materialCache.delete(materialCache.keys().next().value!);return n;};
let status='complete',failure:string|undefined;
try{for(const game of games){
 if(totalPositions+game.nodes.length>1500)throw Error('1500-position cap before next whole game');
 const module=await moduleFactory({wasmMemory:new WebAssembly.Memory({initial:1536,maximum:32767,shared:true}),locateFile:(f:string)=>fileURLToPath(new URL(f,assetUrl)),mainScriptUrlOrBlob:fileURLToPath(new URL('sf_19_smallnet.js',assetUrl))});
 module.setNnueBuffer(net,0);let listener:(s:string)=>void=()=>{};module.listen=(s:string)=>{if(s.startsWith('id name '))engineName=s.slice(8);listener(s)};
 const waitCommand=(command:string,end:string,timeout:number)=>new Promise<void>((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('Native UCI startup timeout')),timeout);listener=s=>{if(s===end){clearTimeout(timer);resolve()}};module.uci(command)});
 try{
  await waitCommand('uci','uciok',45000);for(const c of ['setoption name Threads value 1','setoption name Hash value 16','setoption name UCI_Chess960 value false','setoption name UCI_AnalyseMode value true'])module.uci(c);
  await waitCommand('isready','readyok',45000);let session:symbol|undefined;
  const search=async(fen:string,signal:AbortSignal,depth:number,time:number,nextSession?:symbol)=>{
   if(signal.aborted)throw Error('Cancelled');if(engineMs>=1500000)throw Error('25-minute engine budget exhausted');
   if(++totalPositions>1500)throw Error('1500-position cap including confirmations');
   const terminal=terminalScore(fen);if(terminal){const review={current:{depth:99,lines:[{...terminal,moves:[]}]},terminal:true};searchRows.push({game_id:game.game_id,fen,terminal:true,review});return review;}
   const legal=new Set(legalUcis(fen)),count=Math.min(2,legal.size);const snapshots=new SearchSnapshots(legal,count,position(fen).turn==='white');
   const newSession=!nextSession || nextSession!==session;if(newSession){module.uci('ucinewgame');module.uci('setoption name Clear Hash')}session=nextSession;
   module.uci('setoption name MultiPV value '+count);await waitCommand('isready','readyok',45000);
   return await new Promise<any>((resolve,reject)=>{const start=performance.now();const timer=setTimeout(()=>{module.uci('stop');engineMs+=performance.now()-start;reject(Error('Stockfish review timed out or engine cap reached'))},Math.min(time+15000,1500000-engineMs));let lastInfo='';
    listener=s=>{if(s.startsWith('info ')){snapshots.add(s);lastInfo=s;}else if(s.startsWith('bestmove')){clearTimeout(timer);const elapsed=performance.now()-start;engineMs+=elapsed;const review=snapshots.completed?{current:snapshots.completed,previous:snapshots.previous}:undefined;searchRows.push({game_id:game.game_id,fen,depth,movetime:time,multiPV:count,new_session:newSession,elapsed_ms:elapsed,last_info:lastInfo,bestmove:s,review});if(!review)reject(Error('No complete MultiPV iteration'));else resolve(review)}};
    module.uci('position fen '+fen);module.uci(`go depth ${depth} movetime ${time}`);
   });
  };
  const decisions:any[]=[];const controller=new AbortController();
  const classifier=new FullGameClassifier({search,classify:async(input:any)=>{
   const v7=classify({...input,policy:'mute-brilliant-v7'},material),v6=classify({...input,policy:'mute-brilliant-v6'},material);const n=input.reviews.length,b=input.reviews[n-2],a=input.reviews[n-1],p=input.reviews[n-3];
   const color=position(input.positions[n-2]).turn;const ec=annotation(p?.current.lines[0],b.current,a.current.lines[0],color,input.move,isSacrifice(input.positions[n-2],input.positions[n-1],material));
   decisions.push({ply:input.ply,confirmation:!!input.confirmation,input,v7,v6,ec_direct:ec});return v7;
  }});
  const results=await classifier.run(game.nodes,controller.signal,()=>true,()=>{},{depth:14,movetime:1000});gameRows.push({game_id:game.game_id,account:game.account,complete:true,results:[...results],decisions});
 }finally{module.uci('quit')}
}}
catch(e){status='incomplete';failure=String(e)}
writeFileSync(outputUrl,JSON.stringify({scope:smoke?'Synthetic-only smoke; not study evidence':'SF19 smallnet native whole-game Balanced flow; v6/EC paired on the exact v7-requested evidence',started_at_utc:startedUTC,finished_at_utc:new Date().toISOString(),status,failure,engineName,gameCount:gameRows.length,searchCount:searchRows.length,engine_ms:engineMs,elapsed_ms:Date.now()-started,games:gameRows,searches:searchRows},null,2)+'\n');
console.log(JSON.stringify({status,failure,games:gameRows.length,searches:searchRows.length,engine_ms:engineMs,output:fileURLToPath(outputUrl)}));process.exit(status==='complete'?0:1);
