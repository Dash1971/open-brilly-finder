# Shallow-versus-deep surprise: one fixed extension

The added surprise descriptors produce a small diagnostic gain, **not the requested 90% result**. The default depth-four tree rises from 82.5% to 83.1% grouped-CV agreement, recovering a net five Brilliants with the same 23 false awards. The strict raw 98 point rises from 74.6% to 75.1%, with the same seven false awards and only 50.6% recall. Both results remain below the desired agreement/recall combination.

| Feature set | Operating point | Grouped-CV agreement | Brilliant recall | Extra awards |
| --- | --- | ---: | ---: | ---: |
| Baseline depth 4 | default_cost 5 | 82.5% | 69.7% | 23 /435 (5.3%) |
| Baseline depth 4 | strict98 | 74.6% | 49.6% | 7 /435 (1.6%) |
| With shallow surprise | default_cost 5 | 83.1% | 70.9% | 23 /435 (5.3%) |
| With shallow surprise | strict98 | 75.1% | 50.6% | 7 /435 (1.6%) |

Every result uses the original 434 connected game/position groups, the same five folds, depth 4, minimum 15 distinct moves per leaf, negative cost 5 and both-window quality/offer/floor/confidence guards. Exactly ten descriptors were added; no threshold or model grid was explored. [The extension protocol](EXTENSION-PROTOCOL.json) was saved before fitting. All 848 cases were already unblinded development; this is not a new independent validation set.

The full-data descriptive fit does not use any surprise descriptor and is unchanged. Some CV-fold trees use weak after-scores, strong-minus-weak after-scores or the mapped-loss difference; their modest benefit does not establish a production rule. [Paired changes](PAIRED-CV-CHANGES.json) preserve both corrected and newly introduced disagreements rather than reporting only the net gain.

## What “surprise” means here

The lower-budget run is the same SF18 binary with 10,000 nodes, compared with the saved 300,000-node evidence. It is a search-budget proxy, not a human rating or Maia probability. Current and prior completed windows are paired explicitly. All 1,696 before/after FEN matches pass; no weak decision window is missing. The played move is absent from 451 weak root windows, so its rank/gap remain null rather than being invented.

The ten descriptors are weak mapped loss, weak played-root presence/rank/gap, weak after-centipawns, strong-minus-weak after-centipawns, weak-minus-strong mapped loss, whether the weak and strong first choices differ, before-depth difference, and an explicit missing-window flag. Existing missing indicators are retained for all numeric descriptors. Centipawn differences stay null when either score is mate-valued.

Among cases satisfying both hard eligibility masks, the predeclared larger-is-more-surprising mapped-loss difference has descriptive rank AUC **0.494** (394 observed Brilliants/134 explicit non-Brilliants). This scalar’s observed ranking is approximately chance in this selected group. This rank association is not a fitted threshold, independent significance test or evidence that Chess.com uses this feature.

[Zaidi and Guerzhoy’s 2024 paper, *Predicting User Perception of Move Brilliance in Chess*](https://arxiv.org/abs/2406.11895), reports that a move was more likely to be judged brilliant when a weaker engine rated it worse for the same stronger-engine assessment. That concerns perceived brilliance in their study, not Chess.com’s private labeling formula. Our fixed node-budget comparison is a limited test inspired by that association.

These small trees and this feature extension have not met the goal. Richer validated features or broader independent data may be necessary; neither a larger model nor additional collection is launched automatically from this result.

## Artifacts and reproduction

[Features](features.json), [CSV](features.csv), [predictions](predictions.csv), [full rules](depth4-rules.txt), [full/fold trees](trees-full.json), [results](RESULTS.json) and [audit](AUDIT.json) expose every decision. The copied [CART kernel](cart_kernel.py) is unchanged from the original two-model diagnostic. Extraction peaked at 117 MB and fitting at 78 MB; no engine/browser/application/publication changes occurred here.

```sh
python3 features.py
python3 fit.py
```

The two source analysis files and base feature bank are read-only; this extension writes only its own directory. Strict 98 always means raw unweighted leaf-positive fraction>=0.98, not weighted or calibrated probability.
