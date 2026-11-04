"""Bounded saved-feature learner comparison. No engine, collection, or app writes.

Run with the isolated environment recorded in PROTOCOL.json. This is a one-study
script, not a reusable training or deployment framework.
"""
import os
for setting in ['OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS', 'MKL_NUM_THREADS']:
    os.environ[setting] = '1'
import ast
import hashlib
import json
import math
import resource
import signal
import sys
import time
from pathlib import Path
sys.dont_write_bytecode = True
import joblib
import numpy as np
import scipy
import sklearn
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from threadpoolctl import threadpool_limits

HERE = Path(__file__).resolve().parent
WORK = HERE.parents[1]
STUDY = WORK / 'mute-chess-research-overnight-2026-11-03/studies/brilliant-training-2026-11-03'
KERNEL = WORK / 'research/brilliants-improvement-2026-11-03/learning-v5/forest-diagnostic/fit.py'
START = time.monotonic()
FITS = 0

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(name, data):
    (HERE / name).write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')

def guard():
    if time.monotonic() - START > 600 or resource.getrusage(resource.RUSAGE_SELF).ru_maxrss > 512 * 1024**2:
        raise RuntimeError('Study limit: 600 seconds / 512 MiB; no automatic retry')

def timeout_handler(*_):
    raise RuntimeError('Study wall deadline reached; no automatic retry')

def fold_map(groups, n, salt):
    ordered = sorted(set(groups), key=lambda g: (hashlib.sha256((salt + ':' + str(g)).encode()).hexdigest(), str(g)))
    return {g: i % n for i, g in enumerate(ordered)}

def arrays(cases, base):
    windows = [c['windows'][w] for c in cases for w in ['current', 'previous']]
    assert all(set(w['features']) == set(base) for w in windows)
    x = np.array([[float(w['features'][n]) if w['features'][n] is not None else np.nan for n in base]
                  + [float(w['features'][n] is None) for n in base] for w in windows])
    assert not np.isinf(x).any()
    eligible = np.array([w['eligible'] for w in windows], dtype=bool)
    guards = eligible.reshape(-1, 2).all(axis=1) & np.array([c['confidence_sufficient'] for c in cases])
    guards &= ~np.array([any(w['features']['physical_unknown'] for w in c['windows'].values()) for c in cases])
    return x, eligible, guards

def main():
    global FITS
    protocol = json.loads((HERE / 'PROTOCOL.json').read_text())
    assert not (HERE / 'RESULTS.json').exists() and not (HERE / 'STOPPED.json').exists()
    assert sha(STUDY / 'data/training.json') == protocol['input_sha256']
    assert sha(KERNEL) == protocol['kernel_sha256']
    assert sha(Path(__file__)) == protocol['script_sha256']
    assert sklearn.__version__ == '1.7.2'
    tree_ast = next(n for n in ast.parse(KERNEL.read_text()).body if isinstance(n, ast.ClassDef) and n.name == 'Tree')
    exec(compile(ast.Module(body=[tree_ast], type_ignores=[]), str(KERNEL), 'exec'), globals())
    data = json.loads((STUDY / 'data/training.json').read_text())
    cases, base = data['cases'], data['predictors']
    assert len(cases) == 3724 and len(base) == 75 and len({c['key'] for c in cases}) == 3724
    names = base + [n + '__missing' for n in base]
    x, eligible, gates = arrays(cases, base)
    truth = np.array([c['truth'] for c in cases], dtype=bool)
    easy = np.array([c['negative_bucket'] == 'easy_error' for c in cases]) & ~truth
    ids = np.repeat(np.arange(len(cases)), 2)
    y = np.repeat(truth, 2)
    group_order = sorted({c['group'] for c in cases})
    gi = {g: i for i, g in enumerate(group_order)}
    cg = np.array([gi[c['group']] for c in cases])
    groups = np.repeat(cg, 2)
    counts = np.bincount(ids[eligible], minlength=len(cases))
    weights = 1 / np.maximum(1, counts[ids])
    game_groups, position_groups = {}, {}
    for c in cases:
        for game in {c['game_id']} | {k.rsplit(':', 1)[0] for k in c.get('aliases', [])}:
            assert game_groups.setdefault(game, c['group']) == c['group']
        pos = ' '.join(c['fen_before'].split()[:4])
        assert position_groups.setdefault(pos, c['group']) == c['group']
    assert int(truth.sum()) == 917 and len(group_order) == 972
    print(json.dumps({'stage': 'input_verified', 'cases': len(cases), 'groups': len(group_order),
                      'eligible_moves': int(gates.sum()), 'versions': [numpy_version(), scipy.__version__, sklearn.__version__]}), flush=True)

    def fit(kind, ti, vi, seed):
        global FITS
        guard()
        assert not set(cg[ti]) & set(cg[vi])
        train = np.flatnonzero(eligible & np.repeat(np.isin(np.arange(len(cases)), ti), 2))
        test = np.ravel(np.column_stack([2 * vi, 2 * vi + 1]))
        if kind == 'custom':
            train_codes = np.unique(cg[ti])
            pred = np.zeros(len(test))
            trees = []
            w = weights * np.where(y, 1, 5)
            for number in range(64):
                guard()
                rng = np.random.default_rng(np.random.SeedSequence([20261103, *seed, number]))
                draws = rng.choice(train_codes, size=len(train_codes), replace=True)
                mult = np.bincount(draws, minlength=len(group_order))
                ix = np.repeat(train, mult[groups[train]])
                assert set(groups[ix]) <= set(train_codes)
                trainer = Tree(x, y, ids, w, names, groups, rng)
                model = trainer.fit(ix)
                pred += trainer.predict(model, test) / 64
                trees.append(model)
            fitted = {'features': names, 'trees': trees}
        else:
            state = int(np.random.SeedSequence([20261103, *seed]).generate_state(1)[0])
            if kind == 'standard_rf':
                fitted = RandomForestClassifier(n_estimators=128, max_depth=6, min_samples_leaf=16,
                    max_features=12, bootstrap=True, n_jobs=1, random_state=state)
            elif kind == 'hist_boost':
                fitted = HistGradientBoostingClassifier(max_iter=200, learning_rate=.05, max_leaf_nodes=15,
                    min_samples_leaf=16, l2_regularization=1, early_stopping=False, random_state=state)
            else:
                raise ValueError(kind)
            fitted.fit(x[train], y[train], sample_weight=weights[train])
            pred = fitted.predict_proba(x[test])[:, 1] if len(test) else np.array([])
        FITS += 1
        guard()
        return pred.reshape(-1, 2).min(axis=1), fitted

    def award(score, idx, threshold):
        return (score >= threshold) & gates[idx]

    def metrics(pred, idx):
        yy = truth[idx]
        tp, fp = int((pred & yy).sum()), int((pred & ~yy).sum())
        total = tp + fp
        return {'TP': tp, 'FN': int((~pred & yy).sum()), 'FP': fp, 'TN': int((~pred & ~yy).sum()),
                'recall': tp / int(yy.sum()) if yy.any() else None,
                'precision': tp / total if total else None,
                'wrong_fraction_of_awards': fp / total if total else None,
                'easy_error_FP': int((pred & easy[idx]).sum())}

    def best_threshold(score, idx, ref):
        # Exact attainable inner-OOF thresholds, keeping ties together. Never
        # inspect outer test labels when picking an operating point.
        order = np.argsort(-score, kind='stable')
        vals = score[order]
        valid = gates[idx][order]
        yy = truth[idx][order]
        tp = np.cumsum(valid & yy)
        fp = np.cumsum(valid & ~yy)
        ends = np.r_[np.flatnonzero(vals[:-1] != vals[1:]), len(vals) - 1]
        feasible = [int(j) for j in ends if fp[j] <= ref['FP'] and
                    fp[j] * ref['TP'] <= ref['FP'] * tp[j] and tp[j] > 0]
        if not feasible:
            threshold = 1.0000001
        else:
            j = max(feasible, key=lambda j: (int(tp[j]), -int(fp[j]), float(vals[j])))
            threshold = float(vals[j])
        return {'threshold': threshold, **metrics(award(score, idx, threshold), idx)}

    def select(scores, idx):
        ref = {'kind': 'custom', 'arm': 'custom_fixed', 'threshold': 5/6,
               **metrics(award(scores['custom'], idx, 5/6), idx)}
        points = {'custom_fixed': ref}
        for kind, arm in [('custom', 'custom_retuned'), ('standard_rf', 'standard_rf'), ('hist_boost', 'hist_boost')]:
            points[arm] = {'kind': kind, 'arm': arm, **best_threshold(scores[kind], idx, ref)}
        priority = {'custom_fixed': 3, 'custom_retuned': 2, 'standard_rf': 1, 'hist_boost': 0}
        # Includes fixed reference as fallback; higher TP then fewer FP.
        selected = max(points.values(), key=lambda p: (p['TP'], -p['FP'], priority[p['arm']]))
        return {'points': points, 'selected': selected}

    all_cases = np.arange(len(cases))
    kinds = ['custom', 'standard_rf', 'hist_boost']
    arms = ['custom_fixed', 'custom_retuned', 'standard_rf', 'hist_boost', 'selected_procedure']
    outer_map = fold_map(group_order, 5, 'mute-optimization-v1-outer')
    outer = np.array([outer_map[c['group']] for c in cases])
    outer_scores = {k: np.full(len(cases), np.nan) for k in kinds}
    outer_preds = {a: np.zeros(len(cases), dtype=bool) for a in arms}
    outer_records = []
    prior_outer = json.loads((STUDY / 'optimization/RESULTS.json').read_text())['outer_folds']
    for fold in range(5):
        ti, vi = all_cases[outer != fold], all_cases[outer == fold]
        imap = fold_map([cases[i]['group'] for i in ti], 3, 'mute-optimization-v1-inner-' + str(fold))
        inner = np.array([imap[cases[i]['group']] for i in ti])
        scores = {k: np.full(len(ti), np.nan) for k in kinds}
        for inner_fold in range(3):
            it, iv = ti[inner != inner_fold], ti[inner == inner_fold]
            for kind in kinds:
                scores[kind][inner == inner_fold], _ = fit(kind, it, iv, [10, fold, inner_fold])
        assert all(np.isfinite(s).all() for s in scores.values())
        selection = select(scores, ti)
        for kind in kinds:
            outer_scores[kind][vi], _ = fit(kind, ti, vi, [20, fold])
        for arm in arms:
            point = selection['selected'] if arm == 'selected_procedure' else selection['points'][arm]
            outer_preds[arm][vi] = award(outer_scores[point['kind']][vi], vi, point['threshold'])
        results = {a: metrics(outer_preds[a][vi], vi) for a in arms}
        old = prior_outer[fold]['outer_reference']
        assert results['custom_fixed']['TP'] == old['TP']
        assert results['custom_fixed']['FP'] == old['FP'] + old['easy_error_FP']
        outer_records.append({'fold': fold, 'inner_selection': selection, 'test_metrics': results,
                              'test_keys': [cases[i]['key'] for i in vi]})
        write('PROGRESS.json', {'completed_outer_folds': fold + 1, 'fits': FITS, 'elapsed_seconds': time.monotonic() - START})
        print(json.dumps({'stage': 'outer_fold', 'fold': fold, 'selected': selection['selected']['arm'],
                          'results': results, 'elapsed_seconds': round(time.monotonic() - START, 1)}), flush=True)

    # Separate training-only calibration for choosing the final full-fit method.
    final_map = fold_map(group_order, 5, 'mute-optimization-v1-final')
    final_folds = np.array([final_map[c['group']] for c in cases])
    final_scores = {k: np.full(len(cases), np.nan) for k in kinds}
    prior_final = {r['key']: min(r['scores']['5']) for r in json.loads((STUDY / 'optimization/FINAL-OOF.json').read_text())['rows']}
    for fold in range(5):
        ti, vi = all_cases[final_folds != fold], all_cases[final_folds == fold]
        for kind in kinds:
            final_scores[kind][vi], _ = fit(kind, ti, vi, [30, fold])
    for scores in [*outer_scores.values(), *final_scores.values()]:
        assert np.isfinite(scores).all() and ((scores >= 0) & (scores <= 1)).all()
    parity_max_diff = float(np.max(np.abs(final_scores['custom'] - [prior_final[c['key']] for c in cases])))
    assert parity_max_diff < 1e-12
    final_selection = select(final_scores, all_cases)
    chosen = final_selection['selected']
    _, full_model = fit(chosen['kind'], all_cases, np.array([], dtype=int), [5])
    if chosen['kind'] == 'custom':
        model_path = HERE / 'selected-model.json'
        write(model_path.name, full_model)
    else:
        model_path = HERE / 'selected-model.joblib'
        joblib.dump(full_model, model_path)
    write('MODEL-FREEZE.json', {'scope': 'Experimental only; not application-compatible release artifact',
          'selected': chosen, 'model_sha256': sha(model_path), 'script_sha256': sha(Path(__file__)),
          'protocol_sha256': sha(HERE / 'PROTOCOL.json'), 'input_sha256': protocol['input_sha256']})
    print(json.dumps({'stage': 'training_only_selection_frozen', 'selected': chosen}), flush=True)

    # Secondary replay on the already-seen 89-game benchmark, after selection.
    replay = replay_seen(full_model, chosen, base, cases)

    # Paired whole-group bootstrap: descriptive uncertainty, conditional on fitted
    # OOF predictions. It does not include fitting or repeated-research uncertainty.
    rng = np.random.default_rng(20261104)
    group_pos = np.bincount(cg, weights=truth, minlength=len(group_order))
    by_group = {a: (np.bincount(cg, weights=outer_preds[a] & truth, minlength=len(group_order)),
                    np.bincount(cg, weights=outer_preds[a] & ~truth, minlength=len(group_order))) for a in arms}
    samples = {a: {'recall_delta': [], 'FP_delta': []} for a in arms if a != 'custom_fixed'}
    for _ in range(2000):
        draw = np.bincount(rng.integers(0, len(group_order), len(group_order)), minlength=len(group_order))
        pos = float(draw @ group_pos)
        rt, rf = [float(draw @ v) for v in by_group['custom_fixed']]
        for a in samples:
            tp, fp = [float(draw @ v) for v in by_group[a]]
            samples[a]['recall_delta'].append((tp-rt)/pos)
            samples[a]['FP_delta'].append(fp-rf)
    intervals = {a: {k: [float(v) for v in np.quantile(values, [.025, .975])] for k, values in ss.items()}
                 for a, ss in samples.items()}
    subgroup = {}
    for value in [True, False]:
        idx = np.array([i for i,c in enumerate(cases) if gates[i] and c['windows']['current']['features']['ec_sacrifice'] == value])
        subgroup[str(value)] = {a: metrics(outer_preds[a][idx], idx) for a in arms}
    predictions = [{'key': c['key'], 'group': c['group'], 'truth': c['truth'], 'cohort': c['cohort'],
                    'eligible': bool(gates[i]), 'outer_fold': int(outer[i]), 'final_calibration_fold': int(final_folds[i]),
                    'outer_scores': {k: float(outer_scores[k][i]) for k in kinds},
                    'outer_awards': {a: bool(outer_preds[a][i]) for a in arms},
                    'final_calibration_scores': {k: float(final_scores[k][i]) for k in kinds}}
                   for i,c in enumerate(cases)]
    write('PREDICTIONS.json', predictions)
    summary = {'scope': protocol['scope'], 'protocol_sha256': sha(HERE / 'PROTOCOL.json'),
               'script_sha256': sha(Path(__file__)), 'input_sha256': protocol['input_sha256'],
               'versions': {'python': sys.version, 'numpy': np.__version__, 'scipy': scipy.__version__, 'sklearn': sklearn.__version__},
               'counts': {'cases': len(cases), 'positive': int(truth.sum()), 'negative': int((~truth).sum()),
                          'groups': len(group_order), 'both_window_eligible': int(gates.sum())},
               'outer_pooled': {a: metrics(outer_preds[a], all_cases) for a in arms},
               'outer_folds': outer_records, 'final_training_only_selection': final_selection,
               'paired_group_bootstrap_95_percentile': intervals,
               'bootstrap_caveat': 'Conditional on fixed OOF predictions; excludes refitting and repeated-study selection uncertainty',
               'eligible_subgroup_ec_sacrifice': subgroup, 'seen_benchmark_replay': replay,
               'reference_parity_max_score_difference': parity_max_diff,
               'fits': FITS, 'elapsed_seconds': time.monotonic()-START,
               'peak_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
    guard()
    write('RESULTS.json', summary)
    print(json.dumps({'stage': 'complete', 'outer_pooled': summary['outer_pooled'],
                      'seen_benchmark_replay': replay['metrics'], 'fits': FITS,
                      'elapsed_seconds': summary['elapsed_seconds'], 'peak_rss_bytes': summary['peak_rss_bytes']}), flush=True)

def numpy_version():
    return np.__version__

def replay_seen(model, chosen, base, training):
    saved = json.loads((STUDY / 'RESULTS.json').read_text())['rows']
    features = {}
    hashes = {}
    for p in sorted((WORK / 'research/brilliants-training-overnight-2026-11-03/assessment-batches').glob('*/features.json')):
        hashes[str(p.relative_to(WORK))] = sha(p)
        for row in json.loads(p.read_text())['rows']:
            assert row['key'] not in features
            features[row['key']] = row['features']
    assert len(saved) == len(features) == 654 and {r['key'] for r in saved} == set(features)
    train_keys = {c['key'] for c in training} | {k for c in training for k in c.get('aliases', [])}
    train_games = {k.rsplit(':',1)[0] for k in train_keys}
    assert not {r['key'] for r in saved} & train_keys
    assert not {r['key'].rsplit(':',1)[0] for r in saved} & train_games
    xx, _, gg = arrays([features[r['key']] for r in saved], base)
    if chosen['kind'] == 'custom':
        pred = np.zeros(len(xx))
        for tree in model['trees']:
            for i, values in enumerate(xx):
                node = tree
                while node['kind'] == 'split':
                    v = values[node['feature_index']]
                    node = node['left' if np.isnan(v) or v <= node['threshold'] else 'right']
                pred[i] += node['raw_p'] / 64
        score = pred.reshape(-1,2).min(axis=1)
    else:
        score = model.predict_proba(xx)[:,1].reshape(-1,2).min(axis=1)
    awarded = (score >= chosen['threshold']) & gg
    yy = np.array([r['truth'] for r in saved], dtype=bool)
    def met(pred):
        tp, fp = int((pred & yy).sum()), int((pred & ~yy).sum())
        return {'TP': tp, 'FN': int((~pred & yy).sum()), 'FP': fp, 'TN': int((~pred & ~yy).sum()),
                'recall': tp/int(yy.sum()), 'precision': tp/(tp+fp) if tp+fp else None,
                'wrong_fraction_of_awards': fp/(tp+fp) if tp+fp else None}
    result = {'scope': 'Already-seen benchmark; no independent validation claim; loaded after model freeze',
              'feature_hashes': hashes, 'metrics': {'selected': met(awarded),
                'deployed_reference': met(np.array([r['baseline']['award'] for r in saved])),
                'expanded_reference': met(np.array([r['candidate']['award'] for r in saved]))}}
    write('SEEN-BENCHMARK-PREDICTIONS.json', [{'key': r['key'], 'truth': r['truth'], 'score': float(score[i]),
          'eligible': bool(gg[i]), 'award': bool(awarded[i])} for i,r in enumerate(saved)])
    return result

if __name__ == '__main__':
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(600)
    try:
        with threadpool_limits(limits=1):
            main()
    except Exception as error:
        write('STOPPED.json', {'reason': repr(error), 'elapsed_seconds': time.monotonic()-START,
                              'no_automatic_retry': True})
        raise
    finally:
        signal.alarm(0)
