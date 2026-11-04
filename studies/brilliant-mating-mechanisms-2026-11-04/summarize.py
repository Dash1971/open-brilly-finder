"""Diagnostic summaries and evidence checks; not a new classifier or evaluation."""
import collections,hashlib,json,math,re,sys
from pathlib import Path
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;S=H.parent/'brilliant-mating-prospective-2026-11-04'
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
cc=read(H/'CASES.json');assert collections.Counter(c['group'] for c in cc)=={'correct_award':4,'wrong_award':8,'missed_brilliant':7}
for n,digest in read(S/'PRELABEL-FREEZE.json')['sha256'].items():assert sha(S/n)==digest
assert sha(S/'LABELS.json')==read(S/'RESULTS.json')['label_sha256']
depth=read(H/'DEPTH.json');dp=read(H/'DEPTH-PROTOCOL.json');assert depth['status']=='complete' and depth['queries_completed']==9 and depth['wall_seconds']<120
assert depth['protocol_sha256']==sha(H/'DEPTH-PROTOCOL.json')
wc=lambda cp:100/(1+math.exp(-.00368208*max(-1000,min(1000,cp))))
ce=read(H/'CHESSCOM-EVALUATIONS.json');ev={r['key']:r for r in ce['rows']}
for r in ce['rows']:
 prefix=r['san'].upper();prefix='NG4' if r['san']=='Ng4' else 'NB8' if r['san']=='Nb8' else 'QXE3'
 for phase in ['before','after']:
  text=(H/f'{prefix}-CHESSCOM-{phase.upper()}.txt').read_text();pattern=rf'link Description: {r[phase+"_white_cp"]/100:+.2f}, Value: support.chess.com/article/656'
  assert pattern in text,(r['san'],phase,pattern)
 r['existing_logistic_loss_from_displayed_scores_pp']=wc(-r['before_white_cp'])-wc(-r['after_white_cp'])
summary=[]
for c in cc:
 f=c['features']['windows']['current']['features'];summary.append({'key':c['key'],'san':c['san'],'group':c['group'],'chesscom_label':c['label'],'source_url':c['url'],'forest_min_score':min(c['window_scores'].values()),'eligible':{w:c['features']['windows'][w]['eligible'] for w in ['current','previous']},'base_rule_failures':c['base_rule_failures'],'material_features':c['material_features'],'features_current':{n:f[n] for n in ['ec_sacrifice','mating_acceptance','mapped_loss_pp','same_root_loss_pp','same_root_rank','best_second_gap_pp','prior_cp','before_depth','after_depth']},'mate_witnesses':{w['acceptance_san']:[r['san'] for r in w['mate_replies']] for w in c['witnesses'].values()},'deeper_search':next((r['comparison'] for r in depth['cases'] if r['key']==c['key']),None)})
out={'scope':'19case diagnostic comparison only. No fitted model, new rules, thresholds, changed labels or retrospective performance re-evaluation. Ratings excluded.','case_counts':dict(collections.Counter(c['group'] for c in cc)),'cases':summary,'chesscom_display_evaluations':ce,'official_definition_source':'https://support.chess.com/en/articles/8572705-how-are-moves-classified-what-is-a-blunder-or-brilliant-etc','interpretation_limits':['Labels and savedlegalchessmechanisms are observed; Chess.com internal sacrifice criterion is not exposed.','Finite material proxy0 is no saved witness, not proof no viable nonmate route exists.','Current/previous are successive search iterations, not independent engine replications.','New3Msearches are diagnostic; no oldprospective verdict or model classification has been replaced.']}
(H/'COMPARISON.json').write_text(json.dumps(out,indent=2)+'\n')
(H/'VERIFICATION.json').write_text(json.dumps({'status':'pass','checks':['exact4correct8wrong7missed membership','all previous prospective freezes/labels unchanged','nine bounded diagnostic engine searches and protocolhash','three paired visibleChesscombefore/after scores matched to fullUIreceipts','no rules/model/thresholds changed; diagnostic outputs only'],'artifact_sha256':{p.name:sha(p) for p in H.iterdir() if p.suffix in ['json','py','txt'] and p.name!='VERIFICATION.json'}},indent=2)+'\n')
print('19case summary verified; previous prospective evidence unchanged;9boundeddepthsearches and6visibleevaluationreceipts checked.')
