# Coverage and prior competitive context

**The main recall opportunity is a better corroborating sacrifice proof, not a looser quality threshold or a blanket previous-winning veto.** Among the26 recent Brilliant moves missed by frozen v4,20 fail only EC/mate corroboration in both complete windows. However,17 recent non-Brilliant moves have that same sole-blocker signature. Removing the guard indiscriminately would recover those20 at the cost of17 additional false awards. A replacement must distinguish their physical investment or tactical mechanism.

All818 core moves and30 mechanism-panel moves are now unblinded development evidence for future v5. The former200-move validation cohort remains identified for diagnosis of v4's historical result. Nothing here is a fresh v5 validation, threshold search, or production change.

## Exact coverage of the26 recent misses

The diagnostic independently reconstructs every necessary Brilliant gate in each current and previous complete decision window, then checks its provisional/final award against the actual frozen TypeScript. Reconstruction matches all848 moves exactly.

| Union of current/prior failed gates | Moves |
|---|---:|
| EC/mate corroboration alone |20|
| Quality alone |3|
| Phase-aware safe winning alternative alone |1|
| EC/mate corroboration and quality |1|
| EC/mate corroboration and raw legal offer |1|

Overlapping totals are22 corroboration failures, four quality failures, one raw-offer failure, and one safe-alternative failure. No recent miss fails the after-position floor, two-root availability, checked-continuation rule, or separate whole-window confirmation. Current and prior failures have the same signatures in these26 cases. This does not imply identical scores: the complete values are preserved in `recent-misses.csv` and `context-results.json`.

Quality-only misses are **173522572211:31 Nxe5** (loss5.586pp in both windows), **174185738360:43 Bxg6** (5.259pp), and **175079514275:29 Bxe6** (9.550/9.658pp). The dual quality/corroboration miss is **185357791081:68 Rxf7** (11.000/6.507pp). The safe-alternative-only miss is **185228493400:44 Nc6**. The only raw-offer-false recent positive is **187172896469:56 Rxc6**, which also lacks EC/mate corroboration. Its label is retained; there is no position exception.

For context, the same sole-corroboration exposure occurs in62 positive and70 negative core moves overall, and two positive/six negative panel moves. These are descriptive exact gate signatures, not an additional tested source candidate or an instruction to remove the guard.

## One prior-context hypothesis

The prespecified candidate adds one Brilliant veto: if the mover was already at least600 normalized cp after their preceding own move, do not award Brilliant now. It uses the existing `routineWinCp` boundary and includes an explicitly positive mate; mate0 is not a win. The relevant position is two plies before the target, before the opponent's last move. Current and previous score windows apply this gate independently. Missing history supplies no added veto, consistent with the existing history rule; all existing confidence checks remain.

The actual private source copy preserves EC mode, native accuracy/cpLoss, after-position floor, material/mate proof, raw offer, checked history, phase/safe alternatives, and fallback labels. There is no threshold grid.

| Cohort | Policy | TP | FN | FP | TN |
|---|---|---:|---:|---:|---:|
| Core818 | Frozen v4 |320|89|25|384|
| Core818 | Prior600 veto |294|115|21|388|
| Recent200 | Frozen v4 |74|26|10|90|
| Recent200 | Prior600 veto |69|31|7|93|
| Panel30 | Frozen v4 |2|2|3|23|
| Panel30 | Prior600 veto |2|2|2|24|

In the recent cohort, the gate removes three false awards but also five correct awards, lowering agreement from82% to81%. It is not a useful standalone candidate toward the90% agreement/low-false-award goal. Across all848 cases it loses26 correct awards while removing five false awards; all other decisions remain unchanged.

The removed recent false awards are **Rh1,169827191694:67**, with prior981 and before1000; **Bc5,173084454389:59**, with prior750, before755, after630; and **Qg6+,186393990159:71**, with a prior winning mate. Correct Brilliant counterexamples include **Rxf7,184431785024:65** (prior721, before948, after763), **Nxe2,174429457866:50** (prior687, before707, after547), and three cases already showing a winning mate: **Bf6,172590636870:45**, **Be3+,173049117092:40**, and **Rxh7+,184430392420:37**. Prior winning context alone therefore does not establish that a sacrifice should lose its Brilliant label.

All ten recent false awards,74 true awards, and26 misses have saved prior score and before/after deltas in `context-results.json`; `context-summary.json` supplies distributions and exact examples. Scores are normalized and clipped to±1000. A positive mate maps to1000 as a comparison sentinel, not a literal centipawn advantage; these deltas do not measure mate distance.

## Promotion check and verification

None of the100 recent Brilliant moves is a promotion, so there is no observed raw-offer-false promotion miss to recover. Three positive positions have legal promotion alternatives, but none of those alternatives immediately stalemates, and the selected Brilliant moves are ordinary non-promotion moves. Across all positive cases,14 positions have legal promotion alternatives; no selected positive move is a promotion. This bounded check supplies no observed underpromotion/avoid-stalemate witness and does not justify inventing a new promotion mechanism from this sample.

The actual-source replay reports zero EC-mode, accuracy/cpLoss, or non-Brilliant-symbol differences. Gate reconstruction matches848/848. It ran in7.657seconds with172,512KiB peak RSS, one Node process under a256MB old-space cap, and saved engine evidence only. No engines, browsers, application files, public artifacts, or frozen v4 source were changed. The source copies, hypotheses, exact hashes, full results, and counterexample exposure lists remain private under this directory.
