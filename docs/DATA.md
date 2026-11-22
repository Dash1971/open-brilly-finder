# Data guide

## Annotated games

The [combined PGN](../studies/brilliant-selective-2026-11-06/data/seven-accounts-last-12-months-chesscom-brilliants.pgn) contains **7,019 unique games, 8,298 Brilliant annotations and 522,053 mainline moves**, with original clocks and full history.

The accounts are **nelsi, hansen, KNVB, GothamChess, Hikaru, MagnusCarlsen and Witty_Alien**. Labels come from their captured last-year Brilliant galleries and are matched to legal moves in official PGNs. Captured categories and source identity are retained. Witty’s categories were not captured and remain uncategorized.

[Per-account counts](../studies/brilliant-selective-2026-11-06/data/seven-account-source-counts.json) · [Move labels](../studies/brilliant-selective-2026-11-06/data/seven-account-labels.csv) · [PGN validation and evidence grades](../studies/brilliant-selective-2026-11-06/data/seven-account-manifest.json)

## Chess.com Game Review labels

For 1,005 of these games we also recorded Chess.com's own review: **77,696 moves** with their class (Book, Brilliant, Great, Best, Excellent, Good, Inaccuracy, Mistake, Miss, Blunder, Forced), evaluation, search depth and Chess.com's preferred move. The table is [chesscom-review-moves.csv.gz](../studies/brilliant-exchange-2026-11-22/data/chesscom-review-moves.csv.gz). Reviews were run on November 22, 2026 from one member account; another account or day can give different labels.

## Training and evaluation

Mute Exchange was trained on **33,037 candidate moves** and tested on **337 Witty_Alien games** held out from training. [Methods](../studies/brilliant-exchange-2026-11-22/METHODS.md) give the split, the two label references and the limits. The paragraphs below describe the previous study, whose games and gallery labels this one reuses.

## Training and evaluation of the previous study

Mute Selective was trained on **6,293 labeled moves**, including Brilliant examples and ordinary controls. Its independent-account evaluation uses **1,000 Witty_Alien games** outside training and model selection. Only the account’s own moves are scored. The complete captured gallery defines positive labels and the other own moves define negatives within those represented games; missing PGN annotations alone do not define negatives.

The corpus download includes both development and evaluation material. It is not an additional independent test. Source verification varies by label and is recorded explicitly. [Methods](../studies/brilliant-selective-2026-11-06/METHODS.md) give the exact split, overlap exclusions, engine profile and limitations.

## Complete evidence

[The scientific source manifest](../studies/brilliant-selective-2026-11-06/SOURCE-MANIFEST.json) inventories training cases, source PGNs/gallery captures, models, search recipes, saved engine evidence, outcomes and checks. [Extraction and reproduction instructions](../studies/brilliant-selective-2026-11-06/README.md) explain the numbered archives.

[Archived data notes](HISTORICAL-DATA.md) preserve the older studies’ dataset definitions and evaluation boundaries. [Third-party attribution](../THIRD_PARTY.md) covers upstream code and factual game data.
