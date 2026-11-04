// Unchanged saved classifiers; evaluation wrapper only, after complete fresh core.
import {readFileSync,writeFileSync,existsSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {dirname,join} from 'node:path';
import {classify as v4,annotation,isSacrifice,naiveMaterial} from '../../root/frozen-v4/noSweatClassify.ts';
import {classify as A} from '../../astra/v5/variants/variantA.ts';
const root=dirname(fileURLToPath(import.meta.url));
const read=(p:string)=>JSON.parse(readFileSync(p,'utf8'));
const hash=(p:string)=>createHash('sha256').update(readFileSync(p)).digest('hex');
const oldroot=join(root,'../../uniform-stronger-v5');
const frozen=read(join(oldroot,'REPLAY-SOURCE-FREEZE.json'));
for(const [path,sha]of Object.entries(frozen.source_hashes))if(hash(join(oldroot,path))!==sha)throw Error('Frozen source changed: '+path);
const data=read(join(root,'analysis-core.json')),primary=read(join(root,'primary-moves.json'));
if(data.status!=='complete'||data.nodes_per_position!==300000||data.targets.length!==200||Object.keys(data.snapshots).length>600)throw Error('Complete core required');
const identities=new Map(primary.map((t:any)=>[t.game_id+':'+t.ply,t]));
const materialCache=new Map<string,number>();
for(const s of Object.values(data.snapshots) as any[])if(s.ec_material!==undefined)materialCache.set(s.fen,s.ec_material);
const material=(fen:string)=>{if(!materialCache.has(fen))materialCache.set(fen,naiveMaterial(fen));return materialCache.get(fen)!;};
const rows:any[]=[];
for(const t of data.targets){
 const key=t.game_id+':'+t.ply,identity:any=identities.get(key);
 if(!identity||identity.uci!==t.uci||identity.fen_before!==t.fen_before||identity.fen_after!==t.fen_after)throw Error('Identity mismatch '+key);
 const ss=t.snapshot_ids.map((id:string)=>data.snapshots[id]),n=ss.length,color=t.fen_before.split(' ')[1]==='w'?'white':'black';
 const input={positions:ss.map((s:any)=>s.fen),reviews:ss.map((s:any)=>({current:s.current,previous:s.previous||undefined,terminal:s.terminal,quality:'sf18:'+data.engine_sha256+':'+data.nodes_per_position})),move:t.uci,policy:'mute-brilliant-v4'};
 const direct=annotation(n>2?ss[n-3].current?.lines[0]:undefined,ss[n-2].current,ss[n-1].current.lines[0],color,t.uci,isSacrifice(t.fen_before,t.fen_after,material));
 rows.push({key,game_id:t.game_id,ply:t.ply,san:t.san,v4:v4(input as any,material),A:A(input as any,material),ec_direct_symbol:direct,ec_confirmed:v4({...input,policy:'en-croissant'} as any,material)});
}
const out=join(root,'rule-predictions.json');if(existsSync(out))throw Error('Refusing to replace replay');
writeFileSync(out,JSON.stringify({scope:'Frozen fresh-test predictions; no classifier tuning, no partial metrics.',core_sha256:hash(join(root,'analysis-core.json')),source_freeze:frozen,rows},null,2)+'\n');
console.log(JSON.stringify({status:'complete',predictions:rows.length,metrics_computed:false}));
