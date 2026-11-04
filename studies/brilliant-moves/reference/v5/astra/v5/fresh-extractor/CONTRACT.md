# Fixed-forest prospective feature extraction

The study-local extractor is ready for prospective research inputs in its original SF18/300k domain. FREEZE.json pins its function sources, reused kernels, full-data forest and protocol at2026-11-03T09:57:01.081170Z. This is not a native implementation or a new model fit.

## Interface

Import extractor.py and call `extract_batch(requests)`. Each request contains exactly the evidence needed for a move:

- `pgn`: full legal game history. Headers/comments are not predictors; only starting position and mainline legal moves are used.
- `ply`: one-based target move index.
- `snapshots`: ordered previous-own-after, before, after snapshots; at the first move, deduplicated initial and after positions. Each includes exact `fen`, explicit nonempty analysis `quality` provenance, `current`, `previous` and `terminal`. Missing engine iterations are None; they are never invented. Each present iteration contains depth and nonempty lines with score and legal UCI PV.

The wrapper checks PGN legality, target position identity and every supplied PV. It recomputes context from the frozen native helpers, physical investment, raw material, attribution, avoidability, stalemate probes and all75 features. There is no game/account/label lookup, no old-case fallback and no engine invocation. Explicit quality provenance must describe the actual engine/configuration; the wrapper checks equality where the reference checks equality, not the truth of an externally supplied provenance string.

Output contains current/previous feature dictionaries, eligibility, case confidence and limited physical-probe diagnostics. `score_fixed_forest(case, model)` uses the frozen full-data forest:75 ordered predictors followed by75 missing indicators,64 arithmetic-mean raw leaf fractions, threshold5/6 in BOTH windows, both original eligibility guards and case confidence. Missing numeric values route left exactly as in the saved model. Scores are not calibrated probabilities.

The CLI reads a JSON request array on stdin and writes features plus fixed-model decisions on stdout. Use the existing Node24 executable and tsx loader recorded in extractor.py; no dependencies were installed. Model and dependency hashes must match FREEZE.json before prospective scoring. Do not use post-fit pooled ranking thresholds or fold-specific models as the prospective predictor.

## Observed parity and focused checks

The initial independent recomputation matched all75 numerical/Boolean/missing features, two-window eligibility and confidence on848 cases:0differences across127,200 feature values. The full PGN/PV wrapper run independently repeated this comparison and matched all full-fit forest award decisions, with maximum floating-point score difference5.55e−16. It reproduced247 full-data training awards; this is a parity check, NOT a validation result.

The full wrapper run took approximately29seconds, peak Python RSS106.6MB. The initial direct-kernel run took approximately12.8seconds and about105MB. The implementation remained within the requested bounded effort; no new engine job or generalized ML framework was created.

Two positions absent from the848 training before-positions were processed end-to-end using existing exact saved engine windows and no observed labels:184514610842:69 and187780686673:34. Both were declined by the fixed forest. Their games occur elsewhere in development data, so these are unseen-position smoke tests, not independent test games or evidence about accuracy.

Enforced boundary tests reject a mismatched target FEN, missing provenance, and illegal PV; missing previous evidence produces an ineligible nonaward. Legal castling, en passant and promotion fixtures verify their feature flags and abstention with explicitly absent engine evidence. The848 real cases cover181 checking moves,47 check evasions,54 after-mate scores,180 missing played roots,394 checked physical horizons and63 physical mate leaves. They contain no castling, en passant or promotion moves, hence the separate fixtures. Special-move fixtures do not claim forest calibration for those move types.

## Time-cap nondeterminism and limits

Attribution, avoidability and direct-stalemate probes retain their original512-node bounds. The reused physical search retains10,000nodes AND250milliseconds, with separate original same-square acceptance SEE limits of100,000calls AND one second. No budget was increased to achieve parity and no old computed feature was substituted.

The completed runs had zero physical-unknown discrepancies, but this does not make the feature map fully deterministic under variable load. A slower or loaded machine can exhaust a wall-clock cap at a different point, changing physical_unknown, missing debt, partial acceptance-derived features or related diagnostics. The original818 and panel feature generation also had different surrounding bookkeeping costs; matching the numerical search algorithm and limits does not reproduce historical CPU scheduling. These effects are explicitly unresolved, not concealed by a cache. No deterministic feature mismatch or unreplicable numeric artifact was observed in the completed corpus runs.

The physical search, including its permissive same-square SEE conventions and checked-horizon diagnostics, is reproduced for model parity; it is not promoted into an exact general chess proof. The model has no training physical_unknown examples in this corpus. Fresh timeouts must remain visible, and inference must preserve missingness/guards rather than pretend that incomplete evidence is complete.

All learned depth/root/missingness inputs remain tied to the original SF18/300k evidence regime. SF19, changed MultiPV, different completed-iteration conventions or variable budgets are outside this parity result. Freeze the prospective collection/analysis configuration before labels; do not adjust extraction or thresholds after seeing them. No prediction here establishes99% deployment precision or meets the earlier90% agreement target.
