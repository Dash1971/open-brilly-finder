// Label-independent completion of all possible own-turn origins for quiet base-A awards.
import {readFileSync,writeFileSync,existsSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {DatabaseSync} from 'node:sqlite';
import {classify} from '../sources/native/ui/analyse/src/noSweatClassify.ts';
import {position} from '../sources/native/ui/analyse/src/noSweatCore.ts';
import {parseUci} from 'chessops/util';
const [corePath,dbPath,outPath]=process.argv.slice(2);if(!outPath)throw Error('Expected completed core, frozen database, output queue');
if(existsSync(outPath))throw Error('No automatic queue replacement');
const hash=(p:any)=>createHash('sha256').update(readFileSync(p)).digest('hex');const core=JSON.parse(readFileSync(corePath,'utf8'));
if(core.status!=='complete'||core.targets.length!==200||core.nodes_per_position!==300000)throw Error('Require complete fixed200 core');
const db=new DatabaseSync(dbPath,{readOnly:true});const needed=new Map<string,any>();const origins:any[]=[];
for(const t of core.targets){const ss=t.snapshot_ids.map((id:string)=>core.snapshots[id]);const input={positions:ss.map((s:any)=>s.fen),reviews:ss.map((s:any)=>({current:s.current,previous:s.previous||undefined,terminal:s.terminal,quality:'fixed-sf18:'+core.engine_sha256})),move:t.uci,policy:'mute-history-base' as const};
 const result=classify(input);if(result.symbol!=='!!')continue;
 const before=position(t.fen_before),after=position(t.fen_after),move=parseUci(t.uci);if(!move||!('from'in move))throw Error('Invalid frozen move');
 const mover=before.board.get(move.from),victim=before.board.get(move.to);const capture=(victim&&victim.color!==before.turn)||(mover?.role==='pawn'&&move.to===before.epSquare);
 const castle=mover?.role==='king'&&((Math.floor(move.from/8)===Math.floor(move.to/8)&&Math.abs(move.from%8-move.to%8)===2)||(victim?.color===before.turn&&victim.role==='rook'));
 if(after.isCheck()||capture||move.promotion||castle)continue;
 for(let distance=1;distance<=3;distance++){const ply=t.ply-2*distance;if(ply<1)continue;
  if(!db.prepare('select 1 from positions where game_id=? and ply=?').get(t.game_id,ply))throw Error('Missing physical history');
  const ids=[Math.max(0,ply-2),ply-1,ply].filter((p,i,a)=>i===0||p!==a[i-1]);const missing=ids.filter(p=>!core.snapshots[t.game_id+':'+p]);
  origins.push({target:t.game_id+':'+t.ply,origin_ply:ply,missing});for(const p of missing)needed.set(t.game_id+':'+p,{game_id:t.game_id,ply:p});
 }
}
db.close();if(needed.size>1200)throw Error('Supplement exceeds fixed1200 cap');
const positions=[...needed.values()].sort((a,b)=>String(a.game_id).localeCompare(String(b.game_id))||a.ply-b.ply);
writeFileSync(outPath,JSON.stringify({frozen_at_utc:new Date().toISOString(),scope:'All possible prior own-turn baseA windows for confirmed quiet baseA candidates; no labels or prior glyphs; separate stream, no core replacement',core_path:corePath,core_sha256:hash(corePath),database_sha256:hash(dbPath),script_sha256:hash(new URL(import.meta.url)),positions,origins},null,2)+'\n');console.log(JSON.stringify({missing:positions.length,origins:origins.length,output:outPath}));
