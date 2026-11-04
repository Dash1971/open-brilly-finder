"""One fixed, label-independent immediate-mating-offer rule."""
import math

def window_rule(window):
    f = window['features']
    required = ['prior_offer_gain_same_square_max', 'prior_offer_gain_original_square_max',
                'same_root_rank', 'best_second_gap_pp', 'best_mapped_score', 'prior_mapped_score']
    if not window['eligible'] or any(f.get(n) is None or not math.isfinite(f[n]) for n in required):
        return False
    if any(f.get(n) is not False for n in ['ec_sacrifice', 'physical_unknown', 'prior_history_missing', 'attribution_unknown']):
        return False
    if f.get('mating_acceptance') is not True:
        return False
    wc = lambda s: 100 / (1 + math.exp(-0.00368208 * max(-1000, min(1000, s))))
    return (f['prior_offer_gain_same_square_max'] == 0
            and f['prior_offer_gain_original_square_max'] == 0
            and f['same_root_rank'] == 1 and f['best_second_gap_pp'] > 10
            and wc(f['best_mapped_score']) - wc(f['prior_mapped_score']) > 5)

def mating_rule(case):
    return bool(case['confidence_sufficient'] and all(window_rule(case['windows'][w]) for w in ['current','previous']))
