// Exactly two requested full-window private experiments. All848 are development.
import {readFileSync,writeFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {classify as v4,naiveMaterial} from '../../../root/frozen-v4/noSweatClassify.ts';
import {classify as A} from './variantA.ts';
import {classify as B} from './variantB.ts';
import {hasAttributableMatingAcceptance,noNonOfferingEscape,hasDirectStalemateAcceptance} from './offerProofs.ts';
const base='/Users/da/Documents/ChatGPT/No Sweat Chess/';
const final=base+'research/brilliants-final-2026-11-03/';
const out=base+'research/brilliants-improvement-2026-11-03/astra/v5/variants/';
const hash=(p:string)=>createHash('sha256').update(readFileSync(p)).digest('hex');
const primary=JSON.parse(readFileSync(final+'primary-moves.json','utf8'));
const panel=JSON.parse(readFileSync(final+'panel-moves.json','utf8'));
const identities=new Map([...primary,...panel].map((x:any)=>[x.game_id+':'+x.ply,x]));
const materialCache=new Map<string,number>();
const material=(fen:string)=>{if(!materialCache.has(fen))materialCache.set(fen,naiveMaterial(fen));return materialCache.get(fen)!;};
const rows:any[]=[];const started=Date.now();
for(const file of ['analysis-baseline.json','analysis-panel.json']){
 const data=JSON.parse(readFileSync(final+file,'utf8'));
 for(const t of data.targets){
  const key=t.game_id+':'+t.ply;const identity:any=identities.get(key);if(!identity)throw new Error('Identity missing');
  const snaps=t.snapshot_ids.map((id:string)=>data.snapshots[id]);
  const input={positions:snaps.map((s:any)=>s.fen),reviews:snaps.map((s:any)=>({current:s.current,previous:s.previous||undefined,terminal:s.terminal,quality:'fixed-sf18:'+data.engine_sha256})),move:t.uci,policy:'mute-brilliant-v4'};
  const a=v4(input as any,material),b=A(input as any,material),c=B(input as any,material);
  const truth=identity.fresh_label==='!!';
  const cohort=file==='analysis-panel.json'?'panel30':identity.source_cohort==='reference618'?'old618':'recent200';
  rows.push({key,san:t.san,cohort,truth,label:identity.fresh_label,v4:a,A:b,B:c,features:{attributableMate:hasAttributableMatingAcceptance(snaps.length>2?snaps[snaps.length-3].fen:undefined,t.fen_before,t.fen_after,t.uci),noNonOfferingEscape:noNonOfferingEscape(t.fen_before)??null,directStalemate:hasDirectStalemateAcceptance(t.fen_before,t.fen_after)}});
 }
}
const tally=(selected:any[],variant:string)=>{const m={TP:0,FN:0,FP:0,TN:0};for(const r of selected)m[r.truth?(r[variant].symbol==='!!'?'TP':'FN'):(r[variant].symbol==='!!'?'FP':'TN')]++;return m;};
const summaries:any={};
for(const cohort of ['old618','recent200','core818','panel30','all848']){
 const selected=rows.filter(r=>cohort==='all848'||(cohort==='core818'?r.cohort!=='panel30':r.cohort===cohort));
 summaries[cohort]={n:selected.length,v4:tally(selected,'v4'),A:tally(selected,'A'),B:tally(selected,'B')};
}
if(summaries.core818.v4.TP!==320||summaries.core818.v4.FP!==25)throw new Error('Frozen baseline parity failed');
const changes=(variant:string)=>rows.filter(r=>(r.v4.symbol==='!!')!==(r[variant].symbol==='!!'));
const result={scope:'Exactly A and B; all848includinghistoricalrecent200/panelnowdevelopment. Existing complete-window confidence replay, no new engine evidence.',source_sha256:{v4:hash(base+'research/brilliants-improvement-2026-11-03/root/frozen-v4/noSweatClassify.ts'),A:hash(out+'variantA.ts'),B:hash(out+'variantB.ts'),helpers:hash(out+'offerProofs.ts'),core:hash(final+'analysis-baseline.json'),panel:hash(final+'analysis-panel.json')},summaries,changes:{A:changes('A'),B:changes('B')},rows,elapsed_ms:Date.now()-started,max_rss_kib:process.resourceUsage().maxRSS};
writeFileSync(out+'results.json',JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify({summaries,changes:{A:result.changes.A.map(r=>[r.key,r.san,r.truth,r.v4.symbol,r.A.symbol]),B:result.changes.B.map(r=>[r.key,r.san,r.truth,r.v4.symbol,r.B.symbol])},elapsed_ms:result.elapsed_ms}));
