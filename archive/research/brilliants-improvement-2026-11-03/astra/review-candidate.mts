import {readFileSync} from 'node:fs';
import {hasMatingAcceptance,continuedOfferWhileInCheck,convertedMaterialOrEndgame} from '../root/candidate-source/noSweatClassify.ts';
const base='/Users/da/Documents/ChatGPT/No Sweat Chess/';
const data=JSON.parse(readFileSync(base+'mute-chess-research/studies/brilliant-moves/analysis-baseline.json','utf8'));
const features=JSON.parse(readFileSync(base+'research/brilliants-improvement-2026-11-03/astra/all-618-mate-history-features.json','utf8'));
const byKey=new Map(features.rows.map((x:any)=>[x.key,x]));const mismatches:any[]=[];let mates=0,continuations=0;
for(const t of data.targets){const key=t.game_id+':'+t.ply;const f:any=byKey.get(key);const previous=t.snapshot_ids.length>=3?data.snapshots[t.snapshot_ids[t.snapshot_ids.length-3]].fen:undefined;
const mate=hasMatingAcceptance(t.fen_before,t.fen_after),continued=continuedOfferWhileInCheck(previous,t.fen_before,t.fen_after,t.uci);if(mate)mates++;if(continued)continuations++;
if(mate!==f.acceptance_mate_in_one||continued!==f.unchanged_offer_check_evasion)mismatches.push({key,mate,expectedMate:f.acceptance_mate_in_one,continued,expectedContinued:f.unchanged_offer_check_evasion});}
console.log(JSON.stringify({n:data.targets.length,mates,continuations,mismatches}));
