# Native fixed-forest draft port

Implemented only the new noSweatBrilliantForest.ts adapter and byte-identical noSweatBrilliantForestModel.json in this isolated draft. No model retraining, dependencies, shared chess rules, app.patch, public assets, git operations, worker or classifier integration were changed by this subagent. Root owns the separate Classify/worker integration. Code was AI-assisted with Codex; human review/manual testing required by the repository policy remains outstanding.

## Parity

The final benchmark uses the native current Core/Chessops and native callback helpers on848 development cases plus200 fresh cases, with their exact original saved SF18 windows. All157,200 window feature values match numerically/missingness-wise apart from floating-point differences at most2.84217e−14. No score difference exceeds1e−12; all1,048 award decisions are identical. No probe timeout occurred.

The same run exercises root's integrated native Classify v5:0Brilliant-decision differences from the frozen forest. Native EC mode is compared against the pinned original EC implementation with full result objects:0differences, including annotations, accuracy and cpLoss. No alternate threshold or post-test source fitting was used.

Strict isolated TypeScript checking and Oxfmt pass. Focused checks cover confirmation replacing only the second window, lower-depth/quality mismatch rejection, explicit missing-quality nonaward, NaN/Infinity rejection, two-position legacy missing prior features, missing prior-iteration nonaward, and castling/en-passant/promotion flags with absent engine evidence. The two complete benchmark artifacts preserve reference-callback and native-callback results.

The isolated feature+inference pass took about11seconds for1,048 cases, with approximately6.1ms median,34.6ms p95 and222ms maximum observed per-case time including callback material evaluation. The final joint feature+Classify+EC pass took13.0seconds and about191MiB peak RSS. These are local measurements, not browser or mobile performance guarantees. Full raw model JSON is1,296,626bytes; it is deliberately not rewritten or stripped.

## API contract

`evaluateBrilliantForest(input, helpers)` returns:

- `awarded`: final two-window forest decision.
- `windowScores.current/previous`: arithmetic mean of64 raw leaf fractions, not calibrated probabilities.
- `windows.current/previous.features`: all75 semantic features, including window_complete.
- `windows.current/previous.eligible`: only raw legal offer, two roots, mapped loss<=5 and after score>=−100.
- `confidenceSufficient`: explicit nonempty matching before/after quality plus confirmation provenance/depth/terminal preservation when present.
- `diagnostics`: physical-probe unknownness and node count.

Input positions/reviews align with the existing classification window; move is UCI. Optional confirmation uses its current snapshots for the SECOND forest window only. The primary window remains unchanged. Without confirmation, the previous completed iterations are used, including the original terminal-after reuse rule. Two-position inputs honestly set prior_history_missing and null prior numerical/attribution features; they do not invent history.

Helpers are injected: rawOffer, ecMaterial, isSacrifice, matingAcceptance, checkedContinuation, phaseRelevant, normalized and winChance. Bind isSacrifice to the same memoized material callback supplied as ecMaterial. The module never imports Classify, avoiding a runtime cycle. EC/mate/phase/checked-continuation features are predictors, NOT extra hard gates. Parent integration must preserve this distinction and the separate non-Brilliant annotation/confirmation path.

## Bounded probe behavior

Legality comes exclusively from current Chessops/Core. A local move sorter reproduces Python-chess traversal order inside these bounded probes only: descending nonpawn squares/destinations, castling, pawn captures/promotions, single/double pushes, en passant, and checking king evasions first. No upstream move generator was changed.

Original material values and proof bounds remain:512nodes for attribution/avoidability/stalemate,10,000nodes/250ms for the three-ply physical search,100,000calls/1s for acceptance SEE. The physical probe searches captures/promotions plus all check evasions; its mate/checked-horizon diagnostics remain features. Timeout/unknown semantics are retained rather than replacing incomplete values with old-case lookups or raising caps.

Wall-clock limits can still produce different missingness on different hardware/load, and the study training data had no physical_unknown examples. Numerical parity on these1,048 positions does not prove universal parity of every possible bounded-search execution or imply trained robustness to new missingness patterns.

## Hold boundary

This is a DRAFT prototype. Saved SF18/300k reference parity does not validate native SF19 or variable native budgets, changed root availability/depths, or production calibration. The earlier same-engine cross-budget diagnostic already showed decisions can shift. Keep merge/deploy on hold until the intended native domain and human interaction have been evaluated. No claim of99% overall agreement follows from this implementation work.

SUMMARY.json pins final module/model hashes and concise check results. The model SHA256 remains44704ac06378d3f671a4eed959e21959f759c0437c71af1f9119d1081293c0b7.
