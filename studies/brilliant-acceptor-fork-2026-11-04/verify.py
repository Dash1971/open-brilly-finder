"""Independent checks of frozen artifacts and all held-out decisions; no refits."""
import hashlib,json,math
from pathlib import Path
H=Path(__file__).resolve().parent;W=H.parents[1]
def load(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def metric(rows,a):
    tp=sum(r['truth'] and r['outer_awards'][a] for r in rows);fp=sum(not r['truth'] and r['outer_awards'][a] for r in rows)
    pos=sum(r['truth'] for r in rows)
    return dict(TP=tp,FP=fp,FN=pos-tp,TN=len(rows)-pos-fp,recall=tp/pos if pos else None,
                precision=tp/(tp+fp) if tp+fp else None,wrong_fraction_of_awards=fp/(tp+fp) if tp+fp else None)
def main():
    p=load(H/'EVAL-PROTOCOL.json');r=load(H/'RESULTS.json');rows=load(H/'PREDICTIONS.json');features=load(H/'FEATURES.json')
    e=load(H/'EXTRACTION.json');ep=load(H/'EXTRACTION-PROTOCOL.json')
    train=W/'mute-chess-research-overnight-2026-11-03/studies/brilliant-training-2026-11-03/data/training.json'
    cs={c['key']:c for c in load(train)['cases']};old={x['key']:x for x in load(W/'research/brilliant-standard-learners-2026-11-04/PREDICTIONS.json')}
    assert all(sha(W/k)==v for k,v in p['source_sha256'].items())
    assert all(sha(k)==v for k,v in ep['input_sha256'].items())
    assert all(sha(k)==v for k,v in ep['dependency_sha256'].items())
    assert sha(H/'extract.py')==ep['script_sha256']==e['script_sha256']
    assert sha(H/'EXTRACTION-PROTOCOL.json')==e['protocol_sha256']
    assert sha(H/'evaluate.py')==p['script_sha256']==r['script_sha256']
    assert sha(H/'EVAL-PROTOCOL.json')==r['protocol_sha256']
    assert sha(H/'FEATURES.json')==p['feature_sha256']==r['feature_sha256']==e['feature_sha256']
    assert sha(H/'EXTRACTION.json')==p['extraction_sha256']==r['extraction_sha256']
    assert sha(H/'FEATURE-EVIDENCE.json')==e['evidence_sha256']
    assert sha(train)==r['input_sha256']==e['input_sha256']
    groups=sorted({c['group'] for c in cs.values()},key=lambda g:(hashlib.sha256(('mute-optimization-v1-outer:'+g).encode()).hexdigest(),g))
    fmap={g:i%5 for i,g in enumerate(groups)};gamegroups={};positions={};folds={f['fold']:f for f in r['outer_folds']}
    arms=list(r['outer_pooled']);panel=load(W/'research/brilliant-forest-miss-diagnosis-2026-11-04/PANEL.json')
    panelgroups={x[k]['group'] for x in panel for k in ('miss','ordinary')}
    assert len(rows)==len(cs)==3724 and len(groups)==972 and len(panelgroups)==24
    assert len({x['key'] for x in rows})==3724
    original_miss=known=0
    for x in rows:
        c=cs[x['key']];o=old[x['key']]
        assert x['truth']==c['truth'] and x['group']==c['group'] and x['outer_fold']==fmap[c['group']]==o['outer_fold']
        for gid in {c['game_id']}|{a.rsplit(':',1)[0] for a in c['aliases']}:assert gamegroups.setdefault(gid,c['group'])==c['group']
        pos=' '.join(c['fen_before'].split()[:4]);assert positions.setdefault(pos,c['group'])==c['group']
        gate=all(w['eligible'] and not w['features']['physical_unknown'] for w in c['windows'].values()) and c['confidence_sufficient']
        assert gate==x['eligible']==o['eligible']
        assert x['added_features']==features[x['key']]
        assert x['hypothesis_panel_group']==(c['group'] in panelgroups)
        anyeligible=any(w['eligible'] for w in c['windows'].values())
        for w in ('current','previous'):
            assert set(features[x['key']][w])=={'acceptor_fork','reply_check'}
            assert all((type(v) is bool) if anyeligible else v is None for v in features[x['key']][w].values())
        known+=anyeligible
        target=gate and x['truth'] and not o['outer_awards']['custom_retuned']
        assert x['original_429_miss']==target;original_miss+=target
        for kind in ('custom','standard_rf'):assert abs(x['outer_scores'][kind+'_original']-o['outer_scores'][kind])<=1e-12
        for a in ('custom_fixed','custom_retuned','standard_rf'):assert x['outer_awards'][a]==o['outer_awards'][a]
        for a in arms:
            point=folds[x['outer_fold']]['inner_selection']['points'][a];score=x['outer_scores'][point['kind']]
            assert math.isfinite(score) and 0<=score<=1
            assert x['outer_awards'][a]==bool(gate and score>=point['threshold'])
    assert original_miss==429 and known==1320
    for a in arms:
        for k,v in metric(rows,a).items():assert r['outer_pooled'][a][k]==v
    for f,fr in folds.items():
        subset=[x for x in rows if x['outer_fold']==f];assert {x['key'] for x in subset}==set(fr['test_keys'])
        for a in arms:
            for k,v in metric(subset,a).items():assert fr['test_metrics'][a][k]==v
        points=fr['inner_selection']['points'];ref=points['custom_fixed']
        for a,point in points.items():
            if a.endswith('_fixed'):continue
            assert point['FP']<=ref['FP'] and point['FP']*ref['TP']<=ref['FP']*point['TP']
    excluded=r['hypothesis_panel_groups_excluded_outer_report'];subset=[x for x in rows if not x['hypothesis_panel_group']]
    assert set(excluded['excluded_groups'])==panelgroups and excluded['remaining_cases']==len(subset)
    for a in arms:
        for k,v in metric(subset,a).items():assert excluded['outer_pooled'][a][k]==v
    comparisons={'custom_bundle_vs_original':('custom_fork_check','custom_retuned'),
                 'custom_bundle_vs_check_only':('custom_fork_check','custom_check'),
                 'standard_rf_bundle_vs_original':('standard_rf_fork_check','standard_rf'),
                 'standard_rf_bundle_vs_check_only':('standard_rf_fork_check','standard_rf_check'),
                 'bundle_fixed_vs_original_fixed':('custom_fork_check_fixed','custom_fixed')}
    changed_diagnostic={}
    for name,(a,b) in comparisons.items():
        for label,predicate in [('gained_correct',lambda x:x['truth'] and x['outer_awards'][a] and not x['outer_awards'][b]),
                                ('lost_correct',lambda x:x['truth'] and not x['outer_awards'][a] and x['outer_awards'][b]),
                                ('gained_wrong',lambda x:not x['truth'] and x['outer_awards'][a] and not x['outer_awards'][b]),
                                ('removed_wrong',lambda x:not x['truth'] and not x['outer_awards'][a] and x['outer_awards'][b])]:
            keys={x['key'] for x in rows if predicate(x)};want=r['paired_award_changes'][name][label]
            assert set(want['keys'])==keys and want['count']==len(keys)
        changed_diagnostic[name]={}
        for state in (True,False):
            ss=[x for x in rows if any(v['acceptor_fork'] is True for v in x['added_features'].values())==state]
            changed_diagnostic[name][str(state)]=dict(n=len(ss),candidate=metric(ss,a),reference=metric(ss,b))
    assert r['fits']==120 and r['reference_parity_max_outer_score_difference']=={'custom':0.0,'standard_rf':0.0}
    out=dict(status='pass',rows=3724,groups=972,known_both_features=1320,original_eligible_misses=429,
             checks=['source/script/feature freeze hashes','baseline scores and awards exact','original grouping/game/aliases/positions',
                     'all8arm case/fold/pooled decisions','inner cutoff count and fraction constraints','panel exclusion report',
                     'all paired gained/lost keys','missingness and firstfeature coverage','exact120fit cap'],
             descriptive_fork_presence_breakdown=changed_diagnostic,
             script_sha256=sha(Path(__file__)),artifact_sha256={f.name:sha(f) for f in H.iterdir() if f.is_file() and f.name not in ('VERIFICATION.json','PROGRESS.json')})
    (H/'VERIFICATION.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({'status':'pass','rows':3724,'groups':972,'arms':len(arms),'fits':120}))
if __name__=='__main__':main()
