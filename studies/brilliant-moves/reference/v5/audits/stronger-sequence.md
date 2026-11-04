# Frozen-rule stronger-evidence sensitivity

The final uniform development replay gives S323TP18FP, versus322TP19FP at300k. The improvement is small and includes genuine losses. The unchanged full-data forest moves from its training247TP0FP to240TP1FP when its inputs are recomputed at1.5m. Neither result is independent validation or evidence of99% deployment accuracy.

## Exact S paired comparison

| Development subset | Frozen S at300k TP/FP | Same S at1.5m TP/FP |
|---|---:|---:|
| Old618 |246/10|247/10|
| Historical200 |74/6|74/5|
| Core818 |320/16|321/15|
| Panel30 |2/3|2/3|
| All848 |322/19|323/18|

There are twelve changed decisions: five true awards added, four true awards lost, two false awards removed and one false award added. The added false award is186398857750:45 hxg6. Every changed decision is listed in paired-S-summary.json; do not replace this joint result with an arithmetic sum of gains from earlier targeted analyses.

At the stronger budget, baseline A itself gives323TP27FP. The frozen temporal restriction removes nine false awards without removing a true award from that stronger A output. New qualifying repeated continuations Bg5 and Qg6 are suppressed; Bc5 is already declined by stronger A. The same Nb5 fork and Qh6 new-acceptance exceptions remain operative. No structural proof budget was exhausted. The historical200 subset now has84.5% agreement and5% false-positive rate; it remains development evidence and below the requested future target.

## Complete prior-origin evidence

After explicit engine-slot handoff, a label-independent structural recount examined ALL848 stronger A outputs. It found89 quiet current A awards and16 missing snapshots across all potentially relevant earlier own-turn origins, including origins that might be redundant before considering forcing exceptions. The queue was frozen in prior-plan.json before any supplemental search. It added172590636870:33/34 and omitted187780686673:32/33 relative to the earlier baseline-conditional list.

All16 were collected once at1.5m nodes, Threads1, Hash64, with full PGN history and recorded source/engine/PGN hashes. Recorded search time was20.62seconds. The engine exited; there were no retries, substituted baseline snapshots or mixed300k prior decisions. The subsequent all848 coverage check reports zero missing relevant origins. Frozen corrected S and A/helper hashes were verified unchanged.

The main2445-window uniform artifact discloses three partial-game transposition-table restarts in its once-only tails. Supplemental origins start clean per-game sessions. Thus the node budget, engine and legal history are uniform, but cache warmth is not claimed identical across every position or the two budget runs. This is an analysis-setting sensitivity result, not a causal isolation of depth alone.

## Frozen full-data forest cross-budget comparison

The frozen fresh extractor and exact frozen64-tree full-data forest were run unchanged on all848 stronger windows after all engines exited. The threshold remains5/6; no fitting, leaf revision, threshold calibration or original-fold regeneration occurred.

| Full-data fitted model, development inputs | TP | FN | FP | TN |
|---|---:|---:|---:|---:|
| Original300k inputs |247|166|0|435|
| Recomputed1.5m inputs |240|173|1|434|

This compares the SAME full-data forest with itself. It must NOT be presented as a change from the223TP2FP out-of-fold diagnostic: those predictions came from different fitted fold models. The300k reference is training resubstitution, and the stronger inputs belong to those same development positions.

Twenty forest awards change: six true awards are added, thirteen are lost, and one false award is added. The false award is178360672165:63 Nxh6+: its current/previous mean tree scores change from0.81276/0.82499 to0.84635/0.84242, crossing the fixed5/6 threshold in both windows. These scores are not calibrated probabilities.

846 of848 cases have at least one changed input. Across1696 window rows, before/after/prior depth changes in1630/1568/1648 rows respectively. Played-root absence changes in81 rows, producing81 missingness changes in played-root mapped score, same-root loss and rank. Centipawn/mate scores, score differences, alternative scores and root ranks also change. No board-only feature changes were observed; physical_unknown remains false throughout this run. Input changes and all twenty changed awards are preserved in forest-cross-budget.json and its compact summary.

The run took17.2seconds, peak Python RSS113MB, with no engine active. All extractor, model and protocol freeze hashes matched before inference. Retained250ms physical proof limits remain load-dependent in general; zero timeout differences here are an observation, not a guarantee.

## Decision implication

More analysis does not automatically improve a learned classifier's outputs. The observed full-fit recall loss and new false award support keeping prospective evaluation in the frozen feature/engine domain, or explicitly declaring a different domain before labels. S is comparatively stable here, but still misses the requested accuracy/false-award combination. These diagnostics justify honest fresh comparison of the already frozen candidates, not another development threshold sweep or a native deployment claim.
