# When should a move earn Brilliant?

**Private review draft.**

On a fresh 200-move test, our precision-first candidate recognized **55 of 100 Chess.com Brilliants**, compared with **26 for En Croissant**. It also made **1 extra award among 100 explicitly non-Brilliant moves**, compared with En Croissant’s 2. That is about **2.1 times as many recognized Brilliants, with fewer extra awards in this test**.

The tradeoff is substantial: the candidate missed **45 Brilliants**. Its **55% recognition** and **77% overall agreement** belong beside its **98.2% sample badge precision**—55 matching labels among 56 awards. That precision estimate has a descriptive 95% interval of **90.6–99.7%**. High badge precision does not mean high overall agreement.

![Fresh-test recognition and extra awards, each with a denominator of 100.](figures/fresh-test-results.png)

| Fixed candidate | Brilliants recognized | Extra awards | Sample badge precision | Overall agreement |
| --- | ---: | ---: | ---: | ---: |
| Precision-first forest | **55 / 100** | **1 / 100** | **98.2%** | **77.0%** |
| History rule | 78 / 100 | 5 / 100 | 94.0% | 86.5% |
| En Croissant: direct annotation | 26 / 100 | 2 / 100 | 92.9% | 62.0% |

The research corpus contains **1,048 moves from 545 games**: 848 development moves from 439 games, and this separate 200-move test from 106 games. All five accounts—nelsi, hansen, KNVB, GothamChess and Hikaru—contribute 20 Brilliants and 20 explicit non-Brilliants to the test. The model, rules and threshold were fixed before its current labels were captured.

## A sacrifice the candidate recognizes

![Hansen’s 17.Bxh7+ and the actual king capture, drawn with native Mute Chess pieces and colors.](figures/fresh-bxh7.gif)

In [Hansen’s 17.Bxh7+](https://www.chess.com/analysis/game/live/167741829524/review?move=32), the bishop takes a pawn and gives check while becoming available to the king. Both Chess.com and the frozen forest award Brilliant. The animation then shows **17...Kxh7**, the reply recorded in the game: White gives up a bishop for a pawn. Acceptance is not claimed forced, and the illustration makes no claim about the complete compensation. This is one of the 55 recognized test moves.

## A Brilliant can also be quiet

![Hikaru’s 27.Bg2 leaves a rook available; the following captures are conditional.](../visuals/outputs/quiet-offer-bg2.gif)

[Hikaru’s 27.Bg2](https://www.chess.com/analysis/game/live/186567991235/review?move=52) retreats a bishop while leaving the rook on b1 available. The legal **...Bxb1 Rxb1** illustration trades a rook for a bishop; those replies are not asserted forced or played. Only Bg2 has the reported Brilliant label.

The history rule recognizes this development example, but the forest withholds its badge. Caution can miss exactly the quiet idea that makes Brilliants enjoyable.

## Material alone does not settle it

![Similar material trades receive different Chess.com labels.](../visuals/outputs/similar-trades-native.png)

The [14...Ndxe5 reference](https://www.chess.com/analysis/game/live/186311900336/review?move=27) offers a knight, then recovers material elsewhere in the illustrated sequence. It finishes a pawn up and received Excellent. The different [9...Nxd5 reference](https://www.chess.com/analysis/game/live/186305472636/review?move=17) also finishes a pawn ahead after equal-valued pieces are traded, yet received Brilliant.

The forest withholds both: it declines the Excellent move but misses the Brilliant one. Both references are **outside the benchmark totals**. Their [Excellent](../visuals/outputs/pawn-win-excellent.gif) and [Brilliant](../visuals/outputs/pawn-win-brilliant.gif) capture sequences are conditional legal illustrations.

[Chess.com’s published guidance](https://support.chess.com/en/articles/8572705-how-are-moves-classified-what-is-a-blunder-or-brilliant-etc) describes strong piece sacrifices, position conditions and more generous treatment of newer players. It does not publish the complete formula. Similar material is only part of the boundary.

## What is being tested?

The **forest** first requires a legal piece offer and adequate engine-assessed move quality. It then combines 64 fixed decision trees using chess and engine features. Both completed analysis windows must clear the same threshold. Its score is not a calibrated probability that a move is Brilliant.

The **history rule** is a separate, more permissive comparator. Among other checks, it prevents a quiet follow-up earning another badge merely because an earlier sacrifice remains available. It recognizes more Brilliants here, with more extra awards. Its exact exceptions and finite proof limits are documented alongside the forest.

We favor the forest for an experiment that prioritizes convincing badges. This test supports that choice against direct En Croissant on these cases; it does not establish the best classifier globally. The single forest extra award was Hansen’s 37.Rxd7+, labeled Excellent.

The balanced, challenging sample does not estimate ordinary-game badge frequency or deployment precision. Moves share games, and the displayed intervals are not adjusted for that clustering. These five established accounts cannot establish beginner behavior; recorded Game Review labels are evidence, not objective chess truth.

The tested configuration is **SF18 at 300,000 requested nodes**. Native Mute Chess’s SF19 and varying browser budgets remain **unvalidated**. Mobile Maia keeps its existing En Croissant-based classifier. [Exact algorithms](README-DRAFT.md), [methods and sources](METHODS-DRAFT.md), and the saved predictions make the tradeoff inspectable.
