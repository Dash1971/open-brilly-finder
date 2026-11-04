// Fixed source replay; source inputs contain positions/windows, never observed labels.
import {readFileSync,writeFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {DatabaseSync} from 'node:sqlite';
import {classify,annotation,isSacrifice,naiveMaterial} from '../sources/native/ui/analyse/src/noSweatClassify.ts';
import {position} from '../sources/native/ui/analyse/src/noSweatCore.ts';
const root=new URL('../',import.meta.url);const load=(p:any)=>JSON.parse(readFileSync(p,'utf8'));const hash=(p:any)=>createHash('sha256').update(readFileSync(p)).digest('hex');
const [corePath,supplementPath,dbPath,outPath]=process.argv.slice(2);if(!outPath)throw Error('Expected frozen core, separate supplement, PGN database, output');
const go=load(new URL('EVALUATION-GO.json',root));if(!go.paired_primary || go.primary_adapter_sha256!==hash(new URL(import.meta.url)) || go.core_sha256!==hash(corePath) || go.supplement_sha256!==hash(supplementPath) || go.database_sha256!==hash(dbPath))throw Error('Root paired evaluation GO/hash binding absent');
const freeze=load(new URL('FREEZE.json',root));for(const [p,v]of Object.entries(freeze.files)as any)if(hash(new URL(p,root))!==v.sha256)throw Error('Frozen source changed:'+p);
const core=load(corePath),sup=load(supplementPath);if(core.engine_sha256!==sup.engine_sha256)throw Error('Mixed engine domain');const snapshots={...core.snapshots};for(const[k,v]of Object.entries(sup.snapshots)){if(snapshots[k])throw Error('Supplement would replace core');snapshots[k]=v;}
const db=new DatabaseSync(dbPath,{readOnly:true});const query=db.prepare('select * from positions where game_id=? and ply=?');
const cache=new Map<string,number>();const material=(f:string)=>{if(!cache.has(f))cache.set(f,naiveMaterial(f));return cache.get(f)!;};
const window=(id:string,ply:number)=>{const ids=[Math.max(0,ply-2),ply-1,ply].filter((x,i,a)=>i===0||a[i-1]!==x).map(x=>id+':'+x);const missing=ids.filter(k=>!snapshots[k]);if(missing.length)return{missing};const ss=ids.map(k=>snapshots[k]);return{positions:ss.map(s=>s.fen),reviews:ss.map(s=>({current:s.current,previous:s.previous||undefined,terminal:s.terminal,quality:'fixed-sf18:'+core.engine_sha256})),snapshot_ids:ids};};
const rows:any[]=[];
for(const t of core.targets){const key=t.game_id+':'+t.ply;const current:any=window(t.game_id,t.ply);if(current.missing){rows.push({key,status:'incomplete-core',missing:current.missing});continue;}
 const played:any=query.get(t.game_id,t.ply);if(!played||current.positions.at(-2)!==played.fen_before||current.positions.at(-1)!==played.fen_after)throw Error('PGN/window identity mismatch:'+key);
 const history:any[]=[];const missingOrigins:any[]=[];
 for(let ply=Math.max(1,t.ply-6);ply<t.ply;ply++){const d:any=query.get(t.game_id,ply);if(!d)throw Error('Missing physical PGN history');const old:any=window(t.game_id,ply);if((t.ply-ply)%2===0&&old.missing)missingOrigins.push({ply,missing:old.missing});history.push({ply,before:d.fen_before,after:d.fen_after,move:d.uci,...old});}
 const input:any={positions:current.positions,reviews:current.reviews,move:played.uci,ply:t.ply,history};const v7=classify({...input,policy:'mute-brilliant-v7'},material),v6=classify({...input,policy:'mute-brilliant-v6'},material);
 const n=input.reviews.length,b=input.reviews[n-2],a=input.reviews[n-1],p=input.reviews[n-3],color=position(input.positions[n-2]).turn;
 const ec=annotation(p?.current.lines[0],b.current,a.current.lines[0],color,input.move,isSacrifice(input.positions[n-2],input.positions[n-1],material));
 rows.push({key,status:'complete-core',snapshot_ids:current.snapshot_ids,missing_origin_windows:missingOrigins,v7,v6,ec_direct:ec,ec_confirmed:classify({...input,policy:'en-croissant'},material)});
}
db.close();writeFileSync(outPath,JSON.stringify({source_freeze_sha256:hash(new URL('FREEZE.json',root)),core_sha256:hash(corePath),supplement_sha256:hash(supplementPath),rows},null,2)+'\n');console.log(JSON.stringify({cases:rows.length,output:outPath}));
