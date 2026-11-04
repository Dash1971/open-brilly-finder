# What makes a move brilliant?

*318 reviewed moves, three open rulesets, and the line between a sacrifice and a clever trade.*

A Brilliant badge makes a chess move feel worth sharing. We want Mute Chess to celebrate more of those moments while making the award understandable. Our comparison suggests a useful compromise: keep Mute's generous treatment of strong sacrifices, but ask for a second material check before awarding the badge.

That guard removed **36 unwanted awards** in this sample, at the cost of **26 correctly recognized Brilliants**. It still recognized **117 Chess.com Brilliants, compared with En Croissant's 44**. This is a promising experiment, with a visible tradeoff.

## What we studied

We checked **159 moves currently labeled Brilliant by Chess.com and 159 moves explicitly labeled otherwise**, drawn from **153 games**. Hikaru and nelsi contributed 60 pairs each, hansen 29, and GothamChess 10. Every selected move was matched to its full game and exact move number.

The comparison moves include apparent piece offers, captures, exchanges and quiet defenses. We deliberately looked for difficult cases. These counts describe a challenge set of strong players' games; they are not estimates of how often either site awards Brilliants in ordinary play.

Chess.com describes a Brilliant as a good piece sacrifice among the strongest moves available. Its published criteria also consider the resulting position, easy winning alternatives and player strength. The complete formula is not public. [Chess.com's explanation](https://support.chess.com/en/articles/8572705-how-are-moves-classified-what-is-a-blunder-or-brilliant-etc)

## A Brilliant can be quiet

![A quiet bishop move leaves a rook offered, trading that rook for a bishop if accepted.](figures/quiet-offer.png)

In [Hikaru's 27.Bg2](https://www.chess.com/analysis/game/live/186567991235/review?move=52), White leaves the attacked rook on b1 available. After ...Bxb1, the other rook can recapture the bishop. White gives up a rook for a bishop while keeping a playable position.

Chess.com and both tested Mute rules award Brilliant. An algorithm that only inspected the piece that moved would miss the offer elsewhere on the board.

## How the rules differ

**En Croissant**, whose approach also informs Mobile Maia, is selective: its Brilliant rule combines move quality and a material-sacrifice heuristic with a requirement that the played move be the engine's first choice and sufficiently better than the second. Two similarly strong sacrifices can therefore receive no badge. [Pinned source](https://github.com/franciscoBSalgueiro/en-croissant/blob/6f2d2628f0fbe11cb62a7dd2f9c102bb52907d53/src/utils/score.ts)

**Mute before the guard** accepts one of several strong moves. It checks for a legal capture of a non-pawn piece that wins the opponent more material than the mover has already gained. It also checks soundness, evaluated safe winning alternatives and agreement between completed engine checks.

**Mute with the proposed guard** retains those checks and additionally requires En Croissant's material-sacrifice heuristic to agree, **or an explicit engine mate score showing the mover wins**. A large numerical advantage alone does not satisfy the mate exception. Mobile Maia keeps its existing En Croissant behavior.

![Five checks explain the proposed Mute award, including the new material corroboration or winning-mate guard.](figures/current-rules.png)

The second material check is a heuristic, not proof of a beautiful sacrifice. Exact formulas, thresholds, evidence requirements and source snapshots are in the [methods](METHODS.md).

## More celebrations, with fewer unwanted awards

![Three rulesets compared on 159 confirmed Brilliants and 159 confirmed comparison moves.](figures/rule-comparison.png)

| Ruleset | Confirmed Brilliants found | Other moves also awarded |
| --- | ---: | ---: |
| En Croissant | 44 / 159 | 2 / 159 |
| Mute before the guard | 143 / 159 | 42 / 159 |
| Mute with the proposed guard | 117 / 159 | 6 / 159 |

The proposal keeps about **2.66 times** En Croissant's recognized Brilliants on these moves. It gives up some of the previous Mute rule's generosity: 26 confirmed Brilliants lose their award, while 36 comparison moves stop receiving one.

Three examples show what that means:

| Move | Chess.com | Proposed Mute behavior |
| --- | --- | --- |
| [Hansen's 15.Nxb5](https://www.chess.com/analysis/game/live/183988710985/review?move=28) | Best | Removes the previous Mute Brilliant. |
| [nelsi's 11.Qxg6+](https://www.chess.com/analysis/game/live/186367356936/review?move=20) | Brilliant | Keeps Brilliant through the explicit winning-mate exception. |
| [Hikaru's 30.Kh1](https://www.chess.com/analysis/game/live/185741429132/review?move=58) | Best | Still awards Brilliant: the guard does not resolve every disagreement. |

## Why material coming back is a difficult boundary

![Two reference combinations finish a pawn up but receive different Chess.com labels.](figures/similar-trades.png)

These two **supplemental examples are outside the 318-move comparison**. Both illustrated capture sequences exchange equal-valued pieces and finish a pawn ahead. A rook recovers material on another square in the first; a bishop does so in the second. Their Chess.com labels are Excellent and Brilliant respectively.

![A rook recovers material elsewhere in the Excellent reference example.](figures/pawn-win-excellent.gif)

![A bishop recovers material elsewhere in the Brilliant reference example.](figures/pawn-win-brilliant.gif)

The sequences are legal possibilities, not claims that the opponent must accept them. The positions differ. Similar material accounting with different labels shows why simply rejecting every temporary offer would miss enjoyable Brilliants too.

## What we recommend, and what remains uncertain

Experiment with the corroboration guard in Mute Chess, publish its rules, and keep examples of both the awards it prevents and the Brilliants it misses. This preserves a more generous experience than En Croissant on this sample without treating every apparent offer as special.

The proposal was chosen **after inspecting these moves**. Its results are retrospective, not blind validation. Separate game and player groups do not make that later choice independent.

A targeted check of 30 difficult positions used five times the engine budget. Three decisions changed for both Mute versions: two previously missed Brilliants gained awards and one extra award disappeared. The guard still reduced extra awards in that subset, but this was neither a random sample nor independent validation.

Chess.com's labels can change with review settings and deeper analysis; we preserve historical gallery labels separately from current review displays. [How Game Review works](https://support.chess.com/en/articles/8584089-how-does-game-review-work) The [methods and evidence](METHODS.md) include the games, disagreements, stronger checks and remaining limitations.
