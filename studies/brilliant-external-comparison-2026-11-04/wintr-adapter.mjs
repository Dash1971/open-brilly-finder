// Study-specific adapter. Classifier policy is bundled directly from the pinned upstream checkout.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { pathToFileURL } from 'node:url';
import { execFileSync } from 'node:child_process';
const SOURCE='/private/tmp/mute-brilliant-repo-review/wintrchess-lib';
const PIN='0a63a69a544105e218b11f7459815bf195707776';
const RUNTIME='/private/tmp/mute-brilliant-repo-review/wintr-runtime';
const ESBUILD='/private/tmp/mute-bot-activity-source/lila-adapter/node_modules/esbuild/lib/main.js';
const sha=x=>crypto.createHash('sha256').update(x).digest('hex');
const canon=x=>x.split(' ').slice(0,4).join(' ');
const freezeSha=()=>sha(fs.readFileSync(new URL(import.meta.url)));
async function loadUpstream(){
 const commit=execFileSync('git',['-C',SOURCE,'rev-parse','HEAD'],{encoding:'utf8'}).trim();
 if(commit!==PIN)throw Error('Wintr commit differs from frozen pin');
 if(execFileSync('git',['-C',SOURCE,'status','--porcelain','--untracked-files=no'],{encoding:'utf8'}).trim())throw Error('Tracked Wintr source changed');
 const {build}=await import(pathToFileURL(ESBUILD));
 const shim=`export { classify, createClassifyContexts } from '${SOURCE}/src/classify/index.ts';\nexport { samples } from '${SOURCE}/src/classify/test/samples.ts';\nexport { chessFromFen } from '${SOURCE}/src/utils/fen.ts';\nexport { contextualizeMove } from '${SOURCE}/src/types/ContextualMove.ts';\nexport { getWinPercentLoss } from '${SOURCE}/src/engine/lib/analysis.ts';\nexport { parseUci, makeUci } from 'chessops';\nexport { parseSan } from 'chessops/san';\nexport { makeFen } from 'chessops/fen';\n`;
 const entry=path.join(RUNTIME,'entry.ts'),out=path.join(RUNTIME,'bundle.mjs');
 fs.writeFileSync(entry,shim);
 const result=await build({entryPoints:[entry],outfile:out,bundle:true,format:'esm',platform:'node',target:'node24',nodePaths:[path.join(RUNTIME,'node_modules')],alias:{'@':path.join(SOURCE,'src')},metafile:true,logLevel:'silent'});
 const sourceHashes={};
 for(const input of Object.keys(result.metafile.inputs))sourceHashes[path.resolve(input)]=sha(fs.readFileSync(path.resolve(input)));
 return {lib:await import(pathToFileURL(out)),build:{commit,source_hashes:sourceHashes,bundle_sha256:sha(fs.readFileSync(out)),esbuild:'0.28.2',dependencies:{chessops:'0.15.0','es-toolkit':'1.45.1','@badrap/result':'0.3.1'},adapter_sha256:freezeSha()}};
}
function evaluation(line){
 if(line.mate!=null&&Number.isFinite(line.mate))return {type:'mate',value:line.mate};
 if(line.cp!=null&&Number.isFinite(line.cp))return {type:'cp',value:line.cp};
 throw Error('missing_score');
}
function rawLines(snapshot){return Array.isArray(snapshot)?snapshot:snapshot?.lines;}
function convertLines(lib,fen,snapshot){
 const lines=rawLines(snapshot);
 if(!lines?.length)throw Error('missing_engine_lines');
 return lines.map((line,i)=>{
  const position=lib.chessFromFen(fen),moves=[];
  if(!line.moves?.length)throw Error('empty_pv');
  for(const uci of line.moves){
   const move=lib.parseUci(uci);
   if(!move||!position.isLegal(move))throw Error('illegal_pv');
   moves.push(lib.contextualizeMove(position,move));position.play(move);
  }
  const depth=line.depth??snapshot.depth;
  if(!Number.isInteger(depth)||depth<0)throw Error('missing_depth');
  return {depth,index:line.index??line.multipv??i+1,moves,evaluation:evaluation(line)};
 });
}
function evaluateWindow(lib,row,window){
 let diagnostics=[];
 try{
  const position=lib.chessFromFen(row.fen_before),move=lib.parseUci(row.uci);
  if(!move||!position.isLegal(move))throw Error('illegal_played_move');
  const after=position.clone();after.play(move);
  if(canon(lib.makeFen(after.toSetup()))!==canon(lib.makeFen(lib.chessFromFen(row.fen_after).toSetup())))throw Error('after_fen_mismatch');
  const previous=convertLines(lib,row.fen_before,window?.before),current=convertLines(lib,row.fen_after,window?.after);
  let lastWinPercentLoss;
  const prior=rawLines(window?.prior);
  if(prior?.length)lastWinPercentLoss=lib.getWinPercentLoss(evaluation(prior[0]),previous.find(l=>l.index===1).evaluation,position.turn==='white'?'black':'white');
  const opts={position,move,engineLines:{previous,current},lastWinPercentLoss};
  const ctx=lib.createClassifyContexts(opts);
  const originalLog=console.log;
  let classification;
  try{console.log=(...args)=>diagnostics.push(args.map(String).join(' '));classification=lib.classify({...opts,logs:true});}
  finally{console.log=originalLog;}
  // The only prior-dependent gate precedes Brilliant and is Miss. Its minimum
  // possible current loss is 0.1*0.7; below this a missing prior cannot affect Brilliant.
  const couldMiss=lastWinPercentLoss===undefined&&ctx.current.winPercentLoss>=0.07&&classification==='brilliant';
  return {status:couldMiss?'unavailable':'ok',award:couldMiss?null:classification==='brilliant',classification:couldMiss?null:classification,
   reason:couldMiss?'missing_prior_can_change_miss_gate':null,prior_missing:lastWinPercentLoss===undefined,last_win_percent_loss:lastWinPercentLoss??null,
   current_win_percent_loss:ctx.current.winPercentLoss,diagnostics};
 }catch(error){return {status:'unavailable',award:null,classification:null,reason:error.message,diagnostics};}
}
function combine(results){const a=Object.values(results).map(x=>x.award);return a.includes(false)?false:a.every(x=>x===true)?true:null;}
async function selfTest(lib,build){
 const results=[];
 for(const s of lib.samples){
  const position=lib.chessFromFen(s.fen),move=lib.parseSan(position,s.moveSan);
  const got=lib.classify({position,move,engineLines:s.lines,lastWinPercentLoss:s.lastWinPercentLoss});
  if(got!==s.expected)throw Error(`Upstream fixture failed: ${s.moveSan}: ${got} != ${s.expected}`);
  // Replay and round-trip every recorded line using the upstream UCI converter.
  const raw=xs=>({lines:xs.map(l=>({depth:l.depth,index:l.index,moves:l.moves.map(lib.makeUci),cp:l.evaluation.type==='cp'?l.evaluation.value:null,mate:l.evaluation.type==='mate'?l.evaluation.value:null}))});
  const after=position.clone();after.play(move);
  const previous=convertLines(lib,s.fen,raw(s.lines.previous));
  const current=convertLines(lib,lib.makeFen(after.toSetup()),raw(s.lines.current));
  const roundtrip=lib.classify({position,move,engineLines:{previous,current},lastWinPercentLoss:s.lastWinPercentLoss});
  if(roundtrip!==got)throw Error('Raw-line fixture roundtrip mismatch');
  const withoutPrior=lib.classify({position,move,engineLines:{previous,current}});
  const wrapped=evaluateWindow(lib,{fen_before:s.fen,fen_after:lib.makeFen(after.toSetup()),uci:lib.makeUci(move)},
   {before:raw(s.lines.previous),after:raw(s.lines.current),prior:null});
  if(wrapped.status!=='ok'||wrapped.classification!==withoutPrior)throw Error('Adapter wrapper fixture mismatch');
  results.push({san:s.moveSan,expected:s.expected,actual:got,raw_roundtrip:roundtrip,wrapper_without_prior:wrapped.classification});
 }
 const cp={type:'cp',value:100},zero={type:'cp',value:0};
 if(!(lib.getWinPercentLoss(cp,zero,'white')>0&&lib.getWinPercentLoss(cp,zero,'black')===0))throw Error('Score perspective failed');
 return {status:'pass',fixtures:results,white_pov_score_check:true,build};
}
async function main(){
 const {lib,build}=await loadUpstream();
 const args=process.argv.slice(2);
 if(args[0]==='--self-test'){
  const result=await selfTest(lib,build);if(args[1])fs.writeFileSync(args[1],JSON.stringify(result,null,2)+'\n');
  console.log(JSON.stringify({status:result.status,fixtures:result.fixtures.length,bundle_sha256:build.bundle_sha256}));return;
 }
 if(args[0]!=='--run'||!args[1]||!args[2])throw Error('Usage: --self-test [receipt.json] | --run INPUTS.jsonl OUTPUT.jsonl');
 if(fs.existsSync(args[2]))throw Error('Output exists; refusing rerun/overwrite');
 const input=fs.readFileSync(args[1],'utf8'),rows=input.trim().split('\n').map(JSON.parse),start=performance.now();
 const fd=fs.openSync(args[2],'wx');let count=0;
 try{
  for(const row of rows){
   if(performance.now()-start>300000)throw Error('300 second Wintr adapter limit');
   const windows=Object.fromEntries(['current','previous'].map(w=>[w,evaluateWindow(lib,row,row.windows[w])]));
   fs.writeSync(fd,JSON.stringify({key:row.key,windows,award:combine(windows)})+'\n');count++;
  }
 }finally{fs.closeSync(fd);}
 const receipt={status:'complete',cases:count,elapsed_seconds:(performance.now()-start)/1000,input_sha256:sha(input),output_sha256:sha(fs.readFileSync(args[2])),build};
 fs.writeFileSync(args[2]+'.receipt.json',JSON.stringify(receipt,null,2)+'\n');
 console.log(JSON.stringify({status:'complete',cases:count,elapsed_seconds:receipt.elapsed_seconds}));
}
await main();
