# Same-root quality evidence

Neither prespecified same-root hypothesis addresses the recent false awards. **All ten false awards in the200-move set have the played move in both saved MultiPV roots and pass same-root quality in both windows.** Seven are the current best root and three the second root. Their problem is not a child score that disguises a root-quality failure. No threshold was adjusted after seeing this result, and neither variant should be promoted as a standalone precision improvement.

All818 core examples are now unblinded development data. The618 reference cases and200 recent cases are reported separately for diagnosis, not as a new train/test split. The additional30 stronger-budget cases are targeted sensitivity evidence, not another independent sample. The mechanism panel is excluded from this experiment.

## Two fixed hypotheses

Both actual source copies change only Mute Brilliant eligibility. They compare the best before-position root against the played move's root score at the same completed MultiPV depth, using the existing5-percentage-point win-chance loss threshold. They retain the independent after-position floor, raw legal offer, material/mate corroboration, checked-history veto, phase-aware safe-alternative rule, and complete current/previous confidence checks. Each window uses its own evidence; no scores are mixed between budgets.

* **A, matched root with fallback:** use matched-root loss when that root is present; otherwise retain the existing child-score loss for that window.
* **B, matched root required:** a missing played root supplies no Brilliant quality proof. Both current and previous complete windows therefore need that root and must pass the quality test. Absence is not a bad-move label.

The original early return for child-derived mistake labels is delayed until after potential Brilliant eligibility, allowing an intentional `!!` override when the new quality evidence and all other gates pass. Without that override, the experiment would still secretly require the old child-quality test. When a move does not receive `!!`, the original fallback semantics remain in force.

## Actual full-window results

| Evidence | Policy | TP | FN | FP | TN | Agreement |
|---|---|---:|---:|---:|---:|---:|
| All818 | Frozen v4 |320|89|25|384|86.06%|
| All818 | A: root/fallback |322|87|26|383|86.19%|
| All818 | B: root required |295|114|24|385|83.13%|
| Reference618 | Frozen v4 |246|63|15|294|87.38%|
| Reference618 | A |248|61|16|293|87.54%|
| Reference618 | B |229|80|14|295|84.79%|
| Recent200 | Frozen v4 |74|26|10|90|82.00%|
| Recent200 | A |74|26|10|90|82.00%|
| Recent200 | B |66|34|10|90|78.00%|

A recovers three observed brilliants, loses one, adds one false award, and removes none. B recovers the same three but loses28 correct awards, removes two old false awards, and adds one. Neither removes any recent false award. B's net precision change chiefly reflects missing root coverage rather than quality disagreement.

Played-root coverage is644/818 in the current window and637/818 in both windows. Among320 baseline true awards,293 have both roots; among25 false awards,23 do. In the recent set, all ten false awards have both roots, but eight of74 correct awards lack a current matched root. Rejecting incomplete MultiPV2 coverage therefore has an unfavorable observed tradeoff.

No baseline false award has a matched-root quality failure hidden by a child-quality pass in either saved window. Four of89 baseline misses have the reverse disagreement somewhere in the window; three are recovered by A. The fourth remains blocked by material corroboration.

## Contradictory examples

* **186398857750:45, hxg6, explicitly non-Brilliant:** the old child losses are5.771 and5.044pp, while matched-root losses are4.759 and4.031pp. Both variants now award `!!`, overriding the original `?!`. This is the precision counterexample to treating same-root quality as a universally safer replacement.
* **185897727454:25, Bxh7+, Brilliant:** the move is best at both roots, so root loss is0. Child loss is14.593pp in both windows. A correctly recovers it, intentionally overriding the old `?`.
* **184634890030:37, Qxh7+, Brilliant:** current child loss is−2.066pp, but the previous window loses13.564pp. Both matched roots are best, so the source variant recovers the award without bypassing whole-window confirmation.
* **186007180386:89, b6, Brilliant:** previous child loss5.464pp narrowly fails; matched-root loss2.936pp passes. A recovers it.
* **184623800724:84, Qxf6, Brilliant:** previous child loss4.509pp passes, but previous matched-root loss6.055pp fails. Both variants lose a correct award. Root evidence can introduce a contradiction as well as resolve one.
* **185357791081:68, Rxf7, Brilliant:** both played roots are best, while child losses are11.000 and6.507pp. It still receives no Brilliant because the raw offer is true but EC material corroboration and mating acceptance are both false, with no searched winning mate. At the stronger budget child quality also passes; this separate material blocker remains. Changing quality alone cannot recover it.

The recent false-award identities and all current/previous scores are preserved in `same-root-results.json`; board-only corroboration/context features for illustrative contradictions are in `counterexample-features.json`. These identities are descriptive examples, never classifier inputs or position exceptions.

## Stronger sensitivity and verification

On the separate targeted30-case stronger window, frozen v4 and A both produce TP6/FN14/FP8/TN2. B produces TP4/FN16/FP8/TN2. No stronger false award is removed by either quality variant. This is a standalone complete stronger window; no baseline/root score is substituted into it.

The actual frozen source reproduces all818 prior complete classification results exactly, including provisional symbols and withheld status. Both experimental sources produce zero EC-mode differences, zero native accuracy/cpLoss differences, and zero differences between non-Brilliant symbols where neither result is `!!`. The explicit Brilliant overrides above remain visible. The replay took7.631seconds, with peak RSS173,712KiB, using one Node process with a256MB old-space cap and saved engine inputs only.

`EXPERIMENT.json` describes the hypotheses; `same-root-summary.json` records metrics, paired changes, coverage, contracts, and input/source hashes. `replay.mts` imports the actual copied TypeScript and applies the full classifier, not precomputed gate substitutions. `diagnose-cases.mts` adds descriptive existing-source board features. Run with the existing Node/tsx dependency paths used by the study. No application, public report, frozen v4 source, engine evidence, or database was changed. Any further candidate must be frozen before genuinely unseen evaluation; these818 labels cannot serve as that evaluation.
