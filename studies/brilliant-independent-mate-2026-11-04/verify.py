"""Independent artifact/decision checks; no fitting or classifier selection."""
import json,hashlib,math
from pathlib import Path
from collections import Counter
H=Path(__file__).resolve().parent;W=H.parents[1]
def load(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def metrics(rows,arm):
    tp=sum(r['truth'] and r['outer_awards'][arm] for r in rows)
    fp=sum(not r['truth'] and r['outer_awards'][arm] for r in rows)
    pos=sum(r['truth'] for r in rows)
    return {'TP':tp,'FP':fp,'FN':pos-tp,'TN':len(rows)-pos-fp,'recall':tp/pos if pos else None,
            'precision':tp/(tp+fp) if tp+fp else None,'wrong_fraction_of_awards':fp/(tp+fp) if tp+fp else None}
def main():
    protocol=load(H/'EVAL-PROTOCOL.json');result=load(H/'RESULTS.json');pred=load(H/'PREDICTIONS.json')
    extraction=load(H/'EXTRACTION.json');features=load(H/'FEATURES.json')
    source=W/'mute-chess-research-overnight-2026-11-03/studies/brilliant-training-2026-11-03/data/training.json'
    cases={r['key']:r for r in load(source)['cases']}
    original={r['key']:r for r in load(W/'research/brilliant-standard-learners-2026-11-04/PREDICTIONS.json')}
    assert all(sha(W/k)==v for k,v in protocol['source_sha256'].items())
    assert sha(H/'evaluate.py')==protocol['script_sha256']==result['script_sha256']
    assert sha(H/'EVAL-PROTOCOL.json')==result['protocol_sha256']
    assert sha(H/'FEATURES.json')==result['feature_sha256']==extraction['feature_sha256']==protocol['feature_sha256']
    assert sha(H/'EXTRACTION.json')==result['extraction_sha256']==protocol['extraction_sha256']
    assert sha(source)==result['input_sha256']==extraction['input_sha256']
    groups=sorted({c['group'] for c in cases.values()},key=lambda g:(hashlib.sha256(('mute-optimization-v1-outer:'+str(g)).encode()).hexdigest(),str(g)))
    foldmap={g:i%5 for i,g in enumerate(groups)}
    gamegroups={};positions={};flips=[];misses=0
    assert len(pred)==len(cases)==3724 and len(groups)==972
    arms=protocol['arms'];folds={f['fold']:f for f in result['outer_folds']}
    for r in pred:
        c=cases[r['key']];old=original[r['key']]
        assert r['truth']==c['truth'] and r['group']==c['group'] and r['outer_fold']==foldmap[c['group']]==old['outer_fold']
        for gid in {c['game_id']}|{a.rsplit(':',1)[0] for a in c['aliases']}:assert gamegroups.setdefault(gid,c['group'])==c['group']
        pos=' '.join(c['fen_before'].split()[:4]);assert positions.setdefault(pos,c['group'])==c['group']
        gate=all(w['eligible'] and not w['features']['physical_unknown'] for w in c['windows'].values()) and c['confidence_sufficient']
        assert gate==r['eligible']==old['eligible']
        for w in ('current','previous'):
            f=c['windows'][w]['features'];assert r['original_mating_acceptance'][w]==f['mating_acceptance']
            assert f['mating_acceptance']==(not f['ec_sacrifice'] and features[c['key']])
        assert r['corrected_mating_acceptance']==features[c['key']]
        changed=r['corrected_mating_acceptance']!=r['original_mating_acceptance']['current']
        if changed:flips.append(r)
        target=bool(gate and r['truth'] and not old['outer_awards']['custom_retuned'])
        assert r['original_429_miss']==target;misses+=target
        for k in ('custom','standard_rf'):assert abs(r['outer_scores'][k]-old['outer_scores'][k])<=1e-12
        for a in ('custom_fixed','custom_retuned','standard_rf'):assert r['outer_awards'][a]==old['outer_awards'][a]
        for arm in arms:
            point=folds[r['outer_fold']]['inner_selection']['points'][arm]
            score=r['outer_scores'][point['kind']];assert math.isfinite(score) and 0<=score<=1
            assert r['outer_awards'][arm]==bool(gate and score>=point['threshold'])
    assert misses==429 and len(flips)==67 and sum(r['eligible'] for r in flips)==64
    for arm in arms:
        for key,value in metrics(pred,arm).items():assert value==result['outer_pooled'][arm][key]
    for fold in range(5):
        rows=[r for r in pred if r['outer_fold']==fold]
        assert {r['key'] for r in rows}==set(folds[fold]['test_keys'])
        for arm in arms:
            for key,value in metrics(rows,arm).items():assert value==folds[fold]['test_metrics'][arm][key]
        points=folds[fold]['inner_selection']['points'];ref=points['custom_fixed']
        for arm in ('custom_retuned','custom_corrected','standard_rf','standard_rf_corrected'):
            p=points[arm];assert p['FP']<=ref['FP'] and p['FP']*ref['TP']<=ref['FP']*p['TP']
    comparisons={'custom_corrected_vs_retuned':('custom_corrected','custom_retuned'),
                 'standard_rf_corrected_vs_original':('standard_rf_corrected','standard_rf'),
                 'corrected_fixed_vs_original_fixed':('custom_corrected_fixed','custom_fixed')}
    effects={}
    for name,(candidate,base) in comparisons.items():
        effects[name]={}
        for changed in (False,True):
            counts=Counter()
            for r in pred:
                flip=r['corrected_mating_acceptance']!=r['original_mating_acceptance']['current']
                if flip!=changed:continue
                a,b=r['outer_awards'][candidate],r['outer_awards'][base]
                if a==b:continue
                counts[('gained_' if a else 'lost_')+('correct' if r['truth'] else 'wrong')]+=1
            effects[name]['feature_changed' if changed else 'feature_unchanged']=dict(counts)
        for label,check in [('gained_correct',lambda r:r['truth'] and r['outer_awards'][candidate] and not r['outer_awards'][base]),
                            ('lost_correct',lambda r:r['truth'] and not r['outer_awards'][candidate] and r['outer_awards'][base]),
                            ('gained_wrong',lambda r:not r['truth'] and r['outer_awards'][candidate] and not r['outer_awards'][base]),
                            ('removed_wrong',lambda r:not r['truth'] and not r['outer_awards'][candidate] and r['outer_awards'][base])]:
            want={r['key'] for r in pred if check(r)};reported=result['paired_award_changes'][name][label]
            assert want==set(reported['keys']) and len(want)==reported['count']
    direct=[]
    for label,select in [('original22misses',lambda r:r['original_429_miss']),('original31found',lambda r:r['truth'] and r['outer_awards']['custom_retuned']),
                         ('ordinary11',lambda r:not r['truth'] and r['eligible'])]:
        rows=[r for r in flips if select(r)]
        direct.append(dict(group=label,n=len(rows),awards={a:sum(r['outer_awards'][a] for r in rows) for a in arms}))
    output={'status':'pass','verified_rows':3724,'group_components':972,'feature_flips':67,'eligible_feature_flips':64,
            'original_eligible_misses':429,'checks':['frozen sources/evaluator/features','all baseline scores and awards','all6arm row decisions and pooled/fold metrics',
              'original group hash mapping/game/alias/position isolation','all inner selected cutoffs obey reference count/fraction constraints',
              'all paired changed-key sets','same feature in bothwindows and exact original masked parity'],
            'effects_by_feature_change':effects,'direct_changed_feature_cases':direct,
            'protocol_prose_erratum':'EVAL-PROTOCOL custom learner says raw weighted leaf probabilities. Exact unchanged Tree uses raw bootstrap-window class fractions; class cost5 affects splits. No implementation change.',
            'script_sha256':sha(Path(__file__)),'artifact_sha256':{p.name:sha(p) for p in H.iterdir() if p.is_file() and p.name not in ('VERIFICATION.json','PROGRESS.json')}}
    (H/'VERIFICATION.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps({'status':'pass','effects':effects,'direct_cases':direct},indent=2))
if __name__=='__main__':main()
