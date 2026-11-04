/** Study-local adapter. Invokes frozen Knight's Eye policy/core without changing rules. */
import fs from 'node:fs';
import crypto from 'node:crypto';
import readline from 'node:readline';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
import {Chess} from '/private/tmp/mute-brilliant-repo-review/chessjs-runtime/package/dist/esm/chess.js';
import {createChessAnalyzerCore} from '/private/tmp/mute-brilliant-repo-review/knights-runtime/package/dist/core.js';
import {createKnightsEyePolicy} from '/private/tmp/mute-brilliant-repo-review/knights-runtime/package/dist/policy.js';

export const CONFIG=Object.freeze({repository:'knights-eye-chess/move-classifier',commit:'c8183a6da88f3b5a2450dab35353dedd1d8d7a62',revision:48,candidateCount:2,verificationDepth:10,chessJs:'1.4.0',openingLookup:false});
const sha=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const nativeRoot='/private/tmp/mute-brilliant-repo-review/knights-runtime/package';
export function runtimeIdentity(){return {...CONFIG,files:Object.fromEntries(['dist/core.js','dist/policy.js','src/chess-analysis/analyze.ts','src/chess-analysis/knights-eye-policy.ts','src/chess-analysis/knights-eye-policy-runtime.js'].map(p=>[p,sha(`${nativeRoot}/${p}`)])),chessSha256:sha('/private/tmp/mute-brilliant-repo-review/chessjs-runtime/package/dist/esm/chess.js')};}
const scopeKey=(fen,roots)=>JSON.stringify([fen,roots?[...roots].sort():null]);
function normalizedFen(fen){return new Chess(fen).fen();}
function replay(row){
  if(!row.rootFen||!Array.isArray(row.historyUcis)||!row.historyUcis.length)throw Error('Exact history unavailable');
  const game=new Chess(row.rootFen),fens=[game.fen()];
  for(const u of row.historyUcis){game.move({from:u.slice(0,2),to:u.slice(2,4),...(u[4]?{promotion:u[4]}:{})});fens.push(game.fen());}
  assert.equal(fens.at(-2),normalizedFen(row.fen_before),'before FEN/replay mismatch');
  assert.equal(fens.at(-1),normalizedFen(row.fen_after),'after FEN/replay mismatch');
  if(row.uci)assert.equal(row.historyUcis.at(-1),row.uci,'move/replay mismatch');
  return {rootFen:fens[0],beforeFen:fens.at(-2),afterFen:fens.at(-1),priorFen:fens.length>=3?fens.at(-3):null};
}
export function convertSnapshot(snapshot,fen){
  if(!snapshot)return null;
  if(snapshot.fen)assert.equal(normalizedFen(snapshot.fen),fen,'snapshot FEN/replay mismatch');
  if(!Array.isArray(snapshot.lines)||!snapshot.lines.length)return null;
  const sign=fen.split(' ')[1]==='w'?1:-1;
  const candidates=snapshot.lines.map((line,i)=>{
    const hasCp=line.cp!==null&&line.cp!==undefined,hasMate=line.mate!==null&&line.mate!==undefined;
    assert.notEqual(hasCp,hasMate,'exactly one source score required');
    const mapped={multipv:i+1,depth:line.depth??snapshot.depth,scoreCp:hasCp?line.cp*sign:null,mate:hasMate?line.mate*sign:null,pv:[...(line.moves??line.pv??[])]};
    if(line.lowerbound)mapped.lowerbound=true;
    if(line.upperbound)mapped.upperbound=true;
    return mapped;
  });
  const depth=Math.min(snapshot.depth??Infinity,...candidates.map(c=>c.depth));
  return {kind:'live-position',fen,analysis:{...candidates[0],depth,bestmove:candidates[0].pv[0],candidates}};
}
function policyWithTrace(trace){
  const p=createKnightsEyePolicy(Chess);
  assert.equal(p.identity.revision,CONFIG.revision);
  return {...p,fork:()=>policyWithTrace(trace),brilliantComparison(context){const q=p.brilliantComparison?.(context);if(q)trace.push(structuredClone(q));return q;}};
}
function compactDecision(d){
  const v=d.sacrificeVerification;
  return {classification:d.classification,sacrifice:d.sacrifice,playedBest:d.playedBest,nearBest:d.nearBest,qualityLoss:d.qualityLoss,afterEp:d.afterEp,comparisonSource:d.comparisonSource,comparisonDepth:d.comparisonDepth,forced:d.forced,evasion:d.evasion,routine:d.routine,sacrificeCandidates:d.sacrificeCandidates,
    sacrificeVerification:v?{offerMode:v.offerMode,acceptedMove:v.acceptedMove,qualifyingMaterialOffer:v.qualifyingMaterialOffer,rawQualifyingMaterialOffer:v.rawQualifyingMaterialOffer,directRecoveryResidual:v.directRecoveryResidual,requiresSettledDeficit:v.requiresSettledDeficit,settledRecoveryResidual:v.settledRecoveryResidual,settledRecoveryOverBudget:v.settledRecoveryOverBudget,materialThreadOrigin:v.materialThreadOrigin,coverageComplete:v.coverageComplete,verifiedCandidateUcis:v.verifiedCandidateUcis,worstAcceptedEp:v.worstAcceptedEp,depth:v.depth,declinedRecaptureWitness:v.declinedRecaptureWitness,forcingCheckWitness:v.forcingCheckWitness,continuationComplete:v.continuationComplete,continuationStatus:v.continuationStatus,declineBestEp:v.declineBestEp,recaptureBestEp:v.recaptureBestEp}:null};
}
export async function classifyWindow({row,window='current',evidence=[]}){
  const started=performance.now();
  try{
    const replayed=replay(row),w=row.windows?.[window];
    if(!w)throw Error('Missing source window');
    const nativeEvidence=[],depths=[];
    for(const name of ['prior','before','after']){
      const fen=replayed[`${name}Fen`];if(!fen)continue;
      const board=new Chess(fen);if(board.isCheckmate()||board.isStalemate()||board.isInsufficientMaterial())continue;
      const item=convertSnapshot(w[name],fen);
      if(item){nativeEvidence.push(item);depths.push(item.analysis.depth);}
    }
    const depth=depths.length?Math.min(...depths):10;
    if(!Number.isInteger(depth)||depth<1)throw Error('Invalid source depth');
    const admittedMap=new Map(nativeEvidence.map(e=>[scopeKey(e.fen,e.rootMoves),e]));
    for(const extra of evidence){
      const k=scopeKey(extra.fen,extra.rootMoves);
      if(admittedMap.has(k))throw Error('Supplemental evidence must not overwrite original unrestricted source scope');
      admittedMap.set(k,extra);
    }
    const trace=[],policy=policyWithTrace(trace);
    const core=createChessAnalyzerCore(Chess,undefined,policy,{searchPolicy:{candidateCount:CONFIG.candidateCount,verificationDepth:CONFIG.verificationDepth}});
    const result=await core.classifySuppliedEvidence({startFen:replayed.rootFen,history:row.historyUcis,depth,book:false,evidence:[...admittedMap.values()]});
    const common={key:row.key,window,requestedOrdinaryDepth:depth,nativeStatus:result.status,policy:CONFIG,elapsedMs:performance.now()-started};
    if(result.status!=='complete')return {...common,status:'unavailable',reason:result.reason,message:result.message,request:result.request??null};
    const decision=compactDecision(result.decision);
    // The native API may complete ordinarily when optional Brilliant pair proof is missing.
    // For this comparison, expose that missing proof rather than silently treating it as a full negative.
    const missingPair=trace.find(q=>{const comparison=result.context?.comparisonAnalysis;return !comparison||comparison.candidates?.length!==q.multiPv||!policy.prepared.admitClassificationComparison(result.context,q,comparison);});
    if(missingPair)return {...common,status:'unavailable',reason:'optional-brilliant-pair-unresolved',request:missingPair,nativeDecision:decision};
    return {...common,status:'complete',brilliant:result.decision.classification==='brilliant',decision};
  }catch(error){return {key:row?.key,window,status:'unavailable',reason:'adapter-input-invalid',message:String(error.message),elapsedMs:performance.now()-started};}
}

async function selfTest(){
  const white='4k3/8/8/8/8/8/8/4K2R w - - 0 1',black='4k3/8/8/8/8/8/8/4K2R b - - 0 1';
  const snap={depth:12,lines:[{cp:123,mate:null,moves:['e1d1']}]};
  assert.equal(convertSnapshot(snap,white).analysis.scoreCp,123);
  assert.equal(convertSnapshot({...snap,lines:[{cp:123,mate:null,moves:['e8d8']}]},black).analysis.scoreCp,-123);
  assert.equal(convertSnapshot({depth:12,lines:[{cp:null,mate:-3,moves:['e8d8']}]},black).analysis.mate,3);
  const board=new Chess(),root=board.fen();board.move('e4');
  const row={key:'synthetic-only',rootFen:root,historyUcis:['e2e4'],uci:'e2e4',fen_before:root,fen_after:board.fen(),windows:{current:{before:{depth:12,lines:[{cp:30,mate:null,moves:['e2e4']},{cp:20,mate:null,moves:['d2d4']}]},after:{depth:12,lines:[{cp:30,mate:null,moves:['e7e5']},{cp:20,mate:null,moves:['c7c5']}]}}}};
  const result=await classifyWindow({row});assert.equal(result.status,'complete',JSON.stringify(result));assert.equal(result.brilliant,false);
  const bad=structuredClone(row);bad.windows.current.after.lines[0].moves=['e2e4'];
  const invalid=await classifyWindow({row:bad});assert.equal(invalid.status,'unavailable');assert.equal(invalid.reason,'incomplete-evidence');
  return {status:'pass',checks:['white cp direction','black cp direction','black mate direction','exact legal replay with native ordinary decision','illegal source PV rejected'],identity:runtimeIdentity()};
}
if(process.argv[1]&&fileURLToPath(import.meta.url)===process.argv[1]){
  if(process.argv.includes('--identity'))console.log(JSON.stringify(runtimeIdentity()));
  else if(process.argv.includes('--self-test'))console.log(JSON.stringify(await selfTest()));
  else {for await(const line of readline.createInterface({input:process.stdin,crlfDelay:Infinity})){if(!line.trim())continue;try{const input=JSON.parse(line);console.log(JSON.stringify(await classifyWindow(input)));}catch(error){console.log(JSON.stringify({status:'unavailable',reason:'adapter-message-invalid',message:String(error.message)}));}}}
}
