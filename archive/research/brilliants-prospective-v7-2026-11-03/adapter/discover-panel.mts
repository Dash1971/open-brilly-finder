// Board-only screening with frozen recovery proof. No scores, classifier outputs or labels.
import {readFileSync,writeFileSync,existsSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {parsePgn,startingPosition} from 'chessops/pgn';
import {makeFen} from 'chessops/fen';
import {parseSan,makeSan} from 'chessops/san';
import {legalMoves,standardUci} from '../sources/native/ui/analyse/src/noSweatCore.ts';
import {existingOfferRecovery} from '../sources/native/ui/analyse/src/noSweatRecoveryProof.ts';
const root=new URL('../',import.meta.url);const [poolPath,outPath]=process.argv.slice(2);if(!outPath)throw Error('Expected frozen500-PGN pool and output');
const hash=(p:any)=>createHash('sha256').update(readFileSync(p)).digest('hex');const go=JSON.parse(readFileSync(new URL('SF18-GO.json',root),'utf8'));
if(!go.panel_discovery || go.panel_pool_sha256!==hash(poolPath) || go.panel_discovery_sha256!==hash(new URL(import.meta.url)))throw Error('Root board-discovery GO/hash binding absent');
if(existsSync(outPath))throw Error('No automatic discovery replacement');const pool=JSON.parse(readFileSync(poolPath,'utf8'));if(pool.games.length!==500||new Set(pool.games.map((g:any)=>g.game_id)).size!==500)throw Error('Require frozen500 distinctgames');
const exclusionUrl=new URL(pool.known_position_exclusions_artifact,root);
if(hash(exclusionUrl)!==pool.known_position_exclusions_sha256)throw Error('Known-position exclusions changed');
const exclusions=new Set(JSON.parse(readFileSync(exclusionUrl,'utf8')).canonical_first_four);
const canonical=(fen:string)=>fen.split(' ').slice(0,4).join(' ');
const targets:any[]=[],audit:any[]=[];let scanned=0,captures=0,excludedPositions=0;
for(const game of pool.games){if(targets.length===300)break;
 if(createHash('sha256').update(game.pgn).digest('hex')!==game.pgn_sha256)throw Error('PGN bytes changed');
 const parsed=parsePgn(game.pgn);if(parsed.length!==1)throw Error('Ambiguous PGN');const pos=startingPosition(parsed[0].headers).unwrap();if(pos.rules!=='chess')throw Error('Nonstandard poolgame');let ply=0;
 for(const node of parsed[0].moves.mainline()){if(targets.length===300)break;ply++;scanned++;
  const move=parseSan(pos,node.san);if(!move||!('from'in move))throw Error('Illegal pool PGN');const before=makeFen(pos.toSetup()),uci=standardUci(pos,move),san=makeSan(pos,move);
  const victim=pos.board.get(move.to),mover=pos.board.get(move.from);const capture=!!((victim&&victim.color!==pos.turn)||(mover?.role==='pawn'&&move.to===pos.epSquare));const wasCheck=pos.isCheck();pos.play(move);
  if(!capture||move.promotion||wasCheck||pos.isCheck())continue;captures++;const after=makeFen(pos.toSetup());if(exclusions.has(canonical(before))||exclusions.has(canonical(after))){excludedPositions++;continue;}let result:any;
  // Placeholder roots exercise only board proof membership, never engine evidence.
  for(const acceptance of legalMoves(pos)){
   const p=pos.board.get(acceptance.to);if(!p||p.color===pos.turn||p.role==='pawn'||p.role==='king')continue;
   const rootUci=standardUci(pos,acceptance);const placeholder={depth:0,lines:[{moves:[rootUci]}]};result=existingOfferRecovery(before,after,uci,placeholder,placeholder);
   if(result.status!=='best-defense-declines-offer')break;
  }
  if(result?.status==='unknown')audit.push({game_id:game.game_id,ply,status:'unknown'});
  if(result?.veto)targets.push({game_id:game.game_id,account:game.account,ply,san,uci,fen_before:before,fen_after:after,pgn_sha256:game.pgn_sha256,ordering_hash:game.ordering_hash,source_link:game.source_link,board_prefilter:result});
 }
}
writeFileSync(outPath,JSON.stringify({frozen_at_utc:new Date().toISOString(),scope:'Board-only recovery candidates, not actual v7 activations; root placeholders are not engine scores',pool_sha256:hash(poolPath),script_sha256:hash(new URL(import.meta.url)),pool_games:500,scanned_plies:scanned,eligible_capture_positions:captures,known_position_exclusions_sha256:pool.known_position_exclusions_sha256,excluded_positions:excludedPositions,selected_count:targets.length,cap:300,targets,unknowns:audit},null,2)+'\n');console.log(JSON.stringify({candidates:targets.length,scanned,unknown:audit.length}));
