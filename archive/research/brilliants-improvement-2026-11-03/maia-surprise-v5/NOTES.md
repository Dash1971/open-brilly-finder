# Local Maia move-surprise pilot

The prespecified20-case diagnostic provides **weak separation**: higher move surprisal has sample AUC0.58 for the ten true Brilliant moves versus ten false v4 awards. Median legal-normalized played probability is0.1872 for true Brilliants and0.1885 for false awards; median rank is2.5 versus2. This small matched development sample does not support using human move rarity as a strong standalone classifier signal.

No classifier, threshold, calibration, or production change was fitted. The complete whole-tie sample ROC is descriptive, with its direction fixed beforehand: higher `-ln(played_probability)` means more Brilliant-like surprise. Labels were joined only after inference and were never supplied to the model.

## Model identity and input amendment

The graph is the existing44MB frontend `maia3_simplified.onnx`, SHA256 `405bf76c15727dad8728b352c06a8f3c1b80fb2760e8d666b32485c63d75b856`. It is a tracked asset in local frontend commit `a6e52f5c811ee18863cb2f0e81f2433a5b9905de`. That frontend's `MaiaEngineContext.tsx` explicitly selects the asset, while `tensor.ts` and `maia-worker.js` define the single-board encoder and feed layout.

The one runtime preflight verified `tokens:[batch,64,12]`, `elo_self:[batch]`, `elo_oppo:[batch]`, and4352 policy outputs. It therefore cannot accept the native eight-history97-channel representation. The parent conditionally authorized the documented legacy frontend model for the same20 identities. `PLAN.json` was amended **before the first inference**, recording that the current board alone would be fed. `PLAN-INITIAL.json` preserves the original history request and conditional authorization.

This is explicitly a **legacy frontend single-board model diagnostic**, not a native79M or eight-history Maia fidelity test. The real last eight PGN positions are saved in `inputs.json` for every case but are not falsely described as model inputs. No history was fabricated, padded, or reshaped to fit the wrong graph.

## Encoding and execution checks

The legacy encoder mirrors black positions vertically while swapping relative piece channels. Legal moves come from the exact current FEN, with actual castling/en-passant rights and promotions. The model policy is normalized only over those legal moves, without temperature adjustment. Both Elo inputs are fixed at1600; actual account ratings never enter inference.

All eight existing native encoder fixtures pass their stored token hashes. Every one of the4352 vocabulary indices, including black-mirrored promotions, matches the native policy-index formula and reversed vocabulary. The20 legal masks independently match Python-chess PGN replay. Legacy current-board channels also match the corresponding native single-board frame. These checks verify preprocessing and policy mapping, while preserving the architecture distinction above.

Execution reused local ONNX Runtime Web1.30.0 with the WASM provider, one thread, proxy disabled, local model/runtime buffers, and network fetch blocked. It completed exactly20 inferences in2.556seconds, with715,920KiB peak RSS, below the1GB resident cap. The process exited and released its model; no dependency, model, or runtime was installed or downloaded.

## Counterexamples and artifacts

Some cases fit the intuition: false **Rh1,169827191694:67** has probability0.6601 and rank1, while true **Nxb4,174490497572:26** has probability0.004737 and rank6. But false **Re1,184514610842:73** is also rare, at0.018996 and rank7. In the requested pair, false **Qh4,187780686673:36** has probability0.1415/rank2, whereas true **h6,169827191694:65** has probability0.4777/rank1. Rarity points in the opposite direction for that pair.

`policy-results.json` contains only identities, inference provenance, and the requested probability/rank/entropy/surprisal outputs. `SAMPLE-ROC.json` adds the post-inference labels, group descriptions, and whole-tie ROC. `PLAN.json`, `PREFLIGHT.json`, and `ENCODER-CHECKS.json` pin sources, actual dimensions, preprocessing checks, and fixed settings. This pilot does not establish a population frequency, a new validation result, or a deployable operating point.
