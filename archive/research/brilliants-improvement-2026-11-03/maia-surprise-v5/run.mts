// One existing-runtime preflight, then at most20 authorized local inferences.
import fs from 'node:fs';
import crypto from 'node:crypto';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {position,legalUcis,encodeHistory,policyIndex} from '../root/frozen-v4/core.ts';
const dir=new URL('.',import.meta.url),workspace=new URL('../../../',dir);
const read=(u:URL)=>JSON.parse(fs.readFileSync(u,'utf8'));
const hash=(u:URL)=>crypto.createHash('sha256').update(fs.readFileSync(u)).digest('hex');
const plan=read(new URL('PLAN.json',dir)),inputs=read(new URL('inputs.json',dir));
const source=(name:string)=>new URL(plan.sources[name].path,workspace);
for(const spec of Object.values(plan.sources) as any[])if(hash(new URL(spec.path,workspace))!==spec.sha256)throw Error('Pinned source changed');
const vocabulary=read(source('vocabulary')),reverse=read(source('vocabulary_reversed'));
const mirror=(uci:string)=>uci[0]+(9-Number(uci[1]))+uci[2]+(9-Number(uci[3]))+uci.slice(4);
if(Object.keys(vocabulary).length!==4352)throw Error('Wrong policy vocabulary');
for(const [uci,index]of Object.entries(vocabulary)){
 if(policyIndex(uci,false)!==index||policyIndex(mirror(uci),true)!==index||reverse[index as any]!==uci||mirror(mirror(uci))!==uci)throw Error('Vocabulary/mirroring/promotion mismatch');
}
const fixture=read(source('encoder_fixtures'));
for(const f of fixture){
 const tokens=encodeHistory(f.historyFens,f.history);
 const sha=crypto.createHash('sha256').update(new Uint8Array(tokens.buffer)).digest('hex');
 if(sha!==f.tokensSha256)throw Error('Existing native history encoder fixture mismatch');
}
const roles=['pawn','knight','bishop','rook','queen','king'];
function singleBoard(fen:string){
 const pos=position(fen),black=pos.turn==='black',tokens=new Float32Array(64*12);
 for(const [sq,piece]of pos.board){
  const target=black?sq^56:sq;
  tokens[target*12+roles.indexOf(piece.role)+(piece.color===pos.turn?0:6)]=1;
 }
 return tokens;
}
for(const c of inputs.cases){
 if(c.real_history_fens.length!==8||c.real_history_fens.at(-1)!==c.fen_before)throw Error('Real history incomplete');
 if(JSON.stringify(legalUcis(c.fen_before).sort())!==JSON.stringify(c.legal_uci))throw Error('Independent legal move mask differs');
 const legacy=singleBoard(c.fen_before),native=encodeHistory([c.fen_before],false);
 for(let square=0;square<64;square++)for(let role=0;role<12;role++)if(legacy[square*12+role]!==native[square*97+84+role])throw Error('Single-board mirror encoder differs');
}
fs.writeFileSync(new URL('ENCODER-CHECKS.json',dir),JSON.stringify({native_token_fixtures:fixture.length,all_pass:true,
 vocabulary_moves:4352,all_vocabulary_and_black_mirrored_promotion_indices_match:true,
 legal_masks_independently_match_python_chess:20,legacy_board_channels_match_native_last_frame:20,
 no_history_padding_for20_cases:true},null,2)+'\n');

const start=Date.now();let session:any;
function stop(reason:string){
 fs.writeFileSync(new URL('STOPPED.json',dir),JSON.stringify({reason,inferences:results.rows.length,elapsed_ms:Date.now()-start,peak_rss_kib:process.resourceUsage().maxRSS,no_retry:true},null,2)+'\n');
 process.exit(1);
}
const results:any={scope:'Matched20 development diagnostic; no classifier fit, threshold selection, or native-Maia fidelity claim.',rows:[]};
const guard=()=>{if(process.memoryUsage().rss>1073741824||process.resourceUsage().maxRSS*1024>1073741824)stop('1GB resident cap');if(Date.now()-start>120000)stop('120second wall cap');};
const watchdog=setInterval(guard,100);
const deadline=setTimeout(()=>stop('120second wall cap'),120000);
// No downloads, cache services or remote runtime/model URLs are permitted.
globalThis.fetch=async()=>{throw Error('Network fetch blocked by study protocol');};
try{
 const ort:any=await import(source('runtime_js').href);
 ort.env.wasm.numThreads=1;ort.env.wasm.proxy=false;ort.env.wasm.initTimeout=30000;
 ort.env.wasm.wasmPaths={mjs:source('runtime_wasm_js').href,wasm:source('runtime_wasm').href};
 ort.env.wasm.wasmBinary=fs.readFileSync(source('runtime_wasm'));
 const model=fs.readFileSync(source('model'));
 session=await ort.InferenceSession.create(model,{executionProviders:['wasm'],graphOptimizationLevel:'all'});
 guard();
 const preflight={at_utc:new Date().toISOString(),input_names:session.inputNames,output_names:session.outputNames,input_metadata:session.inputMetadata,output_metadata:session.outputMetadata,
  runtime_version:'1.30.0',wasm_numThreads:1,network_disabled:true,resident_bytes:process.memoryUsage().rss,peak_rss_kib:process.resourceUsage().maxRSS};
 fs.writeFileSync(new URL('PREFLIGHT.json',dir),JSON.stringify(preflight,null,2)+'\n');
 console.log(JSON.stringify(preflight));
 if(!['tokens','elo_self','elo_oppo'].every(n=>session.inputNames.includes(n))||!session.outputNames.includes('logits_move'))throw Error('Graph interface differs from documented source');
 const tokenInfo=session.inputMetadata.find((m:any)=>m.name==='tokens');
 if(!tokenInfo||tokenInfo.type!=='float32'||tokenInfo.shape.length!==3||tokenInfo.shape[1]!==64||![12,97].includes(tokenInfo.shape[2]))throw Error('Unverified token shape; stop rather than adapt architecture');
 const channels=tokenInfo.shape[2];
 // Parent explicitly authorized this conditional legacy-model amendment.
 const amended={...plan,metadata_verified_at_utc:new Date().toISOString(),initial_plan_sha256:hash(new URL('PLAN-INITIAL.json',dir)),
  actual_model_mode:channels===12?'legacy_frontend_single_board64x12_NOT_native79M_or_historymodel':'history_compatible64x97',
  history_actually_fed:channels===97?'Eight real chronological PGN positions':'Current board only, exactly documented frontend encoder; real eight-position history retained for audit but not fed',
  no_fake_history:true,actual_graph_token_metadata:tokenInfo,encoder_checks_sha256:hash(new URL('ENCODER-CHECKS.json',dir)),
  amendment_before_first_inference_at_utc:new Date().toISOString(),inferences_at_amendment:0};
 fs.writeFileSync(new URL('PLAN.json',dir),JSON.stringify(amended,null,2)+'\n');
 results.plan_sha256=hash(new URL('PLAN.json',dir));results.model_mode=amended.actual_model_mode;results.model_sha256=plan.sources.model.sha256;
 results.runtime_sha256=plan.sources.runtime_js.sha256;results.script_sha256=hash(new URL('run.mts',dir));
 for(const c of inputs.cases){
  guard();if(results.rows.length>=20)throw Error('Inference cap reached');
  const black=c.fen_before.split(' ')[1]==='b';
  const tokens=channels===12?singleBoard(c.fen_before):encodeHistory(c.real_history_fens,true);
  const feeds={tokens:new ort.Tensor('float32',tokens,[1,64,channels]),elo_self:new ort.Tensor('float32',Float32Array.from([1600]),[1]),elo_oppo:new ort.Tensor('float32',Float32Array.from([1600]),[1])};
  const began=Date.now(),outputs=await session.run(feeds);guard();
  const logits=outputs.logits_move.data;if(logits.length!==4352)throw Error('Unexpected policy output');
  const legal=c.legal_uci.map((uci:string)=>{const index=vocabulary[black?mirror(uci):uci];if(index===undefined||!Number.isFinite(logits[index]))throw Error('Invalid legal logit');return {uci,index,logit:logits[index]};});
  const max=Math.max(...legal.map((m:any)=>m.logit)),sum=legal.reduce((s:number,m:any)=>s+Math.exp(m.logit-max),0);
  for(const m of legal)m.probability=Math.exp(m.logit-max)/sum;
  const played=legal.find((m:any)=>m.uci===c.uci);if(!played)throw Error('Played move missing from legal policy');
  const entropy=-legal.reduce((s:number,m:any)=>s+m.probability*Math.log(m.probability),0);
  results.rows.push({key:c.key,game_id:c.game_id,ply:c.ply,san:c.san,uci:c.uci,played_move_probability:played.probability,
   legal_rank:1+legal.filter((m:any)=>m.logit>played.logit).length,legal_count:legal.length,entropy_nats:entropy,
   surprisal_nats:-Math.log(played.probability),inference_ms:Date.now()-began,token_sha256:crypto.createHash('sha256').update(new Uint8Array(tokens.buffer)).digest('hex')});
  fs.writeFileSync(new URL('policy-results.json',dir),JSON.stringify(results,null,2)+'\n');
 }
 results.status='complete';results.elapsed_ms=Date.now()-start;results.peak_rss_kib=process.resourceUsage().maxRSS;
 fs.writeFileSync(new URL('policy-results.json',dir),JSON.stringify(results,null,2)+'\n');
 console.log(JSON.stringify({status:results.status,mode:results.model_mode,inferences:results.rows.length,elapsed_ms:results.elapsed_ms,peak_rss_kib:results.peak_rss_kib}));
}catch(error){stop(String(error));}
finally{clearInterval(watchdog);clearTimeout(deadline);if(session)await session.release();}
