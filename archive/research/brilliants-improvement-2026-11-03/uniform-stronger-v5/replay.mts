// Exact saved-source paired replay. EC direct and EC confirmed are explicitly distinct.
import {readFileSync,writeFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {dirname,join} from 'node:path';
import {classify as v4,annotation,isSacrifice,naiveMaterial} from '../root/frozen-v4/noSweatClassify.ts';
import {classify as A} from '../astra/v5/variants/variantA.ts';
const root=dirname(fileURLToPath(import.meta.url)),research=join(root,'../..'),final=join(research,'brilliants-final-2026-11-03');
const read=(p:string)=>JSON.parse(readFileSync(p,'utf8'));
const hash=(p:string)=>createHash('sha256').update(readFileSync(p)).digest('hex');
const frozen=read(join(root,'REPLAY-SOURCE-FREEZE.json'));
for(const [path,sha]of Object.entries(frozen.source_hashes))if(hash(join(root,path))!==sha)throw Error('Frozen replay source changed: '+path);
const selections=read(join(root,'primary-moves.json')),identities=new Map(selections.map((t:any)=>[t.game_id+':'+t.ply,t]));
const files=[join(final,'analysis-baseline.json'),join(final,'analysis-panel.json')];
const baseline=files.map(read),strongPath=join(root,'analysis-uniform.json');
const stages:any={baseline};if(!process.argv.includes('--baseline-only')){const strong=read(strongPath);if(strong.status!=='complete'||strong.targets.length!==848||Object.keys(strong.snapshots).length!==2445)throw Error('Uniform evidence incomplete; no partial/old substitution');stages.uniform=[strong];}
const materialCache=new Map<string,number>();
for(const sets of Object.values(stages) as any[])for(const d of sets)for(const s of Object.values(d.snapshots) as any[])if(s.ec_material!==undefined){const old=materialCache.get(s.fen);if(old!==undefined&&old!==s.ec_material)throw Error('Static EC material conflict');materialCache.set(s.fen,s.ec_material);}
const material=(fen:string)=>{if(!materialCache.has(fen))materialCache.set(fen,naiveMaterial(fen));return materialCache.get(fen)!;};
const rows:any[]=[];
for(const [stage,datasets]of Object.entries(stages) as any){
 for(const data of datasets){for(const t of data.targets){
  const key=t.game_id+':'+t.ply,identity:any=identities.get(key);if(!identity||identity.uci!==t.uci||identity.fen_before!==t.fen_before||identity.fen_after!==t.fen_after)throw Error('Frozen identity mismatch '+key);
  const snaps=t.snapshot_ids.map((id:string)=>data.snapshots[id]),n=snaps.length,color=t.fen_before.split(' ')[1]==='w'?'white':'black';
  if(snaps[n-2].fen!==t.fen_before||snaps[n-1].fen!==t.fen_after)throw Error('Snapshot identity mismatch '+key);
  const input={positions:snaps.map((s:any)=>s.fen),reviews:snaps.map((s:any)=>({current:s.current,previous:s.previous||undefined,terminal:s.terminal,quality:'sf18:'+data.engine_sha256+':'+data.nodes_per_position})),move:t.uci,policy:'mute-brilliant-v4'};
  const ecDirect=annotation(n>2?snaps[n-3].current?.lines[0]:undefined,snaps[n-2].current,snaps[n-1].current.lines[0],color,t.uci,isSacrifice(t.fen_before,t.fen_after,material));
  rows.push({stage,key,game_id:t.game_id,ply:t.ply,san:t.san,truth:identity.fresh_label==='!!',label:identity.fresh_label,cohort:identity.split==='mechanism_panel'?'panel30':identity.source_cohort==='reference618'?'old618':'recent200',v4:v4(input as any,material),A:A(input as any,material),ec_direct_symbol:ecDirect,ec_confirmed:v4({...input,policy:'en-croissant'} as any,material)});
 }}
}
function tally(selected:any[],name:string){const m:any={TP:0,FN:0,FP:0,TN:0};for(const r of selected){const award=name==='ec_direct'?r.ec_direct_symbol==='!!':r[name].symbol==='!!';m[r.truth?(award?'TP':'FN'):(award?'FP':'TN')]++;}m.n=selected.length;m.agreement=(m.TP+m.TN)/m.n;m.recall=m.TP/(m.TP+m.FN);m.false_award_rate=m.FP/(m.FP+m.TN);m.sample_precision=m.TP/(m.TP+m.FP);return m;}
const summaries:any={};for(const stage of Object.keys(stages)){summaries[stage]={};for(const cohort of ['all848','core818','old618','recent200','panel30']){const selected=rows.filter(r=>r.stage===stage&&(cohort==='all848'||(cohort==='core818'?r.cohort!=='panel30':r.cohort===cohort)));summaries[stage][cohort]=Object.fromEntries(['ec_direct','ec_confirmed','v4','A'].map(name=>[name,tally(selected,name)]));}}
if(summaries.baseline.all848.v4.TP!==322||summaries.baseline.all848.v4.FP!==28||summaries.baseline.all848.A.TP!==322||summaries.baseline.all848.A.FP!==27||summaries.baseline.old618.ec_direct.TP!==84||summaries.baseline.old618.ec_direct.FP!==6)throw Error('Existing saved baseline parity failed');
const changes:any={};if(stages.uniform){const old=new Map(rows.filter(r=>r.stage==='baseline').map(r=>[r.key,r]));for(const name of ['ec_direct','ec_confirmed','v4','A'])changes[name]=rows.filter(r=>r.stage==='uniform').filter(r=>{const b:any=old.get(r.key);return(name==='ec_direct'?r.ec_direct_symbol==='!!':r[name].symbol==='!!')!==(name==='ec_direct'?b.ec_direct_symbol==='!!':b[name].symbol==='!!');}).map(r=>({key:r.key,san:r.san,truth:r.truth,before:(old.get(r.key) as any)[name==='ec_direct'?'ec_direct_symbol':name],after:r[name==='ec_direct'?'ec_direct_symbol':name]}));}
const output={scope:'All848development. Uniform stronger budget is a full-corpus sensitivity check, not new validation. Direct EC current annotation and EC confirmed/shared-window outputs are separate; Mute v4/A are full-window confirmed.',source_freeze:frozen,input_hashes:Object.fromEntries([...files,...(stages.uniform?[strongPath]:[])].map(p=>[p,hash(p)])),summaries,changes,rows};
const destination=join(root,stages.uniform?'paired-results.json':'baseline-results.json');writeFileSync(destination,JSON.stringify(output,null,2)+'\n');console.log(JSON.stringify({summaries,changed_counts:Object.fromEntries(Object.entries(changes).map(([k,v]:any)=>[k,v.length]))},null,2));
