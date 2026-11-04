// One fixed context hypothesis plus exact per-window gate diagnostics.
import fs from 'node:fs';
import crypto from 'node:crypto';
import {classify,annotation,naiveMaterial,isSacrifice,isMuteSacrifice,hasMatingAcceptance,continuedOfferWhileInCheck,convertedMaterialOrEndgame,normalized,winChance} from '../../root/frozen-v4/noSweatClassify.ts';
import {classify as prior600} from './prior600/noSweatClassify.ts';
import {after} from '../../root/frozen-v4/noSweatCore.ts';
const dir=new URL('.',import.meta.url);
const final=new URL('../../../brilliants-final-2026-11-03/',dir);
const load=(url:URL)=>JSON.parse(fs.readFileSync(url,'utf8'));
const hash=(url:URL)=>crypto.createHash('sha256').update(fs.readFileSync(url)).digest('hex');
const materialCache=new Map<string,number>();
const material=(fen:string)=>{if(!materialCache.has(fen))materialCache.set(fen,naiveMaterial(fen));return materialCache.get(fen)!;};
const rows:any[]=[];const start=Date.now();let reconstructionDifferences=0,ecDifferences=0,accuracyDifferences=0,nonBrilliantDifferences=0;
for(const file of ['analysis-baseline.json','analysis-panel.json']){
 const data=load(new URL(file,final));
 for(const t of data.targets){
  if(Date.now()-start>120000)throw Error('Bounded120second diagnostic cap reached');
  const snaps=t.snapshot_ids.map((id:string)=>data.snapshots[id]);
  const reviews=snaps.map((s:any)=>({current:s.current,previous:s.previous||undefined,terminal:s.terminal,quality:'fixed-sf18:'+data.engine_sha256}));
  const input={positions:snaps.map((s:any)=>s.fen),reviews,move:t.uci,policy:'mute-brilliant-v4'};
  const base=classify(input as any,material),experiment=prior600(input as any,material);
  const ec=classify({...input,policy:'en-croissant'} as any,material);
  if(JSON.stringify(ec)!==JSON.stringify(prior600({...input,policy:'en-croissant'} as any,material)))ecDifferences++;
  if(base.accuracy!==experiment.accuracy||base.cpLoss!==experiment.cpLoss)accuracyDifferences++;
  if(base.symbol!==experiment.symbol&&base.symbol!=='!!'&&experiment.symbol!=='!!')nonBrilliantDifferences++;
  const color=t.fen_before.split(' ')[1]==='w'?'white':'black',n=reviews.length;
  const broad=isSacrifice(t.fen_before,t.fen_after,material),raw=isMuteSacrifice(t.fen_before,t.fen_after);
  const mateAcceptance=!broad&&hasMatingAcceptance(t.fen_before,t.fen_after);
  const continuation=continuedOfferWhileInCheck(n>2?snaps[n-3].fen:undefined,t.fen_before,t.fen_after,t.uci);
  const phaseRelevant=convertedMaterialOrEndgame(t.fen_before);
  const offers=new Map<string,boolean>();
  const isOffer=(uci:string)=>{if(!offers.has(uci))offers.set(uci,isMuteSacrifice(t.fen_before,uci===t.uci?t.fen_after:after(t.fen_before,uci)));return offers.get(uci)!;};
  const window=(b:any,a:any,p:any)=>{
   if(!b||!a)return {complete:false,gates:null};
   const next=normalized(a.lines[0],color),best=normalized(b.lines[0],color),loss=winChance(best)-winChance(next);
   const searchedMate=a.lines[0].mate!==undefined&&next>0;
   const safe=b.lines.filter((l:any)=>l.moves[0]!==t.uci&&normalized(l,color)>=600&&!isOffer(l.moves[0])).map((l:any)=>({uci:l.moves[0],cp_mover:normalized(l,color)}));
   const gates={two_roots:b.lines.length>1,raw_offer:raw,ec_or_mate_corroboration:!!(broad||searchedMate||mateAcceptance),
    quality:loss<=5,after_floor:next>=-100,phase_safe_alternative:!(phaseRelevant&&safe.length),checked_continuation:!continuation};
   const previous=p?.lines[0],prior=previous?normalized(previous,color):null;
   return {complete:true,gates,all_gates_pass:Object.values(gates).every(Boolean),failed_gates:Object.entries(gates).filter(([,pass])=>!pass).map(([k])=>k),
    before_depth:b.depth,after_depth:a.depth,previous_depth:p?.depth,best_cp_mover:best,after_cp_mover:next,loss_pp:loss,
    previous_own_after_cp_mover:prior,previous_explicit_winning_mate:previous?.mate!==undefined&&prior!==null&&prior>0,
    previous_score:previous?{cp:previous.cp,mate:previous.mate}:null,
    before_minus_previous_cp:prior===null?null:best-prior,after_minus_previous_cp:prior===null?null:next-prior,
    prior600_veto:prior!==null&&prior>=600,safe_alternatives:safe,
    raw_ec_annotation:annotation(previous,b,a.lines[0],color,t.uci,broad)};
  };
  const current=window(reviews[n-2].current,reviews[n-1].current,n>2?reviews[n-3].current:undefined);
  const previous=window(reviews[n-2].previous,reviews[n-1].terminal?reviews[n-1].current:reviews[n-1].previous,n>2?reviews[n-3].previous:undefined);
  const sufficient=reviews[n-2].quality===reviews[n-1].quality;
  if((base.provisional==='!!')!==current.all_gates_pass||(base.symbol==='!!')!==!!(current.all_gates_pass&&previous.all_gates_pass&&sufficient))reconstructionDifferences++;
  const truth=[...new Set(t.observations.filter((o:any)=>o.source_type==='fresh_review'&&o.label!=='unknown').map((o:any)=>o.label==='!!'))];
  if(truth.length!==1)throw Error('Unreconciled labels');
  rows.push({cohort:file==='analysis-panel.json'?'panel30':t.split==='validation'?'recent200':'reference618',key:`${t.game_id}:${t.ply}`,game_id:t.game_id,ply:t.ply,san:t.san,uci:t.uci,
   truth_brilliant:truth[0],observed_labels:[...new Set(t.observations.filter((o:any)=>o.source_type==='fresh_review').map((o:any)=>o.label))],
   raw_offer:raw,ec_sacrifice:broad,mate_acceptance:mateAcceptance,phase_context_relevant:phaseRelevant,checked_continuation:continuation,
   current,previous,confidence_sufficient:sufficient,withheld_confirmation:base.provisional==='!!'&&base.symbol!=='!!',baseline:base,prior600:experiment});
 }
}
if(rows.length!==848||reconstructionDifferences||ecDifferences||accuracyDifferences||nonBrilliantDifferences)throw Error('Exact gates/contract parity failed');
const metrics:any={},groups:any={};
for(const cohort of ['all848','core818','reference618','recent200','panel30']){
 const selected=cohort==='all848'?rows:cohort==='core818'?rows.filter(r=>r.cohort!=='panel30'):rows.filter(r=>r.cohort===cohort);
 metrics[cohort]={};
 for(const policy of ['baseline','prior600']){
  const m:any={TP:0,FN:0,FP:0,TN:0};
  for(const r of selected)m[r.truth_brilliant?(r[policy].symbol==='!!'?'TP':'FN'):(r[policy].symbol==='!!'?'FP':'TN')]++;
  m.agreement=(m.TP+m.TN)/selected.length;m.detection=m.TP/(m.TP+m.FN);m.false_award_rate=m.FP/(m.FP+m.TN);metrics[cohort][policy]=m;
 }
 const subsets={false_awards:selected.filter(r=>!r.truth_brilliant&&r.baseline.symbol==='!!'),misses:selected.filter(r=>r.truth_brilliant&&r.baseline.symbol!=='!!'),true_awards:selected.filter(r=>r.truth_brilliant&&r.baseline.symbol==='!!')};
 groups[cohort]={};
 for(const [name,rs]of Object.entries(subsets)){
  const gateNames=Object.keys(rs[0]?.current.gates??{}),failures:any={};
  for(const gate of gateNames)failures[gate]={current:rs.filter(r=>r.current.gates?.[gate]===false).length,prior:rs.filter(r=>r.previous.gates?.[gate]===false).length,either:rs.filter(r=>r.current.gates?.[gate]===false||r.previous.gates?.[gate]===false).length};
  const signatures:any={};for(const r of rs){const failed=[...new Set([...(r.current.failed_gates??[]),...(r.previous.failed_gates??[])])].sort().join('+')||'none';signatures[failed]=(signatures[failed]??0)+1;}
  groups[cohort][name]={n:rs.length,gate_failures:failures,combined_failure_signatures:signatures,current_prior600_veto:rs.filter(r=>r.current.prior600_veto).length,both_prior600_veto:rs.filter(r=>r.current.prior600_veto&&r.previous.prior600_veto).length,
   explicit_previous_winning_mate:rs.filter(r=>r.current.previous_explicit_winning_mate).length,confirmation_withheld:rs.filter(r=>r.withheld_confirmation).length};
 }
}
const changes=rows.filter(r=>(r.baseline.symbol==='!!')!==(r.prior600.symbol==='!!'));
const output={scope:'All848 now unblinded development; historical recent200/panel labels are diagnostic only. One fixed600cp prior-context candidate, no grid or new evidence.',generated_at:new Date().toISOString(),
 source_sha256:{baseline:hash(new URL('../../root/frozen-v4/noSweatClassify.ts',dir)),candidate:hash(new URL('prior600/noSweatClassify.ts',dir))},
 input_sha256:Object.fromEntries(['analysis-baseline.json','analysis-panel.json'].map(f=>[f,hash(new URL(f,final))])),
 contracts:{exact_gate_reconstruction_n:848,reconstruction_differences:reconstructionDifferences,ec_differences:ecDifferences,accuracy_cploss_differences:accuracyDifferences,other_nonbrilliant_symbol_differences:nonBrilliantDifferences},metrics,groups,changes,rows,
 elapsed_ms:Date.now()-start,max_rss_kib:process.resourceUsage().maxRSS};
fs.writeFileSync(new URL('context-results.json',dir),JSON.stringify(output,null,2)+'\n');
console.log(JSON.stringify({metrics,recent_misses:groups.recent200.misses,recent_context:groups.recent200,elapsed_ms:output.elapsed_ms,max_rss_kib:output.max_rss_kib},null,2));
