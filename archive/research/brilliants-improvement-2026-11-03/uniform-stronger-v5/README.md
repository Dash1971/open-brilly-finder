# Uniform stronger-search development check

**More search did not solve Mute’s extra-award problem on the full corpus.** The unchanged v4 rule goes from 322 to 323 recognized Brilliants while keeping 28 false awards. Variant A goes from 322 to 323 while keeping 27 false awards. Both remove three earlier false awards but introduce three different ones; they recover five observed Brilliants and lose four.

All 848 cases are already-unblinded development: 413 observed Brilliants and 435 explicitly non-Brilliant moves. This is a paired engine-evidence sensitivity check, not fresh validation and not another rule-selection exercise.

| Rule | Baseline 300k TP / FN / FP / TN | Uniform 1.5m TP / FN / FP / TN | Agreement |
| --- | --- | --- | ---: |
| En Croissant direct | 113 / 300 / 7 / 428 | 117 / 296 / 6 / 429 | 63.8% → 64.4% |
| EC with confirmation | 109 / 304 / 7 / 428 | 116 / 297 / 6 / 429 | 63.3% → 64.3% |
| Mute v4 confirmed | 322 / 91 / 28 / 407 | 323 / 90 / 28 / 407 | 86.0% → 86.1% |
| Variant A confirmed | 322 / 91 / 27 / 408 | 323 / 90 / 27 / 408 | 86.1% → 86.2% |

On the historical 200-case cohort, v4 retains 74/100 Brilliants and changes 10 to 9 extra awards; A retains 74 and changes 9 to 8. The panel’s counts are unchanged. [SUMMARY.csv](SUMMARY.csv) records every cohort and policy; [CHANGED-CASES.csv](CHANGED-CASES.csv) includes every corrected and newly introduced disagreement. No favorable subset replaces the headline 848.

Direct EC means its original **current-window annotation**, not Mute-style confirmation. EC confirmation is a separately labeled output. V4 and A use their unchanged complete current/prior-window classifier. Baseline replay reproduces the established 618-case EC84TP/6FP and full 848 v4322TP/28FP, A322TP/27FP before stronger evidence is compared. Copied classifier/helpers are pinned in [REPLAY-SOURCE-FREEZE.json](REPLAY-SOURCE-FREEZE.json); no policy source or threshold was tuned here.

## Uniform evidence and limits

The same pinned SF18 executable, Threads 1, Hash 64 MB and requested MultiPV 2 were used at **1,500,000 requested nodes per position**. Fewer legal roots and terminal positions retain the existing collector’s handling. Every target has full standard-chess PGN history. The collector accepts complete same-depth roots and retains the actual preceding completed iteration; it never copies a final score to manufacture confirmation.

All 848 targets and 2,445 unique positions are covered. Four fixed whole-game partitions preserve chronological positions within games, with Clear Hash and a distinct UCI game session at each game boundary. The [cache-policy verification](CACHE-POLICY-VERIFICATION.json) records the relevant official SF18 and installed python-chess source hashes. No baseline 300k or targeted 90-case engine output was substituted.

Original workers retained 1,769 complete position snapshots before their initial time caps. A parent-authorized once-only continuation computed the remaining 676 positions at the same requested node budget. It preserved every checkpointed snapshot byte-for-byte. Three partially completed games have explicitly recorded fresh-UCI/TT restart boundaries; no claim is made that their warm-cache history is identical to uninterrupted searches. The fourth restart occurred at a game boundary. Original evidence, frozen remaining-position queues and both source files are retained; no checkpointed position was searched again. Interrupted uncheckpointed attempts were discarded and recomputed only under that bounded authorization.

The original 60-minute recorded-search estimate was superseded by explicit throughput allowances after measured runtime. Quantity, node limit and algorithms stayed fixed. Final caps were 1,600 recorded seconds per worker, with no further expansion. Actual aggregate recorded search was **86.22 minutes**, including interrupted attempts, while elapsed time from first worker start to final completion was **24.71 minutes**. Recorded parallel search durations are not billing or single-core CPU time. [PLAN.json](PLAN.json), [final allowance](PLAN-FINAL-ALLOWANCE.json), worker/tail plans and source receipts expose these changes. As-run collectors are retained unchanged; their actual `BUDGETS`/output metadata are authoritative over an inherited shallow-run comment.

[MERGE-AUDIT.json](MERGE-AUDIT.json) and [FINAL-AUDIT.json](FINAL-AUDIT.json) check unique windows, PGN/FEN identities, legal distinct roots, unchanged source window blocks and caps. All engine processes exited before the separately authorized supplemental-S work was handed to its owner. No further core searches, app changes or public-report updates are performed by this experiment.

## What this does and does not show

The previously selected 90-case stronger check looked uniformly favorable. That did not establish full-corpus behavior: this uniform run reveals new false awards and lost Brilliants outside that impression. Search depth matters, but greater budget alone does not establish the desired 90% agreement/low-false-award classifier. Differences also reflect recorded cache/session history, including the disclosed restart boundaries; this is not a claim of pure node-count causality.

The fair **baseline 300k** comparison against the prespecified forest diagnostic is retained separately: forest grouped out-of-fold predictions give 223TP/2FP versus direct EC113TP/7FP on identical 848 keys, labels and SAN. Those sample counts favor the forest on recognition and extra awards, but the forest was developed on this now-unblinded corpus. It is not fresh validation, a calibrated production claim, or a comparison against EC on different stronger evidence. See [EC-FOREST-BASELINE.json](EC-FOREST-BASELINE.json).

Exact saved-input rule replay needs no engine:

```sh
node /path/to/tsx/dist/cli.mjs replay.mts
```

[paired-results.json](paired-results.json) preserves every classifier output and input hash. New engine runs can vary with search/session history; they must write separate outputs rather than replace the evidence or force desired labels. No new collection or larger experiment is launched automatically from these results.
