// Private bounded decision-sequence proof. No identities or observed labels enter this module.
import { legalMoves, position } from '../../../root/frozen-v4/noSweatCore.ts';
export interface Decision { ply:number; before:string; after:string; uci:string; confirmedBaseAward?:boolean }
const values:Record<string,number>={pawn:90,knight:300,bishop:300,rook:500,queen:1000,king:0};
const square=(s:string)=>s.charCodeAt(0)-97+(Number(s[1])-1)*8;
const squareName=(n:number)=>String.fromCharCode(97+n%8)+(1+Math.floor(n/8));
const key=(m:any)=>`${m.from}:${m.to}:${m.promotion||''}`;
class Budget { used=0; tick(){if(++this.used>512)throw new Error('proof-budget');} }
const raw=(p:any)=>{let v=0;for(const[,x]of p.board)v+=values[x.role]*(x.color===p.turn?1:-1);return v;};
const capture=(p:any,m:any)=>{const victim=p.board.get(m.to);return victim&&victim.color!==p.turn?values[victim.role]:p.board.get(m.from)?.role==='pawn'&&m.to===p.epSquare?90:0;};
const gain=(p:any,m:any)=>capture(p,m)+(m.promotion?values[m.promotion]-90:0);
function see(p:any,s:number,b:Budget):number {b.tick();let best=0;for(const m of legalMoves(p)){if(m.to!==s||!capture(p,m))continue;const child=p.clone();child.play(m);best=Math.max(best,gain(p,m)-see(child,s,b));}return best;}
function offers(d:Decision,b:Budget){const p=position(d.after),before=position(d.before),credit=Math.max(0,-raw(p)-raw(before));const out:any[]=[];if(p.isEnd())return out;for(const[s,x]of p.board){if(x.color===p.turn||x.role==='pawn'||x.role==='king')continue;const cost=see(p,s,b);if(cost>credit+100)out.push({square:s,role:x.role,color:x.color,cost});}return out;}
interface Acceptance { move:string; mates:string[]; forks:string[] }
function forcing(d:Decision,s:number,b:Budget):Acceptance[]{
 const p=position(d.after),credit=Math.max(0,-raw(p)-raw(position(d.before)));const out:Acceptance[]=[];
 for(const a of legalMoves(p)){
  if(a.to!==s||!capture(p,a))continue;const accepted=p.clone();accepted.play(a);
  if(gain(p,a)-see(accepted,s,b)<=credit+100)continue;
  const witness:Acceptance={move:key(a),mates:[],forks:[]};out.push(witness);
  for(const m of legalMoves(accepted)){
   const checked=accepted.clone();checked.play(m);if(!checked.isCheck())continue;b.tick();
   const role=accepted.board.get(m.from)?.role;const signature=`${role}:${m.to}`;
   const evasions=legalMoves(checked);
   if(!evasions.length){witness.mates.push(signature);continue;}
   let all=true;
   for(const e of evasions){
    b.tick();const escaped=checked.clone();escaped.play(e);let best=-Infinity;
    for(const c of legalMoves(escaped)){
     if(c.from!==m.to||!capture(escaped,c))continue;
     const captured=escaped.clone();captured.play(c);
     best=Math.max(best,gain(accepted,m)-gain(checked,e)+gain(escaped,c)-see(captured,c.to,b));
    }
    if(best<=100){all=false;break;}
   }
   if(all)witness.forks.push(signature);
  }
 }
 return out;
}
export interface ProofResult { veto:boolean; status:'complete'|'unknown'|'ineligible'; nodes:number; origins?:any[]; reason?:string }
export function repeatContinuation(current:Decision,history:Decision[]):ProofResult {
 const budget=new Budget();const origins:any[]=[];
 try{
  const before=position(current.before),after=position(current.after);const from=square(current.uci.slice(0,2)),to=square(current.uci.slice(2,4));
  // Preserve checks, captures, promotions, and castling (both ordinary and rook-square UCI).
  const mover=before.board.get(from);const castle=mover?.role==='king'&&((Math.floor(from/8)===Math.floor(to/8)&&Math.abs(from%8-to%8)===2)||(before.board.get(to)?.color===before.turn&&before.board.get(to)?.role==='rook'));
  if(!current.confirmedBaseAward||after.isCheck()||capture(before,{from,to})||current.uci.length!==4||castle)return{veto:false,status:'ineligible',nodes:0};
  const currentOffers=offers(current,budget);if(!currentOffers.length)return{veto:false,status:'ineligible',nodes:budget.used};
  const byPly=new Map(history.map(d=>[d.ply,d]));byPly.set(current.ply,current);
  let veto=false;
  for(let distance=1;distance<=3;distance++){
   const old=byPly.get(current.ply-2*distance);if(!old?.confirmedBaseAward)continue;
   const path:Decision[]=[];for(let ply=old.ply+1;ply<=current.ply;ply++){const d=byPly.get(ply);if(!d)return{veto:false,status:'unknown',nodes:budget.used,reason:'incomplete physical history'};path.push(d);}
   const oldPosition=position(old.after),oldCredit=Math.max(0,-raw(oldPosition)-raw(position(old.before)));let covers=true;
   for(const offer of currentOffers){
    const s=squareName(offer.square),piece=oldPosition.board.get(offer.square);
    if(!piece||piece.role!==offer.role||piece.color!==offer.color||path.some(d=>{const at=position(d.after).board.get(offer.square);return d.uci.slice(0,2)===s||d.uci.slice(2,4)===s||!at||at.role!==offer.role||at.color!==offer.color;})){covers=false;break;}
    const cost=see(oldPosition,offer.square,budget);if(cost!==offer.cost||cost<=oldCredit+100){covers=false;break;}
    for(const d of path.filter(d=>(d.ply-old.ply)%2===0))if(see(position(d.after),offer.square,budget)!==offer.cost){covers=false;break;}
    if(!covers)break;
   }
   if(!covers)continue;
   let renewed=false;const details:any[]=[];
   for(const offer of currentOffers){
    const previous=forcing(old,offer.square,budget),present=forcing(current,offer.square,budget);
    const oldLegal=new Set(legalMoves(oldPosition).map(key));
    const oldForks=new Set(previous.flatMap(a=>a.forks));
    for(const a of present){
     if(a.mates.length&&!oldLegal.has(a.move)){renewed=true;details.push({kind:'new-acceptance-mate',square:squareName(offer.square),acceptance:a.move,replies:a.mates});}
     const freshForks=a.forks.filter(f=>!oldForks.has(f));
     if(freshForks.length){renewed=true;details.push({kind:'new-safe-checking-fork',square:squareName(offer.square),acceptance:a.move,replies:freshForks});}
    }
   }
   origins.push({ply:old.ply,renewed,details});if(!renewed)veto=true;
  }
  return{veto,status:'complete',nodes:budget.used,origins};
 }catch(e){if((e as Error).message!=='proof-budget')throw e;return{veto:false,status:'unknown',nodes:512,origins,reason:'shared proof budget exhausted'};}
}
