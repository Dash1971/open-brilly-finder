// Bounded study replay. Reads supplied saved evidence; never starts an engine/browser.
import {readFileSync,writeFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {dirname,join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {classify as v4} from './frozen-v4/noSweatClassify.ts';
import {classify as v3,naiveMaterial} from '../missed/baseline-v3/noSweatClassify.ts';
const root=dirname(fileURLToPath(import.meta.url));
const study=join(root,'../../../mute-chess-research/studies/brilliant-moves');
const source=process.argv[2]||join(study,'analysis-baseline.json');
const output=process.argv[3]||join(root,'frozen-v4-development.json');
const data=JSON.parse(readFileSync(source,'utf8'));
const old=JSON.parse(readFileSync(join(root,'concrete-offer-experiments.json'),'utf8'));
const materialCache=new Map<string,number>();
const material=(fen:string)=>{if(!materialCache.has(fen))materialCache.set(fen,naiveMaterial(fen));return materialCache.get(fen)!;};
const tally=()=>({TP:0,FN:0,FP:0,TN:0});
const metrics={v3:tally(),v4:tally()};const rows:any[]=[];const started=Date.now();
for(const t of data.targets){
 const snapshots=t.snapshot_ids.map(id=>data.snapshots[id]);
 const input={positions:snapshots.map(s=>s.fen),reviews:snapshots.map(s=>({current:s.current,previous:s.previous||undefined,terminal:s.terminal,quality:'fixed-sf18:'+data.engine_sha256})),move:t.uci};
 const a=v3({...input,policy:'mute-brilliant-v3'},material);const b=v4({...input,policy:'mute-brilliant-v4'},material);
 const truth=[...new Set(t.observations.filter(x=>x.source_type==='fresh_review'&&x.label!=='unknown').map(x=>x.label==='!!'))];
 if(truth.length!==1)throw new Error('Missing/unreconciled explicit label');
 const pos=truth[0];
 for(const [k,v]of [['v3',a],['v4',b]] as const)metrics[k][pos?(v.symbol==='!!'?'TP':'FN'):(v.symbol==='!!'?'FP':'TN')]++;
 rows.push({game_id:t.game_id,ply:t.ply,san:t.san,truth_brilliant:pos,v3:a,v4:b});
}
if(data.targets.length===618){
 const prior=old.variants.combined;for(const k of ['TP','FN','FP','TN'])if(prior.metrics[k]!==metrics.v4[k])throw new Error('Clean candidate differs from exploratory combination: '+k);
 const expectedChanges=new Set(prior.changes.map(x=>x.key));const actualChanges=rows.filter(x=>(x.v3.symbol==='!!')!==(x.v4.symbol==='!!'));
 if(actualChanges.length!==expectedChanges.size||actualChanges.some(x=>!expectedChanges.has(`${x.game_id}:${x.ply}`)))throw new Error('Clean candidate changed a different set');
}
const result={scope:data.targets.length===618?'All618 unblinded development; not a fresh validation result.':'Frozen policy on supplied fresh evidence; no tuning.',source_sha256:createHash('sha256').update(readFileSync(source)).digest('hex'),candidate_sha256:createHash('sha256').update(readFileSync(join(root,'frozen-v4/noSweatClassify.ts'))).digest('hex'),metrics,rows,elapsed_ms:Date.now()-started,max_rss_kib:process.resourceUsage().maxRSS};
writeFileSync(output,JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify({output,metrics,rows:rows.length,elapsed_ms:result.elapsed_ms}));
