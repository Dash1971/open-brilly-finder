// Bounded200-case input adapter for the existing native forest parity check.
// Run only after root confirms restored native source is ready. No engines or fitting.
import {readFileSync,writeFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {DatabaseSync} from 'node:sqlite';
import {evaluateBrilliantForest} from '/private/tmp/mute-precision-native/ui/analyse/src/noSweatBrilliantForest.ts';
import * as native from '/private/tmp/mute-precision-native/ui/analyse/src/noSweatClassify.ts';
import * as independent from '../sources/native/ui/analyse/src/noSweatClassify.ts';
const root=new URL('../',import.meta.url),out=new URL('./',import.meta.url);
const load=(p:URL)=>JSON.parse(readFileSync(p,'utf8'));const hash=(p:URL|string)=>createHash('sha256').update(readFileSync(p)).digest('hex');
if(process.argv[2]!=='--root-go')throw Error('Explicit root GO required');
const data=load(new URL('sf18-core.json',root)),pred=load(new URL('predictions.json',out));
if(data.targets.length!==200||pred.rows.length!==200)throw Error('Expected exactly200 frozen cases');
const expected=new Map<string,any>(pred.rows.map((r:any)=>[r.key,r]));
const db=new DatabaseSync(new URL('workingassessment.db',root),{readOnly:true});const query=db.prepare('select * from positions where game_id=? and ply=?');
const cache=new Map<string,number>();const material=(f:string)=>{if(!cache.has(f))cache.set(f,native.naiveMaterial(f));return cache.get(f)!};
const helpers={rawOffer:native.isMuteSacrifice,ecMaterial:material,isSacrifice:(b:string,a:string)=>native.isSacrifice(b,a,material),matingAcceptance:native.hasMatingAcceptance,checkedContinuation:native.continuedOfferWhileInCheck,phaseRelevant:native.convertedMaterialOrEndgame,normalized:native.normalized,winChance:native.winChance};
const rows:any[]=[],features:any[]=[],scores:any[]=[],integration:any[]=[],ec:any[]=[];let maxFloat=0;const started=Date.now();
for(const t of data.targets){
 const key=t.game_id+':'+t.ply,want=expected.get(key);if(!want)throw Error('Missing reference '+key);
 const ss=t.snapshot_ids.map((id:string)=>data.snapshots[id]);const played:any=query.get(t.game_id,t.ply);
 if(!played||played.uci!==t.uci||played.fen_before!==ss.at(-2).fen||played.fen_after!==ss.at(-1).fen)throw Error('PGN identity mismatch '+key);
 const input={positions:ss.map((s:any)=>s.fen),reviews:ss.map((s:any)=>({current:s.current,previous:s.previous||undefined,terminal:s.terminal,quality:'fixed-sf18:'+data.engine_sha256})),move:played.uci};
 const start=performance.now(),actual=evaluateBrilliantForest(input,helpers),diff:any[]=[];
 for(const w of ['current','previous'] as const){const a=actual.windows[w],b=want.features.windows[w];for(const name of new Set([...Object.keys(a.features),...Object.keys(b.features)])){const av=a.features[name],bv=b.features[name];if(av!==bv){if(typeof av==='number'&&typeof bv==='number'&&Math.abs(av-bv)<1e-10)maxFloat=Math.max(maxFloat,Math.abs(av-bv));else diff.push({window:w,feature:name,actual:av,expected:bv});}}if(a.eligible!==b.eligible)diff.push({window:w,feature:'eligible',actual:a.eligible,expected:b.eligible});}
 if(actual.confidenceSufficient!==want.features.confidence_sufficient)diff.push({feature:'confidence'});if(diff.length)features.push({key,differences:diff});
 if(actual.awarded!==want.selective.award||(['current','previous'] as const).some(w=>Math.abs(actual.windowScores[w]-want.selective.window_scores[w])>1e-12))scores.push({key,actual:actual.windowScores,expected:want.selective,awarded:actual.awarded});
 const integrated=native.classify({...input,policy:'mute-brilliant-v5'},material);if((integrated.symbol==='!!')!==want.selective.award)integration.push({key,actual:integrated,expected:want.selective.award});
 const nativeEC=native.classify({...input,policy:'en-croissant'},material),fixedEC=independent.classify({...input,policy:'en-croissant'},material);if(JSON.stringify(nativeEC)!==JSON.stringify(fixedEC))ec.push({key,nativeEC,fixedEC});
 rows.push({key,features:actual.windows,confidence:actual.confidenceSufficient,scores:actual.windowScores,awarded:actual.awarded,diagnostics:actual.diagnostics,integrated,nativeEC,milliseconds:performance.now()-start});
}
db.close();const model='/private/tmp/mute-precision-native/ui/analyse/src/noSweatBrilliantForestModel.json';
const summary={scope:'Saved SF18 inputs only; native SF19 domain remains unvalidated. No cached predictor substitution.',cases:rows.length,hashes:{driver:hash(new URL(import.meta.url)),core:hash(new URL('sf18-core.json',root)),database:hash(new URL('workingassessment.db',root)),predictions:hash(new URL('predictions.json',out)),module:hash('/private/tmp/mute-precision-native/ui/analyse/src/noSweatBrilliantForest.ts'),classifier:hash('/private/tmp/mute-precision-native/ui/analyse/src/noSweatClassify.ts'),model:hash(model)},modelByteEqual:hash(model)==='44704ac06378d3f671a4eed959e21959f759c0437c71af1f9119d1081293c0b7',featureMismatchCases:features.length,scoreMismatchCases:scores.length,integrationMismatchCases:integration.length,ecFullObjectMismatchCases:ec.length,physicalUnknownCases:rows.filter(r=>r.diagnostics.physicalUnknown).map(r=>r.key),maxFloatingDifference:maxFloat,elapsed_ms:Date.now()-started,maxRSS:process.resourceUsage().maxRSS};
writeFileSync(new URL('native-parity-trace.json',out),JSON.stringify({summary,featureDifferences:features,scoreDifferences:scores,integrationDifferences:integration,ecDifferences:ec,rows},null,2)+'\n');writeFileSync(new URL('native-parity-summary.json',out),JSON.stringify(summary,null,2)+'\n');console.log(JSON.stringify(summary));
