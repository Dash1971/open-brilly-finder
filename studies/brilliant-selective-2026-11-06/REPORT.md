# Bringing Chess.com-style Brilliants to open chess

## Abstract

**Mute Selective recognizes 62.7% of Chess.com’s Brilliant moves in our test on unseen games. Of the Brilliant badges it awards, 95.3% match Chess.com.**

Our goal is simple: make discovering a great chess idea more rewarding on an open platform. We studied Chess.com’s Brilliant labels, started from En Croissant’s open-source classifier, and trained a small model to recognize the patterns in those examples. The result is **Mute Selective**, which combines learned patterns with checks for a sound move and a real piece offer. It runs locally in the browser.


## What we achieved

![Mute Selective recognizes 774 of 1,234 Chess.com Brilliants; 774 of its 812 Brilliant badges match Chess.com.](figures/fresh-results.png)

We tested Mute Selective on **1,000 games from Witty_Alien**, whose examples were not used to train or tune the model. The test used Mute Chess’s default Fast analysis with Stockfish 19.

| What we measured | Result |
| --- | ---: |
| Chess.com Brilliants recognized | **774 of 1,234 — 62.7%** |
| Our Brilliant badges matching Chess.com | **774 of 812 — 95.3%** |
| Extra awards on other moves | **38 of 30,423 — 0.125%** |

The first number asks how many genuine Brilliants we find. The second asks how trustworthy our awarded badges are. The third measures false awards across all other moves. These percentages have different denominators.

For this test, Chess.com’s complete Brilliant gallery was the reference: listed moves counted as Brilliant; the player’s other moves in those games counted as non-Brilliant. We scored only Witty_Alien’s moves. This measures agreement on one account’s gallery-listed games, rather than every player or every game.

## How we did it

We assembled **7,019 games with 8,298 Brilliant annotations** from nelsi, hansen, KNVB, GothamChess, Hikaru, MagnusCarlsen and Witty_Alien. The downloadable game files (PGNs) preserve the moves, clocks and history; recorded categories and source links accompany the labels.

We trained the model on **6,293 labeled moves**, including both Brilliants and ordinary tactics. Testing used separate games and excluded previously seen positions. The model was fixed before the Witty_Alien test.

The classifier combines three kinds of evidence:

1. **Move quality.** Stockfish checks whether the move remains sound.
2. **A real piece offer.** Legal move analysis checks whether the opponent can profitably take a piece, accounting for material already captured.
3. **Patterns learned from examples.** The model considers material, king attacks, possible recovery, alternative moves and earlier positions. Two completed engine checks must support the award.

The model is a small **forest of decision trees**: many simple questions about the chess position combine into a decision. We train it ahead of time and publish its weights. Your browser runs it as ordinary JavaScript alongside Stockfish. It does not call ChatGPT or a remote service, use a neural network, or learn while you play.

## How this compares with other projects

| Project | Approach |
| --- | --- |
| **En Croissant** | Developer-written rules use engine scores and material changes to recognize sacrifices. This was our starting point. |
| **WintrChess** | Rules examine hanging pieces, legal exchanges and immediate tactical punishment after acceptance. |
| **Knight’s Eye** | Rules examine sacrifice acceptance, material recovery and alternatives that retain compensation. |
| **Mute Selective** | Chess checks establish eligibility; a model trained on Chess.com examples decides which eligible moves earn the badge. |

We chose the learned approach because recognizing an offer is only part of the problem: ordinary material-winning tactics can resemble sacrifices. We also examined methods that recognized more Brilliants, but their extra false awards did not justify choosing them.

The **62.7% result measures agreement with Chess.com**. It is not a direct ranking against these projects: their numerical comparisons use different test conditions. [Comparison evidence and source versions](COMPARISONS.md) are available for readers who want the details.

## Future research

- **Recognize more worthwhile sacrifices**, including quiet offers and less common tactical ideas.
- **Reject more ordinary recovery tactics**, so a quick material win does not earn an undeserved badge.
- **Improve the training examples and position features**, then prove the benefit on games the model has never seen.
- **Test more players and analysis settings**, to learn how well the result carries across styles, ratings and devices.

The research supports choosing **Mute Selective** as our open implementation of Chess.com-style Brilliant classification. It finds more than six in ten reference Brilliants in this test while keeping false awards uncommon across the other moves. Chess.com’s complete formula remains private; our code, model, data and evaluation are open.

[Download the annotated PGN](data/seven-accounts-last-12-months-chesscom-brilliants.pgn) · [Methods and limits](METHODS.md) · [Exact algorithm and code](README.md)
