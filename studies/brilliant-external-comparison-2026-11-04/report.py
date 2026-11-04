import json,sys
from pathlib import Path
sys.path.insert(0,'/private/tmp/brilly-research-deps')
import chess
P=Path(__file__).resolve().parent
r=json.loads((P/'RESULTS.json').read_text());paired=json.loads((P/'PAIRED-CASES.json').read_text());inputs={x['key']:x for x in map(json.loads,(P/'INPUTS.jsonl').read_text().splitlines())};meta={m['key']:m for m in paired['cases']}
receipt=json.loads((P/'KNIGHTS-RECEIPT.json').read_text())
lines=['Frozen external classifiers against saved Chess.com labels — 2026-11-04','',
'Protocol and scope',
'3,724 original cases:917 Chess.com Brilliants and2,807 ordinary moves,972 original game/position groups. Same five outer group assignments; no external classifier training, threshold selection, or fitting. Reference is the original custom_retuned out-of-fold forest:452 correct awards,6 wrong,49.29% recall,1.31% wrong share of awards. Fixed-cutoff forest is436/6.',
'The primary external award requires both saved engine windows to award; a known rejection in either window establishes no stable award. Single-window native outputs are also reported. Unresolved evidence is not treated as an ordinary move. Confirmed recall uses all917 positives and is a lower bound if any are unresolved. Resolved-only comparisons and per-fold counts are in RESULTS.json.',
'WintrChess commit0a63a69a544105e218b11f7459815bf195707776; actual upstream classifier and bundled openings, no rules changed. Knight\'s Eye commitc8183a6da88f3b5a2450dab35353dedd1d8d7a62, policy48; actual native core/policy from its checked-in package. No rating inputs. Knight acquisition uses supported candidateCount2 to match saved two-root windows (package default3), verificationDepth10, and no openingbook lookup. These settings are acquisition context, not threshold tuning.',
'Full game histories and44,342 saved PVs replayed legally before execution. Supplemental Knight searches retained full history and requested root scope, with complete exact common-depth PVs. 300,000 nodes/5sec max per search,15min aggregate engine cap,20min run cap, no retries. Insufficient proof—including a native optional Brilliant confirmation that remains missing—is reported unresolved rather than as a confident ordinary label.', '',
'Results: correct / wrong / confirmed recall / wrong share / unresolved positives / unresolved ordinary']
for name,a in r['arms'].items():
 m=a['pooled'];lines.append(f"{name}: {m['TP']} / {m['FP']} / {100*m['confirmed_recall_all_positives']:.2f}% / {100*m['wrong_fraction_of_confirmed_awards']:.2f}% / {m['unresolved_positive']} / {m['unresolved_negative']}")
lines+=['','Additional awards relative to the existing forest']
for name in ['wintr_both','knights_both']:
 a=r['arms'][name];c=a['changes_vs_baseline'];u=a['hypothetical_union']['pooled'];s=a['subgroups']['original_429_misses']['external']
 lines.append(f"{name}: recovers{c['recovered_correct']} missed Brilliants; adds{c['new_wrong']} wrong awards; loses{c['lost_correct_known']} previously correct awards and has{c['unresolved_baseline_correct']} previously correct awards unresolved. Removes{c['removed_wrong_known']} prior wrong awards;{c['unresolved_baseline_wrong']} prior wrong awards unresolved. Recovers{s['TP']} of the original429 eligible below-cutoff misses.")
 lines.append(f"If all its confirmed awards were added to the forest, the descriptive union would be{u['TP']} correct/{u['FP']} wrong, recall{100*u['confirmed_recall_all_positives']:.2f}%, wrong-award share{100*u['wrong_fraction_of_confirmed_awards']:.2f}%. This union was not deployed or tuned.")
 lines.append('Paired group-bootstrap95% intervals (fixed observed predictions): '+json.dumps(a['bootstrap']['percentile_95']))
 lines.append('Five folds correct/wrong: '+', '.join(f"{x['fold']}={x['external']['TP']}/{x['external']['FP']}" for x in a['per_fold']))
lines+=['','Coverage and interpretation',
'Unresolved cases are explicit in PAIRED-CASES.json and raw classifier outputs. An unsupported terminal empty-PV input is not given a fabricated classification. Inability to reach requested depth is not evidence of an ordinary tactic. The code never uses truth labels to choose searches, request budgets or ordering.',
'These are repeatedly inspected and deliberately enriched saved research examples. Their wrong-award percentages are sample agreement with the saved labels, not site-wide error-rate guarantees. Source labels have mixed historical provenance. Frozen external policies make this a useful independent implementation comparison; they do not turn previously studied labels into fresh validation.',
'Knight\'s Eye and WintrChess define their own policies. More elaborate logic and successful upstream fixtures do not establish the same definition as Chess.com. High recovery count alone is not success if it comes with extra wrong awards. Do not silently union awards or select a successful-looking subset after inspecting these outcomes.',
'No production classifier, original feature, source label or forest was changed. No new general benchmarking/release framework was built. The hard_ordinary subgroup in RESULTS follows an original cohort flag and can include positive labels; it is not exclusively a negative-class subset.',
f"Knight execution: {receipt['elapsed_seconds']:.2f}sec total, {receipt['engine_seconds']:.2f}sec supplemental engine, {receipt['searches']} new searches; status={receipt['status']}. See VERIFICATION.json for independent checks.", '',
'Case-level additions (primary both-window comparison)',
'Each line records key, played SAN, source EC-sacrifice flag and outer fold. Correct and wrong additions are kept side by side; no contradictions are dropped.']
for arm in ['wintr_both','knights_both']:
 for category in ['recovered_correct','new_wrong']:
  keys=paired['changes'][arm][category]['keys'];lines+=['',f'{arm}: {category} ({len(keys)})']
  for key in keys:
   x=inputs[key];b=chess.Board(x['fen_before']);san=b.san(chess.Move.from_uci(x['uci']));m=meta[key]
   lines.append(f"{key} {san} EC={m['ec_sacrifice']} fold={m['outer_fold']}")
lines+=['','Files: PROTOCOL.json (prespecified comparison), INPUT-VERIFICATION.json, WINTR-FREEZE.json, KNIGHTS-FREEZE.json, raw *-PREDICTIONS.jsonl, KNIGHTS-ENGINE-EVIDENCE.jsonl, RESULTS.json, PAIRED-CASES.json, VERIFICATION.json.']
(P/'REPORT.txt').write_text('\n'.join(lines)+'\n')
print('Wrote REPORT.txt')
