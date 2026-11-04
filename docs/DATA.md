# Data, labels and evaluation boundaries

This repository contains curated research evidence, code, model artifacts and study reports. It is not a dump of authenticated browser sessions or the original workstation. Source hashes and study freezes preserve provenance; any import omissions or transformations should be read alongside the repository import manifest.

## Start with these datasets

| Location | Contents and purpose |
| --- | --- |
| [`studies/brilliant-moves`](../studies/brilliant-moves/README.md) | The selected 848-example model, its 75-feature definition, exact inference rules, reference implementations and the historical independent tests. |
| [`studies/brilliant-training-2026-11-03/data/training.json`](../studies/brilliant-training-2026-11-03/data/training.json) | The expanded development set: 3,724 deduplicated moves, 917 Brilliant labels and 2,807 ordinary labels, with features for two engine windows, aliases and game/position groups. |
| [`studies/brilliant-training-2026-11-03/data/CORPUS-MANIFEST.json`](../studies/brilliant-training-2026-11-03/data/CORPUS-MANIFEST.json) | Hashes and provenance for the overnight collection's compressed PGNs, labels and factual evidence. This collection is a source of the expanded dataset, not a synonym for all legacy training data. |
| [`studies/brilliant-training-2026-11-03/pv-trajectory-experiment/source-pack/MANIFEST.json`](../studies/brilliant-training-2026-11-03/pv-trajectory-experiment/source-pack/MANIFEST.json) | Full training-game records and saved analysis snapshots needed to recover move history and legal engine continuations. |
| [`studies/brilliant-training-2026-11-03/code/SOURCE-MANIFEST.json`](../studies/brilliant-training-2026-11-03/code/SOURCE-MANIFEST.json) | Frozen extraction, inference and training source, plus saved engine-evidence lineage. |
| [`studies/brilliant-external-comparison-2026-11-04/PAIRED-CASES.json`](../studies/brilliant-external-comparison-2026-11-04/PAIRED-CASES.json) | Case-level labels, original groups, forest baseline decisions and frozen Knight's Eye/WintrChess decisions, including unresolved evidence. |

The expanded data contain 987 source game identities but 972 connected evaluation groups. Aliases, repeated positions and games that must remain together can merge into one group. Do not replace those groups with random move-level splits.

The overnight collection itself saved 422 complete games from five established public accounts. Its 390 verified Brilliants, 2,351 challenging ordinary moves, 7,669 clear errors and 46 other explicitly non-Brilliant moves are collection totals; they are not the class counts of the final deduplicated training file. An incomplete collected game was retained as evidence but excluded from the independent comparison.

## Meaning of a label

The target is agreement with the saved Chess.com move-level classification. Positive means a verified Brilliant; negative means explicit evidence for an ordinary classification or the recorded negative category. Absence of a Brilliant annotation is not automatically a negative label. Public game identity, target ply, FEN, legal move identity, source URL and recorded observation help connect a label to the actual position.

A wrong award means disagreement with that recorded label. It does not mean that the move was poor chess. Chess.com review settings, engines, evaluation depth and historical labeling behavior are not uniformly recorded. Where re-review or settings comparisons were performed, the relevant study reports that narrower evidence. No repository result establishes a complete reconstruction of Chess.com's private policy.

Ratings, player/account identifiers, clocks and dates are not classifier predictors. PGN headers may retain public-game context. Keeping metadata for provenance does not authorize using it as a feature; the current research objective is rating-independent classification.

## Three different evaluation populations

1. **Historical independent tests of the selected model.** The 848-example model was evaluated on two game-disjoint 200-move sets: 112 of 200 Brilliants found (56%), with 3 wrong awards among 200 controls. The wrong share of its awards is 3/115 = 2.61%; 3/200 = 1.5% is instead the false-positive rate on controls. The newest test subset alone is 57/100 Brilliants with 2 wrong awards. These results concern that frozen model and those selected samples.
2. **Overnight reserved games.** The separately reserved 89-game evaluation contains 71 Brilliants, 494 challenging ordinary moves and 89 clear errors. Current Mute found 42/71 (59.15%) with 2 wrong ordinary awards; En Croissant found 18/71 with 3 wrong; the expanded-data candidate found 37/71 with 0 wrong ordinary awards. Easy errors are reported separately.
3. **November 4 development comparisons.** Most experiments reuse the expanded 3,724-move set with the same five outer game/position folds and three inner folds. The commonly quoted 452 correct / 6 wrong baseline is the original forest learning method evaluated through those folds, with inner-selected thresholds. It is not the deployed 848-example model's independent test result.

The November 4 experiments have repeatedly informed hypotheses and investigations. Keeping groups intact prevents direct game/position leakage, but repeated research on the same corpus still makes fresh prospective validation necessary. A diagnostic matched panel is not an independent test set. The later mating-offer study has its own prospectively frozen, deliberately targeted sample and denominator.

## Metrics and unknowns

- **Recall:** correctly awarded Brilliants divided by all labeled Brilliants.
- **Wrong share of awards:** wrong Brilliant awards divided by all Brilliant awards. The project target is under 1% by this definition, not under 1% of ordinary moves.
- **False-positive rate:** wrong Brilliant awards divided by ordinary controls. This is a different metric.
- **Unresolved evidence:** no supported classification under the prescribed budget or evidence contract. It is neither a confirmed ordinary decision nor a true negative.

The frozen external comparison reports confirmed recall over all 917 positives as a lower bound when cases remain unresolved, along with explicit coverage and resolved-only comparisons. Its two-window conjunction is separate from each classifier's single-window output. Do not silently substitute one denominator or mode for another.

The cohorts are intentionally rich in Brilliants and difficult tactics. Precision in this sample is not a measured site-wide award reliability. Also, the inherited `negative_bucket` field is a source cohort flag: some rows in `hard_ordinary` or `legacy_mixed` have positive `truth`. Use `truth` for the class label.

## Publication and reproduction limits

The public package keeps structured labels, numerical evidence, original public-game PGNs, source pins, protocols, model artifacts and research outcomes, including rejected experiments. Raw HTTP responses, authenticated browser captures, local session/account state, caches and unrelated Mute operations are excluded from the curated import. Some archived reports and hashes refer to those excluded original observations; their absence must not be disguised as a reproduced browser check.

Historical scripts can contain absolute workstation paths, original source-tree names and temporary dependency locations. Those files are audit snapshots. Follow the repository's current reproduction instructions for supported portable commands; do not assume every archived script is directly runnable after cloning. Saved-output verification, rebuilding a classifier comparison and reacquiring Chess.com labels are distinct levels of reproduction.

The inherited research archive retains its source license. Third-party implementations, chess assets and factual data provenance retain their own attribution records; an aggregate repository license should not be read as a new license for every third-party item.
