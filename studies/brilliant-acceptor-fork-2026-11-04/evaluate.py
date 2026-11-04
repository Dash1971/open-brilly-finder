"""Prespecified accepting-piece fork and reply-check ablation; exactly 120 fits."""
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
import numpy as np
import scipy
import sklearn
from sklearn.ensemble import RandomForestClassifier
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
    protocol = json.loads((HERE / 'EVAL-PROTOCOL.json').read_text())
    assert not (HERE / 'RESULTS.json').exists() and not (HERE / 'STOPPED.json').exists()
    assert sha(Path(__file__)) == protocol['script_sha256']
    for relative, digest in protocol['source_sha256'].items():
        assert sha(WORK / relative) == digest, relative
    assert sha(HERE / 'FEATURES.json') == protocol['feature_sha256']
    assert sha(HERE / 'EXTRACTION.json') == protocol['extraction_sha256']
    extraction = json.loads((HERE / 'EXTRACTION.json').read_text())
    assert extraction['status'] == 'complete'
    assert extraction['feature_sha256'] == protocol['feature_sha256']
    assert extraction['protocol_sha256'] == sha(HERE / 'EXTRACTION-PROTOCOL.json')
    assert extraction['script_sha256'] == sha(HERE / 'extract.py')
    assert extraction['evidence_sha256'] == sha(HERE / 'FEATURE-EVIDENCE.json')
    assert sklearn.__version__ == '1.7.2'
    tree_ast = next(n for n in ast.parse(KERNEL.read_text()).body if isinstance(n, ast.ClassDef) and n.name == 'Tree')
    exec(compile(ast.Module(body=[tree_ast], type_ignores=[]), str(KERNEL), 'exec'), globals())
    data = json.loads((STUDY / 'data/training.json').read_text())
    cases, base = data['cases'], data['predictors']
    assert len(cases) == 3724 and len(base) == 75 and len({c['key'] for c in cases}) == 3724
    names = base + [n + '__missing' for n in base]
    x, eligible, gates = arrays(cases, base)
    features = json.loads((HERE / 'FEATURES.json').read_text())
    assert set(features) == {c['key'] for c in cases}
    extra = ['acceptor_fork', 'reply_check']
    assert all(set(features[c['key']]) == {'current', 'previous'} for c in cases)
    assert all(set(features[c['key']][w]) == set(extra) for c in cases for w in ['current', 'previous'])
    assert all(v is None or type(v) is bool for c in cases for w in ['current', 'previous']
               for v in features[c['key']][w].values())
    z = np.array([[float(features[c['key']][w][n]) if features[c['key']][w][n] is not None else np.nan
                   for n in extra] for c in cases for w in ['current', 'previous']])
    check_z = z.copy()
    check_z[:, 0] = np.where(np.isnan(z[:, 0]), np.nan, 0.0)
    expanded_names = names + extra + [n + '__missing' for n in extra]
    matrices = {'original': x,
                'check': np.column_stack([x, check_z, np.isnan(check_z).astype(float)]),
                'fork_check': np.column_stack([x, z, np.isnan(z).astype(float)])}
    matrix_names = {'original': names, 'check': expanded_names, 'fork_check': expanded_names}
    for suffix, size in [('original', 150), ('check', 154), ('fork_check', 154)]:
        assert matrices[suffix].shape == (7448, size)
        assert np.array_equal(matrices[suffix][:, :150], x, equal_nan=True)
        assert len(matrix_names[suffix]) == size and math.isqrt(size) == 12
    assert np.array_equal(np.isnan(matrices['check']), np.isnan(matrices['fork_check']))
    assert np.array_equal(matrices['check'][:, 151:], matrices['fork_check'][:, 151:], equal_nan=True)
    assert (matrices['check'][np.isfinite(z[:, 0]), 150] == 0).all()
    panel_groups = set(protocol['hypothesis_panel']['groups'])
    panel = json.loads((WORK / protocol['hypothesis_panel']['source']).read_text())
    assert len(panel) == 12
    assert panel_groups == {r[k]['group'] for r in panel for k in ['miss', 'ordinary']}
    assert len(panel_groups) == 24
    nonpanel = np.array([c['group'] not in panel_groups for c in cases])
    previous_predictions = {r['key']: r for r in json.loads((WORK / 'research/brilliant-standard-learners-2026-11-04/PREDICTIONS.json').read_text())}
    assert set(previous_predictions) == {c['key'] for c in cases}
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
        assert FITS < 120
        guard()
        assert not set(cg[ti]) & set(cg[vi])
        train = np.flatnonzero(eligible & np.repeat(np.isin(np.arange(len(cases)), ti), 2))
        test = np.ravel(np.column_stack([2 * vi, 2 * vi + 1]))
        suffix = kind.split('_', 1)[1] if kind.startswith('custom_') else kind[len('standard_rf_'):]
        xx, nn = matrices[suffix], matrix_names[suffix]
        if kind.startswith('custom_'):
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
                trainer = Tree(xx, y, ids, w, nn, groups, rng)
                model = trainer.fit(ix)
                pred += trainer.predict(model, test) / 64
                trees.append(model)
            fitted = {'features': nn, 'trees': trees}
        else:
            state = int(np.random.SeedSequence([20261103, *seed]).generate_state(1)[0])
            if kind.startswith('standard_rf_'):
                fitted = RandomForestClassifier(n_estimators=128, max_depth=6, min_samples_leaf=16,
                    max_features=12, bootstrap=True, n_jobs=1, random_state=state)
            else:
                raise ValueError(kind)
            fitted.fit(xx[train], y[train], sample_weight=weights[train])
            pred = fitted.predict_proba(xx[test])[:, 1] if len(test) else np.array([])
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
        ref = {'kind': 'custom_original', 'arm': 'custom_fixed', 'threshold': 5/6,
               **metrics(award(scores['custom_original'], idx, 5/6), idx)}
        points = {'custom_fixed': ref}
        for kind, arm in [('custom_original', 'custom_retuned'), ('custom_check', 'custom_check'),
                          ('custom_fork_check', 'custom_fork_check'), ('standard_rf_original', 'standard_rf'),
                          ('standard_rf_check', 'standard_rf_check'), ('standard_rf_fork_check', 'standard_rf_fork_check')]:
            points[arm] = {'kind': kind, 'arm': arm, **best_threshold(scores[kind], idx, ref)}
        points['custom_fork_check_fixed'] = {'kind': 'custom_fork_check', 'arm': 'custom_fork_check_fixed',
            'threshold': 5/6, **metrics(award(scores['custom_fork_check'], idx, 5/6), idx)}
        return {'points': points}

    all_cases = np.arange(len(cases))
    kinds = ['custom_original', 'custom_check', 'custom_fork_check',
             'standard_rf_original', 'standard_rf_check', 'standard_rf_fork_check']
    arms = ['custom_fixed', 'custom_retuned', 'custom_check', 'custom_fork_check', 'custom_fork_check_fixed',
            'standard_rf', 'standard_rf_check', 'standard_rf_fork_check']
    outer_map = fold_map(group_order, 5, 'mute-optimization-v1-outer')
    outer = np.array([outer_map[c['group']] for c in cases])
    outer_scores = {k: np.full(len(cases), np.nan) for k in kinds}
    outer_preds = {a: np.zeros(len(cases), dtype=bool) for a in arms}
    outer_records = []
    parity_max = {'custom': 0.0, 'standard_rf': 0.0}
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
            point = selection['points'][arm]
            outer_preds[arm][vi] = award(outer_scores[point['kind']][vi], vi, point['threshold'])
        results = {a: metrics(outer_preds[a][vi], vi) for a in arms}
        for kind in ['custom', 'standard_rf']:
            original_kind = kind + '_original'
            old_scores = np.array([previous_predictions[cases[i]['key']]['outer_scores'][kind] for i in vi])
            diff = float(np.max(np.abs(outer_scores[original_kind][vi] - old_scores)))
            parity_max[kind] = max(parity_max[kind], diff)
            assert diff <= 1e-12
        for arm in ['custom_fixed', 'custom_retuned', 'standard_rf']:
            assert [bool(v) for v in outer_preds[arm][vi]] == [previous_predictions[cases[i]['key']]['outer_awards'][arm] for i in vi]
        outer_records.append({'fold': fold, 'inner_selection': selection, 'test_metrics': results,
                              'test_keys': [cases[i]['key'] for i in vi]})
        write('PROGRESS.json', {'completed_outer_folds': fold + 1, 'fits': FITS, 'elapsed_seconds': time.monotonic() - START})
        print(json.dumps({'stage': 'outer_fold', 'fold': fold, 'results': results, 'elapsed_seconds': round(time.monotonic() - START, 1)}), flush=True)

    assert FITS == 120
    for values in outer_scores.values():
        assert np.isfinite(values).all() and ((values >= 0) & (values <= 1)).all()

    # Paired whole-group bootstrap: descriptive uncertainty, conditional on fitted
    # OOF predictions. It does not include fitting or repeated-research uncertainty.
    rng = np.random.default_rng(20261104)
    group_pos = np.bincount(cg, weights=truth, minlength=len(group_order))
    by_group = {a: (np.bincount(cg, weights=outer_preds[a] & truth, minlength=len(group_order)),
                    np.bincount(cg, weights=outer_preds[a] & ~truth, minlength=len(group_order))) for a in arms}
    comparisons = {'custom_bundle_vs_original': ('custom_fork_check', 'custom_retuned'),
                   'custom_bundle_vs_check_only': ('custom_fork_check', 'custom_check'),
                   'standard_rf_bundle_vs_original': ('standard_rf_fork_check', 'standard_rf'),
                   'standard_rf_bundle_vs_check_only': ('standard_rf_fork_check', 'standard_rf_check'),
                   'bundle_fixed_vs_original_fixed': ('custom_fork_check_fixed', 'custom_fixed')}
    samples = {a: {'recall_delta': [], 'TP_delta': [], 'FP_delta': []} for a in comparisons}
    for _ in range(2000):
        draw = np.bincount(rng.integers(0, len(group_order), len(group_order)), minlength=len(group_order))
        pos = float(draw @ group_pos)
        for a, (candidate, reference) in comparisons.items():
            rt, rf = [float(draw @ v) for v in by_group[reference]]
            tp, fp = [float(draw @ v) for v in by_group[candidate]]
            samples[a]['recall_delta'].append((tp-rt)/pos)
            samples[a]['TP_delta'].append(tp-rt)
            samples[a]['FP_delta'].append(fp-rf)
    intervals = {a: {k: [float(v) for v in np.quantile(values, [.025, .975])] for k, values in ss.items()}
                 for a, ss in samples.items()}
    original_misses = np.array([gates[i] and truth[i] and not previous_predictions[c['key']]['outer_awards']['custom_retuned']
                                for i, c in enumerate(cases)])
    assert int(original_misses.sum()) == 429
    subgroup = {}
    for value in [True, False]:
        idx = np.array([i for i,c in enumerate(cases) if gates[i] and c['windows']['current']['features']['ec_sacrifice'] == value])
        subgroup[str(value)] = {a: metrics(outer_preds[a][idx], idx) for a in arms}
    changes = {}
    for name, (candidate, reference) in comparisons.items():
        cp, rp = outer_preds[candidate], outer_preds[reference]
        masks = {'gained_correct': cp & ~rp & truth, 'lost_correct': ~cp & rp & truth,
                 'gained_wrong': cp & ~rp & ~truth, 'removed_wrong': ~cp & rp & ~truth}
        changes[name] = {label: {'count': int(mask.sum()), 'keys': [c['key'] for i,c in enumerate(cases) if mask[i]]}
                         for label, mask in masks.items()}
    availability = {}
    for col, name in enumerate(extra):
        values = z[:, col].reshape(-1, 2)
        known = np.isfinite(values)
        known_both = known.all(axis=1)
        any_true = (values == 1).any(axis=1)
        both_true = (values == 1).all(axis=1)
        idx = all_cases[known_both]
        availability[name] = {
            'windows': {w: {'known': int(known[:, j].sum()), 'unknown': int((~known[:, j]).sum()),
                            'true': int((values[:, j] == 1).sum()), 'false': int((values[:, j] == 0).sum())}
                        for j, w in enumerate(['current', 'previous'])},
            'known_both_cases': int(known_both.sum()), 'unknown_either_cases': int((~known_both).sum()),
            'any_true_cases': int(any_true.sum()), 'both_true_cases': int(both_true.sum()),
            'any_true_positive_cases': int((any_true & truth).sum()),
            'any_true_negative_cases': int((any_true & ~truth).sum()),
            'any_true_eligible_cases': int((any_true & gates).sum()),
            'any_true_original_429_miss_cases': int((any_true & original_misses).sum()),
            'known_both_metrics': {a: metrics(outer_preds[a][idx], idx) for a in arms}}
    known_all = np.isfinite(z).all(axis=1).reshape(-1, 2).all(axis=1)
    known_all_idx = all_cases[known_all]
    availability['both_features_known_both_windows'] = {
        'cases': int(known_all.sum()), 'eligible_cases': int((known_all & gates).sum()),
        'metrics': {a: metrics(outer_preds[a][known_all_idx], known_all_idx) for a in arms}}
    outside_idx = all_cases[nonpanel]
    panel_excluded = {'excluded_groups': sorted(panel_groups), 'excluded_cases': int((~nonpanel).sum()),
                      'remaining_cases': len(outside_idx),
                      'remaining_groups': len(set(cases[i]['group'] for i in outside_idx)),
                      'outer_pooled': {a: metrics(outer_preds[a][outside_idx], outside_idx) for a in arms},
                      'caveat': 'Descriptive outer-test reporting only; panel groups remain in the original fold/training procedure.'}
    miss_idx = all_cases[original_misses]
    miss_breakdown = {a: {'recovered': int(outer_preds[a][original_misses].sum()),
                            'still_missed': int((~outer_preds[a][original_misses]).sum()),
                            'recovered_keys': [cases[i]['key'] for i in miss_idx if outer_preds[a][i]]} for a in arms}
    predictions = [{'key': c['key'], 'group': c['group'], 'truth': c['truth'], 'cohort': c['cohort'],
                    'eligible': bool(gates[i]), 'original_429_miss': bool(original_misses[i]), 'outer_fold': int(outer[i]),
                    'hypothesis_panel_group': not bool(nonpanel[i]), 'added_features': features[c['key']],
                    'outer_scores': {k: float(outer_scores[k][i]) for k in kinds},
                    'outer_awards': {a: bool(outer_preds[a][i]) for a in arms}}
                   for i,c in enumerate(cases)]
    write('PREDICTIONS.json', predictions)
    summary = {'scope': protocol['scope'], 'protocol_sha256': sha(HERE / 'EVAL-PROTOCOL.json'),
               'script_sha256': sha(Path(__file__)), 'input_sha256': sha(STUDY / 'data/training.json'),
               'feature_sha256': sha(HERE / 'FEATURES.json'), 'extraction_sha256': sha(HERE / 'EXTRACTION.json'),
               'versions': {'python': sys.version, 'numpy': np.__version__, 'scipy': scipy.__version__, 'sklearn': sklearn.__version__},
               'counts': {'cases': len(cases), 'positive': int(truth.sum()), 'negative': int((~truth).sum()),
                          'groups': len(group_order), 'both_window_eligible': int(gates.sum())},
               'outer_pooled': {a: metrics(outer_preds[a], all_cases) for a in arms},
               'outer_folds': outer_records,
               'paired_group_bootstrap_95_percentile': intervals,
               'bootstrap_caveat': 'Conditional on fixed OOF predictions; excludes refitting and repeated-study selection uncertainty',
               'eligible_subgroup_ec_sacrifice': subgroup,
               'paired_award_changes': changes,
               'original_429_eligible_retuned_misses': miss_breakdown,
               'subgroup_caveat': 'EC strata and 429 misses are descriptive; misses are selected using same outer labels and original OOF awards, not independent validation',
               'feature_availability': availability,
               'hypothesis_panel_groups_excluded_outer_report': panel_excluded,
               'reference_parity_max_outer_score_difference': parity_max,
               'reference_parity_all_3724_awards': True,
               'fits': FITS, 'elapsed_seconds': time.monotonic()-START,
               'peak_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
    guard()
    assert FITS == 120
    write('RESULTS.json', summary)
    print(json.dumps({'stage': 'complete', 'outer_pooled': summary['outer_pooled'],
                      'fits': FITS,
                      'elapsed_seconds': summary['elapsed_seconds'], 'peak_rss_bytes': summary['peak_rss_bytes']}), flush=True)

def numpy_version():
    return np.__version__

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
