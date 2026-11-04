// Freeze ordered model-discordant panel before its current Chess.com labels are collected.
import {readFileSync,writeFileSync,existsSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {classify,naiveMaterial} from '../sources/native/ui/analyse/src/noSweatClassify.ts';
const [corePath,queuePath,outPath]=process.argv.slice(2);if(!outPath)throw Error('Expected complete panel core, candidate queue, output freeze');if(existsSync(outPath))throw Error('No activation reselection');
const hash=(p:any)=>createHash('sha256').update(readFileSync(p)).digest('hex');const core=JSON.parse(readFileSync(corePath,'utf8')),queue=JSON.parse(readFileSync(queuePath,'utf8'));
if(core.status!=='complete'||core.stage!=='panel'||core.queue_sha256!==hash(queuePath)||core.nodes_per_position!==300000)throw Error('Incomplete or changed frozen panel evidence');
const targets=new Map(core.targets.map((t:any)=>[t.game_id+':'+t.ply,t]));const cache=new Map<string,number>();const material=(f:string)=>{if(!cache.has(f))cache.set(f,naiveMaterial(f));return cache.get(f)!};const rows:any[]=[],selected:any[]=[];const games=new Set<string>();
for(const c of queue.targets){const key=c.game_id+':'+c.ply,t:any=targets.get(key);if(!t)throw Error('Missing candidate evidence:'+key);
 const ss=t.snapshot_ids.map((id:string)=>core.snapshots[id]);const input:any={positions:ss.map((s:any)=>s.fen),reviews:ss.map((s:any)=>({current:s.current,previous:s.previous||undefined,terminal:s.terminal,quality:'fixed-sf18:'+core.engine_sha256})),move:t.uci,ply:t.ply,history:[]};
 // Every candidate is a capture: frozen S temporal restriction is ineligible, so no earlier-origin bank is needed.
 const v6=classify({...input,policy:'mute-brilliant-v6'},material),v7=classify({...input,policy:'mute-brilliant-v7'},material);const activated=v6.symbol==='!!'&&v7.symbol!=='!!'&&v7.recoveryProof?.veto===true;
 const row={key,game_id:c.game_id,account:c.account,ply:c.ply,san:c.san,source_link:c.source_link,v6,v7,activated};rows.push(row);
 if(activated&&selected.length<30&&!games.has(c.game_id)){games.add(c.game_id);selected.push(row);}
}
writeFileSync(outPath,JSON.stringify({frozen_at_utc:new Date().toISOString(),scope:'First30 distinct-game actual v7 recovery-veto activations in frozen candidate order; CURRENT LABELS MUST BE COLLECTED ONLY AFTER THIS FILE IS FROZEN',script_sha256:hash(new URL(import.meta.url)),core_sha256:hash(corePath),candidate_queue_sha256:hash(queuePath),count:selected.length,selection: selected,all_candidates:rows},null,2)+'\n');console.log(JSON.stringify({candidates:rows.length,activations:rows.filter(r=>r.activated).length,selected_distinct_games:selected.length}));
