# Methods, evidence and limits

[Report](REPORT.md) · [Exact algorithm and reproduction](README.md)

## Data

**Games and gallery labels.** The seven-account collection from the previous study: 7,019 games by nelsi, hansen, KNVB, GothamChess, Hikaru, MagnusCarlsen and Witty_Alien, with 8,298 annotations from their last-365-day Brilliant galleries ([PGN](../brilliant-selective-2026-11-06/data/seven-accounts-last-12-months-chesscom-brilliants.pgn)). We score only the gallery account's own moves: 262,215 moves, 8,295 Brilliant.

**Chess.com Game Review.** On November 22, 2026 we re-reviewed 1,005 of those games on Chess.com from a signed-in member account and recorded, for every move, the classification, the evaluation, the search depth, and Chess.com's preferred move when it differed. 1,203 games were requested; 198 timed out and were not retried. The 1,005 are 667 development-account games and 338 Witty_Alien games, 337 of which belong to the earlier study's 1,000-game test sample. The decoded per-move table is [chesscom-review-moves.csv.gz](data/chesscom-review-moves.csv.gz) (77,696 moves, both colors).

Review output depends on the reviewing account's settings and on when the review runs. Ours reported depth 18 on typical moves. We did not change any account setting. The review also classifies moves inside its suggested lines; we found those labels depend on how deep in the line a move sits, so we did not train on them.

**Two references.** A gallery label says the move was Brilliant in whatever review populated the gallery. A review label says it is Brilliant in our review today. They agree on 1,110 moves; 60 are gallery-only and 84 review-only. We report results against the gallery, and separately count which disagreements the review confirms.

## The offer test

Exchanges are resolved with fully legal captures on a single square. The side to move takes with its least valuable legal attacker and may stop at any point. Piece values are pawn 1, knight 3, bishop 3, rook 5, queen 9. A move is a **candidate** when, after it, the opponent's best such capture of a non-pawn piece gains 2 or more. 32,584 of 262,215 moves are candidates; they include 8,290 of the 8,295 Brilliants.

## Engine evidence

Stockfish 18, one thread, 64 MB hash, hash cleared between positions, 200,000 nodes per search. For every candidate we searched the position before the move with three lines, and the position after it twice: once restricted to captures of an offered piece and once restricted to every other reply. Scores were recorded at every completed depth so shallower budgets could be read back without re-searching.

The published model uses only what Mute Chess's review window already holds: the top two lines before the move and the single best line after it, read back at depth 12. We emulate the best reply as whichever of the two restricted searches is worse for the mover.

Scores are centipawns from the mover's side clipped to ±9000; mates map beyond that.

## Features

91 numbers per candidate, computed from three positions (before the opponent's last move, before the move, after the move), the move, and the engine lines above. The exact definitions are the reference code in [code/v6ref.py](code/v6ref.py) and its TypeScript twin in [model/](model/noSweatBrilliantExchange.ts).

- **The offer:** piece, exchange gain, whether it is the moved piece, what the move captured, how many other moves kept material.
- **Acceptance:** for each profitable capture of the offered piece, the mover's best immediate recapture by static exchange, whether that capture was already threatened, mate in one, available checks.
- **Capture-only search:** material the opponent can win by captures and promotions alone, to depths 2, 4, 6 and 10, with all replies when in check.
- **History:** whether the same piece was on offer before the opponent's last move, and what that move did to it.
- **Engine:** best and alternative scores, the played move's rank among two lines, its score afterwards, win-chance loss under `100 / (1 + exp(-0.00368208 * cp))`, and whether the engine's reply takes the piece.

Player, rating, game, date and Chess.com label are not inputs.

## Model and cutoff

scikit-learn `HistGradientBoostingClassifier`: 400 iterations, learning rate 0.05, at most 31 leaves, minimum 20 samples per leaf, L2 1.0, seed 0. No hyperparameter search was run.

**Training set:** 33,037 candidates, 7,806 Brilliant. It contains every gallery-account candidate outside the 337 test games, with the review label where a review exists and the gallery label otherwise, plus opponents' candidates in the re-reviewed development games with their review labels. Any training row whose position and move also occur in the test set was removed.

**Cutoff:** chosen from five-fold cross-validation grouped by game inside the training set, as the lowest score reaching 95.3% precision there. That gave 0.8193. The test games were not used to choose it.

## Test

337 Witty_Alien games from the previous study's fixed 1,000-game sample: the ones for which we obtained a review. Positives are the 416 gallery Brilliants on the account's own moves, using that study's primary mask. Mute Selective's decisions on the same moves are that study's published native Stockfish 19 Fast replay outcomes.

| | Awards | Found | Not in gallery | Also not Brilliant in today's review |
| --- | ---: | ---: | ---: | ---: |
| Mute Selective | 274 | 259 | 15 | 12 |
| Mute Exchange, cutoff 0.8193 | 316 | 298 | 18 | 11 |
| Mute Exchange, cutoff 0.8841 (97% training precision) | 277 | 265 | 12 | 6 |
| Mute Exchange, cutoff 0.7207 (93%) | 363 | 331 | 32 | 19 |
| Mute Exchange, cutoff 0.9495 (98.5%) | 182 | 181 | 1 | 0 |

The comparison is not like for like on the engine: Mute Selective's column comes from the site's engine, Mute Exchange's from research Stockfish 18 evidence.

### Variants we measured

Same test, same training rows, different evidence. Each cell is found / not in gallery / also rejected today.

| Evidence | Strict | Medium |
| --- | --- | --- |
| Three lines plus separate accept and decline searches, full 200,000 nodes | 283 / 13 / 6 | 324 / 17 / 9 |
| Same, read back at depth 12 | 265 / 9 / 5 | 311 / 18 / 10 |
| **Published: two lines and one reply, depth 12** | 265 / 12 / 6 | **298 / 18 / 11** |

The first two rows average five seeds; the published row is the single shipped model.

Requiring the depth-11 evidence to agree with depth 12 gives 288 / 16 / 10. Refusing to award any move that loses more than 5 win-chance points by the same lines gives 272 / 16 / 11: it removes 28 awards, 26 of them genuine.

### Development measurements on the 1,000-game sample

Before the reviews existed we iterated against gallery labels on the full 1,000-game sample with 200,000-node evidence, training on the six development accounts only and reading off the found count at 38 false awards: 774, 835, 854, 869 as feature groups were added. These selected the feature groups. They are development measurements and the cutoff there was read from the test itself.

## What we learned about Chess.com's rule

Computed on gallery-account moves in the 1,005 reviewed games, using Chess.com's own numbers ([study-stats.json](data/study-stats.json)):

- 1,194 review Brilliants; 1,189 are candidates.
- All 1,189 are Chess.com's top move. Of 1,526 candidates that are not, none is Brilliant.
- 1,187 have negative net material (capture value minus the offered exchange gain).
- The lowest evaluation after a Brilliant is −17 centipawns from the mover's side.
- 1,178 were played out of check.
- 1,552 moves meet all four conditions; 1,176 of them are Brilliant.

Chess.com's evaluations against Stockfish 18's on 4,251 candidates: correlation 0.97, slope 1.68. Stockfish's top move at 200,000 nodes is Chess.com's top move for 71% of the 1,189 Brilliants. On 566 candidate positions from the first 126 games, searched to depth 22, the agreement on the 145 Brilliants rose from 59% at depth 8 to 79% at depth 22.

## Limits

- No replay on Mute Chess's own engine (Stockfish 19 small network, depth 12, 500 ms) has been run.
- All seven accounts are titled players. Chess.com states that it is more generous to lower-rated players.
- Feature design used aggregate statistics from all seven accounts, including the test account, and other Witty_Alien games are in the training set. The earlier study's test was independent of its model in a way this one is not.
- The test is 337 games from one account. Moves within a game are correlated.
- Review labels reflect one reviewing account's settings on one day.
- The parity check covers feature and score computation, not end-to-end behavior in a browser.

## Sources

Chess.com's public description of its criteria: [how moves are classified](https://support.chess.com/en/articles/8572705-how-are-moves-classified-what-is-a-blunder-or-brilliant-etc). It motivates the study; it does not prove an inferred rule. Games and labels are third-party factual research data. This project is independent of Chess.com and does not claim its method.

The chess logic and model in this study are original to this project. Analysis and writing used Anthropic Claude assistance.
