// One bounded prospective-v7 independent200 selection-descriptor job. No engine or move-quality inference.
import {readFileSync,writeFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {dirname,join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {isMuteSacrifice} from '../brilliants-600-2026-11-03/reference/current-v2/noSweatClassify.ts';
const root=dirname(fileURLToPath(import.meta.url));
const source=join(root,'../brilliants-600-2026-11-03/reference/current-v2/noSweatClassify.ts');
const expected='43d249f76465b1d0966e486a2877a0887d8d1ed629f9e4aafaca67e3ce020234';
if(createHash('sha256').update(readFileSync(source)).digest('hex')!==expected)throw new Error('Frozen raw-v2 source changed');
const started=Date.now();const rows=JSON.parse(readFileSync(join(root,'control-preparation-input.json'),'utf8'));
if(rows.length>20000)throw new Error('Bounded descriptor cap exceeded');
let computed=0;
for(const r of rows){
 if(Date.now()-started>30000)throw new Error('30-second descriptor time cap reached; no retry');
 if(r.current_v2_legal_piece_offer===undefined){r.current_v2_legal_piece_offer=isMuteSacrifice(r.fen_before,r.fen_after);r.offer_source='pinned raw-v2 descriptor computed in prospective-v7 independent200';computed++;}
 r.sampling_priority=r.current_v2_legal_piece_offer?'apparent_piece_offer':!r.capture&&!['p','k'].includes(r.moved_piece.toLowerCase())&&r.moved_piece_attacked&&r.moved_piece_defended?'quiet_attacked_defended_piece':r.recapture_same_square?'recapture_exchange':r.capture?'other_capture':'other_quiet';
 r.source_link=`https://www.chess.com/analysis/game/${r.game_type}/${r.game_id}/review?move=${r.ply-1}`;
}
const summary:any={prepared_at:new Date().toISOString(),source_commit:'b3585f2c5b818bb8dfabb7fc4e3ed37cab848c12',source_sha256:expected,positions:rows.length,new_predicates:computed,accounts:{}};
for(const account of ['KNVB','hansen','GothamChess','Hikaru','nelsi']){
 const prefix=account.toLowerCase();const queue=JSON.parse(readFileSync(join(root,`${prefix}-ui-queue.json`),'utf8'));
 const controls=rows.filter(r=>r.account===account);
 controls.sort((a,b)=>Number(b.current_v2_legal_piece_offer)-Number(a.current_v2_legal_piece_offer)||Number(b.sampling_priority==='quiet_attacked_defended_piece')-Number(a.sampling_priority==='quiet_attacked_defended_piece')||a.game_id.localeCompare(b.game_id)||a.ply-b.ply);
 queue.controls=controls;queue.control_source={policy:'Pinned unchanged raw-v2 legal-offer selection descriptor',source_commit:summary.source_commit,source_sha256:expected,prepared_at:summary.prepared_at,labels:'UNKNOWN until explicit current UI review; not engine classification'};
 writeFileSync(join(root,`${prefix}-ui-queue.json`),JSON.stringify(queue,null,2)+'\n');
 writeFileSync(join(root,`control-candidates-v2-${prefix}.json`),JSON.stringify({source:queue.control_source,rows:controls},null,2)+'\n');
 summary.accounts[account]={targets:queue.targets.length,controls:controls.length,apparent_offers:controls.filter(r=>r.current_v2_legal_piece_offer).length};
}
summary.elapsed_ms=Date.now()-started;summary.rss_bytes=process.memoryUsage().rss;summary.max_rss_kib=process.resourceUsage().maxRSS;
writeFileSync(join(root,'control-preparation-summary.json'),JSON.stringify(summary,null,2)+'\n');console.log(JSON.stringify(summary,null,2));
