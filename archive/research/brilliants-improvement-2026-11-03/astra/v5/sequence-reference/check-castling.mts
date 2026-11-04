import assert from 'node:assert/strict';
import {repeatContinuation} from './temporalProof.ts';
// All positions contain an offered white rook on a1, attacked by a black rook on a8.
const cases=[
 {name:'diagonal Ke1-f2',before:'r3k3/8/8/8/8/8/8/R3K3 w - - 0 1',after:'r3k3/8/8/8/8/8/5K2/R7 b - - 1 1',uci:'e1f2',expected:'complete'},
 {name:'vertical Ke1-e2',before:'r3k3/8/8/8/8/8/8/R3K3 w - - 0 1',after:'r3k3/8/8/8/8/8/4K3/R7 b - - 1 1',uci:'e1e2',expected:'complete'},
 {name:'standard O-O',before:'r3k3/8/8/8/8/8/8/R3K2R w K - 0 1',after:'r3k3/8/8/8/8/8/8/R4RK1 b - - 1 1',uci:'e1g1',expected:'ineligible'},
 {name:'rook-square O-O',before:'r3k3/8/8/8/8/8/8/R3K2R w K - 0 1',after:'r3k3/8/8/8/8/8/8/R4RK1 b - - 1 1',uci:'e1h1',expected:'ineligible'},
];
for(const c of cases){const r=repeatContinuation({ply:1,before:c.before,after:c.after,uci:c.uci,confirmedBaseAward:true},[]);assert.equal(r.status,c.expected,c.name);assert.equal(r.veto,false);}
console.log('PASS diagonal and vertical king moves reach proof; standard and rook-square castling are exempt.');
