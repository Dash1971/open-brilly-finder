# Comparing open Brilliant classifiers

[Reader report](REPORT.md#how-this-compares-with-other-projects) · [Methods](METHODS.md)

Mute Selective combines soundness and legal-offer checks with a trained forest. En Croissant, WintrChess and Knight’s Eye use developer-written policies. The useful comparison is which Chess.com examples they recognize and what ordinary moves they award incorrectly, not simply how elaborate their rules are.

## Recorded numerical comparisons

These comparisons preserve their original samples, model versions and engine settings. **They are not a head-to-head ranking of the current forest on the 1,000 Witty_Alien games.** Only Mute Selective has the 774/1,234 result on that sample.

| Comparison set | Classifier | Reference Brilliants recognized | False awards |
| --- | --- | ---: | ---: |
| 400 explicitly labeled moves; saved SF18 analysis | Earlier Mute forest | 112 / 200 | 3 / 200 non-Brilliants |
| Same 400 moves and analysis | En Croissant | 53 / 200 | 3 / 200 non-Brilliants |
| 3,724 saved examples; 917 positive labels | Earlier Mute forest, grouped predictions | 452 / 917 | 6 |
| Same saved examples; both-window confirmation | WintrChess | 287 / 917 | 20 |
| Same saved examples; both-window confirmation | Knight’s Eye | 590 / 917 | 142 |

WintrChess had five unresolved ordinary cases. Knight’s Eye had 34 unresolved positive cases and 22 unresolved ordinary cases. Unresolved evidence is not a confirmed rejection. The 3,724-example collection was used for research and does not constitute independent validation of the selected forest. Its selected controls also differ from all-move gallery negatives.

The comparisons show different recognition/error tradeoffs. They do not establish that one project is best for every player, engine or definition of Brilliant.

## Sources and implementation differences

- **[En Croissant](https://github.com/franciscoBSalgueiro/en-croissant)** supplied the starting scoring/material approach. [Reference and attribution](../brilliant-moves/reference/README.md) and [original comparison methods](../brilliant-moves/METHODS.md) pin the tested version.
- **[WintrChess](https://github.com/WintrCat/wintrchess-lib)** considers legal accepting captures and immediate punishment elsewhere on the board.
- **[Knight’s Eye](https://github.com/knights-eye-chess/move-classifier)** includes tests of acceptance, recapture and compensation. Its evidence requirements can leave cases unresolved.
- **[Chess-Review](https://github.com/T-Julsgaard/Chess-Review)** and **[Brilliant-Chess](https://github.com/wdeloo/Brilliant-Chess)** provide related material/recovery policies; Chess-Review credits Brilliant-Chess ancestry.
- **[Felix’s chess-game-review](https://github.com/FelixYUFENGSU/chess-game-review)** provides a more restricted moved-piece exchange policy.

[Source review and pinned commits](../brilliant-external-repos-2026-11-04/REPORT.txt) · [Complete external comparison and unresolved cases](../brilliant-external-comparison-2026-11-04/REPORT.txt)

Each project’s code and notices retain their own license. This research measures agreement with observed Chess.com labels, not reconstruction of its unpublished formula.
