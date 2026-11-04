"""Existing category/hash selection policy; partial drafts never authorize collection."""
import collections
import hashlib
import json
import pathlib
ROOT = pathlib.Path(__file__).resolve().parent
load = lambda p: json.loads(p.read_text())
save = lambda n, x: (ROOT / n).write_text(json.dumps(x, indent=2) + '\n')
pool = load(ROOT / 'ELIGIBLE-PGN-POOL.json')['ready']
controls = load(ROOT / 'control-preparation-input.json')
counts = collections.Counter((r['account'],r['game_id']) for r in controls)
cats = ['Queen Sacrifice','Rook Sacrifice','Bishop Sacrifice','Knight Sacrifice','All Types']
rank = lambda r, cat: hashlib.sha256(f'mute-prospective-v7|{r["account"]}|{cat}|{r["game_id"]}|{r["ply"]}'.encode()).hexdigest()
def categories(row):
    value = row.get('categories') or row.get('sampling_category') or row.get('category') or ['All Types']
    if isinstance(value, str):
        value = [value]
    return [c for c in value if c in cats] or ['All Types']
used_games=set(); used_identity=set(); accounts={}
for account in ['nelsi','hansen','KNVB','GothamChess','Hikaru']:
    rows=[r for r in pool if r['account']==account]
    buckets={cat:sorted([r for r in rows if cat in categories(r)],key=lambda r:rank(r,cat)) for cat in cats}
    chosen=[]; reserves=[]
    while any(buckets.values()):
        for cat in cats:
            while buckets[cat]:
                row=buckets[cat].pop(0); identity=(' '.join(row['fen_before'].split()[:4]),row['uci'])
                if row['game_id'] in used_games or identity in used_identity or counts[(account,row['game_id'])]<4:
                    continue
                used_games.add(row['game_id']);used_identity.add(identity)
                item=dict(row,sampling_category=cat,selection_hash=rank(row,cat),selected=False,
                    selection_status='prepared_not_frozen',current_label='unknown')
                (chosen if len(chosen)<20 else reserves).append(item)
                break
    queue={'account':account,'status':'PREPARED_PARTIAL_NO_LABEL_GO', 'targets':chosen,'reserves':reserves,'controls':[],
        'label_status':'Historicalgallerynominationonly; ALLnewcurrentlabelsUNKNOWN',
        'sampling_policy':'Fixed mute-prospective-v7 account/category/game/ply SHA256, categoryroundrobin, onegameglobal; no model outcomes.',
        'control_source':'Existing raw-v2 legal-offer descriptor only; pending final one bounded preparation pass after100gamesready.'}
    save(f'{account.lower()}-ui-queue.json',queue)
    accounts[account]={'targets':len(chosen),'reserves':len(reserves),'missing_to20':max(0,20-len(chosen)),
        'controls_minimum':min((counts[(account,r['game_id'])] for r in chosen),default=0)}
save('QUEUE-DRAFT.json',{'status':'Prepared only; not frozen or authorized for current labels','accounts':accounts,'total_targets':sum(r['targets'] for r in accounts.values())})
print(json.dumps(accounts))
