# Brilliant moves: what makes a sacrifice feel special?

*Working outline. The 600-move study is being collected. No results from that study are asserted here.*

## The question

A brilliant badge can turn a good chess move into a moment worth sharing. We want Mute Chess to celebrate more of those moments while keeping the award understandable: a sound move that offers meaningful material, creates a tactical opportunity, or finds compensation that is easy to overlook.

Chess.com does not publish its complete formula. This study compares its displayed decisions with two open classifiers: the En Croissant approach used by Mobile Maia, and Mute Chess's current approach. The goal is to learn which observable rules bring Mute closer to the experience players enjoy.

**Visual:** one large board showing a confirmed sacrifice, with the offered piece highlighted. A short caption should explain the actual choice: “The queen can be taken, but White has enough compensation.” Choose the example after legal replay and label verification.

## What we looked at

Explain the final completed sample in three short sentences: the five accounts, how the sacrifice categories were sampled, and how every brilliant and comparison move was checked in a newly opened Game Review. Insert actual completed counts only after collection and identity validation.

Explain why ordinary moves matter: a queen-winning combination or a routine recapture can look spectacular without involving a real sacrifice. Comparison moves therefore come from the same games and include captures, trades, material recovery, quiet defenses, and unsuccessful sacrifices.

**Visual:** a small sample map, with one row per player and four sacrifice categories. Show completed counts, missing categories, and historical labels that changed. Separate old gallery evidence from the current review label.

## What Chess.com appears to celebrate

Use three or four findings, each supported by multiple verified examples. Potential themes to test, rather than conclusions to assume:

- A strong move can earn the badge by leaving a valuable piece available to capture.
- The offered piece can be somewhere other than the destination square.
- A temporary sacrifice can be attractive even when the material comes back later.
- Player strength and the position's existing advantage may affect the award.

Describe each established pattern in everyday chess language. State exceptions alongside the pattern. Distinguish Chess.com's published description from an inference drawn from the sample.

**Visual:** three paired boards with a single arrow and at most two highlighted squares each. Under every example: the move, the visible Chess.com label, the offered material, and the practical continuation. Keep engine variations to one short line unless they are essential.

## Where the open classifiers agree and disagree

Explain each algorithm in one paragraph before showing any chart. En Croissant's explanation should describe its actual soundness and material-sacrifice checks. Mute's explanation should describe the actual current rules, including how it detects a legally available piece offer and which quality thresholds apply. Verify every threshold against the code snapshot used for the study.

**Visual:** a two-part comparison chart: “Confirmed brilliants found” and “Comparison moves also awarded.” Use counts with denominators. Label the chart as results on this deliberately selected sample, rather than overall accuracy or general precision.

Follow the chart with two or three concrete disagreements that explain the numbers. Include both missed brilliants and unwanted awards. Avoid treating the Chess.com label as an objective measure of beauty or chess strength.

## The difficult boundary: sacrifice or ordinary material gain?

Explain the central tradeoff using a matched pair. A program should notice when an apparently hanging piece is part of a routine material-winning sequence. It should also preserve the delight of a genuine offer whose compensation arrives later or on another square.

Earlier exploratory examples can guide case selection, but must be identified as earlier examples and kept outside the new study's held-out results:

- **Earlier example: Hansen's 30.Qxe4.** Its gallery entry showed a brilliant; a subsequently opened review called it Best. Use it to explain changing labels and the difference between a dramatic capture and a qualifying offer.
- **Earlier example: KNVB's Bxd5+ and nelsi's Qxd6+.** These were confirmed brilliants missed by the current Mute rules in the earlier pilot. Explain the actual legal continuations before drawing a conclusion about why they were missed.
- **Earlier example: Ndxe5.** Use the verified original position to explain why a routine pawn-winning sequence should not receive a sacrifice badge.

**Visual:** two or three compact capture-sequence diagrams. Show material balances at meaningful points, including recovery on other squares. Avoid presenting a single line as proof when the defender has other legal choices.

## What we recommend for Mute Chess

Lead with the recommendation supported by the completed evidence. State what a player would experience, what the rule checks, and which known cases it improves or worsens. If no candidate rule improves the balance reliably, say so plainly and retain the current rule.

Keep Mobile Maia's existing En Croissant behavior separate from an experiment in Mute. Make the Mute award explainable in the interface with a brief reason such as “Offered a rook while keeping a strong position,” only when that reason is justified by the implemented check.

**Visual:** a compact decision path containing the actual implemented tests. Use plain labels, with exact numeric thresholds linked in the technical appendix. Do not draw a speculative future classifier as if it were already running.

## What this study cannot tell us

The selected accounts mainly represent strong players. Gallery sampling intentionally emphasizes sacrifices; the comparison moves are selected challenges rather than a random sample of all chess moves. Newly opened reviews can disagree with gallery history, and review settings or deeper analysis can change a label. These limits constrain any claim that the rules reproduce Chess.com's behavior generally.

Provide a short explanation of the game-level and player-level holdouts used in the completed analysis. Publish both successful cases and failures.

## Read further

Link to the open evidence, replayable games, annotated examples, exact classifier documentation, and the separate technical appendix. Include the relevant Chess.com descriptions and En Croissant source links beside the claims they support.

## Technical appendix — separate document

Keep implementation and reproducibility details out of the main narrative. The appendix should contain:

- Frozen sampling plan, excluded earlier examples, candidate replacements, and all final denominators.
- Evidence schema and distinction between historical gallery labels, current review labels, and unknown labels.
- Game identity checks: public PGN provenance, exact ply, SAN/UCI, and board-position agreement.
- Exact source revisions and classifier rules, including piece values, quality thresholds, mate treatment, legal-capture checks, and winning-position limits.
- Fixed engine configuration and analysis budget, stronger rechecks, and unresolved cases.
- Evaluation plan and held-out games/players, with category-level confusion counts and uncertainty.
- Candidate changes and their full regression results, including genuine brilliants each proposal would lose.
- Small study-specific commands to reproduce the published figures and tables from the saved corpus.

## Visual style

Use white space, graphite text, and a quiet mint accent. Reserve a separate, consistent color for an unwanted award. Charts must show their denominators directly; boards must show whose turn it is and the move being discussed. Prefer three well-explained positions to a wall of thumbnails. Captions should carry the conclusion so readers can understand the report by scanning its visuals.
