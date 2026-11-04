# Fixed forest capacity diagnostic

**The additional capacity helps precision, but it does not reach the required recall or agreement.** At the fixed5/6 operating point, grouped outer-fold predictions award223 of413 observed brilliants with two false awards among435 negatives. That is54.0% recall and77.36% agreement. At0.98, only16 brilliants are awarded, with no observed false awards. Neither is a production candidate or a new independent validation result.

The protocol was saved before fitting. It fixes64 trees, maximum depth6, minimum eight distinct original moves per leaf, negative class cost5,12 random expanded features per split, and seed20261103. The representation is exactly the existing CART input:75 features plus75 missing indicators. Each bootstrap samples entire game/identical-before-position union components; individual windows are never resampled independently. Both original window eligibility guards and case confidence remain required for an award.

Leaf probability is its raw positive fraction among bootstrap window rows, without class-cost weighting. The forest averages those64 fractions separately for current and previous windows. Both means must reach the threshold. These scores are not calibrated probabilities of Chess.com's label.

## Fixed operating points

| Grouped five-fold diagnostic | TP | FN | FP | TN | Recall | Agreement |
|---|---:|---:|---:|---:|---:|---:|
| Prior depth3 CART, cost5 |256|157|18|417|62.0%|79.36%|
| Prior depth4 CART, cost5 |288|125|23|412|69.7%|82.55%|
| Prior depth4 CART, strict0.98 |205|208|7|428|49.6%|74.65%|
| Forest, mean raw p≥5/6 |223|190|2|433|54.0%|77.36%|
| Forest, mean raw p≥0.98 |16|397|0|435|3.9%|53.18%|

The forest's5/6 point improves on the previous depth4 strict point by18 true detections and five fewer false awards. Against the depth4 cost5 point, it reduces false awards by21 while losing65 true detections. The prespecified FN+5FP cost falls from240 to200, but this improvement does not satisfy the main goal of high recall together with very few false awards. Different ensemble/leaf/operating-point presets changed together, so this is not an isolated causal estimate of depth alone.

The separate full-data descriptive fit gives247TP/166FN/0FP/435TN at5/6, and20TP/393FN/0FP/435TN at0.98. Those are training resubstitution figures, not validation. The guarded case-level out-of-fold AUC is0.9441; the raw minimum-of-two-window AUC is0.9065. The features contain useful ranking signal, but AUC averages over the whole ranking and does not establish the required extreme low-false-award tradeoff.

## Ranking limit of the already-fitted scores

After the fixed fit, the parent separately authorized a descriptive pooled-OOF ranking analysis. **Its common thresholds were chosen using the known pooled labels and must not be treated as validated operating points.** No model was refit, no feature changed, and neither fixed operating point above was revised. Whole equal-score ties enter together, with no fractional or label-based tie splitting; original eligibility/confidence guards always apply.

* At no more than eight false awards among435 negatives, the largest reachable true-positive count is272:65.86% recall and82.43% agreement. The descriptive common threshold is0.7531126542787281.
* To reach at least339 true positives, the minimum reachable false-positive count is24:82.08% recall,5.52% false-award rate, and88.44% agreement. Its descriptive threshold is0.6426334637238499.

Even this optimistically selected pooled threshold cannot simultaneously reach the requested recall/low-false-award combination. Nested calibration alone cannot create ranking separation absent from these fixed scores. This result does not prove an information-theoretic limit on the features, other models, or Chess.com's criteria; it says this fixed larger-capacity diagnostic is insufficient. Better evidence or semantic features remain a more concrete next hypothesis than deploying a retuned threshold from these same labels.

## Audit and artifacts

All848 examples are unblinded development data. The exact existing five folds keep434 union components,439 games, and841 normalized before positions separated. All384 fitted trees pass the bootstrap audit;6,675 leaves have at least eight distinct original moves, with a minimum of five distinct components. Maximum depth is6. There is no training/test component overlap. Identity, game IDs, accounts, ratings, labels, coach text, and fold/group metadata never enter the predictor matrix.

The run took4.804seconds with89,718,784bytes peak RSS, one Python worker, no engine and no installed dependencies. `PROTOCOL.json` records pre-fit settings and input hashes; `MODEL-AUDIT.json` records grouping/leaf checks. Predictions, exact matrices, AUC, bootstrap multiplicities, full descriptive forest, and Gini importances are preserved separately. The leading collapsed importances are EC material margin, EC material after, EC sacrifice, whether the offered piece moved, and competitive-score changes since the previous own turn. These are model split statistics, not causal explanations.

`SELECTION-BIASED-OOF-RANKING.json` deliberately separates the post-fit ranking inspection from the fixed experiment. No further fit, threshold tuning, publication, or application change was performed.
