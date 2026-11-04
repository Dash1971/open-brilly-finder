# What makes a move brilliant?

*{{N}} reviewed moves, an open algorithm, and a comparison with Chess.com.*

Mute Chess should make good chess feel rewarding. A quiet piece offer can deserve the same celebration as a spectacular queen sacrifice. We tested a transparent Brilliant classifier against **{{POSITIVE_N}} moves labeled Brilliant by Chess.com and {{NEGATIVE_N}} moves explicitly labeled otherwise**, from **{{GAMES}} games**. On this balanced challenge set, Mute agreed with Chess.com on **{{MUTE_AGREEMENT}}%**, compared with **{{EC_AGREEMENT}}%** for En Croissant. On separately reserved games, the figures were **{{MUTE_VALIDATION_AGREEMENT}}%** and **{{EC_VALIDATION_AGREEMENT}}%**.

![Direct En Croissant and confirmed Mute awards compared on the full challenge set and separately reserved games.](figures/rule-comparison.png)

Agreement counts both recognizing a Brilliant and correctly withholding the badge. The other two measures show the tradeoff: how many Chess.com Brilliants each rule finds, and how often it awards a badge to an explicitly non-Brilliant comparison move. Mute found **{{MUTE_TP}} / {{POSITIVE_N}}** Brilliants and gave **{{MUTE_FP}} / {{NEGATIVE_N}}** comparison moves an extra award. En Croissant found **{{EC_TP}}** and gave **{{EC_FP}}** extra awards.

These are difficult, deliberately selected examples from nelsi, hansen, KNVB, GothamChess and Hikaru. The sample contains equal numbers of Brilliant and non-Brilliant moves, with comparison moves enriched for apparent offers, exchanges and quiet defenses. Its extra-award rate describes these controls; it does not estimate how often Mute would award an unwanted Brilliant during an ordinary game.

## A Brilliant can be quiet

![Hikaru's Bg2 leaves a rook offered; accepting trades a rook for a bishop.](figures/quiet-offer.png)

In [Hikaru's 27.Bg2](https://www.chess.com/analysis/game/live/186567991235/review?move=52), White leaves the attacked rook on b1 available. After ...Bxb1, the other rook can recapture the bishop: White gives a rook for a bishop while retaining compensation. Chess.com and Mute both award Brilliant.

The earlier sequence **Re1, ...Nd3, Reb1, ...Ne5** matters. The knight's move to e5 clears the g6–b1 diagonal, exposing the rook to the bishop on g6. Bg2 keeps that offer on the board. It does not newly uncover the bishop's attack. A classifier that only examines the piece that moved would miss the rook entirely; a classifier that demands a newly created attack could miss the decision to leave it offered.

## A clever combination is a harder boundary

![Two supplemental legal capture sequences recover material elsewhere and finish a pawn ahead, but have different Chess.com labels.](figures/similar-trades.png)

In [14...Ndxe5](https://www.chess.com/analysis/game/live/186311900336/review?move=27), Black takes a pawn and apparently offers a knight. The legal continuation **15.Nxe5 Nxe5 16.fxe5 Rxd3** recovers a bishop elsewhere. Black exchanges two knights for a knight and bishop, gaining a pawn. Chess.com calls the move **Excellent**; Mute withholds Brilliant.

![The rook recovers a bishop on another square in the Excellent reference combination.](figures/pawn-win-excellent.gif)

Yet the illustrated **...Nxd5** combination beside it also exchanges equal-valued pieces and finishes a pawn ahead, and Chess.com calls that move Brilliant. These two reference positions are **excluded from the benchmark totals**. Their continuations are legal illustrations, not forced replies or the actual game sequence. They show why “material eventually comes back” cannot, by itself, reconstruct Chess.com's boundary.

## How Mute awards Brilliant

The published Mute rule has five checks. Every check must pass:

1. **The move is strong enough.** Its loss is at most five points on the algorithm's mapped win-chance scale, and the resulting engine score is at least −1.00 pawns from the mover's perspective. Five points here does not mean five centipawns or a measured human winning probability.
2. **A piece is genuinely offered.** The opponent has a legal capture of one of the mover's knights, bishops, rooks or queens. Considering captures and recaptures on that square, the opponent can gain more than the move's immediate material profit plus a one-pawn-sized margin. Either side may stop the exchange. The offered piece need not be the piece that moved.
3. **A second check corroborates the sacrifice.** En Croissant's broader capture-only material search must agree that material is being conceded, or the engine must explicitly report a winning mate for the mover. A large numerical advantage alone does not activate the mate exception. These searches are heuristics; they do not prove a forced sacrifice.
4. **The offer remains relevant.** None of the other evaluated moves may already score at least +6.00 pawns without a qualifying legal piece offer. This checks the alternatives actually examined by the engine, rather than every legal move.
5. **Completed engine checks agree.** The current and corroborating complete analysis windows must both award Brilliant. Missing or contradictory evidence withholds the badge. At least two evaluated alternatives are required; the played move need not be uniquely best.

![The five checks in Mute's open Brilliant rule.](figures/current-rules.png)

En Croissant's direct rule instead requires its material-sacrifice test, the engine's first-choice move, and a sufficiently large gap over the second choice. That can reject a good sacrifice when another strong move exists. Its latest stable score and material code was checked against the pinned reference. The headline comparison uses **En Croissant's direct annotation** and **Mute's confirmed award**, including Mute's withholding behavior. Mobile Maia retains its existing En Croissant-based behavior. Exact formulas and reproduction details are in the [methods](METHODS.md).

## What the comparison can establish

The Mute rule was fixed before the newly reviewed games were labeled. The reserved-game result tests it on moves outside the examples used to choose that rule; the full-set result also includes development examples. {{VALIDATION_RESULT_SENTENCE}} The separate prospective result covers all newly reviewed moves, and the methods distinguish these groups. Stronger engine checks are reported separately and do not replace baseline decisions selectively.

There are still disagreements. For example, [Hikaru's 30.Kh1](https://www.chess.com/analysis/game/live/185741429132/review?move=58) is Best on Chess.com but Brilliant under Mute's rule. A legal, sound offer does not necessarily feel exceptional, and the material guard also withholds some Chess.com Brilliants. {{REMAINING_ERRORS_SENTENCE}}

The aim is an enjoyable, inspectable alternative. These results measure agreement with observed labels, not fun itself or recovery of Chess.com's unpublished formula. Chess.com says player strength affects its criteria, and review settings can change classifications. The benchmark largely represents strong players. [Published criteria](https://support.chess.com/en/articles/8572705-how-are-moves-classified-what-is-a-blunder-or-brilliant-etc); [Game Review settings](https://support.chess.com/en/articles/8584089-how-does-game-review-work).
