// Two explicitly requested quality hypotheses; saved evidence only.
import fs from 'node:fs';
import crypto from 'node:crypto';
import {classify,naiveMaterial,normalized,winChance} from '../root/frozen-v4/noSweatClassify.ts';
import {classify as fallback} from './same-root-fallback/noSweatClassify.ts';
import {classify as strict} from './same-root-strict/noSweatClassify.ts';
const root=new URL('.',import.meta.url);
const read=(path:string)=>JSON.parse(fs.readFileSync(new URL(path,root),'utf8'));
const source=(path:string)=>crypto.createHash('sha256').update(fs.readFileSync(new URL(path,root))).digest('hex');
const studies=[
 ['reference618','../../../mute-chess-research/studies/brilliant-moves/analysis-baseline.json','../root/frozen-v4-development.json'],
 ['recent200','../validation/analysis-baseline.json','../validation/frozen-v4-results.json'],
 ['stronger_recent30','../validation/analysis-stronger.json',null],
] as const;
const cache=new Map<string,number>();
const material=(fen:string)=>{if(!cache.has(fen))cache.set(fen,naiveMaterial(fen));return cache.get(fen)!;};
const blank=()=>({TP:0,FN:0,FP:0,TN:0});
const metrics:any={}; const rows:any[]=[];
let parity=0,ecDifferences=0,accuracyDifferences=0,nonBrilliantDifferences=0;
const begin=Date.now();
function diagnostic(b:any,a:any,move:string,color:any){
 if(!b||!a)return {complete:false};
 const rank=b.lines.findIndex((line:any)=>line.moves[0]===move);
 const best=normalized(b.lines[0],color),child=normalized(a.lines[0],color);
 const rootScore=rank>=0?normalized(b.lines[rank],color):null;
 const crossLoss=winChance(best)-winChance(child);
 const rootLoss=rootScore===null?null:winChance(best)-winChance(rootScore);
 return {complete:true,before_depth:b.depth,after_depth:a.depth,best_cp_mover:best,child_cp_mover:child,
  root_rank:rank>=0?rank+1:null,root_cp_mover:rootScore,cross_loss_pp:crossLoss,root_loss_pp:rootLoss,
  child_quality_pass:crossLoss<=5,root_quality_pass:rootLoss===null?null:rootLoss<=5,after_floor_pass:child>=-100};
}
for(const [cohort,path,expectedPath] of studies){
 const data=read(path),expected=expectedPath?read(expectedPath):null;
 const expectedRows=new Map(expected?.rows.map((r:any)=>[`${r.game_id}:${r.ply}`,r])??[]);
 metrics[cohort]={baseline:blank(),same_root_fallback:blank(),same_root_strict:blank()};
 for(const target of data.targets){
  if(Date.now()-begin>120000)throw Error('Bounded two-minute replay cap; stop, no automatic retry');
  const snap=target.snapshot_ids.map((id:string)=>data.snapshots[id]);
  if(snap.some((s:any)=>!s))throw Error('Incomplete saved decision window');
  const reviews=snap.map((s:any)=>({current:s.current,previous:s.previous||undefined,terminal:s.terminal,quality:'fixed-sf18:'+data.engine_sha256}));
  const input={positions:snap.map((s:any)=>s.fen),reviews,move:target.uci,policy:'mute-brilliant-v4'};
  const baseline=classify(input as any,material);
  if(expected){const old:any=expectedRows.get(`${target.game_id}:${target.ply}`);if(!old||JSON.stringify(old.v4)!==JSON.stringify(baseline))throw Error('Full baseline parity failed');parity++;}
  const variants={same_root_fallback:fallback(input as any,material),same_root_strict:strict(input as any,material)};
  const ec=classify({...input,policy:'en-croissant'} as any,material);
  for(const fn of [fallback,strict]){
   if(JSON.stringify(ec)!==JSON.stringify(fn({...input,policy:'en-croissant'} as any,material)))ecDifferences++;
  }
  const truth=[...new Set(target.observations.filter((o:any)=>o.source_type==='fresh_review'&&o.label!=='unknown').map((o:any)=>o.label==='!!'))];
  if(truth.length!==1)throw Error('Unreconciled label');
  const positive=truth[0] as boolean;
  const n=reviews.length,color=target.fen_before.split(' ')[1]==='w'?'white':'black';
  const current=diagnostic(reviews[n-2].current,reviews[n-1].current,target.uci,color);
  const previous=diagnostic(reviews[n-2].previous,reviews[n-1].terminal?reviews[n-1].current:reviews[n-1].previous,target.uci,color);
  const all={baseline,...variants};
  for(const [name,result] of Object.entries(all))metrics[cohort][name][positive?(result.symbol==='!!'?'TP':'FN'):(result.symbol==='!!'?'FP':'TN')]++;
  for(const value of Object.values(variants)){
   if(value.accuracy!==baseline.accuracy||value.cpLoss!==baseline.cpLoss)accuracyDifferences++;
   if(value.symbol!==baseline.symbol&&value.symbol!=='!!'&&baseline.symbol!=='!!')nonBrilliantDifferences++;
  }
  rows.push({cohort,key:`${target.game_id}:${target.ply}`,game_id:target.game_id,ply:target.ply,san:target.san,uci:target.uci,
   account:target.observations.find((o:any)=>o.source_type==='fresh_review')?.account,
   label:positive?'brilliant':'non_brilliant',observed_labels:[...new Set(target.observations.filter((o:any)=>o.source_type==='fresh_review').map((o:any)=>o.label))],
   truth_brilliant:positive,current,previous,baseline,...variants});
 }
}
if(parity!==818||ecDifferences||accuracyDifferences||nonBrilliantDifferences)throw Error('Contract check failed');
const core=rows.filter(r=>r.cohort!=='stronger_recent30');
metrics.all818={baseline:blank(),same_root_fallback:blank(),same_root_strict:blank()};
for(const r of core)for(const name of ['baseline','same_root_fallback','same_root_strict'])metrics.all818[name][r.truth_brilliant?(r[name].symbol==='!!'?'TP':'FN'):(r[name].symbol==='!!'?'FP':'TN')]++;
for(const group of Object.values(metrics) as any[])for(const m of Object.values(group) as any[]){m.n=m.TP+m.FN+m.FP+m.TN;m.agreement=(m.TP+m.TN)/m.n;m.detection=m.TP/(m.TP+m.FN);m.false_award_rate=m.FP/(m.FP+m.TN);}
function coverage(rs:any[]){return {n:rs.length,current_root_present:rs.filter(r=>r.current.root_rank!==null).length,both_roots_present:rs.filter(r=>r.current.root_rank!==null&&r.previous.root_rank!==null).length,
 current_first:rs.filter(r=>r.current.root_rank===1).length,current_second:rs.filter(r=>r.current.root_rank===2).length,
 current_root_pass_child_fail:rs.filter(r=>r.current.root_quality_pass===true&&!r.current.child_quality_pass).length,
 current_root_fail_child_pass:rs.filter(r=>r.current.root_quality_pass===false&&r.current.child_quality_pass).length};}
const groups:any={};
for(const cohort of ['all818','reference618','recent200','stronger_recent30']){
 const rs=cohort==='all818'?core:rows.filter(r=>r.cohort===cohort);
 groups[cohort]={all:coverage(rs)};
 for(const [label,predicate] of Object.entries({baseline_false_awards:(r:any)=>!r.truth_brilliant&&r.baseline.symbol==='!!',baseline_misses:(r:any)=>r.truth_brilliant&&r.baseline.symbol!=='!!',baseline_true_awards:(r:any)=>r.truth_brilliant&&r.baseline.symbol==='!!'}))groups[cohort][label]=coverage(rs.filter(predicate));
}
const changes:any={};
for(const name of ['same_root_fallback','same_root_strict']){
 changes[name]=rows.filter(r=>(r.baseline.symbol==='!!')!==(r[name].symbol==='!!')).map(r=>({cohort:r.cohort,key:r.key,san:r.san,label:r.label,observed_labels:r.observed_labels,account:r.account,baseline:r.baseline,candidate:r[name],current:r.current,previous:r.previous}));
}
const output={generated_at:new Date().toISOString(),scope:'Exploratory only: all818 core moves are now unblinded development. The additional stronger30 is targeted sensitivity, not an independent validation set.',
 source_sha256:{baseline:source('../root/frozen-v4/noSweatClassify.ts'),same_root_fallback:source('same-root-fallback/noSweatClassify.ts'),same_root_strict:source('same-root-strict/noSweatClassify.ts')},
 parity818:parity,contracts:{ec_differences:ecDifferences,accuracy_cploss_differences:accuracyDifferences,other_nonbrilliant_symbol_differences:nonBrilliantDifferences},metrics,coverage:groups,changes,rows,elapsed_ms:Date.now()-begin,max_rss_kib:process.resourceUsage().maxRSS};
fs.writeFileSync(new URL('same-root-results.json',root),JSON.stringify(output,null,2)+'\n');
console.log(JSON.stringify({metrics,coverage:groups.recent200,elapsed_ms:output.elapsed_ms,max_rss_kib:output.max_rss_kib},null,2));
