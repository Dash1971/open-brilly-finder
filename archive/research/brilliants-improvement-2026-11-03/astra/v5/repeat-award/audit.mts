// One decision-sequence hypothesis, with label-independent engine-gap selection.
import {readFileSync,writeFileSync,existsSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {DatabaseSync} from 'node:sqlite';
import {classify,naiveMaterial} from '../../../root/frozen-v4/noSweatClassify.ts';
import {position,legalMoves} from '../../../root/frozen-v4/noSweatCore.ts';
const base='/Users/da/Documents/ChatGPT/No Sweat Chess/';
const root=base+'research/brilliants-improvement-2026-11-03/';const dir=root+'astra/v5/repeat-award/';const final=base+'research/brilliants-final-2026-11-03/';
const hash=(p:string)=>createHash('sha256').update(readFileSync(p)).digest('hex');
const sourceFiles=[final+'analysis-baseline.json',final+'analysis-panel.json'];
const snapshots:any={};const targets:any[]=[];let engineHash='';
for(const path of sourceFiles){const d=JSON.parse(readFileSync(path,'utf8'));Object.assign(snapshots,d.snapshots);targets.push(...d.targets);engineHash=d.engine_sha256;}
for(const name of ['six-snapshots.json','completion-snapshots.json'])if(existsSync(dir+name)){
 const d=JSON.parse(readFileSync(dir+name,'utf8'));if(d.status!=='complete')throw new Error('Incomplete completion');
 for(const[id,s]of Object.entries(d.snapshots)){if(snapshots[id])throw new Error('Would overwrite baseline');snapshots[id]=s;}sourceFiles.push(dir+name);
}
const db=new DatabaseSync(final+'corpus.sqlite3',{readOnly:true});
const query=db.prepare('select * from positions where game_id=? and ply=?');
const history=db.prepare('select ply,uci,fen_after from positions where game_id=? and ply>? and ply<=? order by ply');
const value:any={pawn:90,knight:300,bishop:300,rook:500,queen:1000,king:0};
const raw=(p:any)=>{let total=0;for(const[,v]of p.board)total+=value[v.role]*(v.color===p.turn?1:-1);return total;};
const capture=(p:any,m:any)=>{const v=p.board.get(m.to);return v&&v.color!==p.turn?value[v.role]:p.board.get(m.from)?.role==='pawn'&&m.to===p.epSquare?90:0;};
const sq=(s:string)=>s.charCodeAt(0)-97+(Number(s[1])-1)*8;
const name=(n:number)=>String.fromCharCode(97+n%8)+(1+Math.floor(n/8));
function see(p:any,s:number,b:any):number{if(++b.n>512)throw Error('structural-budget');let best=0;for(const m of legalMoves(p)){if(m.to!==s||!capture(p,m))continue;const child=p.clone();child.play(m);best=Math.max(best,capture(p,m)+(m.promotion?value[m.promotion]-90:0)-see(child,s,b));}return best;}
function offers(beforeFen:string,afterFen:string):any[]{const b=position(beforeFen),a=position(afterFen);const credit=Math.max(0,-raw(a)-raw(b)),budget={n:0},out=[];if(a.isEnd())return out;for(const[s,p]of a.board){if(p.color===a.turn||p.role==='pawn'||p.role==='king')continue;const gain=see(a,s,budget);if(gain>credit+100)out.push({square:s,role:p.role,color:p.color,gain});}return out;}
const materialCache=new Map<string,number>();
const material=(f:string)=>{if(!materialCache.has(f))materialCache.set(f,naiveMaterial(f));return materialCache.get(f)!;};
const predictionCache=new Map<string,any>();
function predict(gid:string,ply:number):any{
 const key=gid+':'+ply;if(predictionCache.has(key))return predictionCache.get(key);
 const ids=[Math.max(0,ply-2),ply-1,ply].filter((p,i,a)=>i===0||p!==a[i-1]).map(p=>gid+':'+p);const missing=ids.filter(id=>!snapshots[id]);
 if(missing.length)return {missing};const row:any=query.get(gid,ply);if(!row)throw Error('Missing PGN move');
 const ss=ids.map(id=>snapshots[id]);if(ss[ss.length-1].fen!==row.fen_after||ss[ss.length-2].fen!==row.fen_before)throw Error('PGN/snapshot mismatch');
 const result=classify({positions:ss.map(s=>s.fen),reviews:ss.map(s=>({current:s.current,previous:s.previous||undefined,terminal:s.terminal,quality:'fixed-sf18:'+engineHash})),move:row.uci,policy:'mute-brilliant-v4'},material);
 const complete={symbol:result.symbol,provisional:result.provisional,withheld:result.withheld,snapshot_ids:ids};predictionCache.set(key,complete);return complete;
}
const rows:any[]=[];const needed=new Set<string>();
for(const t of targets){
 const key=t.game_id+':'+t.ply;const current=predict(t.game_id,t.ply);const row:any={key,san:t.san,current,eligibleQuiet:false,structuralUnknown:false,priors:[],suppress:false};rows.push(row);
 if(current.symbol!=='!!')continue;
 const before=position(t.fen_before),after=position(t.fen_after);const move={from:sq(t.uci.slice(0,2)),to:sq(t.uci.slice(2,4))};
 row.eligibleQuiet=!after.isCheck()&&!capture(before,move)&&t.uci.length===4;if(!row.eligibleQuiet)continue;
 let currentOffers:any[];try{currentOffers=offers(t.fen_before,t.fen_after);}catch{row.structuralUnknown=true;continue;}
 row.offers=currentOffers.map(o=>({...o,square:name(o.square)}));if(!currentOffers.length)throw Error('Brilliant without raw offer');
 for(let distance=1;distance<=3;distance++){
  const ply=t.ply-2*distance;if(ply<1)continue;const old:any=query.get(t.game_id,ply);if(!old)continue;
  const p=position(old.fen_after),b=position(old.fen_before);const credit=Math.max(0,-raw(p)-raw(b));const intervening:any[]=history.all(t.game_id,ply,t.ply);const budget={n:0};const proof:any={ply,san:old.san,structural:false,pieces:[]};row.priors.push(proof);
  try{
   let covers=true;
   for(const offer of currentOffers){
    const s=name(offer.square),oldPiece=p.board.get(offer.square);
    const unmoved=oldPiece&&oldPiece.color===offer.color&&oldPiece.role===offer.role&&!intervening.some(m=>m.uci.slice(0,2)===s||m.uci.slice(2,4)===s);
    if(!unmoved){covers=false;break;}
    const initialGain=see(p,offer.square,budget);if(initialGain!==offer.gain||initialGain<=credit+100){covers=false;break;}
    let continuous=true;
    for(const node of intervening.filter(m=>(m.ply-ply)%2===0))if(see(position(node.fen_after),offer.square,budget)!==offer.gain){continuous=false;break;}
    proof.pieces.push({square:s,gain:offer.gain,priorCredit:credit,unmoved:true,continuous});
    if(!continuous){covers=false;break;}
   }
   proof.structural=covers;
  }catch{proof.unknown=true;continue;}
  if(!proof.structural)continue;
  proof.prediction=predict(t.game_id,ply);
  if(proof.prediction.missing)for(const id of proof.prediction.missing)needed.add(id);
  if(proof.prediction.symbol==='!!')row.suppress=true;
 }
}
// Do not search earlier unknowns once another fully proven origin already decides the case.
const relevant=new Set<string>();for(const r of rows)if(!r.suppress)for(const p of r.priors)if(p.structural&&p.prediction?.missing)for(const id of p.prediction.missing)relevant.add(id);
const sample=new Set(JSON.parse(readFileSync(root+'quality-v5/acceptance/branch-input.json','utf8')).cases.map((c:any)=>c.key));
const result={scope:'All848development. Selection uses frozen-v4 predictions and PGN/board structure only, not observed labels. Quiet means no capture/promotion/check. One earlier confirmed v4 award must cover ALL current offered pieces with continuous unchanged raw liability and no physical-piece movement for1–3ownturns. Baseline v4 predictions are used for origins, not recursively suppressed outputs.',source_sha256:Object.fromEntries(sourceFiles.map(f=>[f,hash(f)])),rows,needed_snapshot_ids:[...relevant].sort(),matched20:rows.filter(r=>sample.has(r.key))};
const stage=process.argv[2]||'after-six';writeFileSync(dir+'audit-'+stage+'.json',JSON.stringify(result,null,2)+'\n');
if(stage==='after-six')writeFileSync(dir+'completion-plan.json',JSON.stringify({scope:'One parent-authorized fixed completion of all label-independently structurally relevant repeat-award origins across848cases; no baseline replacement; no automatic increase beyond120.',authorized_snapshot_cap:120,snapshot_ids:result.needed_snapshot_ids,audit_source_sha256:hash(dir+'audit-'+stage+'.json')},null,2)+'\n');
console.log(JSON.stringify({targets:rows.length,quietAwardCandidates:rows.filter(r=>r.eligibleQuiet).length,alreadySuppressed:rows.filter(r=>r.suppress).map(r=>[r.key,r.san]),remainingRelevantCases:rows.filter(r=>!r.suppress&&r.priors.some(p=>p.structural&&p.prediction?.missing)).length,neededSnapshots:relevant.size,matched20:result.matched20.map(r=>({key:r.key,san:r.san,suppress:r.suppress,structuralPriors:r.priors.filter(p=>p.structural)}))}));db.close();
