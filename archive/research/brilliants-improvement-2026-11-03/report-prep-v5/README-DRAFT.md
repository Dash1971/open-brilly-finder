# Open Brilliant-badge research

**Private review draft — completed fixed-candidate test.**

This document specifies the frozen research candidates, their evidence and their limits. It does not claim a new native Mute Chess deployment. Mobile Maia retains its existing En Croissant-based classifier.

| Fresh test | Verified result |
| --- | --- |
| Moves / games | 200 / 106 |
| Observed Brilliant / explicitly non-Brilliant | 100 / 100 |
| Frozen forest TP / FN / FP / TN | **55 / 45 / 1 / 99** |
| History rule S TP / FN / FP / TN | 78 / 22 / 5 / 95 |
| Direct En Croissant TP / FN / FP / TN | 26 / 74 / 2 / 98 |
| A and v4, each TP / FN / FP / TN | 78 / 22 / 6 / 94 |
| EC with shared-window confirmation | 26 / 74 / 2 / 98 |

The forest has **55% recognition**, **77% agreement** and **55/56 = 98.21% sample badge precision**; it misses 45 of the 100 observed Brilliants. Its descriptive Wilson 95% intervals are 45.24–64.39% for recognition, 70.69–82.29% for agreement, 90.55–99.68% for sample badge precision and 0.18–5.45% for its 1% extra-control rate. These are distinct measurements, not a 98% overall-match claim.

The unified corpus has **1,048 moves from 545 games**: development contains 848 moves from 439 games (413 Brilliants, 435 non-Brilliants), and the fresh test contains 200 moves from 106 excluded-game/position-checked games (100 per class). Each of the same five accounts contributes 20 per class to the test. Candidate sources, model, threshold and extraction were fixed before its current labels. The test was not used to retune this candidate or choose a threshold.

[Complete metrics, per-account results and prediction traces](../future-validation-v5/engine-core/fresh-results.json), [compact predictions](../future-validation-v5/engine-core/fresh-predictions.csv), [completed source/identity audit](../future-validation-v5/engine-core/FINAL-AUDIT.json) and [test freeze](../future-validation-v5/CORE-FREEZE.json) accompany the result. Core-freeze SHA-256: `99bcffb5a77209f13e61bd0c495625950da6950c028ab9b64a5a1b8eea6a3394`.

| Account | Forest recognized / extra awards | History rule recognized / extra awards | EC direct recognized / extra awards |
| --- | ---: | ---: | ---: |
| GothamChess | 12 / 0 | 16 / 0 | 7 / 0 |
| Hikaru | 9 / 0 | 11 / 0 | 3 / 0 |
| KNVB | 8 / 0 | 16 / 0 | 9 / 0 |
| hansen | 13 / 1 | 17 / 3 | 5 / 1 |
| nelsi | 13 / 0 | 18 / 2 | 2 / 1 |

Every account has 20 positives and 20 controls; “extra awards” uses the control denominator, not the positive denominator. Zero extras in an account is an observed point estimate, not a zero-risk guarantee. Per-account Wilson intervals are saved in the complete metrics.

## Exact primary candidate: fixed precision-first forest

The candidate emits a Boolean Brilliant decision. It does not redefine native accuracy, clocks, ordinary chess rules, or other move-quality annotations.

### Inputs and supported domain

Inputs are a full legal standard-chess PGN, a target one-based ply, and ordered engine snapshots for the previous own-after position, before-position and after-position. Near the start, duplicate initial positions are removed. Snapshots contain exact FEN, explicit engine/configuration provenance, current and actual preceding completed iterations, terminal state, score and legal UCI principal variations.

The validated extraction domain is the pinned **SF18**, **300,000 requested nodes**, **Threads 1**, **Hash 64 MB**, **MultiPV 2 where two legal roots exist**, full PGN history and the recorded complete-iteration convention. The extractor verifies target/PV legality and position identity. A matching provenance string alone cannot prove that a caller really used the declared engine/options.

Native SF19, varying browser depths/budgets, other engines and changed MultiPV are outside this validation. Castling, en passant and promotion have legal feature/abstention fixtures, but none occurs among the 848 training moves; these fixtures do not establish model calibration for those move types. Other variants are unsupported.

### 1. Preserve the hard eligibility gates

Scores are normalized to the mover. Let

```text
C(score, mover) = clamp(mover-relative centipawns, -1000, +1000)
                 or 1000 × sign(mover-relative mate distance)
W(c) = 100 / (1 + exp(-0.00368208 × c))
loss_w = W(best before-position score_w) - W(best after-position score_w)
```

Mate 0 maps to 0. The after-position search is the position after the played move. The quality gate uses that child-position score, not an invented before-search score for an unsearched played root. W is a scoring heuristic, not a calibrated human winning probability.

For **each** current/prior completed analysis window:

```text
eligible_w = before-root-count_w >= 2
             AND raw_piece_offer(before, after)
             AND loss_w <= 5
             AND C(after_w, mover) >= -100
```

The raw offer test is unchanged: the after-position is nonterminal, and some opponent legal capture/exchange on a knight, bishop, rook or queen has static exchange gain **strictly greater** than

```text
max(0, physical mover material_after - physical mover material_before) + 100.
```

Values are pawn 90, knight 300, bishop 300, rook 500, queen 1000, king 0. Capture/promotion gains are credited. The piece offered need not be the piece moved. The one-square exchange evaluator considers legal captures and permits stopping; it is a local material heuristic, including its stop convention in check, not a proof over all legal continuations. The frozen raw-offer recursion has no explicit node cap.

### 2. Extract 75 semantic features, with explicit missingness

The features describe engine quality/root availability and depth; before/after/prior scores; physical and EC material; immediate gains and phase; moved/offered piece roles; checks/captures/special moves; legal acceptance cost; bounded material recovery; prior raw vulnerability; forcing/stalemate/avoidability context; and unknown/absent evidence.

There are no account IDs, ratings, dates, clocks, gallery categories, coach text, observed labels, game IDs, raw board-square encodings or move-string identities among the predictors. PGN headers are metadata, not inputs to prediction. A move absent from the saved roots has null rank/gap; it is not assigned a favorable value.

The 75 ordered values are followed by 75 indicators `feature__missing`. None, False and 0 are distinct. Missing numeric values route left in a tree; explicit missing indicators remain available. The exact field definitions and ordering are linked below. In particular, `mating_acceptance` is the existing additional corroboration flag evaluated when EC material sacrifice is absent; its inapplicable False value does not prove that no mating acceptance exists.

EC material, phase, winning alternatives and history flags are **features**, not additional universal vetoes for the forest. The forest is not silently combined with the separate history rule.

### 3. Score the frozen 64-tree model in both windows

The prospective model is [the full-data forest](../learning-v5/forest-diagnostic/forest-full.json), SHA-256:

```text
44704ac06378d3f671a4eed959e21959f759c0437c71af1f9119d1081293c0b7
```

For each window, route its 150 values through all 64 stored trees. Numeric values use the left branch at `value <= threshold`; None also routes left. Each leaf stores its **unweighted positive bootstrap-window fraction**, not a class-cost-weighted or calibrated probability. Average those 64 leaf fractions:

```text
p_w = (1/64) × sum(raw_positive_fraction(tree_leaf_w))
award = eligible_current AND eligible_prior
        AND case_confidence_sufficient
        AND min(p_current, p_prior) >= 5/6
```

The threshold is **5/6**, approximately 0.8333, in both windows. It is not the earlier diagnostic’s 0.98 operating point, and it is not a guarantee of 83.3% or 99% real-world badge precision. Do not average the two window scores together and test only their mean.

Case confidence requires the recorded matching before/after analysis provenance; both actual completed-window predictions must pass. Missing required engine iterations cannot establish eligibility. A terminal after-position uses the reference contract’s exact terminal evidence in the prior-window comparison; other final scores are never copied to manufacture corroboration.

```mermaid
flowchart LR
  I["Full PGN + saved SF18 windows"] --> F["75 semantic values + missing flags"]
  F --> T["64 fixed trees: score each window"]
  I --> G["Both hard gates + matching provenance"]
  T --> D["Both scores ≥ 5/6 and gates pass?"]
  G --> D
  D --> B["Brilliant or withhold"]
```

### Frozen training procedure

The model has 64 trees, maximum depth 6, minimum 8 distinct original moves per leaf, 12 randomly selected features per split and seed 20261103. Whole game/identical-before-position union groups are bootstrapped with replacement; current/prior windows are not resampled independently. A training window’s Gini weight is `(5 if non-Brilliant else 1) / eligible-window-count-for-that-move`, multiplied by its sampled group multiplicity. Minimum leaf size counts unique original moves, not bootstrap copies. Raw leaf fractions ignore class-cost weights.

The complete [training protocol](../learning-v5/forest-diagnostic/PROTOCOL.json), [fit source](../learning-v5/forest-diagnostic/fit.py), model artifact and recorded hashes define the fixed result. The full-data model is used on new games; the five fold-specific models are not substituted as prospective predictors.

### Proof and search limits

| Component | Frozen limit and uncertainty handling |
| --- | --- |
| Raw one-square offer test | No explicit node/wall cap; finite legal same-square capture recursion with stopping. |
| EC material heuristic | No explicit node/wall cap in the copied helper; all legal initial roots then capture-only continuation, with its check/quiet and terminal-sentinel limitations. This is not physical material. |
| Added literal mate / checked-continuation helpers |512 counted positions per helper invocation. Exhaustion cannot establish the corresponding witness. |
| Forest prior-offer attribution |512 shared counted exchange nodes; retain explicit attribution unknownness. |
| Forest all-root offer avoidability |512 counted nodes; budget exhaustion is None, never a completed unavoidable-offer proof. |
| Forest direct-stalemate probe |512 counted nodes; incomplete enumeration stays unknown. |
| Physical material-recovery feature | Three plies after a qualifying acceptance; captures/promotions, all legal evasions in check, stopping only outside check. Shared 10,000 nodes and 250 ms per target. A checked horizon and mate leaves are flagged; no mate-score sentinel becomes physical material. |
| Physical acceptance’s same-square SEE | Separate 100,000-call and 1-second limits per acceptance. |

Physical timeout clears the relevant debt values to None while preserving the source-defined partial acceptance features and diagnostics. The frozen model can still route optional proof-feature unknowns; they do not imply a new blanket abstention rule. There were no physical-unknown training cases, and no physical timeout occurred in the fresh test, so timeout behavior remains an unvalidated edge. Do not hide it, fill it from an old-case lookup or increase a cap after seeing test labels. Wall-clock caps can produce load-dependent unknownness. The 250 ms physical-search check occurs at search visits; the separate acceptance SEE has its own 1-second limit, so 250 ms is not an end-to-end latency guarantee.

The [standalone extractor contract](../astra/v5/fresh-extractor/CONTRACT.md), [code](../astra/v5/fresh-extractor/extractor.py), [feature kernel](../astra/v5/fresh-extractor/feature_kernel.py) and [freeze manifest](../astra/v5/fresh-extractor/FREEZE.json) are authoritative. Independent 848-case checks reproduced all 75 values/missingness, eligibility, confidence and full-model decisions with no differences. Those are implementation parity checks, not validation accuracy.

### Observed optional unknowns in the fresh test

All 200 cases had sufficient required engine confidence; all 581 core snapshots had actual preceding completed iterations. No physical-feature timeout or S proof unknown occurred. Four avoidability proofs were unknown in both analysis windows and retained the frozen missing-value routing. The 2,724 total None fields across 400 windows also include ordinary inapplicability: alternate cp/mate fields, a played move absent from the saved top two roots, no safe alternative, or no qualifying offer for physical debt. They must not all be counted as failed proofs. Full per-field counts, diagnostics and affected keys are saved with the predictions.

## Exact secondary comparator: history-aware rule S

S starts with the confirmed, unsuppressed baseline A classification and can only remove its Brilliant award. Baseline A retains the mapped quality/after-floor gates, local legal offer, EC material or explicit winning-mate corroboration, the phase-dependent safe-alternative veto, checked-continuation restriction and whole-window confirmation. Its added mate-acceptance fallback requires the original literal-witness predicate plus a capture-specific proof tying liability, attribution and mate to the same victim: the victim moved, or aligned prior history shows a strictly lower raw liability or that this capture was not previously legal. This fallback does not weaken EC-backed or explicit searched-mate corroboration.

The phase-dependent alternative veto applies when remaining phase≤8 or the mover already leads by ≥300 physical material points. Phase weights are N/B1,R2,Q4, initially 24. In that context, another evaluated move scoring ≥+600 without a raw offer blocks an award. This checks the alternatives actually searched, not every legal alternative.

For a current quiet A award, S examines up to the preceding **three own decisions** within the continuous previous six PGN plies. It suppresses a repeated continuation when an earlier **confirmed unsuppressed A** award covers every currently offered physical piece: each piece remains unmoved/unreplaced on its square, qualified against the earlier capture/promotion credit, and retains the same raw exchange loss after intervening own moves. Prior observed labels, provisional badges and recursively suppressed S decisions never establish origins.

Current checking moves, captures, promotions and actual castling are exempt from this temporal veto. A qualifying earlier origin cannot justify suppression if the same victim supplies either frozen exception:

1. A currently profitable acceptance, previously illegal, permits a literal legal mate-in-one reply. An already legal acceptance with an already existing mate is insufficient.
2. A new checking-fork reply lets the checking piece win more than 100 net static-exchange material points after **every** legal check evasion. Novelty compares checking-piece role plus checking destination; it is deliberately coarser than exact threat identity.

For the second test, the net calculation is checking-reply capture/promotion gain, minus evasion gain, plus the best subsequent capture by that checking piece, minus its final same-square liability. The shared structural/forcing budget is 512 counted nodes per target. Incomplete physical history, a missing earlier confirmed classification or proof exhaustion cannot establish the veto; unknownness does not become a fabricated earlier badge. Relevant origin evidence must be completed and coverage reported. The fresh test had one structurally relevant earlier origin, already fully covered by the core snapshots; no supplemental searches or S proof unknowns were needed. A uniform stronger result cannot borrow 300k origin windows.

The corrected [temporal source](../astra/v5/sequence-reference/temporalProof.ts) is pinned at SHA-256 `16faa288afc2e18716cdc7135efa8275712cd3b12624e4f696f33f25f6b3fe29`; its [contract](../astra/v5/sequence-reference/PROSPECTIVE-CONTRACT.md) and [effective freeze](../astra/v5/sequence-reference/source-freeze-castling-addendum.json) pin A/helpers and correct castling recognition. Ordinary one-square king moves are not castling exemptions. The prototype is a separate comparator, not a hidden forest gate.

## En Croissant comparator and Mobile Maia

The peer is **direct En Croissant annotation** on the same saved current engine windows. Brilliant requires its material-sacrifice predicate, the played first-choice move, at least two roots, and a best-versus-second mapped gap strictly greater than 10 points. Its broader material predicate is `EC(before) > -EC(after) + 100` with a nonterminal after-position. Capture-only search can notice recovery on another square, but it omits quiet replies, uses permissive stopping/check conventions and has a nonphysical mate sentinel.

The pinned [score source](https://github.com/franciscoBSalgueiro/en-croissant/blob/6f2d2628f0fbe11cb62a7dd2f9c102bb52907d53/src/utils/score.ts) and [material source](https://github.com/franciscoBSalgueiro/en-croissant/blob/6f2d2628f0fbe11cb62a7dd2f9c102bb52907d53/src-tauri/src/chess.rs) were verified byte-identical to [v0.15.1](https://github.com/franciscoBSalgueiro/en-croissant/releases/tag/v0.15.1); [the source-equivalence record](../../../mute-chess-research/studies/brilliant-moves/ec-latest-stable-check.json) retains hashes. This does not assert identical app search behavior. EC with shared-window confirmation is a separate appendix output and never silently replaces direct EC in a comparison. Mobile Maia remains unchanged.

[Chess.com’s published criteria](https://support.chess.com/en/articles/8572705-how-are-moves-classified-what-is-a-blunder-or-brilliant-etc) motivate good piece sacrifices and player-strength conditioning, without supplying an executable formula. No account or rating predictor is present in this frozen forest. These five established accounts do not establish a beginner curve or ordinary-game badge prevalence. There is no fitted player-rating conditioning curve: the published player-strength dependence motivates research, but is not an implemented forest input.

## Fresh-test identity and label contract

Historical galleries identify candidates; the label used for evaluation is the explicit current Game Review classification captured with a timestamp. A missing gallery entry is never a confirmed negative. Controls require an explicit non-Brilliant label, including Best, Great, Excellent, Good, Book, Forced, Miss, Inaccuracy, Mistake or Blunder.

Game type/live-daily namespace, numeric ID, one-based ply, visible SAN, full PGN replay and before/after FEN must agree; captured board pieces corroborate identity. Complete games and normalized sampled positions are separated from development under the frozen exclusion/selection plan. Changed gallery labels and Brilliant controls remain secondary, with replacements drawn from the fixed reserve order rather than classifier outcomes. Labels and identities are never predictor inputs.

## Reading the test honestly

```text
badge precision = TP / (TP + FP)
recognition     = TP / (TP + FN)
extra-award rate= FP / (FP + TN)
agreement       = (TP + TN) / total
```

If no badges are awarded, badge precision is undefined, not 100%. The same distinction applies to missing class denominators. A model can have reliable-looking awarded badges yet miss most observed Brilliants. Balanced, offer-enriched controls do not estimate the frequency of false badges across all ordinary game moves. Test groups share five accounts and games contribute multiple moves. Wilson intervals are descriptive binomial intervals treating moves independently; they are not game-cluster-adjusted confidence estimates. A claim of zero universal risk is never justified by zero observed errors.

Development forest diagnostics use whole-game/identical-before-position grouped out-of-fold predictions:223TP/190FN/2FP/433TN. Direct EC gives 113/300/7/428 on the identical 848 keys and saved baseline inputs. S gives 322/91/19/416; its preceding v4 rule gives 322/91/28/407. These are development findings, separate from the fresh results at the top. The final forest’s training 247TP/0FP is resubstitution and supplies no prospective performance estimate. The fresh test uses that final frozen model, with no label-driven threshold changes or winner selection.

The two outside pawn-winning references remain outside all metrics. The forest withholds both Ndxe5(Excellent) and Nxd5(Brilliant), and misses the Bg2 development example that S recognizes. Reference illustrations must show those limits rather than imply a candidate success.

## Sensitivity and unsuccessful directions: audit index

The main report leads with the fresh test, not an experiment chronology. Detailed diagnostics remain inspectable:

- [Small semantic trees](../learning-v5/README.md): the fixed shallow trees did not meet the combined recognition/false-award goal; stricter leaf purity lost many Brilliants.
- [Lower-budget surprise](../learning-v5/surprise-extension/README.md): a prespecified feature extension produced only a small diagnostic gain, with no false-award reduction.
- [Mover-rating extension](../learning-v5/rating-extension/README.md): no prediction changes under grouped or account-held-out diagnostics; sparse/disjoint rating coverage prevents a beginner-curve conclusion.
- [Fixed forest protocol/audit](../learning-v5/forest-diagnostic/PROTOCOL.json): cost5 threshold5/6 was prespecified. Post-fit pooled-ranking thresholds are not prospective candidates.
- [Uniform1.5m development check](../uniform-stronger-v5/README.md): v4/A extra-award totals did not improve. [Full S replay](../astra/v5/stronger-sequence/RESULTS.md) changes 322TP/19FP to 323TP/18FP. The unchanged full-data forest changes its 300k training outputs 247TP/0FP to 240TP/1FP with stronger evidence. These are sensitivity checks, not new validation or proof that a different engine/budget is supported. Cache/session boundaries are disclosed in the evidence.

## Source, assets and reproduction

The [feature definitions](../learning-v5/FEATURE-DEFINITIONS.json), extractor freeze, forest protocol/model, S freeze and [fresh-test plan](../future-validation-v5/PLAN.json) define the candidates and evaluation. Frozen files and exact output hashes accompany the completed private [test audit](../future-validation-v5/engine-core/FINAL-AUDIT.json) and [manifest](../future-validation-v5/engine-core/MANIFEST.json). The [methods](METHODS-DRAFT.md) record source roles, collection/engine configuration, illustrative move verification and asset provenance.

Input validation and fixed scoring need no engine invocation:

```python
cases = extract_batch(requests)  # legal full PGN + recorded windows only
result = score_fixed_forest(cases[0], frozen_model)
```

The extractor uses the recorded Python-chess, Node 24 and Chessops references. It does not fetch an old observation by game ID or pass observed labels to prediction. No generalized ML runtime or native browser port is implied. Any production integration needs its own validated input/runtime contract, especially native SF19.

Illustrations use actual Mute Chess Moss squares `#C7CFBA` / `#668478`, native gold highlights and Colin M. L. Burnett’s Cburnett SVG pieces, GPL-2.0-or-later. Original vectors, full license and exact source hashes accompany [the visual exports](../visuals/README.md). Quiet-offer capture replies and both pawn-winning sequences are conditional legal illustrations, not asserted forced/game continuations. Only the labeled target move carries its observed Chess.com classification. The successful fresh-test illustration shows Hansen’s actual 17.Bxh7+ Kxh7 from its PGN; only Bxh7+ is the observed Brilliant/frozen-forest award. Its [identity/legality receipt](illustration-proof.json) records exact FENs and the public PGN hash.

### Exact ordered 75-field schema

```text
after_cp, after_depth, after_mapped_score, after_mate
after_minus_prior_cp, already_vulnerable_same_square_count, attribution_unknown, avoidability
avoidability_unknown, before_depth, before_roots, best_cp
best_mapped_score, best_mate, best_minus_prior_cp, best_second_gap_pp
capture_promotion_credit, checked_continuation, converted_material_or_endgame, direct_stalemate_acceptance
ec_material_after, ec_material_before, ec_material_margin, ec_sacrifice
immediate_material_gain, mapped_loss_pp, mating_acceptance, move_capture
move_castling, move_check, move_en_passant, move_in_check
move_promotion, moved_role_b, moved_role_k, moved_role_n
moved_role_p, moved_role_q, moved_role_r, offer_exchange_gain_max
offer_exchange_gain_min, offered_piece_count, offered_piece_moved, offered_role_b
offered_role_k, offered_role_n, offered_role_p, offered_role_q
offered_role_r, phase, physical_checked_horizon, physical_debt3_max
physical_debt3_min, physical_mate_leaf, physical_unknown, played_root_cp
played_root_mapped_score, played_root_mate, played_root_missing, prior_cp
prior_depth, prior_history_missing, prior_mapped_score, prior_mate
prior_offer_gain_original_square_max, prior_offer_gain_same_square_max, raw_material_after, raw_material_before
raw_offer, safe_alternative_best_cp, same_root_loss_pp, same_root_rank
stalemate_probe_unknown, window_complete, winning_safe_alternatives
```
