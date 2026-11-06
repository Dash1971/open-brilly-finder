"""One bounded saved-feature MLP comparison. No engine, browser, or app writes."""
import os
for setting in ['OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS', 'MKL_NUM_THREADS']:
    os.environ[setting] = '1'
import datetime
import hashlib
import json
import math
import resource
import signal
import subprocess
import sys
import time
from pathlib import Path
sys.dont_write_bytecode = True
import numpy as np
import scipy
import sklearn
from scipy.special import expit
from sklearn.impute import SimpleImputer
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

HERE = Path(__file__).resolve().parent
INPUT = HERE.parent / 'brilliant-training-2026-11-03/data/training.json'
REFERENCE = HERE.parent / 'brilliant-standard-learners-2026-11-04'
CONFIG = dict(hidden_layer_sizes=(64, 32), activation='relu', solver='adam',
              alpha=.01, batch_size=128, learning_rate_init=.001,
              max_iter=200, early_stopping=False, tol=0., n_iter_no_change=10000,
              shuffle=True)
EPOCHS = 200
SEEDS = [0, 1, 2]
START = time.monotonic()
LAST_PRESSURE = 0.
FITS = 0
AUDIT = []


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, value):
    temporary = (HERE / name).with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    temporary.replace(HERE / name)


def guard():
    global LAST_PRESSURE
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if sys.platform == 'darwin' else 1024)
    if time.monotonic() - START >= 1800 or rss >= 1024**3 or (HERE / 'STOP').exists():
        raise RuntimeError('1800-second/1-GiB/STOP limit; no partial winner or automatic retry')
    if time.monotonic() - LAST_PRESSURE >= 1:
        p = subprocess.run(['/usr/sbin/sysctl', '-n', 'kern.memorystatus_vm_pressure_level'],
                           capture_output=True, text=True, check=True, timeout=3)
        LAST_PRESSURE = time.monotonic()
        if int(p.stdout.strip()) != 1:
            raise RuntimeError('Memory pressure is not normal; no automatic retry')


def deadline(*_):
    raise RuntimeError('Study wall deadline reached; no automatic retry')


def fold_map(groups, n, salt):
    ordered = sorted(set(groups), key=lambda g: (hashlib.sha256((salt + ':' + str(g)).encode()).hexdigest(), str(g)))
    return {g: i % n for i, g in enumerate(ordered)}


def metrics(pred, truth, easy):
    tp, fp = int((pred & truth).sum()), int((pred & ~truth).sum())
    return dict(TP=tp, FN=int((~pred & truth).sum()), FP=fp, TN=int((~pred & ~truth).sum()),
                recall=tp / int(truth.sum()),
                wrong_fraction_of_awards=fp / (tp + fp) if tp + fp else None,
                hard_ordinary_FP=int((pred & ~truth & ~easy).sum()),
                easy_error_FP=int((pred & easy).sum()))


def threshold(scores, truth, gates, easy, reference):
    order = np.argsort(-scores, kind='stable')
    vals, yy, valid = scores[order], truth[order], gates[order]
    tp, fp = np.cumsum(valid & yy), np.cumsum(valid & ~yy)
    ends = np.r_[np.flatnonzero(vals[:-1] != vals[1:]), len(vals) - 1]
    feasible = [int(j) for j in ends if tp[j] > 0 and fp[j] <= reference['FP']
                and fp[j] * reference['TP'] <= reference['FP'] * tp[j]]
    cut = float(vals[max(feasible, key=lambda j: (int(tp[j]), -int(fp[j]), float(vals[j])))]) if feasible else 1.0000001
    return dict(threshold=cut, **metrics((scores >= cut) & gates, truth, easy))


def fit_network(x, y, weights, seed, epochs):
    model = MLPClassifier(**CONFIG, random_state=np.random.RandomState(seed))
    assert set(np.unique(y)) == {False, True}
    optimizer_id = None
    for _ in range(epochs):
        guard()
        model.partial_fit(x, y, classes=np.array([False, True]), sample_weight=weights)
        if optimizer_id is None:
            optimizer_id = id(model._optimizer)
        assert id(model._optimizer) == optimizer_id
    assert len(model.loss_curve_) == epochs and model.t_ == epochs * len(y)
    assert np.isfinite(model.loss_curve_).all()
    return model


def export_model(imputer, scaler, models, names):
    return dict(features=names, medians=imputer.statistics_.tolist(),
                means=scaler.mean_.tolist(), scales=scaler.scale_.tolist(),
                networks=[dict(weights=[w.tolist() for w in model.coefs_],
                               biases=[b.tolist() for b in model.intercepts_]) for model in models],
                activation='relu', output='sigmoid', aggregation='mean seeds per window, then minimum of both windows')


def infer_export(model, raw):
    z = np.where(np.isnan(raw), np.asarray(model['medians']), raw)
    z = (z - np.asarray(model['means'])) / np.asarray(model['scales'])
    out = []
    for network in model['networks']:
        a = z
        for layer, (w, b) in enumerate(zip(network['weights'], network['biases'])):
            a = a @ np.asarray(w) + np.asarray(b)
            a = np.maximum(0, a) if layer < 2 else expit(a)
        out.append(a[:, 0])
    return np.mean(out, axis=0)


def self_check():
    rng = np.random.RandomState(17)
    raw = rng.normal(size=(320, 75))
    y = raw[:, 0] > 0
    raw[:, 4] = np.nan
    x = np.column_stack([raw, np.isnan(raw).astype(float)])
    imputer = SimpleImputer(strategy='median', keep_empty_features=True).fit(x[:256])
    assert imputer.statistics_[4] == 0 and len(imputer.statistics_) == 150
    scaler = StandardScaler().fit(imputer.transform(x[:256]))
    original_mean = scaler.mean_.copy()
    scaler.transform(imputer.transform(x[256:] * 10000))
    assert np.array_equal(original_mean, scaler.mean_)
    z = scaler.transform(imputer.transform(x[:256]))
    models = [fit_network(z, y[:256], np.linspace(.5, 1.5, 256), n, 30) for n in [9, 10]]
    assert all(m.loss_curve_[-1] < m.loss_curve_[0] for m in models)
    saved = json.loads(json.dumps(export_model(imputer, scaler, models, [str(i) for i in range(150)])))
    expected = np.mean([m.predict_proba(scaler.transform(imputer.transform(x)))[:, 1] for m in models], axis=0)
    assert np.max(np.abs(expected - infer_export(saved, x))) < 1e-12
    t = threshold(np.array([.9, .9, .8]), np.array([True, False, True]),
                  np.ones(3, bool), np.zeros(3, bool), {'TP': 1, 'FP': 0})
    assert t['TP'] == t['FP'] == 0  # Tied positive/negative scores cannot be split.
    toy = np.array([[[.9, .2], [.1, .8]], [[.3, .6], [.7, .4]], [[.6, .4], [.4, .6]]])
    assert np.allclose(toy.mean(axis=0).min(axis=1), [.4, .4])
    write('PREP-CHECKS.json', dict(passed=True, scope='Synthetic only; no real labels or fits',
          checks=['150-column all-missing imputation preserved', 'training-only scaling',
                  'persistent Adam optimizer and exact epoch/sample counters', 'finite decreasing synthetic loss',
                  'JSON inference matches sklearn within1e-12', 'threshold ties cannot leak labels',
                  'seed mean precedes window minimum'], script_sha256=sha(Path(__file__))))
    print('Synthetic preparation checks passed', flush=True)


def main():
    global FITS
    protocol = json.loads((HERE / 'PROTOCOL.json').read_text())
    assert not any((HERE / n).exists() for n in ['RESULTS.json', 'STOPPED.json', 'RUNNING.json'])
    assert sha(Path(__file__)) == protocol['script_sha256']
    assert sha(INPUT) == protocol['input_sha256']
    for name, digest in protocol['reference_hashes'].items():
        assert sha(REFERENCE / name) == digest
    assert list(CONFIG['hidden_layer_sizes']) == protocol['network']['hidden_layers']
    assert EPOCHS == protocol['network']['epochs'] and SEEDS == protocol['network']['starting_seeds']
    assert [np.__version__, scipy.__version__, sklearn.__version__] == protocol['versions']
    assert json.loads((HERE / 'PREP-CHECKS.json').read_text())['script_sha256'] == sha(Path(__file__))
    signal.signal(signal.SIGALRM, deadline)
    signal.alarm(1800)
    guard()
    write('RUNNING.json', dict(pid=os.getpid(), started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                              protocol_sha256=sha(HERE / 'PROTOCOL.json')))
    data = json.loads(INPUT.read_text())
    cases, base = data['cases'], data['predictors']
    assert len(cases) == 3724 and len(base) == 75
    names = base + [n + '__missing' for n in base]
    windows = [c['windows'][w] for c in cases for w in ['current', 'previous']]
    assert all(set(w['features']) == set(base) for w in windows)
    x = np.asarray([[float(w['features'][n]) if w['features'][n] is not None else np.nan for n in base]
                    + [float(w['features'][n] is None) for n in base] for w in windows])
    assert not np.isinf(x).any()
    truth = np.array([c['truth'] for c in cases], dtype=bool)
    easy = ~truth & np.array([c['negative_bucket'] == 'easy_error' for c in cases])
    y = np.repeat(truth, 2)
    eligible = np.array([w['eligible'] for w in windows], dtype=bool)
    gates = eligible.reshape(-1, 2).all(axis=1) & np.array([c['confidence_sufficient'] for c in cases])
    gates &= ~np.array([any(c['windows'][w]['features']['physical_unknown'] for w in ['current', 'previous']) for c in cases])
    ids = np.repeat(np.arange(len(cases)), 2)
    n_windows = np.bincount(ids[eligible], minlength=len(cases))
    weights = 1 / np.maximum(1, n_windows[ids])
    assert np.allclose(np.bincount(ids[eligible], weights=weights[eligible], minlength=len(cases))[n_windows > 0], 1)
    groups = [c['group'] for c in cases]
    group_order = sorted(set(groups))
    assert truth.sum() == 917 and len(group_order) == 972 and gates.sum() == 1302
    game_groups, position_groups = {}, {}
    for c in cases:
        for game in {c['game_id']} | {k.rsplit(':', 1)[0] for k in c.get('aliases', [])}:
            assert game_groups.setdefault(game, c['group']) == c['group']
        assert position_groups.setdefault(' '.join(c['fen_before'].split()[:4]), c['group']) == c['group']
    outer_map = fold_map(groups, 5, 'mute-optimization-v1-outer')
    final_map = fold_map(groups, 5, 'mute-optimization-v1-final')
    outer = np.array([outer_map[g] for g in groups])
    final = np.array([final_map[g] for g in groups])
    reference = json.loads((REFERENCE / 'RESULTS.json').read_text())
    cached = json.loads((REFERENCE / 'PREDICTIONS.json').read_text())
    assert reference['input_sha256'] == sha(INPUT) and len(cached) == len(cases)
    assert sha(REFERENCE / 'PROTOCOL.json') == reference['protocol_sha256']
    assert sha(REFERENCE / 'experiment.py') == reference['script_sha256']
    baseline = {a: np.array([r['outer_awards'][a] for r in cached]) for a in ['custom_fixed', 'custom_retuned', 'standard_rf']}
    for i, (c, r) in enumerate(zip(cases, cached)):
        assert (c['key'], c['group'], c['truth'], bool(gates[i]), int(outer[i]), int(final[i])) == (
            r['key'], r['group'], r['truth'], r['eligible'], r['outer_fold'], r['final_calibration_fold'])
        assert baseline['custom_fixed'][i] == bool(gates[i] and r['outer_scores']['custom'] >= 5/6)
    for a, pred in baseline.items():
        m = metrics(pred, truth, easy)
        assert all(m[k] == reference['outer_pooled'][a][k] for k in ['TP', 'FP', 'FN', 'TN'])
    print(json.dumps(dict(stage='inputs_and_cached_reference_verified', cases=len(cases), groups=len(group_order))), flush=True)

    def fit(ti, vi, seed_parts, keep=False):
        global FITS
        guard()
        assert not set(groups[i] for i in ti) & set(groups[i] for i in vi)
        train = np.flatnonzero(eligible & np.repeat(np.isin(np.arange(len(cases)), ti), 2))
        test = np.ravel(np.column_stack([2 * vi, 2 * vi + 1]))
        assert set(ids[train]) <= set(ti) and not set(ids[train]) & set(vi)
        imputer = SimpleImputer(strategy='median', keep_empty_features=True).fit(x[train])
        filled = imputer.transform(x[train])
        scaler = StandardScaler().fit(filled, sample_weight=weights[train])
        z = scaler.transform(filled)
        ztest = scaler.transform(imputer.transform(x[test])) if len(test) else np.empty((0, 150))
        predictions, models = [], []
        for starting in SEEDS:
            guard()
            start = time.monotonic()
            seed = int(np.random.SeedSequence([20261105, *seed_parts, starting]).generate_state(1)[0])
            model = fit_network(z, y[train], weights[train], seed, EPOCHS)
            pred = model.predict_proba(ztest)[:, 1] if len(test) else np.array([])
            assert np.isfinite(pred).all() and ((pred >= 0) & (pred <= 1)).all()
            predictions.append(pred.reshape(-1, 2))
            models.append(model)
            FITS += 1
            AUDIT.append(dict(seed_parts=seed_parts, starting=starting, epochs=EPOCHS, training_cases=len(ti),
                              training_groups=len({groups[i] for i in ti}), eligible_window_rows=len(train),
                              first_loss=model.loss_curve_[0], last_loss=model.loss_curve_[-1],
                              seconds=time.monotonic() - start))
            if FITS == 1:
                print(json.dumps(dict(stage='first_required_fit_timed', seconds=time.monotonic() - start)), flush=True)
            guard()
        scores = np.array(predictions)
        exported = export_model(imputer, scaler, models, names) if keep else None
        if keep:
            check = x[:64]
            transformed = scaler.transform(imputer.transform(check))
            expected = np.mean([m.predict_proba(transformed)[:, 1] for m in models], axis=0)
            assert np.max(np.abs(infer_export(exported, check) - expected)) < 1e-12
        return scores, exported

    all_cases = np.arange(len(cases))
    scores = np.full((3, len(cases), 2), np.nan)
    predicted = np.zeros(len(cases), bool)
    seed_predicted = np.zeros((3, len(cases)), bool)
    records = []
    for fold in range(5):
        ti, vi = all_cases[outer != fold], all_cases[outer == fold]
        ref_fold = reference['outer_folds'][fold]
        assert ref_fold['fold'] == fold and ref_fold['test_keys'] == [cases[i]['key'] for i in vi]
        imap = fold_map([groups[i] for i in ti], 3, 'mute-optimization-v1-inner-' + str(fold))
        inner = np.array([imap[groups[i]] for i in ti])
        inner_scores = np.full((3, len(ti), 2), np.nan)
        for infold in range(3):
            it, iv = ti[inner != infold], ti[inner == infold]
            inner_scores[:, inner == infold, :], _ = fit(it, iv, [10, fold, infold])
        assert np.isfinite(inner_scores).all()
        ref = ref_fold['inner_selection']['points']['custom_fixed']
        chosen = threshold(inner_scores.mean(axis=0).min(axis=1), truth[ti], gates[ti], easy[ti], ref)
        seed_chosen = [threshold(s.min(axis=1), truth[ti], gates[ti], easy[ti], ref) for s in inner_scores]
        scores[:, vi, :], _ = fit(ti, vi, [20, fold])
        predicted[vi] = (scores[:, vi, :].mean(axis=0).min(axis=1) >= chosen['threshold']) & gates[vi]
        for j in SEEDS:
            seed_predicted[j, vi] = (scores[j, vi, :].min(axis=1) >= seed_chosen[j]['threshold']) & gates[vi]
        record = dict(fold=fold, inner_reference=ref, inner_selection=chosen, seed_selections=seed_chosen,
                      metrics=metrics(predicted[vi], truth[vi], easy[vi]), test_keys=[cases[i]['key'] for i in vi])
        records.append(record)
        write('PROGRESS.json', dict(completed_outer_folds=fold + 1, fits=FITS, seconds=time.monotonic() - START))
        print(json.dumps(dict(stage='outer_fold', fold=fold, metrics=record['metrics'], seconds=round(time.monotonic() - START, 1))), flush=True)

    calibration = np.full_like(scores, np.nan)
    for fold in range(5):
        ti, vi = all_cases[final != fold], all_cases[final == fold]
        calibration[:, vi, :], _ = fit(ti, vi, [30, fold])
    assert np.isfinite(scores).all() and np.isfinite(calibration).all()
    ref_final = reference['final_training_only_selection']['points']['custom_fixed']
    selection = threshold(calibration.mean(axis=0).min(axis=1), truth, gates, easy, ref_final)
    write('SELECTION-FREEZE.json', dict(scope='Training-only calibration; no assessment replay or promotion',
          selected=selection, protocol_sha256=sha(HERE / 'PROTOCOL.json'), input_sha256=sha(INPUT)))
    _, model = fit(all_cases, np.array([], dtype=int), [5], keep=True)
    model['threshold_both_windows'] = selection['threshold']
    model['status'] = 'experimental; chess guards required; not a browser release artifact'
    write('model.json', model)
    loaded = json.loads((HERE / 'model.json').read_text())
    # Verify JSON remains finite and scores identically after serialization.
    raw = x[:64]
    assert np.max(np.abs(infer_export(model, raw) - infer_export(loaded, raw))) < 1e-12
    write('MODEL-FREEZE.json', dict(model_sha256=sha(HERE / 'model.json'),
          selection_sha256=sha(HERE / 'SELECTION-FREEZE.json'), script_sha256=sha(Path(__file__)),
          protocol_sha256=sha(HERE / 'PROTOCOL.json'), input_sha256=sha(INPUT)))
    comparisons = {a: metrics(p, truth, easy) for a, p in baseline.items()}
    comparisons['neural_ensemble'] = metrics(predicted, truth, easy)
    write('PREDICTIONS.json', [dict(key=c['key'], group=c['group'], truth=c['truth'], eligible=bool(gates[i]),
          outer_fold=int(outer[i]), final_fold=int(final[i]), seed_window_scores=scores[:, i, :].tolist(),
          calibration_seed_window_scores=calibration[:, i, :].tolist(), neural_award=bool(predicted[i]),
          seed_awards=seed_predicted[:, i].tolist(), baseline_awards={a: bool(v[i]) for a, v in baseline.items()})
          for i, c in enumerate(cases)])
    write('TRAINING-AUDIT.json', AUDIT)
    guard()
    write('RESULTS.json', dict(scope='Accumulated development data; no new independent test or deployment claim',
          counts=dict(cases=3724, brilliant=917, negatives=2807, non_easy_negatives=2477, easy_errors=330,
                      groups=972, eligible_both=1302), outer_pooled=comparisons, outer_folds=records,
          seed_diagnostics=[metrics(p, truth, easy) for p in seed_predicted],
          final_training_only_selection=selection, fits=FITS, elapsed_seconds=time.monotonic() - START,
          peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if sys.platform == 'darwin' else 1024),
          reference_reused='Frozen identical-data/fold outputs; not refitted in this experiment',
          input_sha256=sha(INPUT), script_sha256=sha(Path(__file__)), protocol_sha256=sha(HERE / 'PROTOCOL.json'),
          seed_results_are_not_selection=True, reserved_games_loaded=False))
    guard()
    write('COMPLETE.json', dict(status='complete', results_sha256=sha(HERE / 'RESULTS.json'),
                               model_sha256=sha(HERE / 'model.json')))
    (HERE / 'RUNNING.json').unlink()
    print(json.dumps(dict(stage='complete', results=comparisons, fits=FITS, seconds=time.monotonic() - START)), flush=True)


if __name__ == '__main__':
    with threadpool_limits(limits=1):
        if sys.argv[1:] == ['--check']:
            self_check()
        else:
            try:
                main()
            except Exception as error:
                write('STOPPED.json', dict(reason=str(error), no_automatic_retry=True, no_partial_winner=True))
                (HERE / 'RUNNING.json').unlink(missing_ok=True)
                (HERE / 'model.json').unlink(missing_ok=True)
                (HERE / 'MODEL-FREEZE.json').unlink(missing_ok=True)
                raise
            finally:
                signal.alarm(0)
