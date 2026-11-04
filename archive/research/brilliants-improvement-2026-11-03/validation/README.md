# Independent validation plan

The frozen candidate must be tested on **100 newly confirmed Brilliants and 100 explicitly non-Brilliant moves**, with 20 of each per account. Treat every one of the existing 618 cases as development, including the former reserved subset. The candidate source is frozen in [CANDIDATE-FREEZE.json](../CANDIDATE-FREEZE.json); no tuning or alternative candidate selection is allowed from the new results.

## What is available without opening profiles

A read-only inventory found connected Chrome profile D and one existing user tab. No tab was claimed, opened or read. No fresh review, engine or network collection was started by this planning work.

The cached-source audit covers 558 distinct historical gallery move candidates. It excludes **325 reviewed/development game IDs**: all 299 primary games plus 26 other development games. There are 320 fresh-reviewed games and 684 distinct observed fresh move keys. Position protection includes 1,931 explicit/sampled development positions and, conservatively, 25,904 positions from their full cached games.

| Account | Checked unused moves | Checked new games | PGN/position-pending moves | Available checked categories |
| --- | ---: | ---: | ---: | --- |
| nelsi | 0 | 0 | 0 | None |
| hansen | 41 | 39 | 3 | Bishop, Knight |
| KNVB | 94 | 87 | 4 | All four |
| GothamChess | 32 | 32 | 12 | All four |
| Hikaru | 0 | 0 | 9 | None yet |

These are **historical candidates, not confirmed new Brilliants**. Overall there are 167 position-checked moves in 158 new games, plus 28 moves requiring additional PGN/position preparation. One candidate overlaps a development position and three duplicate before-position/move candidates are excluded. A read-only scan of existing monthly PGN files resolved none of the 28 pending moves; no new download was made.

A cached-only, account-balanced sample can fill **60 of the 100 positive slots**. Requiring five per sacrifice category per account would fill only 50: Hansen's checked pool has no Queen/Rook candidates. The main protocol therefore uses category round robin where available, with the actual distribution reported. Preserve 20 per account and obtain focused nelsi/Hikaru topups; do not silently fill their quotas with more KNVB games.

## Collection path

1. Verify candidate hashes against the source freeze. Refresh the exclusions with every additional development game or explicitly inspected position before fresh labels.
2. Prepare 20 cached targets each for Hansen, KNVB and GothamChess, using account/category hash ordering, one positive per game and frozen systematic reserves. Keep candidate IDs/FENs collector-only until the source freeze; aggregate availability is safe to report earlier.
3. Parent captures focused nelsi/Hikaru category gallery topups in fresh profile tabs, closing each afterward. Skip all excluded games; derive exact plies from observed links and verify the live/daily namespace against the PGN Link. Freeze eligible topup identities before opening their Game Reviews. Current source capacity needs at least 20 new eligible games for each of those accounts, plus reserves for changed labels and overlaps.
4. Resolve PGNs from existing monthly files first, then only the documented public monthly downloads needed for missing games. Store each game once; keep raw HTTP response metadata private.
5. Prefer an alternative raw-v2 legal offer for each negative, then a quiet attacked/defended move, exchange/recapture, other capture or other quiet move. Exclude development-position overlap and terminal-after cases before labels. Missing gallery membership is unknown. Retain Book labels that satisfy this pre-label procedure and report the hard-offer subgroup separately.
6. Collect in one fresh review tab per game. Save visible SAN, exact game/namespace/ply/URL, explicit label and rendered board; record visible coach completeness honestly. Close immediately after the pair is saved. Preserve failed historical positives and unexpected Brilliant controls as secondary, then take the next frozen reserve. Cap the main sample at100/100.
7. Do not inspect candidate agreement while filling the sample. Run the fixed engine configuration only after collection tabs are closed. Report paired changes against v3, v2 and direct EC, including false awards and missed Brilliants, account/category coverage and clustered uncertainty.

## Why 100 + 100

This is a credible first independent check for a moderate improvement, not a precise estimate for every account or sacrifice type. Each account has only20 examples per class, and a nominal five per category is too small for reliable subgroup claims. Even zero errors in100 independent negative cases has an approximately2.95% one-sided95% binomial upper bound; game/position dependence makes optimistic move-level precision inappropriate. Report uncertainty and the predeclared FN+3×FP tradeoff. Do not turn a disappointing result into another tuned candidate on the same test.

A smaller50/50 batch is useful for operational feasibility, but too weak for the final false-award claim. If a first few pairs are used to measure throughput, keep the rule frozen and the author blinded to outcomes; those pairs can remain in the predeclared200.

## Optional mechanism panel

A separate **40-case panel** may contain10 preselected cases each for mating acceptance, unchanged offers while answering check, phase/winning context and cross-square material recovery. Fix identities from board/history features before current labels. Keep every observed label and report this panel separately; do not rebalance it into20 positive/20 negative or merge it into the main200 headline.

Legal mate-in-one witnesses and exact check/history features can be prepared without an engine. Material/phase alone does not prove a winning position, and capture-only recoup lines do not prove forced play. If a proposed feature is too scarce, report the shortage; do not inspect labels and substitute a different mechanism. Definitions and resource rules are in [PLAN.json](PLAN.json).

## Expected work and limits

After source preparation,100 game/pair captures should take roughly20–45 minutes with one collector, including uncached reviews and routine replacements; this is a planning range, not a promised throughput. The successful fresh-tab-per-game workflow previously needed about5–30 seconds per game, while the earlier accumulating-tab workflow caused severe memory growth. Start with five pairs to measure actual throughput, without inspecting policy agreement. Two collectors require parent memory clearance and disjoint game assignments.

Budget another5–15 minutes for focused gallery/PGN preparation, depending on page overlap and archive availability. The optional40-case panel adds up to40 explicit move captures and may reuse already opened new games only when preselected; fewer distinct games means dependent observations, which must be reported. Engine replay is a separate parent-controlled phase, never concurrent with heavy browser collection.

[CANDIDATE-AUDIT.json](CANDIDATE-AUDIT.json) records counts, source hashes and capacity checks. [EXCLUSION-AUDIT.json](EXCLUSION-AUDIT.json) records the current game exclusions and position-set hashes. Collector-only candidate files contain no new current labels. No claim of population error frequency, enjoyment or near-perfect Chess.com reproduction follows from this selected test.
