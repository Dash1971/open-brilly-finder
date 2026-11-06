# Offline quickstart tools

These commands use Python 3.10 or newer and only its standard library. They make no network requests, run no engine, fit no model, and write no output files. Run them from the repository root; their data paths are resolved relative to the scripts, so they also work from another working directory.

```sh
python3 tools/reproduce_results.py
python3 tools/reproduce_results.py --verify-forest
python3 tools/infer_saved_features.py --case-key 183200302081:135
```

The first command recomputes the historical external comparison from saved decisions and verifies the original five game/position groups of folds. Expected primary results:

| Method | Correct awards | Wrong awards | Unresolved cases |
|---|---:|---:|---:|
| Original grouped forest benchmark | 452 | 6 | 0 |
| WintrChess, both windows | 287 | 20 | 5 |
| Knight's Eye, both windows | 590 | 142 | 56 |

WintrChess adds 88 correct awards and 19 wrong awards beyond the forest; Knight's Eye adds 256 correct and 141 wrong. Unresolved cases are never counted as ordinary moves. These are sample results on repeatedly studied research data, not site-wide precision guarantees.

`--verify-forest` goes beyond replaying saved awards: it loads the five archived 64-tree held-out forests and actually recomputes every custom forest score on the 3,724 cases. Scores must match the recorded out-of-fold scores within `1e-12`, yielding 452/6 with the recorded fold-specific cutoffs, or 436/6 at the fixed `5/6` cutoff. Both engine windows and aliases remain in their original game/position group. It does not refit the trees or rerun the external classifiers.

## Saved-feature inference

`infer_saved_features.py` evaluates the original 848-case full-fit forest at `5/6`, with the saved eligibility, confidence and physical-evidence gates. It outputs the two window scores and award decision. It does **not** claim that scoring the later dataset with that full model reproduces the 452/6 held-out result.

The later experimental full-fit model is available explicitly:

```sh
python3 tools/infer_saved_features.py --model experimental3724 --case-key 183200302081:135
```

That model was fitted to all 3,724 cases and selected a cutoff of approximately `0.8143062085`. It was not promoted as a release artifact. Predictions on its training cases are not validation.

You can supply a JSON object rather than select an included case:

```sh
python3 tools/infer_saved_features.py --features-json /path/to/case.json
```

The object must contain `windows.current` and `windows.previous`, each with all 75 named `features` and a boolean `eligible`, plus a boolean `confidence_sufficient`. Null feature values are supported; omitted predictors and nonfinite numbers are rejected. The model's additional 75 missing-value columns are constructed by the scorer. The `physical_unknown` feature is a gate as well as a model input. Labels, ratings, game IDs and case keys are not predictors.

This interface accepts **precomputed feature windows**, not a bare FEN or PGN. Fresh-position feature extraction also requires compatible engine observations and the archived chess/feature code. Its original contracts are in `studies/brilliant-moves/reference/v5/README.md` and `studies/brilliant-moves/reference/v5/astra/v5/fresh-extractor/CONTRACT.md`.

## Reproduction levels and dependencies

- **Saved decisions / JSON-forest inference:** the commands above; Python standard library only.
- **Re-fit the original standard learner experiment:** archived `studies/brilliant-standard-learners-2026-11-04/experiment.py`. The recorded environment used NumPy 2.5.4, SciPy 1.18.1, scikit-learn 1.7.2, joblib and threadpoolctl. This historical script assumes the original workspace layout, imports the tree class from a frozen source file, and refuses to overwrite an existing run. It also performs a separate 654-case already-seen benchmark replay. It is an archival executable record, not a portable command promised by this quickstart.
- **Rerun external classifiers:** the archived adapter notes and pinned source revisions describe their exact APIs, dependencies and acquisition settings. The latest run used Node 24.22.1, Stockfish 18, two root candidates and two saved engine windows. Historical adapters retain original temporary runtime paths. Replaying their saved results offline does not require those runtimes.

The original 848-case model, the expanded experimental full model, and the five held-out models have different roles. Keep those roles separate when building new experiments. The source code for the traverser/gates is derived from the archived Mute Chess research/native classifier and is distributed under the repository's AGPL terms. Upstream components retain their own licenses; see repository attribution and licensing records.

## Updated selective model (November 6)

```sh
python3 studies/brilliant-selective-2026-11-06/reproduce.py
python3 tools/infer_saved_features.py --model selective20261106 --case-key 1006812690:48
```

The first command recounts every saved development and Witty test move. The second evaluates the frozen 128-tree model at 0.83 using one of the 6,293 saved feature cases. It remains saved-feature inference, not a new independent test or an engine run. All earlier model options and commands retain their original behavior.
