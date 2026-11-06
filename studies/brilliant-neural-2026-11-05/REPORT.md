# Can a small neural network recognize more Brilliants?

**The tested network did not improve on the tree models.** It recognized far fewer Chess.com Brilliants under the low-error requirement. Retain the existing classifier; this experimental model should not be deployed.

The experiment ran successfully on an M4 MacBook Air with 16 GB of memory. All 78 network fits, validation, and final artifact generation took **47.5 seconds**, with peak process memory of **273 MiB**. The first individual fit took about half a second. The hardware was sufficient.

## Results

All methods below use the same 3,724 labeled moves: 917 Brilliants and 2,807 negatives. Whole games and repeated positions stay together in five validation folds. Each reported move was evaluated by a model that did not train on its group. The tree results are reused from the frozen identical-data comparison, with their hashes, case identities, splits, gates, and metrics checked before neural training.

| Method | Brilliants found /917 | Recognition | Wrong awards | Wrong share of awards |
| --- | ---: | ---: | ---: | ---: |
| Mute tree procedure, fixed cutoff | 436 | 47.5% | 6 | 1.36% |
| Mute tree procedure, validation-selected cutoff | 452 | 49.3% | 6 | 1.31% |
| Standard random forest | 473 | 51.6% | 7 | 1.46% |
| **Small neural network ensemble** | **76** | **8.3%** | **3** | **3.80%** |

The network's lower wrong-award count came with a much larger loss of genuine awards. Its awards also contained a greater proportion of errors. The three separate starting seeds found 59, 57, and 66 Brilliants, with 4, 3, and 3 wrong awards respectively; the poor result was not confined to one starting seed.

These are development results on an enriched research sample, not a new independent game test or a site-wide precision estimate. They do not replace the production model's published independent-test results. All methods rejected the 330 supplemental easy errors; those errors are kept separate from the challenging negatives.

## What we tested

The network receives the existing 75 chess measurements and their 75 missing-value flags. It has two hidden layers of 64 and 32 neurons, then one Brilliant score: 11,777 learned weights and biases per network. The primary prediction averages three fixed starting seeds before requiring both saved engine windows to pass.

The fixed training recipe used Adam, 200 training passes, L2 regularization, and one CPU thread. Missing-value replacement and normalization were fitted using training rows only. Both windows of a move and every move from the same game/position group stayed together. The current chess-quality gates were unchanged. All original training examples remain represented in the combined input.

The award cutoff was chosen using inner validation folds, maximizing genuine awards subject to no more wrong awards and no worse wrong-award fraction than the fixed tree reference. Outer-fold labels did not choose cutoffs or model settings. Individual seed results are diagnostics; we did not select the best seed. The architecture and training recipe were not changed after seeing the results.

## Why it struggled

Training loss decreased, but some ordinary validation moves still received scores extremely close to one. Among eligible validation moves, 74 genuine Brilliants and three ordinary moves scored at least `1 - 10^-10`. Some scores rounded to exactly one, and tied scores were kept together.

The error constraint therefore forced very high cutoffs. In one fold it found no acceptable nonempty award set. Separate final training calibration selected a cutoff near one and recognized only ten of the 917 Brilliants in those calibration predictions. That calibration result is selection evidence, not another performance test.

Checks found correct class/sign handling, persistent training state, training-only normalization, finite parameters, preserved game splits, and agreement between saved-model inference and scikit-learn. The observations are consistent with overconfidence or overfitting; they do not establish which design choice caused it.

## Conclusion and limits

This fixed small network is not a useful replacement. The result does not establish that all neural networks would fail. Stronger regularization, game-aware early stopping, different representations, or other neural architectures remain untested by this experiment. Score saturation also deserves attention before another neural comparison.

Any follow-up should specify those choices before fitting and reserve fresh games for confirmation. This run did not collect new labels, rerun Stockfish, load the already-seen 89-game assessment, change the app, or deploy a model.

## Artifacts

- [Frozen protocol](PROTOCOL.json) and [source](experiment.py).
- [Results and fold decisions](RESULTS.json), [per-case predictions](PREDICTIONS.json), and [training audit](TRAINING-AUDIT.json).
- [Preparation checks](PREP-CHECKS.json) and [final verification](VERIFICATION.json).
- [Experimental model](model.json), [training-only cutoff freeze](SELECTION-FREEZE.json), and [model hashes](MODEL-FREEZE.json).

The model JSON contains the three networks, imputation values, normalization, and cutoff. It is a research artifact, not an application release. Training used the existing Python 3.12.13 / scikit-learn 1.7.2 environment; no new training framework was installed.
