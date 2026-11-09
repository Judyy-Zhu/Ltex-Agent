/** Deterministic task checkpoint. Never calls a model or rewrites mathematical content. */
import {existsSync,readFileSync,readdirSync,appendFileSync} from "node:fs";
import {createHash} from "node:crypto";
import {basename} from "node:path";

export function localCheckpoint(root:string){
  const read=(path:string)=>JSON.parse(readFileSync(`${root}/${path}`,"utf8"));
  const job=read("job.json");
  const parts=[`Local durable checkpoint for ${job.task_id}, language ${job.language}. Original session history remains on disk. `+
    `Continue the same complete candidate; do not reset attempts. Native session replay is controller-owned. `+
    (job.compact_protocol?`Submit the complete repaired source with submit_candidate({code}). `:
      `Write candidate.${job.language==="lean"?"lean":"lit"}, base=none, and call check(incremental). `)+
    `The controller handles final verification and submission. Stop when task_completed=true. `+
    `This is a mechanical state snapshot, not a semantic summary or a proof.`];
  if(existsSync(`${root}/input/task.json`))parts.push("TASK:\n"+readFileSync(`${root}/input/task.json`,"utf8"));
  if(existsSync(`${root}/input/source-manifest.json`)){
    const manifest=read("input/source-manifest.json");
    for(const name of manifest.reading_policy.primary_text_files){
      if(basename(name)!==name)throw new Error("Unexpected source checkpoint path");
      // Always preserve original statement/proof text verbatim, with no model rewrite.
      parts.push(`PRIMARY ORIGINAL TEXT ${name}:\n`+readFileSync(`${root}/input/${name}`,"utf8"));
    }
    parts.push("Additional original context: "+JSON.stringify(manifest.reading_policy.context_text_files));
  }
  parts.push("The immutable technical seed and FULL published own-language predecessor library are already loaded by the verifier. Never redeclare their symbols. "+
    (job.compact_protocol?"The short operation card and task protocol remain in SYSTEM. Intact full references are available by read_docs(topic,section); query a specific missing rule rather than rereading for initialization. ":
      "The core language guide, basic examples, checked generic proof structures and whole-task protocol remain in the SYSTEM prompt; do not reread them merely because compaction occurred. ")+
    "read_docs(feedback) is available for a specific unresolved diagnostic-field question. Next repair the current candidate using the actual error and check it.");
  for(const name of ["foundation.json","seed-interface.json",`seed.${job.language==="lean"?"lean":"lit"}`]){
    if(existsSync(`${root}/input/${name}`))parts.push(`FROZEN INPUT ${name} (already supplied; retained verbatim):\n`+readFileSync(`${root}/input/${name}`,"utf8"));
  }
  const entries=job.library?.index?.entries??[];
  if(job.direct_protocol && existsSync(`${root}/input/direct-context.json`)){
    const context=read("input/direct-context.json");
    parts.push("ALREADY PROVIDED DIRECT LIBRARY CONTEXT (display only, verifier source unchanged):\n"+
      JSON.stringify({library_complete:context.library_complete,library_source_sha256:context.library_source_sha256})+"\n"+context.library_code);
    for(const [name,text] of Object.entries(context.original_context??{}))parts.push(`ORIGINAL CONTEXT ${name}:\n${text}`);
  }
  parts.push("OWN-LANGUAGE PUBLISHED LIBRARY (all entries are loaded in the verifier; source can be retrieved by entry:task_id or exact symbol name):\n"+
    JSON.stringify({total_entries:entries.length,latest_entries:entries.slice(-10).map((e:{task_id:string,symbols:string[]})=>({task_id:e.task_id,symbols:e.symbols}))}));
  if(existsSync(`${root}/context-memory.json`))parts.push("MATERIAL ALREADY RETRIEVED AND RECENT PATH ERRORS:\n"+JSON.stringify(read("context-memory.json")));
  if(existsSync(`${root}/task-rounds.json`))parts.push("ATTEMPT HISTORY:\n"+JSON.stringify(read("task-rounds.json")));
  const candidate=`candidate.${job.language==="lean"?"lean":"lit"}`;
  if(existsSync(`${root}/work/${candidate}`)){
    const source=readFileSync(`${root}/work/${candidate}`,"utf8");
    parts.push(`CURRENT CANDIDATE ${candidate}; SHA256 ${createHash("sha256").update(source).digest("hex")}:\n`+
      (source.length<=12000?source:`Source exceeds checkpoint inline limit. Retrieve its full unchanged contents with read_library(["file:${candidate}"]).`));
  }
  const receipts=readdirSync(`${root}/receipts`).filter(p=>/^check-\d+\.json$/.test(p)).sort();
  if(receipts.length){
    const receipt=read(`receipts/${receipts.at(-1)}`);
    parts.push("LATEST CHECK:\n"+JSON.stringify({receipt_id:receipt.receipt_id,mode:receipt.mode,entry:receipt.entry,
      passed:receipt.passed,error:receipt.error,full_receipt:`receipt:${receipt.receipt_id}`}));
    const failures=(receipt.native_frames??[]).filter((f:{passed:boolean,replay:boolean})=>!f.replay&&!f.passed);
    const native=failures.at(-1)?.native;
    const errors=native && JSON.stringify({errors:native.errors,messages:native.messages,error:native.error,sorries:native.sorries});
    if(errors)parts.push(errors.length<=6000?"NATIVE FAILURE FIELDS (verbatim):\n"+errors:
      `Native failure is too large for the checkpoint. Read read_library(["receipt:${receipt.receipt_id}"]) for full original diagnostics before repairing.`);
    if(job.direct_protocol && existsSync(`${root}/last-direct-repair.json`))parts.push("LOCAL REPAIR HINTS (reference only):\n"+readFileSync(`${root}/last-direct-repair.json`,"utf8"));
  }
  if(existsSync(`${root}/auto-finalization.json`))parts.push("LOCAL FINALIZATION:\n"+JSON.stringify(read("auto-finalization.json")));
  return parts.join("\n\n");
}

export function recordLocalCompaction(root:string,reason:string,tokensBefore:number,summary:string){
  appendFileSync(`${root}/local-compactions.jsonl`,JSON.stringify({utc:new Date().toISOString(),
    reason,tokens_before:tokensBefore,summary_sha256:createHash("sha256").update(summary).digest("hex"),
    summary_characters:summary.length,model_calls:0})+"\n");
}
