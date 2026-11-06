# Methods, evidence, and limitations

## Development and frozen selection

The benchmark contains 3,473 games from GothamChess, hansen, Hikaru, KNVB, MagnusCarlsen, and nelsi: 3,857 Brilliant moves and 146,188 other own moves. Two owner examples are separate full-fit diagnostics, excluded from benchmark totals. Training uses 6,293 labeled move cases, representing 6,189 unique fitting positions; selected feature controls and all-move replay negatives have different denominators.

Whole-game and identical-position grouping determines three development folds. Models are refitted per fold. The search covers 96 compiled-tree recipes plus two fixed custom reference recipes; 32-tree scouts promote twelve recipes to 128 trees. Seeds, recipes, folds, missing indicators, costs, candidate cutoffs, all results, and every model are archived. The selected recipe is `r009`: 128 trees, maximum depth 12, minimum leaf size 2, 24 sampled predictors, class cost 1, cutoff 0.83. Development replay uses the native classifier and shared complete-confirmation scheduler. It is **selection-biased development evaluation**, not an independent test: recipes and cutoffs were chosen using its labels. Production/reference comparisons with historical overlap are descriptive.

Selected native development totals are 2,292 true awards, 1,565 missed Brilliants, 89 extra awards, and 146,099 correctly unawarded ordinary moves. At cutoffs 0.79 and 0.73 the same forest recognized more Brilliants but produced 124 and 180 extra awards respectively. No Witty labels or predictions were used to alter weights, features, cutoffs, or gates.

## Fresh Witty_Alien comparison

A complete visible last-365-days gallery supplied 4,411 Brilliant entries in 3,546 games. The capture interval, public URLs, full metadata, evidence grades, and official monthly PGN download receipts are preserved. Game selection used a fixed SHA ordering, excluded development games, and masked canonical before-position overlap with development. The first 1,000 eligible ranked games were used. An original 200-game run is reused byte-for-byte in the 1,000-game result. The owner expanded the same frozen sample after partial original-run outcomes were visible; therefore the stopping/sample-size decision was not fully outcome-blind. There was no model tuning, replacement of disappointing games, or recomputation of the original 200.

The test contains 62,992 complete mainline plies and 31,658 Witty own moves. One prior-position Brilliant is excluded, leaving **1,234 positive and 30,423 negative primary moves**. Unmasked and excluded outcomes remain separate. Only the named account’s moves count. Listed gallery moves are positive; other own moves in these gallery-represented games use the explicitly adopted gallery-negative convention. They are not all independently re-reviewed Game Review labels, and missing PGN NAGs are not negative evidence. The study does not estimate performance in arbitrary games with no gallery entry.

Of 1,235 unmasked labels, 496 have exact rendered-board and arrow evidence; 739 have gallery-link/UUID/ply/mover/legal-PGN identity evidence. These grades remain per label, rather than being described collectively as full board verification. The primary masks do not silently discard the weaker grade. Official full PGNs preserve history, clocks, SAN/UCI, before/after positions, both colors, and the distinction between nominated and verified evidence.

## Paired native replay

All three versions share the same initial native Fast engine evidence, full history, terminal handling, and six-search-per-game confirmation cap. Confirmation may require variant-specific checks. The complete-confirmation fix retains preceding position evidence when an award is rechecked; it does not expand the six-search cap. The active scheduler is `noSweatFullReview285.ts`. The unused older scheduler copy is not the tested implementation. Initial depth is 12 with 500 ms; confirmation depth is 14 with 500 ms. Engine: SF19 smallnet 1 MB, Threads 1, Hash 16 MB. Timing, worker receipts, source/model hashes, initial/confirmation snapshots, scored masks, raw decisions, and partial/failure records are included.

On primary moves, updated Mute Selective gives **774 TP / 460 FN / 38 FP / 30,385 TN**, versus complete-confirmation older forest **725 / 509 / 58 / 30,365** and older production **721 / 513 / 57 / 30,366**. Against complete-confirmation older forest, it gains 95 genuine awards, loses 46, adds seven false awards, and removes 27: net +49 genuine and −20 extra awards. No fresh En Croissant run was performed.

## Interpreting the numbers

Recognition is `TP / (TP + FN)`: 62.7%. Badge precision is `TP / (TP + FP)`: 95.3%. Wrong-award share is `FP / (TP + FP)`: 4.7%. Ordinary-move false-positive rate is `FP / (FP + TN)`: 0.125%. These answer different questions. The many ordinary moves make overall agreement an unhelpful headline. Moves within a game are correlated, and one held-out established account does not establish beginner or population behavior. Engine depth/budget, available evidence, and Chess.com’s changing labels can affect results.

The seven-account download contains 7,019 unique games, 8,298 annotations, and 522,053 mainline plies. It includes all captured Witty and Magnus gallery entries, not just scored test games. Shared games merge annotations while retaining account/source identity. Combined evidence grades are 4,831 board-and-arrow exact, 364 board exact, and 3,103 link-only; Witty’s unrecorded sacrifice categories remain `Uncategorized`, not inferred categories.

Earlier En Croissant and 400-move selective comparisons remain [historical studies](../brilliant-moves/REPORT.md). Their engine, sample, and model differ; their numbers are not fresh Witty measurements. The [neural experiment](../brilliant-neural-2026-11-05/REPORT.md) and all failed/current search recipes remain available without being promoted to the chosen model.

## Sources and licensing

Chess.com publishes broad criteria, including sacrifice, move quality, and player strength, but not its complete formula: [classification criteria](https://support.chess.com/en/articles/8572705-how-are-moves-classified-what-is-a-blunder-or-brilliant-etc), [Game Review](https://support.chess.com/en/articles/8584089-how-does-game-review-work), and [PGN export](https://support.chess.com/en/articles/8705305-how-do-i-get-a-pgn-of-my-game). Those descriptions motivate the study; they do not prove an inferred rule. Public monthly archives supply the original games. Chess.com labels are observations with recorded provenance, not an open-source release of its algorithm.

The repository’s code license and bundled upstream notices apply. Native classifier code derives from Mute Chess/lila and En Croissant; upstream source and notices are retained. Stockfish assets retain their GPL notices, chessops and badrap retain their own licenses. Games and gallery observations are third-party factual research data; this project does not claim ownership of Chess.com’s branding or labeling method. No cookies, credentials, browser profiles, shell environments, or private operational logs are published.
