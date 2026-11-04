"""Final prelabel queue and exact evidence/source pins; no classifiers or engines run."""
import collections,hashlib,importlib.util,json,pathlib,sqlite3
ROOT=pathlib.Path(__file__).resolve().parent
IMPROVE=ROOT.parent
WORKSPACE=IMPROVE.parent.parent
load=lambda p:json.loads(p.read_text())
save=lambda n,x:(ROOT/n).write_text(json.dumps(x,indent=2)+'\n')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
s=importlib.util.spec_from_file_location('future_corpus',ROOT/'corpus.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
known={r['canonical_first_four'] for r in load(ROOT/'known-regression-fens.json')['positions']}
excluded=set(load(ROOT/'exclude-games.json')['game_ids'])
canon=lambda f:' '.join(m.chess.Board(f).fen().split()[:4])
plan=load(ROOT/'PLAN.json')
plan['prepared_at_utc']=plan.get('prepared_at_utc',plan['frozen_at_utc'])
plan['frozen_at_utc']=m.now()
plan['reporting']='Researchassessment ofbadgeprecisionanddetection, notclaim90%goalachieved; no threshold/modelretuningfromnew200. All848previousmoves AREtraining/development data and areEXCLUDEDfromthisnewtest.'
plan['engine_evidence']={
    'core':'Only finalexplicitlyverified200primarykeys, AFTERclassquota/identitychecks. Requiredpositions[max(0,ply-2),ply-1,ply], uniondeduplicated/sortedchronologicallyperwholegame. FullPGNstack, ClearHash/newsessionbetweenwholegames, SF18/300k/Threads1/Hash64MB, completecurrent/previousMultiPV2 snapshots. No enginebeforefreshlabelscomplete.',
    'S_supplemental':'OnlyAFTERcorebankcomplete, separatecleanPGNsessions/bankatSAME300kforadditionalpriororigindecisionwindows. NeverprewarmcorewithSlookbacks, neveroverwritereplacecorewindows. Supplementalpriorcurrent+previouscompleteevidenceandcoverageexplicit.',
    'reserves':'Do notprecomputeallreserves oradditionalpositionsbeforecore; preservebaseline warm-hashmeasurementdomain.',
    'configuration_domain':'StandaloneSF18researchprofile; nativeSF19/variablebudgetsnotvalidatedbythisstudy.'}
plan['status']='Final100historicalcandidate targetgames/controlorder frozen; awaitingparentreviewbeforeanyfreshlabel'
plan['fixed_test']='One200freshassessment of fixed full-data forest5/6 primary, correctedScomparator, anddirectEC. All848formerexamples AREtraining/development and EXCLUDEDfromthisnew200test. No tuning fromnew200.'
save('PLAN.json',plan)
effective_source_pins={}
for path in [IMPROVE/'astra/v5/fresh-extractor/FREEZE.json',IMPROVE/'astra/v5/sequence-reference/source-freeze-castling-addendum.json']:
    for raw,expected in load(path)['sha256'].items():
        p=pathlib.Path(raw).resolve();assert sha(p)==expected, f'Frozenexecutablechanged:{p}'
        effective_source_pins[str(p.relative_to(WORKSPACE))]=expected
accounts={};summary={};games=set();identities=set();all_control_keys=set();gallery_keys={(r['game_id'],r['ply']) for r in load(ROOT/'historical-pool-snapshot.json')['rows']}
priority={'apparent_piece_offer':0,'quiet_attacked_defended_piece':1,'recapture_exchange':2,'other_capture':3,'other_quiet':4}
for account in m.ACCOUNTS:
    path=ROOT/f'{account.lower()}-ui-queue.json';queue=load(path);bank=queue['controls'];frozen_controls=[]
    for target in queue['targets']+queue['reserves']:
        gid=target['game_id'];assert gid not in excluded
        assert canon(target['fen_before']) not in known and canon(target['fen_after']) not in known
        matches=[r for r in bank if r['game_id']==gid and (r['game_id'],r['ply']) not in gallery_keys]
        matches.sort(key=lambda r:(priority[r['sampling_priority']],abs(r['ply']-target['ply']),r['ply'],r['uci']))
        target['control_candidates']=[]
        for rank,raw in enumerate(matches[:4]):
            r=dict(raw);assert canon(r['fen_before']) not in known and canon(r['fen_after']) not in known
            r.update(frozen_control_rank=rank,current_label='unknown',label='unknown',selected=False,sample_role='negative_candidate',
                selection_reason='Fixedprioritythennearesttargetply; no classifieroutputorcurrentlabel',paired_positive_key=f'{gid}:{target["ply"]}')
            target['control_candidates'].append(r);frozen_controls.append(r)
        assert target['control_candidates']
        target['matched_control_draft']=target['control_candidates'][0]
        target['control_reserves']=target['control_candidates'][1:]
        target['current_label']='unknown'
        if target in queue['targets']:
            target['selected_at']=plan['frozen_at_utc']
            ident=(canon(target['fen_before']),target['uci']);assert gid not in games and ident not in identities
            games.add(gid);identities.add(ident)
            for control in target['control_candidates']:all_control_keys.add((control['game_id'],control['ply']))
    queue.update(status='FROZEN100_TARGETS_READY_FOR_PARENT_REVIEW_NO_FRESHLABELS',controls=frozen_controls,
        control_policy='Use target.control_candidates in frozen_control_rank order; first plus atmost3reserves. RetainALLencounteredfreshlabels. Ifall4unusable/Brilliant, stopandreport; do notchooseunfrozenmoves.',
        positive_reserve_policy='Use frozen queue.reserves order; no model-drivenreplacement. Keep failedhistorical/currentnomination assecondaryaudit.')
    save(path.name,queue);save(f'evidence/{account.lower()}-gallery-selected.json',queue['targets'])
    accounts[account]=queue
    summary[account]={'targets':len(queue['targets']),'positive_reserves':len(queue['reserves']),
        'frozen_primary_control_candidates':sum(len(t['control_candidates']) for t in queue['targets']),
        'each_target_has_primary_plus3_control_reserves':all(len(t['control_candidates'])==4 for t in queue['targets']),
        'gallery_board_present':sum(t['board_identity_captured'] for t in queue['targets']),
        'categories':dict(collections.Counter(t['sampling_category'] for t in queue['targets']))}
assert len(games)==len(identities)==100
conn=sqlite3.connect(ROOT/'corpus.sqlite3');conn.row_factory=sqlite3.Row
conn.execute('PRAGMA foreign_keys=ON')
assert conn.execute("select count(*) from observations where source_type='fresh_review'").fetchone()[0]==0
# Final protocol completion is an explicit prelabel event. Preserve the exact
# preparation plan and its hash; do not relax the ordinary corpus hash check.
old_plan=conn.execute("select value from metadata where key='plan_sha256'").fetchone()[0]
assert json.loads(old_plan)==sha(ROOT/'PLAN-PREPARED.json')
conn.execute('insert into metadata values(?,?)',('prelabel_prepared_plan_sha256',old_plan))
conn.execute("update metadata set value=? where key='plan_sha256'",(json.dumps(sha(ROOT/'PLAN.json')),))
conn.execute('insert into metadata values(?,?)',('final_queue_frozen_at_utc',json.dumps(plan['frozen_at_utc'])))
conn.commit()
imports=[]
for account in m.ACCOUNTS:imports.append(m.import_evidence(conn,ROOT/'evidence'/f'{account.lower()}-gallery-selected.json'))
validation=m.validate(conn)
assert not validation['indexing_mismatches'] and not validation['observations_waiting_for_pgn'] and not validation['known_regression_fen_matches'],validation
m.export(conn)
assert conn.execute("select count(*) from observations where source_type='fresh_review'").fetchone()[0]==0
assert conn.execute('pragma integrity_check').fetchone()[0]=='ok'
save('FINALQUEUE.json',{'frozen_before_current_labels_at_utc':m.now(),'status':'Awaitingparentreview; no currentlabels collected','target_game_count':100,'planned_primary_fresh_moves':200,
    'targets_per_account':20,'positive_reserves_by_account':{a:v['positive_reserves'] for a,v in summary.items()},
    'selection_source':'QUEUEDRAFT.json initial73 retained; added PGN/control-verified historicaltopups underfixedhash/categorymethod, no currentlabels/modelscores',
    'engine_protocol':plan['engine_evidence'],'summary':summary,'accounts':accounts})
names=['PLAN.json','PLAN-PREPARED.json','FINALQUEUE.json','exclude-games.json','known-regression-fens.json','historical-pool-snapshot.json','PRELABEL-TARGET-SELECTION.json','corpus.py',
    'prepare_metadata.py','prepare_controls.py','select_queue.py','prepare-controls.mts','finalize_queue.py','PUBLIC-ARCHIVE-RESOLUTION.json','METADATA-RESOLUTION-SNAPSHOT.json']
names += [f'{a.lower()}-ui-queue.json' for a in m.ACCOUNTS]
freeze={'frozen_at_utc':m.now(),'all_current_labels_unknown':True,'fresh_review_observations':0,'targets':100,'future_fresh_class_target':{'brilliant':100,'explicit_nonbrilliant':100},
    'accounts':summary,'source_model_executable_sha256':effective_source_pins,
    'file_sha256':{n:sha(ROOT/n) for n in names},'source_freeze_artifact_sha256':plan['source_freezes'],
    'all465reviewed_games_excluded':True,'all38214knowncanonicalpositions_excluded':True,
    'unresolved_or_rejected_historical_cards_retained':'ELIGIBLE-PGN-POOL.json; allsourcecardsretainedhistorical-pool-snapshot.json, no currentoutcomes used toexclude.',
    'initial_draft_target_replacements':load(ROOT/'PRELABEL-TARGET-SELECTION.json')['initial_draft_replacements_for_identity_or_controlavailability_only'],
    'database_games':conn.execute('select count(*) from games').fetchone()[0],
    'notes':'Primary200keys finalizedonlyafterexplicitfreshUIverification/classquotas, usingfixedorders. No enginebeforecollectioncompletion; Scachecleanandseparateaftercore.'}
save('QUEUE-FREEZE.json',freeze);conn.close()
print(json.dumps({'summary':summary,'target_games':100,'frozen_primary_control_candidates':len(all_control_keys),'PGNidentity_validation':validation},indent=2))
