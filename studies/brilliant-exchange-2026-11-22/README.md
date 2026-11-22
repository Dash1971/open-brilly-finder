# Mute Exchange: exact algorithm, data and reproduction

[Read the report](REPORT.md) · [Methods and limits](METHODS.md)

## Award rule

1. Compute the position after the move. If no knight, bishop, rook or queen of the mover can be captured for a static-exchange gain of 2 or more, stop: not Brilliant.
2. Compute the 91 features in `model.features` order.
3. `score = sigmoid(baseline + sum over 400 trees of the reached leaf value)`. At each node go left when `x[feature] <= threshold`.
4. Brilliant when `score >= 0.8193002847777424`.

Model file: [model/mute-exchange-model.json](model/mute-exchange-model.json), SHA-256 `992a792a646b11e612486c4fe26796fc38ee47f395f2220b00d26db65ba1e27d`.

Inputs are three positions (before the opponent's last move if there was one, before the move, after the move), the move in UCI, the top two engine lines for the position before the move and the best line for the position after it. Engine scores are centipawns from the mover's side clipped to ±9000; a mate in `n` is `±(10000 − 10·min(n, 99))`.

The score is a model output, not a calibrated probability.

## Files

| File | What it is |
| --- | --- |
| [model/mute-exchange-model.json](model/mute-exchange-model.json) | Trees, feature order, baseline, cutoff |
| [model/noSweatBrilliantExchange.ts](model/noSweatBrilliantExchange.ts) | The browser implementation (chessops), identical to the one proposed for Mute Chess |
| [code/v6ref.py](code/v6ref.py) | Python reference for the same features (python-chess) |
| [model/parity-fixtures.json](model/parity-fixtures.json) | 360 candidates: inputs, all 91 features, score |
| [data/heldout-outcomes.csv](data/heldout-outcomes.csv) | Scored moves in the 337 test games: both references, Mute Selective, and Mute Exchange on native and on research evidence |
| [data/native-1000-outcomes.csv.gz](data/native-1000-outcomes.csv.gz) | All 1,000 test games on native evidence, with the six-account model's score |
| [data/candidates.csv.gz](data/candidates.csv.gz) | 36,543 candidates with labels, features and `role`: training, held-out test, or excluded |
| [data/chesscom-review-moves.csv.gz](data/chesscom-review-moves.csv.gz) | Chess.com's class, evaluation and preferred move for 77,696 moves in 1,005 games |
| [data/study-stats.json](data/study-stats.json) | Every count quoted in the report and methods |
| [code/](code/) | The scripts that produced all of the above |

Evaluations in the review table are centipawns from White's side; `mate_white` is positive when White mates.

## Recount the published results

Python 3 standard library only, from the repository root:

```sh
python3 studies/brilliant-exchange-2026-11-22/reproduce.py
```

It checks the model hash, the published split (33,037 training rows with 7,806 Brilliants, no game or position shared with the 337 held-out games), the held-out and 1,000-game tables, and rescores all 360 parity cases from their saved features.

In `candidates.csv.gz`, only rows with role `training` were used to fit the model, with `training_label` as the target. `excluded: test game` rows are moves from the 337 held-out games (mostly opponents' moves); `excluded: position also in test` rows repeat a held-out position and move. `exchange_score_research_evidence` is filled for held-out rows only.

## Check the browser implementation

With [Bun](https://bun.sh) or Node 22+ and `chessops@0.15.1` installed next to the file, the TypeScript module reproduces every feature and score in `parity-fixtures.json`. During the study it matched the Python reference on 4,000 candidates: all 91 features exactly, scores within 1e-9.

## Rebuild from scratch

Needs Python 3.12+, `chess`, `numpy`, `pandas`, `scikit-learn`, and a Stockfish binary on the path. Run from `code/` with the seven-account PGN in place:

```sh
python extract_moves.py        # every gallery-account move with board facts      -> moves.pkl
python engine_pass.py          # Stockfish evidence for every candidate (~90 min) -> engine/
python v6build.py              # the 91 features at depth 12                      -> v6-d12.pkl
python v6train.py              # train, choose the cutoff, test, export the model
```

`v6train.py` also needs the per-move review labels. The scripts read them from saved review captures, which are not published; [chesscom-review-moves.csv.gz](data/chesscom-review-moves.csv.gz) holds the same information. `candidates.csv.gz` already contains the finished feature table, so the model can be refitted from its `training` rows without running an engine.

The native-evidence test is `native_replay.py`, `native_eval.py` and `native_dev6.py`, run after extracting archives 062 to 069 of the [previous study](../brilliant-selective-2026-11-06/README.md). `nativeReplay.ts` runs the app's own `classify()` over the same windows.

Collecting reviews required a signed-in Chess.com account; `code/recv.py`, `pb.py` and `ccparse.py` are the receiver and decoder we used. Scripts are published as run, with their original relative paths.

## Engine settings

**Training evidence:** Stockfish 18, one thread, 64 MB hash, hash cleared between positions, 200,000 nodes per search, read back at depth 12 with two root lines.

**Test evidence:** Mute Chess's archived Fast review output for the 1,000 test games: Stockfish 19 small network, depth 12, 500 ms, two root lines.
