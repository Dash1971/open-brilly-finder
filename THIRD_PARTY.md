# Attribution and source boundaries

This repository extracts the brilliant-classification research from Mute Chess and Mute Chess Research. The original selected model is `44704ac06378d3f671a4eed959e21959f759c0437c71af1f9119d1081293c0b7`; this is distinct from later experimental full fits and fold-specific evaluation models.

- Mute Chess and its derived research/reference implementation: AGPL-3.0-only; retain repository LICENSE and existing file headers. Original repository: https://github.com/Dash1971/mute-chess . Research: https://github.com/Dash1971/mute-chess-research .
- En Croissant-derived classifier/reference: GPL-3.0 notices retained under `studies/brilliant-moves/reference/`. The pinned En Croissant scoring source is https://github.com/franciscoBSalgueiro/en-croissant/tree/6f2d2628f0fbe11cb62a7dd2f9c102bb52907d53 . See the detailed source lineage in that reference directory's README and GPL-3.0.txt.
- The retained native core credits CSSLab Maia3 and Mobile Maia. Its copied headers and source mappings remain authoritative. See https://github.com/Dash1971/mute-chess/blob/main/THIRD_PARTY.md .
- Published board imagery retains Colin M. L. Burnett's Cburnett GPL-2.0-or-later notices and full license under the studies' visual asset directories. Raw authenticated browser screenshots are not part of this export.
- WintrChess comparison: WintrCat/wintrchess-lib commit `0a63a69a544105e218b11f7459815bf195707776`, AGPL-3.0-only. The actual pinned classifier was executed, not a rewritten approximation. Upstream source/dependency hashes are in the execution receipt; external runtime dependencies are not vendored here.
- Knight's Eye comparison: knights-eye-chess/move-classifier commit `c8183a6da88f3b5a2450dab35353dedd1d8d7a62`, policy revision48, first-party MIT. Executed the upstream checked-in package artifact with source parity checked. Native dependencies are not vendored. Its own source credits WintrChess prose for some ideas.
- Source-review-only projects: T-Julsgaard/Chess-Review (GPL-3.0), wdeloo/Brilliant-Chess (MIT), FelixYUFENGSU/chess-game-review (no license declaration found at the reviewed commit). These are linked and analyzed; their entire source trees are not copied into this repository.
- Stockfish18, python-chess, Chessops, chess.js, tsx, NumPy, SciPy and scikit-learn retain their upstream licenses. Engine binaries, installed packages, browser sessions and credentials are not distributed.

Public game records, observed Chess.com labels and review evidence are research data with recorded sources. This repository does not claim ownership of third-party services' annotations, text, branding or underlying game records, and does not grant a new blanket software license over those materials. Structured research evidence is retained; raw HTTP metadata and authenticated browser captures are excluded. The source manifest lists export exclusions without changing archived scientific conclusions.

The pinned project/source list is also available in `studies/brilliant-external-repos-2026-11-04/SOURCES.json`. This is an independent research project, not an official implementation of Chess.com's private classifier.
