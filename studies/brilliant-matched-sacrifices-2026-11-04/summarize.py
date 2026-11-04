"""Descriptive matched-case summaries and checks; no fitting or rule selection."""
import collections,gzip,hashlib,json,statistics,sys
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,'/private/tmp/brilly-research-deps')
import chess
HERE=Path(__file__).resolve().parent;WORK=HERE.parents[1]
STUDY=WORK/'mute-chess-research-overnight-2026-11-03/studies/brilliant-training-2026-11-03'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,d):(HERE/n).write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')
protocol=json.loads((HERE/'PROTOCOL.json').read_text())
cases={c['key']:c for c in json.loads((HERE/'MATCHED-CASES.json').read_text())}
probe=json.loads((HERE/'PROBES.json').read_text());probes={c['key']:c for c in probe['cases']}
assert probe['status']=='complete' and probe['searches']==62 and len(cases)==len(probes)==48
assert len({c['group'] for c in cases.values()})==48
assert sha(HERE/'MATCHED-CASES.json')==protocol['cases_sha256']
assert sha(HERE/'MATCHED-GAMES.json')==protocol['games_sha256']
assert sha(STUDY/'data/training.json')==protocol['input_sha256']
assert sha(HERE/'prepare.py')==protocol['script_sha256']
assert sha(HERE/'probe.py')==probe['script_sha256']
assert sha(HERE/'PROTOCOL.json')==probe['protocol_sha256']
def rank(o):
    v=o['value_mover']
    return v['cp'] if v['cp'] is not None else 100000 if v['mate']>0 else -100000 if v['mate']<0 else 0
summary={};root_agreement=collections.Counter();gap_differences=[];legal_lines=0
for key,c in cases.items():
    item=probes[key];assert c['truth']==item['truth']
    for offer in item['offers']:
        b=chess.Board(c['fen_after']);b.push_uci(offer['offer']['uci']);assert b.fen()==offer['accepted_fen']
        for w in ['current','previous']:
            snap=offer['snapshot'].get(w)
            if not snap:continue
            for line in snap['lines']:
                replay=b.copy()
                for u in line['moves']:replay.push_uci(u)
                legal_lines+=1
    chosen=min(item['offers'],key=rank);trace=chosen['best_trace'];snap=chosen['snapshot'];prev=snap.get('previous')
    sign=1 if chess.Board(c['fen_before']).turn else -1
    previous_gap=None
    if prev and len(prev['lines'])>=2 and all(l.get('cp') is not None for l in prev['lines'][:2]):
        previous_gap=sign*(prev['lines'][0]['cp']-prev['lines'][1]['cp'])
    if previous_gap is not None and chosen['best_second_response_gap_cp'] is not None:
        gap_differences.append(abs(previous_gap-chosen['best_second_response_gap_cp']))
    if prev:root_agreement[str(snap['current']['lines'][0]['moves'][:1]==prev['lines'][0]['moves'][:1])]+=1
    summary[key]={'truth':c['truth'],'san':c['san'],'pair':next(p['pair'] for p in protocol['pairs'] if key in [p['positive'],p['ordinary']]),
      'selected_acceptance':chosen['offer']['san'],'cp':chosen['value_mover']['cp'],'mate':chosen['value_mover']['mate'],
      'acceptance_gain_cp':chosen['gain_vs_saved_best_defense_cp'],'compensation_gap_cp':chosen['best_second_response_gap_cp'],
      'previous_compensation_gap_cp':previous_gap,'debt6':trace['debt6'],'debt12':trace['debt12'],
      'first_recoup_ply':trace['first_recoup_ply'],'own_checks6':trace['own_checks_first6'],
      'first_reply_quiet':trace['first_reply_quiet'],'line_san':[s['san'] for s in trace['steps']],
      'new_accepting_branches':sum(not o['was_in_saved_top2'] for o in item['offers']),
      'all_acceptances':len(item['offers'])}
paired={}
for n in ['acceptance_gain_cp','compensation_gap_cp','previous_compensation_gap_cp','debt6','debt12','own_checks6']:
    count=collections.Counter()
    for pair in protocol['pairs']:
        a,b=summary[pair['positive']][n],summary[pair['ordinary']][n]
        count['unknown' if a is None or b is None else 'positive_greater' if a>b else 'ordinary_greater' if a<b else 'equal']+=1
    paired[n]=dict(count)
classes={}
for truth in [True,False]:
    rows=[s for s in summary.values() if s['truth']==truth]
    stats={'n':len(rows),'recoup_first_reply':sum(r['first_recoup_ply']==2 for r in rows),
       'acceptance_forces_winning_mate':sum(r['mate'] is not None and r['mate']>0 for r in rows),
       'sustained_debt6_gt100_without_forced_mate':sum(r['mate'] is None and r['debt6'] is not None and r['debt6']>100 for r in rows),
       'new_accepting_branches':sum(r['new_accepting_branches'] for r in rows),
       'all_accepting_branches':sum(r['all_acceptances'] for r in rows),
       'cases_with_no_saved_acceptance':sum(not cases[k]['saved_pv_features']['pv_any_saved_accepts'] for k in summary if summary[k]['truth']==truth)}
    for n in ['acceptance_gain_cp','compensation_gap_cp','debt6','debt12']:
        vv=[r[n] for r in rows if r[n] is not None]
        stats[n]={'known':len(vv),'median':statistics.median(vv),'min':min(vv),'max':max(vv)}
    classes['brilliant' if truth else 'ordinary']=stats
# Independently check the subagent's broad saved-PV audit.
pred={r['key']:r for r in json.loads((WORK/'research/brilliant-standard-learners-2026-11-04/PREDICTIONS.json').read_text())}
with gzip.open(STUDY/'pv-trajectory-experiment/inputs/training-augmented.json.gz','rt') as f:aug=json.load(f)
audit={}
for truth in [True,False]:
    cc=[c for c in aug['cases'] if c['cohort'].startswith('batch') and c['truth']==truth and
        c['negative_bucket'] in ['positive','hard_ordinary'] and pred[c['key']]['eligible'] and
        not pred[c['key']]['outer_awards']['custom_fixed'] and not c['windows']['current']['features']['ec_sacrifice']]
    fs=[c['windows']['current']['features'] for c in cc]
    audit['missed_brilliant' if truth else 'ordinary']={'n':len(cc),'saved_acceptance':sum(f['pv_any_saved_accepts'] is True for f in fs),
        'no_saved_acceptance':sum(f['pv_any_saved_accepts'] is False for f in fs),
        'recoup_by6':sum(f['pv_recoup_by6_any'] is True for f in fs),
        'no_recoup_by6_known':sum(f['pv_recoup_by6_any'] is False for f in fs)}
assert audit['missed_brilliant']=={'n':51,'saved_acceptance':33,'no_saved_acceptance':18,'recoup_by6':24,'no_recoup_by6_known':9}
assert audit['ordinary']=={'n':149,'saved_acceptance':78,'no_saved_acceptance':71,'recoup_by6':54,'no_recoup_by6_known':24}
write('CASE-SUMMARIES.json',summary)
write('FINDINGS.json',{'scope':'Exploratory matched-case evidence. No estimate of classifier precision/recall.',
    'acceptance_choice':'Opponent-best (lowest mover evaluation) qualifying capture; mates ranked separately from finite cp; no label-driven branch choice.',
    'cases':48,'pairs':24,'searches':62,'new_branches_not_in_saved_top2':sum(s['new_accepting_branches'] for s in summary.values()),
    'class_summaries':classes,'paired_comparisons':paired,'saved_pv_audit':audit,
    'stability':{'chosen_best_reply_agreement_between_windows':dict(root_agreement),
                 'compensation_gap_window_difference_median_cp':statistics.median(gap_differences),
                 'compensation_gap_window_difference_max_cp':max(gap_differences)},
    'limitations':['Matched sample intentionally selects closest controls; not representative','All labels/features previously studied; no independent validation',
                   'Cp acceptance-vs-baseline compares separate engine searches','Previous window is correlated, not independent replication',
                   'Four pairs lack comparable finite-cp gaps because at least one side has forced mate','One ordinary12ply endpoint remains unknown',
                   'Pair similarity is approximate; e.g. minor piece type and evaluation may differ','No refreshed Chess.com labels/settings audit in this study']})
write('VERIFICATION.json',{'status':'pass','full_saved_probe_pv_lines_legality_checked':legal_lines,
    'checks':['48distinctgroups','input/script/protocol hashes','fullPGN before/after identity checked during preparation and probing',
              'all62capture positions and full engine PVs legal','source labels explicitly Brilliant or Good/Excellent/Best/Great',
              'subagent51vs149audit independently reproduced','no classifier fit or award settings changed'],
    'artifact_sha256':{n:sha(HERE/n) for n in ['PROTOCOL.json','MATCHED-CASES.json','MATCHED-GAMES.json','PROBES.json','CASE-SUMMARIES.json','FINDINGS.json','prepare.py','probe.py','summarize.py']}})
print(json.dumps({'status':'verified','legal_lines':legal_lines,'classes':classes,'paired_gaps':paired['compensation_gap_cp']},indent=2))
