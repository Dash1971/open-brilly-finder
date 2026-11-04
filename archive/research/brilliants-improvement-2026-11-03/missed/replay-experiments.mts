// Prespecified three-variant exploratory replay; all618 cases are development.
import {readFileSync,writeFileSync} from 'node:fs';
import {dirname,join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {classify as baselineClassify,naiveMaterial} from './baseline-v3/noSweatClassify.ts';
import {classify as safe800} from './safe800/noSweatClassify.ts';
import {classify as safe900} from './safe900/noSweatClassify.ts';
import {classify as within50} from './safe600_within50best/noSweatClassify.ts';
const root=dirname(fileURLToPath(import.meta.url));const study=join(root,'../../../mute-chess-research/studies/brilliant-moves');
const baseline=JSON.parse(readFileSync(join(study,'analysis-baseline.json'),'utf8'));const expected=JSON.parse(readFileSync(join(study,'comparison-v3.json'),'utf8'));const primary=JSON.parse(readFileSync(join(study,'primary-moves.json'),'utf8'));
const byKey=new Map(expected.rows.map(r=>[`${r.game_id}:${r.ply}`,r]));const primaryMap=new Map(primary.map(r=>[`${r.game_id}:${r.ply}`,r]));
const cache=new Map<string,number>();const material=(fen:string)=>{if(!cache.has(fen))cache.set(fen,naiveMaterial(fen));return cache.get(fen)!;};
const start=Date.now();const results:any={generated_at:new Date().toISOString(),scope:'Exploratory development-only tests; three prespecified safe-winning-alternative hypotheses. No source deployment or new validation.',n:618,baseline_parity:{tested:0,full_symbol_or_withheld_differences:[]},variants:{}};
const candidates=[['safe800',safe800],['safe900',safe900],['safe600_within50best',within50]] as const;
const blank=()=>({TP:0,FN:0,FP:0,TN:0,withheld_positive:0,withheld_negative:0});
const tally=(m:any,pos:boolean,value:any)=>{m[pos?(value.symbol==='!!'?'TP':'FN'):(value.symbol==='!!'?'FP':'TN')]++;if(value.withheld)m[pos?'withheld_positive':'withheld_negative']++;};
for(const [name] of candidates)results.variants[name]={metrics:blank(),changes:[],known_regression_evidence:'Outside618freshlabels; evaluated separately if available.'};
for(const target of baseline.targets){
 if(Date.now()-start>120000)throw new Error('Bounded120second offline replay cap reached; stop/report, no retry');
 const key=`${target.game_id}:${target.ply}`;const row:any=byKey.get(key);const p:any=primaryMap.get(key);const snapshots=target.snapshot_ids.map(id=>baseline.snapshots[id]);
 const reviews=snapshots.map(s=>({current:s.current,previous:s.previous||undefined,terminal:s.terminal,quality:'fixed-sf18:'+baseline.engine_sha256}));
 const input={positions:snapshots.map(s=>s.fen),reviews,move:target.uci,policy:'mute-brilliant-v3'};const control=baselineClassify(input as any,material);
 results.baseline_parity.tested++;
 if(control.symbol!==row.mute_v3.symbol||control.withheld!==row.mute_v3.withheld||control.provisional!==row.mute_v3.provisional)results.baseline_parity.full_symbol_or_withheld_differences.push({key,expected:row.mute_v3,actual:control});
 const pos=row.primary_fresh_binary_label==='brilliant';
 for(const [name,fn]of candidates){const value=fn(input as any,material);tally(results.variants[name].metrics,pos,value);
  if((value.symbol==='!!')!==(control.symbol==='!!'))results.variants[name].changes.push({key,game_id:target.game_id,ply:target.ply,san:target.san,account:p.account,label:row.primary_fresh_binary_label,observed_labels:row.observations.filter(o=>o.source_type==='fresh_review').map(o=>o.label),baseline:control,experimental:value,current_gates:row.baseline_gates,ec_sacrifice:row.ec_sacrifice,piece_offer:row.mute_piece_offer});
 }
}
if(results.baseline_parity.full_symbol_or_withheld_differences.length)throw new Error('Baseline parity failed; do not interpret candidate results');
for(const [name]of candidates){const m=results.variants[name].metrics;m.positive_n=m.TP+m.FN;m.negative_n=m.FP+m.TN;m.agreement=(m.TP+m.TN)/618;m.detection=m.TP/m.positive_n;m.false_award_rate=m.FP/m.negative_n;const c=results.variants[name].changes;results.variants[name].delta={recovered_observed_brilliants:c.filter(r=>r.label==='brilliant'&&r.experimental.symbol==='!!').length,lost_observed_brilliants:c.filter(r=>r.label==='brilliant'&&r.experimental.symbol!=='!!').length,new_false_awards:c.filter(r=>r.label==='non_brilliant'&&r.experimental.symbol==='!!').length,removed_false_awards:c.filter(r=>r.label==='non_brilliant'&&r.experimental.symbol!=='!!').length};}
results.elapsed_ms=Date.now()-start;results.rss_bytes=process.memoryUsage().rss;results.max_rss_kib=process.resourceUsage().maxRSS;
writeFileSync(join(root,'safe-alternative-experiments.json'),JSON.stringify(results,null,2)+'\n');
console.log(JSON.stringify({n:results.n,parity:results.baseline_parity,variants:Object.fromEntries(Object.entries(results.variants).map(([n,v]:any)=>[n,{metrics:v.metrics,delta:v.delta}])),elapsed_ms:results.elapsed_ms,max_rss_kib:results.max_rss_kib},null,2));
