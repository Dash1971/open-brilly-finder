// Supporting counterexamples only; never consulted by experimental classification.
import fs from 'node:fs';
import {isMuteSacrifice,isSacrifice,hasMatingAcceptance,continuedOfferWhileInCheck,convertedMaterialOrEndgame,normalized} from '../root/frozen-v4/noSweatClassify.ts';
import {after} from '../root/frozen-v4/noSweatCore.ts';
const dir=new URL('.',import.meta.url);
const result=JSON.parse(fs.readFileSync(new URL('same-root-results.json',dir),'utf8'));
const selected=new Set(result.rows.filter((r:any)=>r.cohort!=='stronger_recent30'&&(
 (!r.truth_brilliant&&r.baseline.symbol==='!!'&&r.cohort==='recent200')||
 (r.truth_brilliant&&r.baseline.symbol!=='!!'&&['current','previous'].some(w=>r[w].root_quality_pass===true&&!r[w].child_quality_pass))||
 result.changes.same_root_fallback.some((c:any)=>c.cohort===r.cohort&&c.key===r.key)
)).map((r:any)=>r.key));
const rows:any[]=[];
for(const path of ['../../../mute-chess-research/studies/brilliant-moves/analysis-baseline.json','../validation/analysis-baseline.json']){
 const data=JSON.parse(fs.readFileSync(new URL(path,dir),'utf8'));
 for(const t of data.targets){
  if(!selected.has(`${t.game_id}:${t.ply}`))continue;
  const snaps=t.snapshot_ids.map((id:string)=>data.snapshots[id]), b=snaps.at(-2), a=snaps.at(-1);
  const mats=new Map(snaps.map((s:any)=>[s.fen,s.ec_material]));
  const color=t.fen_before.split(' ')[1]==='w'?'white':'black';
  const alternatives=b.current.lines.filter((l:any)=>l.moves[0]!==t.uci).map((l:any)=>({move:l.moves[0],cp_mover:normalized(l,color),raw_piece_offer:isMuteSacrifice(t.fen_before,after(t.fen_before,l.moves[0]))}));
  rows.push({key:`${t.game_id}:${t.ply}`,san:t.san,raw_piece_offer:isMuteSacrifice(t.fen_before,t.fen_after),
   ec_sacrifice:isSacrifice(t.fen_before,t.fen_after,(fen:string)=>{if(!mats.has(fen))throw Error('Missing material');return mats.get(fen) as number;}),
   mating_acceptance:hasMatingAcceptance(t.fen_before,t.fen_after),checked_continuation:continuedOfferWhileInCheck(snaps.length>2?snaps.at(-3).fen:undefined,t.fen_before,t.fen_after,t.uci),
   routine_context_relevant:convertedMaterialOrEndgame(t.fen_before),alternatives,after_current:a.current.lines[0],
   ec_material_before:b.ec_material,ec_material_after:a.ec_material});
 }
}
fs.writeFileSync(new URL('counterexample-features.json',dir),JSON.stringify({scope:'Descriptive existing-source features; no further candidate or tuning.',rows},null,2)+'\n');
console.log(JSON.stringify(rows.find((r:any)=>r.key==='185357791081:68')));
