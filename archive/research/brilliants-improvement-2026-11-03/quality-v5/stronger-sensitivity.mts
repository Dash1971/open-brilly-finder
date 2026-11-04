// Paired sensitivity only: preserve targeted selection, never mix engine budgets.
import { readFileSync, writeFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { classify, naiveMaterial } from '../root/frozen-v4/noSweatClassify.ts';
const final = '/Users/da/Documents/ChatGPT/No Sweat Chess/research/brilliants-final-2026-11-03/';
const read = (name: string) => JSON.parse(readFileSync(final + name, 'utf8'));
const base = read('analysis-baseline.json'), strong = read('analysis-stronger.json');
const identities = new Map(read('primary-moves.json').map((r: any) => [r.game_id + ':' + r.ply, r]));
const targets = new Map(base.targets.map((t: any) => [t.game_id + ':' + t.ply, t]));
const cache = new Map<string, number>();
const material = (fen: string) => { if (!cache.has(fen)) cache.set(fen, naiveMaterial(fen)); return cache.get(fen)!; };
function result(data: any, t: any, policy: any) {
  const snaps = t.snapshot_ids.map((id: string) => data.snapshots[id]);
  return classify({ positions: snaps.map((s: any) => s.fen), reviews: snaps.map((s: any) => ({current:s.current, previous:s.previous || undefined, terminal:s.terminal, quality:'sf18:' + data.engine_sha256 + ':' + data.nodes_per_position})), move:t.uci, policy }, material);
}
const rows = strong.targets.map((t: any) => {
  const key = t.game_id + ':' + t.ply, identity: any = identities.get(key), b: any = targets.get(key);
  if (!identity || !b || b.uci !== t.uci || b.fen_before !== t.fen_before) throw new Error('Identity mismatch');
  return {key, san:t.san, truth:identity.fresh_label === '!!', label:identity.fresh_label, cohort:identity.source_cohort, baseline:result(base,b,'mute-brilliant-v4'), stronger:result(strong,t,'mute-brilliant-v4'), ec_baseline:result(base,b,'en-croissant'), ec_stronger:result(strong,t,'en-croissant')};
});
function tally(rows: any[], name: string) {
  const counts = {TP:0,FN:0,FP:0,TN:0};
  for (const r of rows) counts[r.truth ? (r[name].symbol === '!!' ? 'TP' : 'FN') : (r[name].symbol === '!!' ? 'FP' : 'TN')]++;
  return counts;
}
const summaries = Object.fromEntries(['all90','reference618','recent200'].map(cohort => {
  const selected = rows.filter((r:any) => cohort === 'all90' || (cohort === 'reference618' ? r.cohort === 'reference618' : r.cohort !== 'reference618'));
  return [cohort, {n:selected.length, ...Object.fromEntries(['baseline','stronger','ec_baseline','ec_stronger'].map(n => [n,tally(selected,n)]))}];
}));
const changes = rows.filter((r:any) => (r.baseline.symbol === '!!') !== (r.stronger.symbol === '!!'));
const hashes = Object.fromEntries(['analysis-baseline.json','analysis-stronger.json','primary-moves.json'].map(name => [name,createHash('sha256').update(readFileSync(final+name)).digest('hex')]));
const output = {scope:'Targeted 90-case paired sensitivity on existing saved evidence. All development; not independent validation. No additional engine searches or selectively substituted budgets.',hashes,summaries,changes,rows};
writeFileSync(new URL('./stronger-sensitivity.json',import.meta.url),JSON.stringify(output,null,2)+'\n');
console.log(JSON.stringify({summaries,changes:changes.map((r:any)=>({key:r.key,san:r.san,truth:r.truth,before:r.baseline.symbol,after:r.stronger.symbol}))}));
