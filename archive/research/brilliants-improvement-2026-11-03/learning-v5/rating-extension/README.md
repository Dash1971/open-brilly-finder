# Does mover rating add the missing signal?

**No prediction changes in this fixed experiment.** Adding actual mover PGN rating leaves every grouped-CV and leave-one-account-out award unchanged, at both prespecified operating points. No fitted tree uses a rating split. This is a negative result for this small model/feature bank, not evidence that Chess.com ignores rating.

[Chess.com’s published explanation](https://support.chess.com/en/articles/8572705-how-are-moves-classified-what-is-a-blunder-or-brilliant-etc) says sacrifice criteria are more generous for newer players. That justifies testing rating as a possible conditioning input. The exact private formula and which rating/snapshot it uses are not disclosed; the game’s PGN mover rating is an observable proxy, not a reconstruction of that formula.

## Fixed result

The rows below are **identical with and without rating**. All 848 cases are already-unblinded development; both schemes are diagnostics, not fresh independent validation.

| Evaluation | Operating point | Agreement | Brilliant recall | Extra awards |
| --- | --- | ---: | ---: | ---: |
| group_cv | default_cost 5 | 82.5% | 69.7% | 23 /435 (5.3%) |
| group_cv | strict98 | 74.6% | 49.6% | 7 /435 (1.6%) |
| leave_one_account_out | default_cost 5 | 84.8% | 74.8% | 25 /435 (5.7%) |
| leave_one_account_out | strict98 | 75.5% | 51.3% | 7 /435 (1.6%) |

The strict setting keeps extra awards near 1.6% of sampled controls while missing roughly half of observed Brilliants. Neither operating point reaches 90% agreement or 82% recall with low false awards. A strict leaf’s raw 98% training fraction is not a calibrated future precision guarantee.

The original 75 semantic predictors and depth 4/minimum 15 distinct-move leaf/negative-cost 5 setup were unchanged. Rating is the only new continuous input, with an explicit missing indicator. Account, opponent rating, time control, date and category never enter the model. Both completed-window predictions and the original raw-offer/quality/after-floor/confidence guards still have to pass.

Original grouped-CV predictions were reused. Exactly 16 new training runs were declared: five rating/grouped fits, five original and five rating leave-one-account-out fits, and one full-data descriptive rating fit. No depth, threshold, feature or model selection followed the outcomes. [PROTOCOL.json](PROTOCOL.json) predates fitting.

## Account balance and rating coverage

Core 818 has equal Brilliant/non-Brilliant counts within **every** account, so account identity cannot supply a core class-prior shortcut. The panel is deliberately different and remains separate. Raw-offer/quality eligibility changes class ratios in the training windows, so unconditional balance alone does not remove every player-proxy risk; those conditional counts are recorded in the audit and the account-holdout diagnostic remains necessary. No rating is missing; neither account averages nor opponent ratings were substituted.

| Account | Core Brilliant / other | Panel Brilliant / other | Actual mover rating | Held-out ratings outside training range |
| --- | ---: | ---: | ---: | ---: |
| nelsi | 110 / 110 | 0 / 3 | 2423–2747 | 0 / 223 |
| hansen | 79 / 79 | 2 / 4 | 2536–3174 | 0 / 164 |
| KNVB | 50 / 50 | 2 / 15 | 2924–3178 | 0 / 117 |
| GothamChess | 60 / 60 | 0 / 2 | 1591–3044 | 2 / 122 |
| Hikaru | 110 / 110 | 0 / 2 | 3332–3500 | 222 / 222 |

All 222 held-out Hikaru ratings exceed the other accounts’ maximum 3178. Two GothamChess ratings are below the other accounts’ minimum 2423. These gaps expose missing range coverage, rather than establishing a rating curve. Five established accounts, with mostly high game ratings, cannot establish beginner behavior. Within-account continuous rating could still matter despite balanced class counts; this tree simply did not select it.

Leave-one-account-out holds one account’s entire cases out and purges any training connected group that touches them. In this corpus no additional cross-account group purges were necessary. Grouped CV retains the original 434 whole-game/identical-before-position components and fixed five folds. Current/prior rows from a case stay together in both schemes.

| Held-out account | Operating point | TP / FN / FP / TN | Agreement |
| --- | --- | --- | ---: |
| nelsi | default_cost 5 | 71 / 39 / 5 / 108 | 80.3% |
| nelsi | strict98 | 51 / 59 / 2 / 111 | 72.6% |
| hansen | default_cost 5 | 61 / 20 / 5 / 78 | 84.8% |
| hansen | strict98 | 54 / 27 / 2 / 81 | 82.3% |
| KNVB | default_cost 5 | 40 / 12 / 5 / 60 | 85.5% |
| KNVB | strict98 | 21 / 31 / 1 / 64 | 72.6% |
| GothamChess | default_cost 5 | 50 / 10 / 2 / 60 | 90.2% |
| GothamChess | strict98 | 36 / 24 / 0 / 62 | 80.3% |
| Hikaru | default_cost 5 | 87 / 23 / 8 / 104 | 86.0% |
| Hikaru | strict98 | 50 / 60 / 2 / 110 | 72.1% |

Every account/fold’s full/core/panel confusion counts, recall, false-award rate and sample precision are retained in [ACCOUNT-FOLD-METRICS.csv](ACCOUNT-FOLD-METRICS.csv) and [RESULTS.json](RESULTS.json); no player or panel subset was selected for a favorable headline.

## Audit and reproduction

[PRE-FIT-AUDIT.json](PRE-FIT-AUDIT.json) records class balance, exact ranges, source hashes and train-range gaps. [AUDIT.json](AUDIT.json) checks same rating in both windows, zero train/test group overlap, leaf sizes, guard preservation and zero rating-induced prediction changes. [features.csv](features.csv), [predictions.csv](predictions.csv), [trees.json](trees.json) and [full rules](full-rating-rules.txt) permit row-level review. Identity/account/cohort fields in these files are audit/fold metadata, never predictors.

```sh
python3 prepare.py
python3 fit.py
```

The scripts reuse existing NumPy and saved evidence. Fitting took 1.05 seconds and peaked at 90 MB. No engine, browser, app, public report or new dependency was involved. The bounded experiment stops here; these outcomes do not authorize a larger model or more collection automatically.
