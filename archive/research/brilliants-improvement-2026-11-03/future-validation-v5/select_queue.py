"""Freeze data-availability-only target order before any future current labels."""
import collections,hashlib,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parent
load=lambda p:json.loads(p.read_text())
save=lambda n,x:(ROOT/n).write_text(json.dumps(x,indent=2)+'\n')
pool=load(ROOT/'ELIGIBLE-PGN-POOL.json')['ready'];draft=load(ROOT/'QUEUEDRAFT.json')
controls=load(ROOT/'control-preparation-input.json');count=collections.Counter((r['account'],r['game_id']) for r in controls)
CATS=['Queen Sacrifice','Rook Sacrifice','Bishop Sacrifice','Knight Sacrifice','All Types'];SEED='mute-future-validation-v5-v1'
rank=lambda r,cat:hashlib.sha256(f'{SEED}|{r["account"]}|{cat}|{r["game_id"]}|{r["ply"]}'.encode()).hexdigest()
canon=lambda f:' '.join(f.split()[:4])
usedgames=set();usedident=set();results={};changes=[]
for account in ['nelsi','hansen','KNVB','GothamChess','Hikaru']:
    rows=[r for r in pool if r['account']==account];bykey={(r['game_id'],r['ply']):r for r in rows}
    selected=[]
    for old in draft['accounts'][account]['targets']:
        key=(old['game_id'],old['ply']);r=bykey.get(key)
        if not r or not count[(account,r['game_id'])]:
            changes.append({'account':account,'game_id':key[0],'ply':key[1],'reason':'PGNidentityunavailable' if not r else 'noeligiblecontrolafterfullold-positionandgalleryexclusions','no_current_label_consulted':True});continue
        cat=old['sampling_category'];x=dict(r);x.update(sampling_category=cat,selection_hash=rank(r,cat),retained_from_initial73_draft=True)
        selected.append(x);usedgames.add(r['game_id']);usedident.add((canon(r['fen_before']),r['uci']))
    buckets={cat:sorted([r for r in rows if cat in (r.get('categories') or ['All Types'])],key=lambda r:rank(r,cat)) for cat in CATS}
    reserves=[];localgames=set(usedgames);localident=set(usedident)
    while any(buckets.values()):
        for cat in CATS:
            while buckets[cat]:
                r=buckets[cat].pop(0);ident=(canon(r['fen_before']),r['uci'])
                if r['game_id'] in localgames or ident in localident or not count[(account,r['game_id'])]:continue
                x=dict(r);x.update(sampling_category=cat,selection_hash=rank(r,cat),retained_from_initial73_draft=False)
                localgames.add(r['game_id']);localident.add(ident)
                if len(selected)<20:selected.append(x);usedgames.add(r['game_id']);usedident.add(ident)
                else:reserves.append(x)
                break
    for r in selected:r.update(selected=True,selection_status='primary_historical_gallery_nomination',selected_at=load(ROOT/'PLAN.json')['frozen_at_utc'])
    for r in reserves:r.update(selected=False,selection_status='frozen_order_positive_reserve')
    if len(selected)!=20:raise RuntimeError(f'{account} has{len(selected)}eligiblepositive/controlpairs;stopnofreshlabels')
    queue={'account':account,'status':'PGNVALIDATED100_TARGETS_PENDING_RAWCONTROLRANKANDROOTREVIEW','targets':selected,'reserves':reserves,'controls':[],
        'label_status':'Historicalgallery!!only; currentlabelsALLUNKNOWN','sampling_policy':'Retainedinitialdrafttargetswhereidentity+controlavailabilityallow; thenfixedcategoryroundrobin+hash. No classifieroutcome/currentlabel used.',
        'control_source':'Fixed raw-v2 descriptor job pending; do notcollect yet.'}
    save(f'{account.lower()}-ui-queue.json',queue)
    path=ROOT/'evidence'/f'{account.lower()}-gallery-selected.json';path.write_text(json.dumps(selected,indent=2)+'\n')
    save(f'{account.lower()}-candidate-pool.json',rows)
    save(f'{account.lower()}-reserves.json',reserves)
    results[account]={'targets':len(selected),'positive_reserves':len(reserves),'minimum_available_control_moves':min(count[(account,r['game_id'])] for r in selected),
        'categories':dict(collections.Counter(r['sampling_category'] for r in selected))}
save('PRELABEL-TARGET-SELECTION.json',{'accounts':results,'initial_draft_replacements_for_identity_or_controlavailability_only':changes,
    'all_current_labels_unknown':True,'one_target_per_game_global':len(usedgames)==100,'before_position_move_identities_unique':len(usedident)==100})
print(json.dumps({'accounts':results,'draft_changes':changes},indent=2))
