# Native Mute Chess study illustrations

These exports use Mute Chess’s actual Moss board colors and Lichess’s native Cburnett SVG pieces. Piece shapes are copied faithfully; they are not Unicode chess glyphs or newly drawn substitutes.

- Board squares: **#C7CFBA / #668478**.
- Last-move highlight: native **rgb(217 178 95 / 42%)**.
- Pieces: **Colin M. L. Burnett**, distributed as **GPL-2.0-or-later**. The complete license accompanies the twelve original SVGs in `assets/`. The native Lila `COPYING.md` explicitly attributes `public/piece/cburnett` to Burnett under GPLv2+.
- Exact source paths, checkout revision, and file hashes are recorded in `ASSET-PROVENANCE.json`. Moss colors and highlight match Mute’s `design/quiet-signal/board.svg` and `quiet-signal.css`.

`render-boards.py` is a bounded study export script. It validates every SAN move with python-chess, preserves board orientation, handles castling, en passant and promotion, and exports a final-position PNG/SVG or an animated GIF. Motion eases over 240 ms; captured pieces fade over about 120 ms. Each GIF uses a fixed global palette to prevent color flicker, with explicit exact-color preservation for the native flat squares and highlights. Each render runs in its own process with an eight-ply cap. Raster piece images are cached once from the exact SVG sources using the official [resvg0.47.0 arm64 release](https://github.com/linebender/resvg/releases/tag/v0.47.0); its URL and binary/archive hashes are recorded in `RASTERIZER-PROVENANCE.json`. The executable remains a local export dependency and is not included in the research publication. The script does not call an engine, browser, or service.

The captions distinguish a played move from a conditional continuation. A legal illustrative reply sequence is not evidence that those replies were played or forced. The pawn-winning examples are supplemental examples outside the independent validation sample.

```sh
python3 render-boards.py --case quiet-offer-bg2 --formats png,svg --resvg /path/to/native/resvg
python3 render-boards.py --case pawn-win-excellent --formats gif,svg --resvg /path/to/native/resvg
python3 render-boards.py --case pawn-win-brilliant --formats gif,svg --resvg /path/to/native/resvg
```

The script uses the study’s existing local python-chess/Pillow dependencies. Its local dependency search paths can be removed when those packages are installed normally. No website or hosting setup is included.

The four exported cases include the quiet Bg2 rook offer, the two supplemental pawn-winning comparisons, and the Ng6+ conditional poisoned-knight example. For Ng6+, ...Rxg6 permits Rxe8#; ...fxg6 is also legal, and no mate-in-one claim is made for that acceptance. All four are previously reviewed development examples, not new independent-validation evidence.

`inspect-frames.py` produces a compact contact sheet and frame/time manifest. `outputs/*-render.json` records per-export timing, peak memory and file sizes. The largest measured export used about243MB; no simultaneous GIF rendering was used.
