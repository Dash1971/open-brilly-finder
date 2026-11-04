# Making Brilliant badges feel at home on Mute Chess

Chess.com’s Brilliant badge makes a good chess idea feel special. Our goal is to bring that experience to an open chess platform: recognize more genuine Brilliants while keeping undeserved badges low.

**We recommend Mute Selective: a small model we trained on chess moves labeled by Chess.com, combined with basic chess checks.**

Your browser downloads the model with the analysis code and runs it locally. Stockfish supplies the chess evaluations; the model uses those and facts about the position to decide whether to award Brilliant. It does not call ChatGPT or a remote classification service, and it does not learn from your games during play. The model and training code are openly published. En Croissant decides its Brilliant badge using rules written by its developers. Our model learns patterns from Chess.com’s labels.

## What we studied

The project examined **1,248 labeled moves from 654 games** by nelsi, hansen, KNVB, GothamChess and Hikaru, starting from En Croissant’s classifier.

The headline results below come from **400 test moves in 215 games that were not used to train the model**. Half were Chess.com Brilliants; half were explicitly non-Brilliant. The model and its threshold stayed unchanged throughout the assessment. We compared it with En Croissant on the same positions and engine analysis.

Chess.com does not publish its complete formula. Its [guidance](https://support.chess.com/en/articles/8572705-how-are-moves-classified-what-is-a-blunder-or-brilliant-etc) helped us identify relevant chess ideas, but our chosen system is not a reconstruction of that private formula.

## The approach we chose

- **Keep the move sound.** Current and previous completed engine checks must both support its quality.
- **Require a real piece offer.** The offered piece can be somewhere other than the piece that moved.
- **Learn from Chess.com examples.** We trained the small model using moves Chess.com called Brilliant and moves it did not. It considers material, piece offers, move quality and the position, then runs locally in the browser without changing during play.
- **Prefer convincing badges.** Both engine checks must clear the model’s fixed threshold. This does not add the separate History Rule or material-recovery guard as extra requirements.

## Quiet moves can be Brilliant—and still be missed

![A quiet bishop retreat leaves a rook available.](visuals/outputs/quiet-offer-bg2.gif)

[Hikaru’s 27.Bg2](https://www.chess.com/analysis/game/live/186567991235/review?move=52) retreats a bishop while leaving a rook available. Chess.com calls it Brilliant, but the selective model misses it. That is a real cost of choosing fewer questionable badges. The illustrated **...Bxb1 Rxb1** replies are conditional, not claimed forced or played.

## An apparent sacrifice can be an ordinary trade

![After hxg6, a queen check enables recovery on another square.](visuals/outputs/routine-hxg6.gif)

After [18...hxg6](https://www.chess.com/analysis/game/live/171488501692/review?move=35), **Bxc4 Qc5+** leads to material recovery elsewhere. Chess.com calls hxg6 Best. Mute Selective also withholds Brilliant, as it does for the [rook-recovery example](visuals/outputs/routine-hxg5.gif). These are checked model outcomes; the conditional animations illustrate the chess ideas, not the model’s internal reasoning.

## How closely do the badges match?

![The selective model and En Croissant on independent test moves.](figures/history-recovery-replay.png)

| Across 400 test moves | Mute Selective | En Croissant |
| --- | ---: | ---: |
| Brilliants correctly recognized | **112 / 200** | 53 / 200 |
| Undeserved Brilliant badges | **3 / 200** | 3 / 200 |

Other methods found more Brilliants but gave too many undeserved badges to justify choosing them. In a 200-move comparison, the History Rule recognized 78 Brilliants but wrongly awarded 13 badges. The selective model recognized 57 and wrongly awarded **2**; En Croissant recognized 27 and wrongly awarded 1.

**Adopt Mute Selective alongside its chess rules.** Next, train improved versions using more labeled examples, especially missed Brilliants and ordinary tactics that deserve no badge. The current test examples can become training data, but an improved model must then prove itself on different games it has never seen. The goal is to recognize more genuine Brilliants while keeping wrong awards low. The [exact algorithm](README.md) and [Methods](METHODS.md) explain sampling, uncertainty and limits. Mute Dev handles the app merge. Mobile Maia keeps its existing En Croissant-based classifier.
