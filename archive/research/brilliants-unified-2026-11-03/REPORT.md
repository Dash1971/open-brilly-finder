# What makes a move brilliant?

*618 reviewed moves. Five Chess.com accounts. An open rule anyone can inspect.*

A Brilliant badge makes a good move feel special. But what deserves it: a queen sacrifice, a quiet move that leaves a rook hanging, or an ordinary combination that wins a pawn?

We compared open classifiers against **309 moves labeled Brilliant by Chess.com and 309 explicitly labeled otherwise**, from **299 games**. The proposed Mute Chess rule agreed with **83.0%** of those labels, compared with **62.6%** for En Croissant. On **101 moves from 48 separately reserved games**, agreement was **76.2% versus 64.4%**.

![Agreement, Brilliant recognition and extra awards for Mute and En Croissant, with separate reserved-game results.](figures/rule-comparison.png)

Mute recognized **220 of 309** Chess.com Brilliants, compared with **84** for En Croissant—about **2.6 times as many**. It also awarded Brilliant to **16 of 309** explicitly non-Brilliant moves, compared with **6** for En Croissant. These are disagreements with observed labels, not proof that either site's chess judgment is objectively wrong.

The result is a more generous open alternative to En Croissant that matches more Chess.com labels **in this comparison**. It is a measurable step toward that experience, with substantial gaps still to close.

The sample comes from nelsi, hansen, KNVB, GothamChess and Hikaru. Comparison moves deliberately include apparent sacrifices, exchanges and quiet defenses. This is a balanced challenge set, not a random sample of chess: its percentages do not tell us how often a badge would appear in an ordinary game.

## A Brilliant can be quiet

![Hikaru's Bg2 leaves a rook offered; accepting trades a rook for a bishop.](figures/quiet-offer.png)

In [Hikaru's 27.Bg2](https://www.chess.com/analysis/game/live/186567991235/review?move=52), White leaves the attacked rook on b1 available. After ...Bxb1, the other rook can recapture the bishop: White gives a rook for a bishop while retaining compensation. Chess.com and Mute both award Brilliant.

The earlier sequence **Re1, ...Nd3, Reb1, ...Ne5** matters. The knight's move to e5 clears the g6–b1 diagonal, exposing the rook to the bishop on g6. Bg2 keeps that offer on the board. It does not newly uncover the attack. Looking only at the piece that moved would miss the rook; requiring every Brilliant to create a new attack would miss the choice to leave it offered.

## A clever combination is a harder boundary

![Two legal capture sequences recover material elsewhere and finish a pawn ahead, but have different Chess.com labels.](figures/similar-trades.png)

In [14...Ndxe5](https://www.chess.com/analysis/game/live/186311900336/review?move=27), Black takes a pawn and apparently offers a knight. The continuation **15.Nxe5 Nxe5 16.fxe5 Rxd3** recovers a bishop elsewhere. Black exchanges two knights for a knight and bishop, gaining a pawn. Chess.com calls the move **Excellent**; the proposed Mute rule withholds Brilliant.

![The rook recovers a bishop on another square in the Excellent reference combination.](figures/pawn-win-excellent.gif)

Yet the illustrated [**9...Nxd5** combination](https://www.chess.com/analysis/game/live/186305472636/review?move=17) also exchanges equal-valued pieces and finishes a pawn ahead, and Chess.com calls that move Brilliant. These two reference positions are **outside the benchmark totals**. Their continuations are legal illustrations, not forced replies or the actual game sequence. They show why “the material eventually comes back” cannot, by itself, reconstruct Chess.com's boundary. [Watch the Brilliant example's illustrated continuation](figures/pawn-win-brilliant.gif).

## Turning those observations into a rule

Mute's published rule asks five questions. All must pass:

1. **Is the move strong enough?** It loses at most five points on a mapped win-chance scale, and the resulting engine score is at least −1.00 pawns for the mover. Those five points are a scoring heuristic, not a measured human winning probability.
2. **Is a piece legally offered?** The opponent can capture a knight, bishop, rook or queen and profit from captures and recaptures on that square. The profit must exceed the move's immediate material gain plus a one-pawn-sized margin. Either side can stop exchanging. The offered piece need not be the one that moved.
3. **Does a broader material check agree?** En Croissant's capture-only material search must also find a sacrifice, or the engine must explicitly report a winning mate for the mover. This helps reject ordinary combinations that recover material elsewhere. It remains a heuristic, not proof of a forced sacrifice.
4. **Does the offer still matter?** No other evaluated move without a qualifying piece offer may already score at least +6.00 pawns. This examines the alternatives the engine actually checked.
5. **Do completed engine checks agree?** Complete analysis windows must corroborate the award. Missing or contradictory evidence withholds it. At least two candidate moves must have been evaluated; the played move need not be uniquely best.

![The five checks in Mute's open Brilliant rule.](figures/current-rules.png)

En Croissant instead requires its material-sacrifice test, the engine's first-choice move, and a sufficiently large gap over the second choice. That can reject a good sacrifice when another strong move exists. The comparison uses **En Croissant's direct annotation** and **Mute's confirmed award** on identical saved engine evidence. We verified that En Croissant's latest stable scoring and material code matches the pinned reference. **Mobile Maia keeps its existing En Croissant-based behavior.** [Exact formulas, sources and reproduction](METHODS.md).

## Fewer false awards has a cost

The broader material check is the proposed change to Mute. It removes **61 extra awards**, while also losing **53 correctly recognized Brilliants**:

| Rule on the same 618 moves | Chess.com Brilliants found | Extra awards on non-Brilliants | Overall agreement |
| --- | ---: | ---: | ---: |
| En Croissant | 84 / 309 | 6 / 309 | 62.6% |
| Mute: legal offers alone | 273 / 309 | 77 / 309 | 81.7% |
| **Mute: with the material guard** | **220 / 309** | **16 / 309** | **83.0%** |

That makes the guard a choice about badge quality, rather than a free improvement. On reserved games it cuts extra awards from **11 to 4**, but recognition falls from **44 to 31 of 51** Brilliants. Overall agreement falls from **82.2% to 76.2%** there. The more generous Mute rule wins on that single measure; the guarded rule better addresses unwanted awards. Both exceed En Croissant's reserved-game agreement of **64.4%**.

The guarded rule was fixed before the reserved games were labeled. Full-set results include examples used to choose it, so the reserved result is the more demanding check. Targeted searches at five times the node budget are reported separately in the methods; they do not selectively replace the headline results.

## What remains unresolved

The guarded rule still misses **89 of 309** observed Brilliants and makes **16 extra awards**. For example, [Hikaru's 30.Kh1](https://www.chess.com/analysis/game/live/185741429132/review?move=58) is Best on Chess.com but Brilliant under Mute's rule. A sound piece offer does not necessarily feel exceptional. Conversely, some Chess.com Brilliants recover material in ways that make a strict material filter reject them.

Chess.com says player strength affects its criteria, and review settings can change labels. These established accounts do not establish beginner behavior; game ratings and time controls vary. The full formula is unpublished. [Published criteria](https://support.chess.com/en/articles/8572705-how-are-moves-classified-what-is-a-blunder-or-brilliant-etc); [Game Review settings](https://support.chess.com/en/articles/8584089-how-does-game-review-work).

This study supports an inspectable, more Chess.com-like alternative to the open-source peer tested here. It does not establish 99% agreement, superiority to untested projects, or how much enjoyment the badge creates. The [move-by-move evidence](moves.csv), [open rules](reference/README.md) and [validation methods](METHODS.md) let others check the result and improve it.
