# Current overnight state — resource-controlled continuation

Deadline23:55:39UTC Nov3 =08:55:39JST Nov4. User authorizes9hmaxverifiedcollection; optional experimental training/testing if useful collection finishesearly. NEVER change app/live model, MuteDev PR, merge/deploy. Experimental RESEARCHworktree /Users/da/Documents/ChatGPT/No Sweat Chess/mute-chess-research-overnight-2026-11-03 branchcodex/brilliant-training-overnight-2026-11-03 createdfromffa69cd; no candidatefit yet.

## CURRENT ownership/sessions (supersedes older text below)
- /root/overnight_collector_a owns A UI; root handedoffafter ALL11wave1A complete. NewA agent completed ALL10wave2A andfirst2/6wave3A. Fourwave3A remain, partial186059565788 wasreviewloading/noexport. AgentbrowserChromeid2(agentlocal), validprofilebinding, no reselection. AlltabsCLOSED/resourcePAUSED pendingrootGO.
- /root/pilot_corpus owns B UI. ALL9wave1B+first17of33wave2B complete=26Bcompleted. Pending183370101895 wave2index17 justopened/noexport. Readyfuturewaves: Bwave4 60Hansen +wave5 22Hansen, immutablenewqueues. Chromeid1agentlocalvalid, no literalrootIDrequirement. AlltabsCLOSED/resourcePAUSED pendingrootGO.
- /root/research_repo owns sole SQLiteimport/dedup/counts/immutablequeues + bounded publicmonthlyPGNfetch. 151newgamesassigned, latest49complete1115explicitlabels54Brilliant269hardordinary358individualboardchecks,0conflicts. Metadata tabsCLOSED/resourcePAUSED; offline import/fetchokay. Has76? futurequeuesseewavefiles/DATA-STATE.md. HansenMar2026download0.9MB resolved22newnominees; provenanceunderoriginal-pgn. RootA direct galleryfilesKNVB6categoriesstored.
- /root/astra_offer_timing completed adapter preparation; NOT running. Do not assume send_message triggersidleagent. Root owns engine subprocesses now.

## Resource policy CHANGE after expected guard stop
16GBMac; concurrent2reviews+largegallery+engine caused transientkernelpressure2. Enginebatch02 stopped safely; all3agentsclosedownTabs. Readonlykernel/processcheckthenpressure1, swap4675MB; no runaway process. DO NOT retry expanded procedures or redesign tools.
CURRENT hard phases: either(1) atmost2 browser tabs TOTAL, normally2fullreview collectors, OR1review+1metadata whenAqueueexhausts; NO engine concurrently; or(2) allresearchtabsclosed +ONE fixedSF18engine batch. Metadata cap300 onlypressure1/free>=35%; closemetadatafirstifpressurerises. Pressure2/4=>checkpointcloseownedtabs,pause. UserChromeTabs untouched. No extra collectors.
Roottemporarycaffeinate processsession27552 stopsatdeadline; heartbeat idovernight-brilliant-training-data-collection ACTIVEevery10min through23:56UTC; promptreadsPLAN/RESUME, finalreportonce atdeadline, no chatarchive. Use automation_update ifneeded to stop afterfinal; don'tduplicate.

## Engine/data state
Bounded82lineadapter adapter/run-training-batch.py imports frozen kernels,300k SF18Threads1Hash64 current+previouscompletePV2 fullPGN,600sec/deadline/STOP/pressureguard, onlyTRAINING. No fit. Allsourcehashes verified.
- ENGINE-BATCH-01.json SHA b0062507ec3230981023ca0ccef3ef920ccf2d5a7ca8869e11dd19ce88c2a77a COMPLETE engine-batches/batch-01:10traininggames77targets183snapshots,11both-eligible,7baselineawards,0physicalunknown,52sec. New9Brilliants all9eligible; only2/59hardnegativeeligible. Outputsfeatures.json+analysis+SUMMARY pinned. Rootexec74124completed.
- ENGINE-BATCH-02.json SHA d54f46fa5e3845be0d9b8709ca8841253cf21be3239871384016b362b4c5fdcc:17traininggames133targets336snapshots. Original engine-batches/batch-02 INCOMPLETE reasonpressure2, preserveallpartialresults, DO NOT overwrite ormixsnapshots.
- Root CURRENTLY running SAME frozenbatch02 in output batch-02-recovery-1, log/private/tmp/mute-overnight-engine-batch-02-recovery-1.log, execsession toolresult inchat. AlltabsCLOSED duringthisrun. Oncecompleted/rootchecksnormal, sendGO toB+A toresume2reviews. No metadata/engineconcurrency whiletheyreview. Ifsameguardfailsagainstopretryandreportminblocker; don'ttoolingexpand.
- Importerprepares nexttraining-onlyfrozenbatch (~20games) underENGINE-BATCH-03 etc onrequest; no duplicate processedgames or assessmentrows. Reserved20% wholegamehash assignment beforelabels, excludesoldgames/canonicaltargets, staysSEALED beforecandidatefreeze. Old848+old400maytrainfuturecandidate, cannotreuseasevaluation.

## UI reliability lessons
FullreviewPGNexport method6NAGtypes crosschecked. EveryNAG3positive musthave itsownvisiblelabel+exactPGNply/FEN/renderedboard; missingNAGUNKNOWN. CollectcoachNOTneeded. SavefullPGN/metadata/checks aftereachgame; importercounts easyerrors vs hardnear-best separately.
Click child wc-move-list[data-node...] .node-highlight-content, nevernodecontainercenter. ReadselectedSAN viaINNERtext, nottextContent(SVGCSSpollutes). UIcan stillauto-scrollmisclick: strictnode+board mustreject. Pilot'sminimalfallback usesvisibleNextMove/PreviousMovebuttonsfromobservedmainlineindextorequestedply, thenstrictfinalverification. No desiredcase replacements.
Cua cross-cell closures retainold reassignedtab/game refs. PASSchangingvaluesexplicitly (or stablemutableobject); rootglobalovernightTab/Game assignmentsinsidehelpermaynotupdateoutside! RecoveractualownTabfromcollector activecheckpoint tab_id usingbrowser.tabs.get; do notcreateanother. Dynamic evalcodegenerationDISALLOWED; do not evalui-helperstrings. Existing roothelperssource savedcollector-a/ui-helpers.js forlogic/manualreuse. Root nowNOUIcollection andowns0tabs.
Gallery infiniteappend DOESwork butdelayed: initial13→26→91etcafterprogressivescroll. Rootaction tab.scroll([1150,620],'down',1) withinobserved1470x702viewport, freshAX, repeattowindowbottom thenawaitnewcards. Useyouractualviewportgroundedpoint. DOMa.brilliant-move-item-board parentdiv.brilliant-move-item-component[data-game-item] readpubliclinks. Underpromotion0valid. RreachedHansen276andqueued60fresh+22Mar; nohiddenAPI.

## Next immediate
1. Await root enginebatch02recovery; closeitsprocess, inspectSUMMARY/status. Then resume2review collectors, metadata remainsclosed.
2. Rcontinues import/queueprep offline. WhenAexhaustsfourremaininggamesandcloses, RcanuseonegalleryalongsideBreviewtofeedA, thenclosesbeforeAresumes. Alternateanalysisphaseswhenbothcollectorbatchboundariescooperate.
3. Check actual datasetcounts and resource state, don'ttreatrawblunderNAGs asusefulmodeltraining; mostfailhardgates. Considerfuturehardcontrolpriorityrawlegaloffers via frozen helper(beforelabels/predictions) onlyifboundedandnecessary; NOsuchchangeimplemented.
4. Fitcandidate onlyafterusefulnewdataandinremainingbudget, separateexperimentalresearchbranch, samecurrentfeature/profile/threshold baseline. Existingfit.pyunsafe toexecute directly becausehardcodedoldoutputandglobaldata asserts848; needboundedinputwiring, no oldwrites or post-heldouttuning. No fittingdone.
5. Stopcollectingbydeadline; closeownedtabs; finishsavedverification/dedup andoneplain-Englishreportcounts/splits/unknowns/data+candidatecomparisonifrun. No merge/deploy/currentmodelchange.

## Original setup notes below (historical; superseded whereconflicting)

# Overnight collection — active

User explicitly authorizes nine-hour collection, stop2026-11-03T23:55:39UTC=Nov4 08:55:39JST. Maximize verified unique labels; no fixed quota. Optional experimental training/testing permitted if collection expedited; NEVER touch live/app model, Mute Dev PR, merge/deploy. See PLAN.json.

Automation heartbeat id overnight-brilliant-training-data-collection active every10min throughdeadline; continue currentchat, avoidduplicatecollector launches, finaloneplainreport atdeadline. If atdeadlinequeued heartbeat stopcollection, closeownedtabs, finishsavedverification and report, stopheartbeat. Userdidnotrequestnotificationsperbatch.

## Current ownership
- Root owns futurequeueA nelsi/KNVB and UI collection; selectedChromeid3profileD, trainingBrowser handle, trainingTab closed aftermethodcheck. Cua docsloaded via rewriteDocumentation. Only root'sownresearchTabs mayclose, userTabs untouched.
- Pilot_corpus assigned queueB hansen/Gotham/Hikaru UI collection; awaiting preparedqueue. No shared DB writes/engines.
- Research_repo preparing disjointqueues/fullPGN identity/exclusions/gamehash20%test now; noUI/engines/publicwrites. Askfirstqueuedelivery ASAP.
- One collector tab/game, closepromptly, atmost2total. Lastmacpressure1,swap3758MB. sysctlapprovedprefix /usr/sbin/sysctl forread. Ifpressure2or4, pauseUI, closeownedtabs and doofflinevalidation untilnormal.

## Faster export method VERIFIED on known game only
Methodgame Hansen174838537627 is EXCLUDED fromnewcounts. Freshreview complete. Go to Analysis button changesURL /review→/analysis. Bottomellipsis opensmenu ShareGame. ShareGame dialoghasPGNtextbox. Readvisibletextboxvalue; nohidden APIs orappstate. SavedfullPGN method-check/hansen-174838537627-analysis-export.pgn, parsed17explicitNAGlabels.
Sixindependentvisiblelabel/exactPGNplySANUCI/FEN/renderedboardchecks inmethod-check/visible-label-checks.json:14b5$6inaccuracy,16exd4$2mistake,17O-O$1great,34b4$9miss,42Qc7$4blunder,49Re7$3brilliant. ClassNAG3positive;1/2/4/6/9explicitnegative. UnannotatedmovesUNKNOWN. Coach explanationsNOTneededfortraining, onlyauditoptional.
Newgames mustcompletedfreshreview,exportandstrictPGNcompareofficialmoves. VerifyeachBrilliant and deterministicnon3sampleviareviewmove clicks+renderedboard; preservedisagreements flagged. Add2explicitnear-best hardcontrolscaptures/recaptures orpieceoffersfromunannotatedmoves pergame; UIlabelsrequired. EasyNAGblunders shouldremainseparatelycounted becausemodelqualitygatesalreadyrejectthem. Saveaftereachgame, no source/modelpredselectionforreservedgames.

## CUA helpers/interfaces
trainingFenPieces(fen) parsesexpectedpostboard tosorted strings wq:66 etc. UI pieces #board-analysis-board .piece class matches ([wb][prnbqk]) and square-(\d\d). Move click wc-move-list [data-node="0-(ply-1)"]. Feedback .move-feedback-box-description text label, .move-feedback-box-move .move-san-san SAN. StrictSANandfullboardrequired. Do notclickExplain(itmovesboardPV); coachnotneeded. AlwaysgetfreshAX/DOMafteraction. UseCuaonlyforUI; DOMread-onlyevaluateallowedforvisibletextbox/class attributes, nofetch/hiddenstate. trainingFs hostnodefs allowedlocalpersistence.
ExportUI accessibility ShareGamebutton inellipsis. DialogPGN textbox getByRole(textbox,namePGN,exacttrue). Read .value withlocator.evaluate. Close dialog thenGameReviewbutton. OnefreshTab/game toavoidoldmemoryleak.

## Next
1. GetfirstqueuesfromResearch_repo thenlaunchroot+Pilotdisjointcollections immediately. No needwaitentirelargerqueue.
2. Rootprepareboundedlocalstudyhelpersto parseexport/validateofficialPGNs/deduplicate/evidencecounts; reusecorpus.py, python-chess tmpdep. No generaltoolkit/infrastructure.
3. Keep source+timestamps/reviewsettings and allrawexports. Freezegamehashsplitbeforelabels; assessment excludeoldreviewedgames/canonicalpositions.
4. Onceenoughusefuldata/ifearly, experimentalresearchbranch only, no productionmodel changes. Retainoldtest400labels ifpromotedtraining; theyarenotindependenttestofnewcandidate. Usenewreservedwholegames. SamefixedSF18/300kdomainforexperiment, nativeSF19notvalidated. No numericalperformancepromises.


## Resource-phase receipt 2026-11-03T15:55:00.431893+00:00

Batch02 successful recovery is `engine-batches/batch-02-recovery-1` (17 training games,133 cases,336 snapshots;94s,0physical unknown). Original incomplete batch02 remains preserved. A+B reviews resumed; no concurrent engine/metadata. After A closes remaining four wave3 games, research_repo owns its slot for one A metadata gallery (≤300 cards, pressure1/free≥35%), then closes and directly hands new immutable A queue back to collector A. Batch03 preparation permitted at20 unprocessed training games; engine execution still root GO. Counts live in COUNTS.json, currently49games/1,115labels/54Brilliants/269hardordinary/358boardchecks/0conflicts.


## Active bounded import worker — 2026-11-03 16:13 UTC

Root explicitly authorized one study-only background process. PID50477, exec session50369. Command: `python3 research/brilliants-training-overnight-2026-11-03/import-worker.py`. It is now the SOLE SQLite writer: do not run the importer manually while active. Every30seconds it checks completed-file markers; changed completed games trigger the existing importer, then `prepare-engine-batch.py --batch <next> --min-games 20` freezes each available next training batch. It never runs an engine or fits a model. Invalid/incomplete JSON is skipped until a completed artifact is ready. Raw exports remain unchanged.

Checkpoint `IMPORT-WORKER-STATE.json`; append log `import-worker.log`; launch receipt `IMPORT-WORKER-LAUNCH.json`. Stop by creating `research/brilliants-training-overnight-2026-11-03/STOP_IMPORT`; wait until checkpoint status=stopped before any other database writer. Fixed stop:2026-11-03T23:57:39Z, a120-second saved-data verification grace after collection deadline. No auto-restart.

At launch:82completedgames,1,979labels,88Brilliants,449hardordinary,603individualboardchecks,0conflicts. Sealed assessment remains unscored. Current counts are always in COUNTS.json.
