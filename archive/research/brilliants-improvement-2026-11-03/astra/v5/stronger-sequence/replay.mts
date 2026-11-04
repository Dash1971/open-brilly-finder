import {readFileSync,writeFileSync,existsSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {DatabaseSync} from 'node:sqlite';
import {classify,naiveMaterial} from '../variants/variantA.ts';
import {repeatContinuation,type Decision} from '../sequence-reference/temporalProof.ts';
const root='/Users/da/Documents/ChatGPT/No Sweat Chess/';
const dir=root+'research/brilliants-improvement-2026-11-03/astra/v5/stronger-sequence/';
const final=root+'research/brilliants-final-2026-11-03/';const extra=root+'research/brilliants-improvement-2026-11-03/astra/v5/repeat-award/';
const hash=(p:string)=>createHash('sha256').update(readFileSync(p)).digest('hex');
const sources=[dir+'../sequence-reference/temporalProof.ts',dir+'replay.mts',dir+'../variants/variantA.ts',dir+'../variants/offerProofs.ts',dir+'../../../root/frozen-v4/core.ts'];
// Freeze BEFORE reading/processing outcomes, including all executable rule dependencies.
const freeze={frozen_at:new Date().toISOString(),scope:'One private A plus repeat-continuation rule with new safe checking-fork or new legal mating acceptance exceptions; no identities/labels in proof;512 shared structural and forcing nodes; prior unsuppressed confirmed A.',sha256:Object.fromEntries(sources.map(f=>[f,hash(f)]))};
const freezeFile=existsSync(dir+'source-freeze.json')?'source-freeze-castling-addendum.json':'source-freeze.json';
writeFileSync(dir+freezeFile,JSON.stringify({...freeze,correction:freezeFile.includes('addendum')?'Correct castling detection: same-rank two-file king move or king destination own rook. Original source-freeze.json retained.':undefined},null,2)+'\n');
const snaps:any={};let targets:any[]=[];let engineHash='';const evidence:any={};
for(const f of [root+'research/brilliants-improvement-2026-11-03/uniform-stronger-v5/analysis-uniform.json',dir+'prior-snapshots.json']){
 const d=JSON.parse(readFileSync(f,'utf8'));for(const[id,s]of Object.entries(d.snapshots)){if(snaps[id])throw Error('Snapshot replacement');snaps[id]=s;}if(d.targets)targets.push(...d.targets);engineHash=d.engine_sha256;evidence[f]=hash(f);
}
const db=new DatabaseSync(final+'corpus.sqlite3',{readOnly:true});const query=db.prepare('select * from positions where game_id=? and ply=?');
const materialCache=new Map<string,number>();const material=(fen:string)=>{if(!materialCache.has(fen))materialCache.set(fen,naiveMaterial(fen));return materialCache.get(fen)!;};
const cached=new Map<string,any>();
function predict(gid:string,ply:number){const key=gid+':'+ply;if(cached.has(key))return cached.get(key);const ids=[Math.max(0,ply-2),ply-1,ply].filter((x,i,a)=>!i||x!==a[i-1]).map(x=>gid+':'+x);const missing=ids.filter(id=>!snaps[id]);if(missing.length)return{missing};const row:any=query.get(gid,ply);const ss=ids.map(id=>snaps[id]);if(ss.at(-1).fen!==row.fen_after||ss.at(-2).fen!==row.fen_before)throw Error('PGN identity mismatch');const result=classify({positions:ss.map(s=>s.fen),reviews:ss.map(s=>({current:s.current,previous:s.previous||undefined,terminal:s.terminal,quality:'fixed-sf18:'+engineHash})),move:row.uci,policy:'mute-brilliant-v4'},material);const answer={...result,snapshot_ids:ids};cached.set(key,answer);return answer;}
const rows:any[]=[];const missing=new Set<string>();
for(const t of targets){
 const base=predict(t.game_id,t.ply);const history:Decision[]=[];const earlier:any[]=[];
 if(base.symbol==='!!')for(let ply=Math.max(1,t.ply-6);ply<t.ply;ply++){const r:any=query.get(t.game_id,ply);if(!r)continue;const own=(t.ply-ply)%2===0;const prediction=own?predict(t.game_id,ply):undefined;if(own)earlier.push({ply,prediction});history.push({ply,before:r.fen_before,after:r.fen_after,uci:r.uci,confirmedBaseAward:prediction?.symbol==='!!'});}
 const current:Decision={ply:t.ply,before:t.fen_before,after:t.fen_after,uci:t.uci,confirmedBaseAward:base.symbol==='!!'};
 const proof=repeatContinuation(current,history);
 rows.push({key:t.game_id+':'+t.ply,san:t.san,base,proof,awarded:base.symbol==='!!'&&!proof.veto,earlier});
}
// Identity/label join is evaluation only; neither enters rule or earlier predictions.
const identities=new Map([...JSON.parse(readFileSync(final+'primary-moves.json','utf8')),...JSON.parse(readFileSync(final+'panel-moves.json','utf8'))].map((d:any)=>[d.game_id+':'+d.ply,d]));
for(const r of rows){const d:any=identities.get(r.key);r.truth=d.fresh_label==='!!';r.label=d.fresh_label;r.cohort=d.source_cohort==='reference618'?'old618':d.source_cohort==='frozen_v4_validation200'?'historical200':'panel30';}
const summaries:any={};for(const group of ['old618','historical200','core818','panel30','all848']){const selected=rows.filter(r=>group==='all848'||(group==='core818'?r.cohort!=='panel30':r.cohort===group));const count=(final:boolean)=>{const c={TP:0,FP:0,FN:0,TN:0};for(const r of selected){const pred=final?r.awarded:r.base.symbol==='!!';c[r.truth?(pred?'TP':'FN'):(pred?'FP':'TN')]++;}return c;};summaries[group]={baseA:count(false),sequence:count(true)};}
const result={scope:'All848development; unchanged frozen S at uniform1.5m; no mixed300k prior evidence; paired sensitivity, not validation.',freeze,evidence,summaries,rows};writeFileSync(dir+'results.json',JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify({summaries,changes:rows.filter(r=>r.proof.veto).map(r=>[r.key,r.san,r.truth]),exceptions:rows.filter(r=>r.proof.origins?.some((o:any)=>o.renewed)).map(r=>[r.key,r.san,r.proof]),unknown:rows.filter(r=>r.proof.status==='unknown').map(r=>[r.key,r.san,r.proof.reason])}));db.close();
