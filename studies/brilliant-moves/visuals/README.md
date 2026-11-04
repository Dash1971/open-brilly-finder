# Native Mute Chess board illustrations

These illustrations use Mute Chess’s Moss board and the native Lichess Cburnett piece artwork. They contain original vector pieces, not Unicode chess characters. The same pieces and colors appear in the PNG, SVG and animated GIF exports.

- Moss squares: **#C7CFBA / #668478**; native last-move highlight: **rgb(217 178 95 / 42%)**.
- Pieces: **Colin M. L. Burnett**, **GPL-2.0-or-later**. The twelve original SVGs and [complete GPL2 license](assets/CBURNETT-GPL2-LICENSE) accompany the derived illustrations. Lila’s native `COPYING.md` explicitly attributes `public/piece/cburnett` to Burnett under GPLv2+.
- Board artwork: Mute Chess Quiet Signal, covered by this repository’s AGPL-3.0-or-later license. Exact source paths, revisions and hashes are in [ASSET-PROVENANCE.json](ASSET-PROVENANCE.json).

The Bg2 illustration shows the observed Brilliant move, then a **conditional** ...Bxb1 Rxb1 exchange. Only 27.Bg2 carries the reported Brilliant label. The following moves are legal explanatory replies; they are not claimed to be forced or played in the original game. The two pawn-winning examples are supplemental positions outside the benchmark totals.

Motion eases over 240 ms, captured pieces fade over about 120 ms, and a fixed global palette preserves the native flat colors without flicker. Every SAN move is checked for legality before export. The renderer handles castling, en passant and promotion and limits each animation to eight plies. Each GIF is rendered separately; the provided exports peaked below 250MB per process.

## Reproduce the exports

Use Python 3 with the pinned packages in [requirements.txt](requirements.txt), and the official [resvg 0.47.0 release](https://github.com/linebender/resvg/releases/tag/v0.47.0). [RASTERIZER-PROVENANCE.json](RASTERIZER-PROVENANCE.json) records the exact official macOS arm64 archive and executable hashes used here. The executable is an export dependency, not a distributed artifact. Use the appropriate official binary for your platform.

Run from this directory, substituting your resvg executable path:

```sh
python3 -m pip install -r requirements.txt
python3 render-boards.py --case quiet-offer-bg2 --formats gif,png,svg --resvg /path/to/resvg
python3 render-boards.py --case pawn-win-excellent --formats gif,png,svg --resvg /path/to/resvg
python3 render-boards.py --case pawn-win-brilliant --formats gif,png,svg --resvg /path/to/resvg
python3 render-boards.py --comparison --resvg /path/to/resvg
python3 inspect-frames.py
```

The renderer caches piece rasters locally under `assets/raster/`; that cache is not included in the publication. Arial is used when available, followed by common system sans-serif fonts. Text metrics can vary by font; board geometry, native vector pieces, legal variations and colors remain fixed.

[Case inputs](cases.json), [contact sheet](outputs/animation-contact-sheet.png), [frame audit](outputs/animation-frame-audit.json) and per-export render receipts document the illustrations. No browser, engine or application service is called by these scripts.
