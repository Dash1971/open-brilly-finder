// Bounded, study-specific prelabel challenge-panel selection. No engine or labels.
import fs from 'node:fs';
import crypto from 'node:crypto';
import { position, legalMoves, standardUci } from '../../root/frozen-v4/noSweatCore.ts';
import { hasMatingAcceptance, continuedOfferWhileInCheck, convertedMaterialOrEndgame } from '../../root/frozen-v4/noSweatClassify.ts';

const dir = new URL('.', import.meta.url);
const read = (name: string) => fs.readFileSync(new URL(name, dir), 'utf8');
const sha = (s: string) => crypto.createHash('sha256').update(s).digest('hex');
const inputText = read('selection-input.json');
const input = JSON.parse(inputText);
const source = fs.readFileSync(new URL('../../root/frozen-v4/noSweatClassify.ts', dir), 'utf8');
if (sha(source) !== input.candidate_source_sha256) throw Error('Frozen source changed');
const seed = 'mute-improvement-mechanism-v1';
const categories = ['mating_acceptance', 'unchanged_offer_while_in_check', 'phase_winning_context', 'cross_square_material_recoup'];
const value = (role: string) => ({pawn:90, knight:300, bishop:300, rook:500, queen:1000}[role] ?? 0);
const square = (s: number) => String.fromCharCode(97 + s % 8) + (1 + Math.floor(s / 8));
const raw = (p: any, mover: string) => [...p.board].reduce((n: number, [, q]: any) => n + value(q.role) * (q.color === mover ? 1 : -1), 0);
const captured = (p: any, m: any) => {
  const q = p.board.get(m.to);
  return q && q.color !== p.turn ? value(q.role) : p.board.get(m.from)?.role === 'pawn' && m.to === p.epSquare ? 90 : 0;
};
const ordered = (p: any) => legalMoves(p).sort((a, b) => standardUci(p,a).localeCompare(standardUci(p,b)));
const tick = (budget: any) => { if (++budget.used > 512) throw Error('budget'); };
function see(p: any, target: number, b: any): number {
  tick(b);
  let best = 0;
  for (const m of legalMoves(p)) {
    if (m.to !== target || !captured(p,m)) continue;
    const q = p.clone(); q.play(m);
    best = Math.max(best, captured(p,m) + (m.promotion ? value(m.promotion)-90 : 0) - see(q,target,b));
  }
  return best;
}
function offerProof(before: any, p: any) {
  const b = {used:0};
  const mover = before.turn;
  const credit = Math.max(0, raw(p,mover)-raw(before,mover));
  const offers: any[] = [];
  try {
    if (!p.isEnd()) for (const [s,q] of p.board) {
      if (q.color !== mover || q.role === 'pawn' || q.role === 'king') continue;
      const gain = see(p,s,b);
      if (gain > credit+100) offers.push({square:square(s),role:q.role,color:q.color,exchange_gain:gain});
    }
    return {status:'complete', probes:b.used, credit, offers};
  } catch(e) { if ((e as Error).message !== 'budget') throw e; return {status:'exhausted',probes:b.used,credit,offers:[]}; }
}
function mateProof(before: any, p: any) {
  const b = {used:0};
  const credit = Math.max(0,raw(p,before.turn)-raw(before,before.turn));
  try {
    for (const capture of ordered(p)) {
      const victim = p.board.get(capture.to);
      if (!victim || victim.color === p.turn || victim.role === 'pawn' || victim.role === 'king') continue;
      const child = p.clone(); child.play(capture);
      const net = captured(p,capture) + (capture.promotion ? value(capture.promotion)-90 : 0) - see(child,capture.to,b);
      if (net <= credit+100) continue;
      for (const reply of ordered(child)) {
        tick(b);
        const end = child.clone(); end.play(reply);
        if (end.isCheckmate()) return {status:'witness',probes:b.used,acceptance_net:net,credit,line:[standardUci(p,capture),standardUci(child,reply)]};
      }
    }
    return {status:'complete_no_witness',probes:b.used};
  } catch(e) { if ((e as Error).message !== 'budget') throw e; return {status:'exhausted',probes:b.used}; }
}
function recoupProof(before: any, p: any) {
  const b = {used:0};
  const mover = before.turn, initial = raw(before,mover);
  const credit = Math.max(0,raw(p,mover)-initial);
  function search(q: any, acceptedSquare: number, line: string[], trajectory: number[]): any {
    tick(b);
    for (const m of ordered(q)) {
      if (!captured(q,m)) continue;
      const child = q.clone(); child.play(m);
      const amount = raw(child,mover);
      const nextLine = [...line,standardUci(q,m)], nextTrajectory = [...trajectory,amount];
      if (q.turn === mover && amount >= initial) {
        if (m.to !== acceptedSquare)
          return {line:nextLine, material_trajectory:nextTrajectory, restored_material:amount,recoup_square:square(m.to)};
        // Recovery already completed on the acceptance square. A later,
        // unrelated capture cannot turn it into cross-square recovery.
        continue;
      }
      const found = search(child,acceptedSquare,nextLine,nextTrajectory);
      if (found) return found;
    }
  }
  try {
    for (const capture of ordered(p)) {
      const victim = p.board.get(capture.to);
      if (!victim || victim.color === p.turn || victim.role === 'pawn' || victim.role === 'king') continue;
      const child = p.clone(); child.play(capture);
      const net = captured(p,capture) + (capture.promotion ? value(capture.promotion)-90 : 0) - see(child,capture.to,b);
      if (net <= credit+100) continue;
      const found = search(child,capture.to,[standardUci(p,capture)],[raw(p,mover),raw(child,mover)]);
      if (found) return {status:'witness',probes:b.used,initial_material:initial,credit,acceptance_net:net,accepted_square:square(capture.to),...found};
    }
    return {status:'complete_no_witness',probes:b.used};
  } catch(e) { if ((e as Error).message !== 'budget') throw e; return {status:'exhausted',probes:b.used}; }
}
const byCategory: Record<string, any[]> = Object.fromEntries(categories.map(c=>[c,[]]));
const audit: any = {rows:input.rows.length, offer:{}, mate:{}, recoup:{}, checked_exact_true:0, source_helper_mismatch:0};
function count(group: string, status: string) { audit[group][status] = (audit[group][status] ?? 0)+1; }
for (const row of input.rows) {
  const before = position(row.fen_before), after = position(row.fen_after);
  const offer = offerProof(before,after); count('offer',offer.status);
  const features: any = {raw_offer:offer};
  const accepted: string[] = [];
  // Exact bounded source helper is authoritative; a separate bounded witness
  // must also complete before a case can be included in this category.
  if (hasMatingAcceptance(row.fen_before,row.fen_after)) {
    const mate = mateProof(before,after); features.mating_acceptance = mate;
    count('mate',mate.status);
    if (mate.status === 'witness') accepted.push(categories[0]);
  }
  if (continuedOfferWhileInCheck(row.previous_own_after_fen,row.fen_before,row.fen_after,row.uci)) {
    audit.checked_exact_true++;
    if (offer.status === 'complete' && offer.offers.length) {
      const old = position(row.previous_own_after_fen), b={used:0};
      try {
        const prior = offer.offers.map((q: any) => ({...q,previous_exchange_gain:see(old,(q.square.charCodeAt(0)-97)+8*(Number(q.square[1])-1),b)}));
        if (!prior.every((q: any)=>q.exchange_gain === q.previous_exchange_gain)) throw Error('source helper mismatch');
        features.checked_continuation = {status:'witness',probes:b.used,offers:prior};
        accepted.push(categories[1]);
      } catch(e) { if ((e as Error).message !== 'budget') throw e; }
    }
  }
  if (offer.status === 'complete' && offer.offers.length) {
    const phase = [...before.board].reduce((n: number,[,q]: any)=>n+({knight:1,bishop:1,rook:2,queen:4}[q.role]??0),0);
    const material = raw(before,before.turn);
    const relevant = convertedMaterialOrEndgame(row.fen_before);
    if (relevant !== (phase<=8 || material>=300)) throw Error('phase helper mismatch');
    features.structural_context = {phase,mover_material_before:material,converted_or_endgame:relevant,actual_winning_safe_alternative:'unknown_no_engine'};
    if (relevant) accepted.push(categories[2]);
    const recoup = recoupProof(before,after); count('recoup',recoup.status); features.cross_square_material_recoup=recoup;
    if (recoup.status === 'witness') accepted.push(categories[3]);
  }
  for (const category of accepted) {
    const hash = sha(`${seed}:${category}:${row.account.toLowerCase()}:${row.game_id}:${row.ply}`);
    byCategory[category].push({...row,category,selection_hash:hash,features});
  }
}
// Lowest hash case per category/game; deterministic maximum matching of40
// category slots to games. This avoids greedy starvation, without label input.
const candidates: any = {};
for (const category of categories) {
  const orderedCandidates=byCategory[category].sort((a,b)=>a.selection_hash.localeCompare(b.selection_hash));
  const seen = new Set(); candidates[category]=orderedCandidates.filter((r: any)=>!seen.has(r.game_id)&&seen.add(r.game_id));
}
const owner = new Map<string,string>(), assignments = new Map<string,any>();
function assign(slot: string, visited: Set<string>): boolean {
  const category=slot.split(':')[0];
  for (const r of candidates[category]) {
    if (visited.has(r.game_id)) continue; visited.add(r.game_id);
    const prior=owner.get(r.game_id);
    if (!prior || assign(prior,visited)) {owner.set(r.game_id,slot); assignments.set(slot,r); return true;}
  }
  return false;
}
for (let n=0;n<10;n++) for (const category of categories) assign(`${category}:${n}`,new Set());
const selected = [...assignments.entries()].sort(([a],[b])=>a.localeCompare(b)).map(([slot,r])=>({...r,slot}));
fs.writeFileSync(new URL('candidate-descriptors.json',dir),JSON.stringify({
  seed,input_sha256:sha(inputText),candidate_source_sha256:sha(source),current_labels_read:false,
  candidates:Object.fromEntries(categories.map(c=>[c,byCategory[c]])),
  representatives:Object.fromEntries(categories.map(c=>[c,candidates[c].map((r: any)=>({game_id:r.game_id,ply:r.ply,selection_hash:r.selection_hash}))])),
},null,2)+'\n');
const output = {
  status:'proposed_pending_core_collector_coordination', prepared_at_utc:new Date().toISOString(),
  seed, hash_format:'SHA256(seed+":"+category+":"+lowercaseAccount+":"+gameID+":"+oneBasedPly)',
  input_sha256:sha(inputText), candidate_source_sha256:sha(source), current_labels_read:false, engine_used:false,
  probe_limit_per_individual_proof:512, matching:'Category slots round robin; deterministic augmenting-path matching, one case/game globally; per-category game representative is lowest hash case.',
  counts:Object.fromEntries(categories.map(c=>[c,selected.filter(r=>r.category===c).length])),
  eligible:Object.fromEntries(categories.map(c=>[c,{moves:byCategory[c].length,games:candidates[c].length}])),
  limitations:['Challenge panel, not a natural-frequency sample.','Acceptances and capture-only recoup witnesses are conditional, not forced.','Phase/material context does not establish an engine-winning safe alternative.','Exhausted proofs are unknown, not negative.','All observed labels will be retained without class quotas or post-label replacement.'],
  audit, cases:selected,
};
fs.writeFileSync(new URL('panel-proposed.json',dir),JSON.stringify(output,null,2)+'\n');
console.log(JSON.stringify({counts:output.counts,eligible:output.eligible,audit,selected_games:selected.map(r=>r.game_id)}));
