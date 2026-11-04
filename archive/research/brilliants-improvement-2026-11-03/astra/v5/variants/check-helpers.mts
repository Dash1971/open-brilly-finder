import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {hasAttributableMatingAcceptance,noNonOfferingEscape,hasDirectStalemateAcceptance} from './offerProofs.ts';
import {hasMatingAcceptance} from '../../../root/frozen-v4/noSweatClassify.ts';
const base='/Users/da/Documents/ChatGPT/No Sweat Chess/';
const rows:any[]=JSON.parse(readFileSync(base+'research/brilliants-improvement-2026-11-03/astra/v5/avoidability848.json','utf8')).rows;
const result=JSON.parse(readFileSync(base+'research/brilliants-improvement-2026-11-03/astra/v5/variants/results.json','utf8'));
const byKey=new Map(rows.map(x=>[x.key,x]));const knownMismatch:any[]=[];const capDifferences:any[]=[];
for(const r of result.rows){const old:any=byKey.get(r.key);const expected=old.avoidability512.avoidable===null?null:!old.avoidability512.avoidable;const actual=r.features.noNonOfferingEscape;
if(expected!==actual){if(expected!==null&&actual!==null)knownMismatch.push({key:r.key,expected,actual});else capDifferences.push({key:r.key,expected,actual});}}
assert.equal(knownMismatch.length,0,'Completed Python and TS proofs must agree');
const data=JSON.parse(readFileSync(base+'research/brilliants-final-2026-11-03/analysis-baseline.json','utf8'));
function fixture(key:string){const t=data.targets.find((x:any)=>x.game_id+':'+x.ply===key);const previous=data.snapshots[t.snapshot_ids[t.snapshot_ids.length-3]].fen;return {...t,previous};}
const q=fixture('187780686673:36'),h=fixture('169827191694:65'),n=fixture('185741429132:55');
assert.equal(hasMatingAcceptance(q.fen_before,q.fen_after),true);
assert.equal(hasAttributableMatingAcceptance(q.previous,q.fen_before,q.fen_after,q.uci),false);
assert.equal(hasAttributableMatingAcceptance(h.previous,h.fen_before,h.fen_after,h.uci),true);
assert.equal(hasAttributableMatingAcceptance(undefined,h.fen_before,h.fen_after,h.uci),false);
assert.equal(hasAttributableMatingAcceptance(undefined,n.fen_before,n.fen_after,n.uci),true);
assert.equal(hasDirectStalemateAcceptance(h.fen_before,h.fen_after),false);
console.log(JSON.stringify({completed_proof_mismatches:knownMismatch,cap_ordering_differences:capDifferences,focused_assertions:6}));
