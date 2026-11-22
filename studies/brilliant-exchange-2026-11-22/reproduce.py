#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Recount this study's held-out results and rescore the parity cases. Python 3 standard library only."""
import csv, hashlib, json, math
from pathlib import Path
P = Path(__file__).resolve().parent
MODEL_SHA = '992a792a646b11e612486c4fe26796fc38ee47f395f2220b00d26db65ba1e27d'


def score(model, x):
    raw = model['baseline']
    for t in model['trees']:
        i = 0
        while not t['leaf'][i]:
            i = t['l'][i] if x[t['f'][i]] <= t['t'][i] else t['r'][i]
        raw += t['v'][i]
    return 1 / (1 + math.exp(-raw))


def main():
    blob = (P / 'model/mute-exchange-model.json').read_bytes()
    assert hashlib.sha256(blob).hexdigest() == MODEL_SHA, 'model file changed'
    model = json.loads(blob)
    rows = list(csv.DictReader(open(P / 'data/heldout-outcomes.csv')))
    games = {r['game_id'] for r in rows}
    gallery = sum(r['gallery_brilliant'] == '1' for r in rows)

    def count(pred):
        a = [r for r in rows if pred(r)]
        false = [r for r in a if r['gallery_brilliant'] != '1']
        return dict(awards=len(a), found=len(a) - len(false), false_vs_gallery=len(false),
                    false_by_todays_review_too=sum(r['chesscom_review_today'] != 'brilliant' for r in false))
    out = dict(games=len(games), gallery_brilliants=gallery,
               mute_selective=count(lambda r: r['mute_selective'] == '1'),
               mute_exchange=count(lambda r: r['exchange_brilliant'] == '1'))
    assert out['mute_selective'] == dict(awards=274, found=259, false_vs_gallery=15, false_by_todays_review_too=12), out
    assert out['mute_exchange'] == dict(awards=316, found=298, false_vs_gallery=18, false_by_todays_review_too=11), out
    assert (out['games'], gallery) == (337, 416), out
    fx = json.loads((P / 'model/parity-fixtures.json').read_text())
    worst = 0.0
    for c in fx['cases']:
        s = score(model, [float(c['features'][k]) for k in model['features']])
        worst = max(worst, abs(s - c['score']))
        assert (s >= model['cutoff']) == (c['score'] >= fx['cutoff'])
    assert worst < 1e-9, worst
    out['parity_cases_rescored'] = len(fx['cases'])
    print(json.dumps(dict(PASS=True, **out), indent=2))


if __name__ == '__main__':
    main()
