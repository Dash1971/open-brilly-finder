// Study-only branch identity preparation. Labels are never used by this code.
import fs from 'node:fs';
import crypto from 'node:crypto';
import {isMuteSacrifice} from '../../root/frozen-v4/noSweatClassify.ts';
import {position,legalMoves,standardUci,after} from '../../root/frozen-v4/noSweatCore.ts';
const dir=new URL('.',import.meta.url);
const digest=(p:URL)=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const selectionPath=new URL('../../astra/v5/avoidability20.json',dir);
const analysisPath=new URL('../../../brilliants-final-2026-11-03/analysis-baseline.json',dir);
const selected=JSON.parse(fs.readFileSync(selectionPath,'utf8')).rows.map((r:any)=>r.key);
const analysis=JSON.parse(fs.readFileSync(analysisPath,'utf8'));
const targets=new Map(analysis.targets.map((t:any)=>[`${t.game_id}:${t.ply}`,t]));
const value=(role:string)=>({pawn:90,knight:300,bishop:300,rook:500,queen:1000}[role]??0);
const raw=(p:any,mover:string)=>[...p.board].reduce((n:number,[,q]:any)=>n+value(q.role)*(q.color===mover?1:-1),0);
const captured=(p:any,m:any)=>{const q=p.board.get(m.to);return q&&q.color!==p.turn?value(q.role):p.board.get(m.from)?.role==='pawn'&&m.to===p.epSquare?90:0;};
function exchange(p:any,s:number):number{
 let best=0;
 for(const m of legalMoves(p)){
  if(m.to!==s||!captured(p,m))continue;
  const child=p.clone();child.play(m);
  best=Math.max(best,captured(p,m)+(m.promotion?value(m.promotion)-90:0)-exchange(child,s));
 }
 return best;
}
const cases:any[]=[];
for(const key of selected){
 const t:any=targets.get(key);if(!t)throw Error('Missing selected identity');
 const before=position(t.fen_before),post=position(t.fen_after),mover=before.turn;
 if(!isMuteSacrifice(t.fen_before,t.fen_after))throw Error('Selected move lacks frozen raw offer');
 const credit=Math.max(0,raw(post,mover)-raw(before,mover));
 const accepts:any[]=[];
 for(const m of legalMoves(post)){
  const victim=post.board.get(m.to);if(!victim||victim.color===post.turn||victim.role==='pawn'||victim.role==='king')continue;
  const child=post.clone();child.play(m);
  const net=captured(post,m)+(m.promotion?value(m.promotion)-90:0)-exchange(child,m.to);
  if(net<=credit+100)continue;
  const uci=standardUci(post,m);
  accepts.push({uci,fen:after(t.fen_after,uci),capturer:post.board.get(m.from)?.role,victim:victim.role,
   offered_square:uci.slice(2,4),credit,net_exchange_gain:net,raw_material_after_acceptance:raw(child,mover)});
 }
 accepts.sort((a,b)=>a.uci.localeCompare(b.uci));
 const nonoffers=legalMoves(before).map(m=>standardUci(before,m)).sort().filter(uci=>!isMuteSacrifice(t.fen_before,after(t.fen_before,uci)));
 cases.push({key,game_id:t.game_id,ply:t.ply,san:t.san,uci:t.uci,fen_before:t.fen_before,fen_after:t.fen_after,pgn_sha256:t.pgn_sha256,mover,
  raw_material_before:raw(before,mover),raw_material_after:raw(post,mover),qualifying_acceptances_total:accepts.length,
  acceptance_enumeration_complete:true,acceptance_search_coverage_complete:accepts.length<=3,
  selected_acceptances:accepts.slice(0,3),unsearched_acceptances:accepts.slice(3),nonoffering_legal_roots:nonoffers,
  baseline_before:analysis.snapshots[t.snapshot_ids.at(-2)],baseline_after:analysis.snapshots[t.snapshot_ids.at(-1)]});
}
if(cases.length!==20||new Set(cases.map(c=>c.key)).size!==20)throw Error('Expected20unique matched cases');
const out={generated_at:new Date().toISOString(),scope:'Twenty matched development cases. Selection supplied by parent; labels are not read or used by scoring/preparation.',
 source_sha256:digest(new URL('../../root/frozen-v4/noSweatClassify.ts',dir)),selection_sha256:digest(selectionPath),baseline_analysis_sha256:digest(analysisPath),
 acceptance_limit:3,acceptance_order:'UCI ascending',raw_offer_definition:'Exact frozen legal same-square exchange, credit+100 threshold; acceptance net includes promotion.',cases};
fs.writeFileSync(new URL('branch-input.json',dir),JSON.stringify(out,null,2)+'\n');
console.log(JSON.stringify({cases:cases.length,total_qualifying_acceptances:cases.reduce((s,c)=>s+c.qualifying_acceptances_total,0),selected_acceptances:cases.reduce((s,c)=>s+c.selected_acceptances.length,0),truncated_cases:cases.filter(c=>!c.acceptance_search_coverage_complete).map(c=>({key:c.key,total:c.qualifying_acceptances_total})),restricted_before_searches:cases.filter(c=>c.nonoffering_legal_roots.length).length,planned_positions:cases.reduce((s,c)=>s+c.selected_acceptances.length+(c.nonoffering_legal_roots.length?1:0),0)}));
