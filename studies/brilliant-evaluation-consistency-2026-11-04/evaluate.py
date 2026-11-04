"""One frozen gate ablation on saved grouped OOF predictions. No fitting/search."""
import hashlib, json, math, sys
from collections import Counter
from pathlib import Path
import numpy as np
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
WORK = HERE.parents[1]
OLD = WORK/'research/brilliant-standard-learners-2026-11-04'
TRAIN = WORK/'mute-chess-research-overnight-2026-11-03/studies/brilliant-training-2026-11-03/data/training.json'

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def write(name, value):
    (HERE/name).write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')

def finite(value):
    return isinstance(value,(int,float)) and math.isfinite(value)

def wc(value):
    return 100/(1+math.exp(-.00368208*value))

def window_reasons(f, loss):
    reasons=[]
    if not f['window_complete']: reasons.append('incomplete_window')
    if f['before_roots']<2: reasons.append('fewer_than_two_roots')
    if not f['raw_offer']: reasons.append('no_raw_offer')
    if not finite(loss) or loss>5: reasons.append('quality')
    if not finite(f['after_mapped_score']) or f['after_mapped_score'] < -100: reasons.append('after_floor')
    return reasons

def metrics(rows, field):
    tp=sum(r['truth'] and r[field] for r in rows)
    fp=sum(not r['truth'] and r[field] for r in rows)
    positive=sum(r['truth'] for r in rows)
    return dict(TP=tp,FP=fp,FN=positive-tp,TN=len(rows)-positive-fp,
                recall=tp/positive if positive else None,
                wrong_fraction_of_awards=fp/(tp+fp) if tp+fp else None)

def audit(rows, arm):
    counts=Counter(); overlapping=Counter(); gate_combinations=Counter(); gaps=Counter()
    for r in rows:
        if not r['truth'] or r[arm+'_baseline']: continue
        gate=bool(r['old_reasons']); score=r['score']>=r[arm+'_threshold']
        counts['gates_only' if gate and score else 'gates_and_score' if gate else 'score_only']+=1
        overlapping.update(set(r['old_reasons']))
        if gate: gate_combinations[' + '.join(r['old_reasons'])]+=1
        if not score:
            gap=r[arm+'_threshold']-r['score']
            bucket='(0,.025]' if gap<=.025 else '(.025,.05]' if gap<=.05 else '(.05,.10]' if gap<=.10 else '>.10'
            gaps[bucket]+=1
    return dict(misses=sum(counts.values()),exclusive_blockers=dict(counts),overlapping_failed_gates=dict(overlapping),
                failed_gate_combinations=dict(gate_combinations),score_shortfall_buckets=dict(gaps))

def main():
    protocol=json.loads((HERE/'PROTOCOL.json').read_text())
    assert not (HERE/'RESULTS.json').exists(), 'No outcome-driven reruns'
    assert sha(Path(__file__))==protocol['script_sha256']
    assert all(sha(path)==value for path,value in protocol['input_sha256'].items())
    data=json.loads(TRAIN.read_text()); saved=json.loads((OLD/'PREDICTIONS.json').read_text())
    oldresults=json.loads((OLD/'RESULTS.json').read_text())
    preds={r['key']:r for r in saved}; folds={r['fold']:r for r in oldresults['outer_folds']}
    assert len(data['cases'])==len(preds)==3724
    groups=sorted({c['group'] for c in data['cases']})
    ordered=sorted(groups,key=lambda g:(hashlib.sha256(('mute-optimization-v1-outer:'+str(g)).encode()).hexdigest(),str(g)))
    fold_map={g:i%5 for i,g in enumerate(ordered)}
    game_groups={}; position_groups={};rows=[]
    for c in data['cases']:
        p=preds[c['key']]
        assert c['truth']==p['truth'] and c['group']==p['group'] and fold_map[c['group']]==p['outer_fold']
        for game in {c['game_id']}|{a.rsplit(':',1)[0] for a in c.get('aliases',[])}:
            assert game_groups.setdefault(game,c['group'])==c['group']
        position=' '.join(c['fen_before'].split()[:4])
        assert position_groups.setdefault(position,c['group'])==c['group']
        fs={w:c['windows'][w]['features'] for w in ('current','previous')}
        same_available=all(f['window_complete'] and not f['played_root_missing']
                           and finite(f['same_root_loss_pp']) and finite(f['best_mapped_score'])
                           and finite(f['played_root_mapped_score']) for f in fs.values())
        old_reasons=set();new_reasons=set();windows={}
        for w,f in fs.items():
            old=window_reasons(f,f['mapped_loss_pp'])
            assert (not old)==c['windows'][w]['eligible'], (c['key'],w,old)
            if finite(f['mapped_loss_pp']):
                assert abs(f['mapped_loss_pp']-(wc(f['best_mapped_score'])-wc(f['after_mapped_score'])))<1e-9
            if finite(f['same_root_loss_pp']):
                assert abs(f['same_root_loss_pp']-(wc(f['best_mapped_score'])-wc(f['played_root_mapped_score'])))<1e-9
            newloss=f['same_root_loss_pp'] if same_available else f['mapped_loss_pp']
            new=window_reasons(f,newloss)
            old_reasons.update(old);new_reasons.update(new)
            windows[w]=dict(old_loss_pp=f['mapped_loss_pp'],same_root_loss_pp=f['same_root_loss_pp'],
                            used_loss_pp=newloss,old_reasons=old,new_reasons=new,
                            best_mapped_score=f['best_mapped_score'],after_mapped_score=f['after_mapped_score'],
                            played_root_mapped_score=f['played_root_mapped_score'],same_root_rank=f['same_root_rank'])
        for reason,failed in [('confidence',not c['confidence_sufficient']),
                             ('physical_unknown',any(f['physical_unknown'] for f in fs.values()))]:
            if failed: old_reasons.add(reason);new_reasons.add(reason)
        assert (not old_reasons)==p['eligible']
        row=dict(key=c['key'],group=c['group'],outer_fold=p['outer_fold'],truth=c['truth'],
                 negative_bucket=c['negative_bucket'],cohort=c['cohort'],fen_before=c['fen_before'],uci=c['uci'],
                 score=p['outer_scores']['custom'],same_root_pair_available=same_available,
                 old_reasons=sorted(old_reasons),new_reasons=sorted(new_reasons),windows=windows)
        for arm,priorarm in [('retuned','custom_retuned'),('fixed','custom_fixed')]:
            threshold=folds[p['outer_fold']]['inner_selection']['points'][priorarm]['threshold']
            row[arm+'_threshold']=threshold
            row[arm+'_baseline']=bool(not old_reasons and row['score']>=threshold)
            row[arm+'_consistent']=bool(not new_reasons and row['score']>=threshold)
            assert row[arm+'_baseline']==p['outer_awards'][priorarm]
        rows.append(row)
    assert len(groups)==972 and sum(r['truth'] for r in rows)==917
    results=dict(scope=protocol['purpose'],protocol_sha256=sha(HERE/'PROTOCOL.json'),script_sha256=sha(Path(__file__)),
                 input_sha256=protocol['input_sha256'],counts=dict(cases=3724,positive=917,negative=2807,groups=972),
                 fixed_forest='Exact saved group-held-out custom scores; no fitting, rescoring, feature edits, or threshold selection.',
                 comparisons={},miss_audits={},gate_audit={},outer_folds=[],fits=0,engine_queries=0)
    for arm,priorarm in [('retuned','custom_retuned'),('fixed','custom_fixed')]:
        old=metrics(rows,arm+'_baseline');new=metrics(rows,arm+'_consistent')
        for k,v in old.items(): assert v==oldresults['outer_pooled'][priorarm][k],(k,v)
        changes=[r for r in rows if r[arm+'_baseline']!=r[arm+'_consistent']]
        results['comparisons'][arm]=dict(baseline=old,consistent=new,
            gained_true=[r['key'] for r in changes if r['truth'] and r[arm+'_consistent']],
            lost_true=[r['key'] for r in changes if r['truth'] and r[arm+'_baseline']],
            gained_wrong=[r['key'] for r in changes if not r['truth'] and r[arm+'_consistent']],
            removed_wrong=[r['key'] for r in changes if not r['truth'] and r[arm+'_baseline']],
            observed_success=new['TP']>old['TP'] and new['FP']<=old['FP'] and
              new['FP']*old['TP']<=old['FP']*new['TP'])
        results['miss_audits'][arm]=audit(rows,arm)
    for truth,name in [(True,'positives'),(False,'negatives')]:
        subset=[r for r in rows if r['truth']==truth]
        states=Counter(('pass' if not r['old_reasons'] else 'fail')+'->'+('pass' if not r['new_reasons'] else 'fail') for r in subset)
        reasons=Counter(reason for r in subset for reason in r['old_reasons'])
        results['gate_audit'][name]=dict(total=len(subset),same_root_pair_available=sum(r['same_root_pair_available'] for r in subset),
                                       transitions=dict(states),overlapping_original_failures=dict(reasons))
    for fold in range(5):
        subset=[r for r in rows if r['outer_fold']==fold]
        results['outer_folds'].append(dict(fold=fold,groups=len({r['group'] for r in subset}),
            metrics={a:metrics(subset,a) for a in ('retuned_baseline','retuned_consistent','fixed_baseline','fixed_consistent')}))
    rng=np.random.default_rng(20261104);gi={g:i for i,g in enumerate(groups)}
    ix=np.array([gi[r['group']] for r in rows]);truth=np.array([r['truth'] for r in rows]);pos=np.bincount(ix,weights=truth,minlength=len(groups))
    intervals={}
    for arm in ('retuned','fixed'):
        before=np.array([r[arm+'_baseline'] for r in rows]);after=np.array([r[arm+'_consistent'] for r in rows])
        dt=np.bincount(ix,weights=(after&truth).astype(int)-(before&truth).astype(int),minlength=len(groups))
        df=np.bincount(ix,weights=(after&~truth).astype(int)-(before&~truth).astype(int),minlength=len(groups))
        samples=[]
        for _ in range(2000):
            draw=np.bincount(rng.integers(0,len(groups),len(groups)),minlength=len(groups))
            samples.append([100*float(draw@dt)/float(draw@pos),float(draw@df)])
        q=np.quantile(samples,[.025,.975],axis=0)
        intervals[arm]=dict(recall_delta_percentage_points=q[:,0].tolist(),wrong_award_count_delta=q[:,1].tolist())
    results['conditional_group_bootstrap_95_percentile']=intervals
    results['limits']=[
        'Reused development data and hypotheses; grouped OOF isolation does not restore an untouched research test.',
        'Newly eligible examples were excluded by the original training eligibility policy; fixed-score results probe this selection shift.',
        'Forest inputs retain original measurements, including mapped_loss_pp and same_root_loss_pp. Only the external quality gate changes.',
        'Original after_floor, raw_offer, two_roots, confidence and physical-unknown policies remain; this is not a replacement of every evaluation-based condition.',
        'Both root scores are required in both windows. Missing pairs use the entire original gate policy, not a favorable mixed comparison.',
        'Same-search values can still be shallow or inaccurate. No deeper search or engine calibration has been tested.',
        'Bootstrap conditions on frozen predictions and omits model fitting and repeated research uncertainty; zero observed error change is no future guarantee.',
        'Sample is enriched; no representative live-site precision or recall claim. No fresh prospective confirmation or deployment.'
    ]
    write('PREDICTIONS.json',rows);write('RESULTS.json',results)
    print(json.dumps({k:results[k] for k in ('comparisons','miss_audits','gate_audit','conditional_group_bootstrap_95_percentile')},indent=2))

if __name__=='__main__': main()
