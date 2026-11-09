/** Explicitly loaded Pi extension. No shell/read/write builtins are enabled. */
import { spawn, type ChildProcessWithoutNullStreams } from "node:child_process";
import { createInterface } from "node:readline";
import { appendFileSync, existsSync, readFileSync, readdirSync } from "node:fs";
import { createHash } from "node:crypto";
import { fileURLToPath } from "node:url";
import { Type, openAICompletionsApi } from "@earendil-works/pi-ai";
import { defineTool, type ExtensionAPI } from "@earendil-works/pi-coding-agent";
import {localCheckpoint,recordLocalCompaction} from "./local_compaction.ts";
import {recordLookupTurn,boundLookupPayload} from "./lookup_budget.ts";

const root = process.env.EUCLID_RUN_ROOT;
if (!root) throw new Error("EUCLID_RUN_ROOT is required");
const host = fileURLToPath(new URL("./tool_host.py", import.meta.url));
const schemas = {
  read_input: Type.Object({path: Type.String()}),
  read_docs: Type.Object({topic: Type.String()}),
  read_library: Type.Object({symbols: Type.Array(Type.String())}),
  write_source: Type.Object({path: Type.String(), content: Type.String(), base: Type.Optional(Type.Union([Type.Literal("none"),Type.Literal("library"),Type.Literal("accepted")])),
    item_id: Type.Optional(Type.String()), item_kind: Type.Optional(Type.Union([Type.Literal("definition"),Type.Literal("proof"),Type.Literal("scope")]))}),
  check: Type.Object({path: Type.String(), mode: Type.Union([Type.Literal("incremental"), Type.Literal("final")])}),
  remaining_budget: Type.Object({}),
  submit: Type.Object({submission: Type.Object({
    task_id: Type.String(), language: Type.Union([Type.Literal("lean"), Type.Literal("litex")]),
    agent_claim: Type.Union([Type.Literal("complete"), Type.Literal("incomplete"), Type.Literal("environment_blocked")]),
    source_files: Type.Array(Type.String()), interfaces_file: Type.Union([Type.String(),Type.Null()]),
    clause_mapping: Type.Array(Type.Object({clause_id:Type.String(), declarations:Type.Array(Type.String()), explanation:Type.String()})),
    dependencies: Type.Array(Type.String()), assumptions: Type.Array(Type.String()),
    final_receipt_id: Type.Union([Type.String(),Type.Null()]), unfinished: Type.Array(Type.String()),
  })}),
};
const descriptions:Record<string,string>={
  read_input:"Read approved task specifications, source TXT and own-language seed text by relative path. This experiment is text-only: image and binary reads are forbidden for every task.",
  read_docs:"Read a frozen guide topic for the assigned language; unknown topics return the available topic list.",
  read_library:"Read the own-language predecessor library index and session journal. [\"entry:EUCLID.I.D001\"] retrieves an increment, [\"file:one.lean\"] a current file, [\"accepted_prefix\"] the full accepted source, [\"receipt:check-0001\"] an original receipt, [\"retry_stats\"] per-item candidate/retry counts.",
  write_source:"Follow the job's candidate protocol. In whole_task mode write the COMPLETE new task increment, including helpers, to candidate.lean or candidate.lit with base=none; the primary item ID is automatic. Repair that same file; helper names do not create extra rounds. Historical tracked_fragments jobs use one logical item per file with stable item_id/item_kind. interfaces.json needs no item metadata. base=accepted with empty content assembles seed, predecessor library and accepted source for final; final cannot introduce unchecked code. Read read_docs(items).",
  check:"incremental submits the complete candidate to the persistent native Session/REPL. Automatic completion mode then generates native metadata, independently verifies the saved final file, checks declaration/axiom dependencies and submits locally. task_completed=true ends the task without another model step. Five TOTAL whole-task attempts are shared with network/API failures. Partial prefixes do not complete a task. Final checking consumes no extra candidate attempt. Read native feedback and auto_finalization.",
  remaining_budget:"Read the whole-task round counter and optional legacy time/check limits; null means no such limit. Actual elapsed time is still measured.",
  submit:"Submit files, clause mappings, assumptions and the current successful final receipt; submission is not semantic acceptance.",
};

export function activeToolSchemas(job:{auto_finalize?:boolean,compact_protocol?:boolean,language:string}):Record<string,unknown>{
  if(job.compact_protocol)return {read_input:schemas.read_input,
    read_docs:Type.Object({topic:Type.String(),section:Type.Optional(Type.String()),sections:Type.Optional(Type.Array(Type.String())),query:Type.Optional(Type.String())}),read_library:schemas.read_library,
    submit_candidate:Type.Object({code:Type.String()},{additionalProperties:false}),remaining_budget:schemas.remaining_budget};
  if(!job.auto_finalize)return schemas;
  const path=Type.Literal(job.language==="lean"?"candidate.lean":"candidate.lit");
  return {read_input:schemas.read_input,read_docs:schemas.read_docs,read_library:schemas.read_library,
    write_source:Type.Object({path,content:Type.String(),base:Type.Optional(Type.Literal("none"))},{additionalProperties:false}),
    check:Type.Object({path,mode:Type.Literal("incremental")},{additionalProperties:false}),remaining_budget:schemas.remaining_budget};
}

export function assertTextOnlyPayload(payload:{messages?:{content?:string|{type?:string}[]}[]}){
  if(payload.messages?.some(message=>Array.isArray(message.content) &&
    message.content.some(part=>["image_url","input_image","image"].includes(part.type??"")))){
    throw new Error("Text-only experiment forbids image payloads");
  }
}

export function assertTaskRoundsAvailable(runRoot:string){
  const transactions=`${runRoot}/candidate-transactions`;
  if(existsSync(transactions) && readdirSync(transactions).some(name=>name.endsWith('.json') &&
    JSON.parse(readFileSync(`${transactions}/${name}`,"utf8")).status==="pending")){
    throw new Error("Local candidate transaction is pending recovery; no model request is permitted");
  }
  const completion=`${runRoot}/auto-finalization.json`;
  if(existsSync(completion) && ["pending","complete"].includes(JSON.parse(readFileSync(completion,"utf8")).status)){
    throw new Error("Native candidate accepted; local finalization owns this task. No further model request is permitted");
  }
  const path=`${runRoot}/task-rounds.json`;
  if(existsSync(path) && JSON.parse(readFileSync(path,"utf8")).exhausted){
    throw new Error("Whole-task round limit exhausted; no further model request is permitted");
  }
}

export function providerAttemptOffset(runRoot:string){
  const path=`${runRoot}/provider.jsonl`;
  let maximum=0;
  if(existsSync(path))for(const line of readFileSync(path,"utf8").split("\n")){
    try{const value=JSON.parse(line);if(typeof value.attempt==="number")maximum=Math.max(maximum,value.attempt);}catch{/* Torn records remain unknown in Python telemetry. */}
  }
  return maximum;
}

export default function (pi: ExtensionAPI) {
  const job=JSON.parse(readFileSync(`${root}/job.json`,"utf8"));
  if(job.auto_finalize)pi.on("session_before_compact",event=>{
    const summary=localCheckpoint(root);
    recordLocalCompaction(root,event.reason,event.preparation.tokensBefore,summary);
    return {compaction:{summary,firstKeptEntryId:event.preparation.firstKeptEntryId,
      tokensBefore:event.preparation.tokensBefore,details:{origin:"local_durable_task_checkpoint",model_calls:0}}};
  });
  type Reply = {
    content: {type:"text",text:string}[];
    details: Record<string,unknown>;
    isError?:boolean;
  };
  let broker:ChildProcessWithoutNullStreams|undefined;
  let sequence=0;
  let pending:{child:ChildProcessWithoutNullStreams,id:number,resolve:(value:Reply)=>void,reject:(error:Error)=>void}|undefined;
  const startBroker=()=>{
    if (broker && broker.exitCode===null && !broker.killed) return broker;
    const child=spawn(process.env.EUCLID_PYTHON || "python3",[host,root,"--server"],{stdio:["pipe","pipe","pipe"]});
    broker=child;
    let stderr="";
    child.stderr.on("data",chunk=>{
      stderr=(stderr+chunk).slice(-4000);
      appendFileSync(`${root}/tool-host.stderr.log`,chunk);
    });
    const lines=createInterface({input:child.stdout});
    lines.on("line",line=>{
      try {
        const message=JSON.parse(line) as {id:number,result:Reply};
        if (!pending || pending.child!==child || message.id!==pending.id) throw new Error("Unexpected tool-host response id");
        const current=pending;pending=undefined;current.resolve(message.result);
      } catch(error) {
        if(pending?.child===child){const current=pending;pending=undefined;current.reject(error instanceof Error?error:new Error(String(error)));}
        child.kill("SIGTERM");
      }
    });
    const failed=(error:Error)=>{
      if(pending?.child===child){const current=pending;pending=undefined;current.reject(error);}
      if(broker===child)broker=undefined;
    };
    child.on("error",failed);
    child.on("close",code=>{lines.close();failed(new Error(`Persistent tool host exited ${code}: ${stderr}`));});
    return child;
  };
  const stopBroker=async()=>{
    const child=broker;broker=undefined;
    if(!child || child.exitCode!==null)return;
    child.stdin.end();
    await new Promise<void>(resolve=>{
      const timer=setTimeout(()=>{child.kill("SIGTERM");resolve();},1000);
      child.once("close",()=>{clearTimeout(timer);resolve();});
    });
  };
  pi.on("session_shutdown",stopBroker);
  for (const [name, parameters] of Object.entries(activeToolSchemas(job))) {
    pi.registerTool(defineTool({
      name, label: name, description:name==="submit_candidate"?
        "Submit the COMPLETE new task source in one call. The controller saves it, runs the native incremental verifier and returns full native diagnostics plus remaining attempts. On full success it independently verifies the saved final file and completes locally. Each submission uses one of five total task attempts shared with API failures. Do not repeat the loaded seed/library declarations. Stop when task_completed=true.":
        job.compact_protocol && name==="read_docs"?
        "Look up a specific unresolved syntax/reference question. topic alone lists section IDs. Use query for up to three complete relevant sections, or sections for several exact IDs in one call, or section=all for the intact guide. Use only one of query/sections/section. The operation card is already supplied. Information-only turns are bounded equally for both languages; then submit the complete candidate.":job.auto_finalize && name==="write_source"?
        "Write the COMPLETE new task candidate, including helpers, to the assigned candidate path. The controller supplies the item ID. Do not repeat seed/predecessor definitions; they are already loaded. Next call check(incremental) and repair actual native errors. No interface, final-file or submit tool is needed.":
        job.auto_finalize && name==="read_library"?
        "Look up actual own-language published declarations by exact symbol name, e.g. [\"geo_is_point\"]. Matching source and interfaces are returned. [\"entry:EUCLID.I.D001\"] retrieves a task increment, [\"file:candidate.lean\"] or [\"file:candidate.lit\"] retrieves current work, [\"receipt:check-0001\"] returns original diagnostics. Seed and the whole published library are already in the verifier; never redeclare them.":descriptions[name], parameters:parameters as typeof schemas.read_input,
      executionMode: "sequential",
      async execute(_id, params, signal, _onUpdate, ctx) {
        const child=startBroker();
        const abort=()=>{child.kill("SIGTERM");};
        if(signal?.aborted)throw new Error("Tool call aborted");
        signal?.addEventListener("abort",abort,{once:true});
        try {
          return await new Promise<Reply>((resolve,reject)=>{
            if(pending){reject(new Error("Tool calls must be sequential"));return;}
            const id=++sequence;
            const assistant=[...ctx.sessionManager.getBranch()].reverse().find(entry=>entry.type==="message" &&
              entry.message.role==="assistant" && entry.message.content.some(part=>part.type==="toolCall" && part.id===_id));
            const operation_id=`${assistant?.id ?? ctx.sessionManager.getSessionId()}:${_id}`;
            pending={child,id,resolve,reject};
            child.stdin.write(JSON.stringify({id,operation_id,tool:name,arguments:params})+"\n");
          });
        } finally {signal?.removeEventListener("abort",abort);}
      },
    }));
  }
  // Instrument the native transport, including auxiliary compaction calls that
  // bypass Pi's ordinary agent-message hooks. Protocol serialization is unchanged.
  let attempt = providerAttemptOffset(root);
  const log = (entry: object) => appendFileSync(`${root}/provider.jsonl`, JSON.stringify({utc:new Date().toISOString(),monotonic_ms:performance.now(),...entry}) + "\n");
  pi.registerProvider("paratera", {
    api:"openai-completions",
    streamSimple(model, context, options) {
      const id = ++attempt;
      return openAICompletionsApi().streamSimple(model, context, {
        ...options,
        async onPayload(original, physicalModel) {
          assertTaskRoundsAvailable(root);
          const replacement = await options?.onPayload?.(original, physicalModel);
          const payload = boundLookupPayload(root,(replacement === undefined ? original : replacement)) as {
            tools?:{function?:{name?:string}}[],max_tokens?:number,thinking?:unknown,
            messages?:{content?:string|{type?:string}[]}[],
          };
          assertTextOnlyPayload(payload);
          log({kind:"request",attempt:id,payload_sha256:createHash("sha256").update(JSON.stringify(payload)).digest("hex"),
            max_tokens:payload.max_tokens,thinking:payload.thinking,tool_names:payload.tools?.map(tool=>tool.function?.name)});
          return payload;
        },
        async onResponse(response, physicalModel) {
          log({kind:"response",attempt:id,status:response.status});
          await options?.onResponse?.(response,physicalModel);
        },
        async onProviderStreamEvent(value, physicalModel) {
          const data = value as {usage?:unknown};
          if (data && data.usage) log({kind:"usage",attempt:id,usage:data.usage});
          await options?.onProviderStreamEvent?.(value,physicalModel);
        },
      });
    },
  });
  pi.on("message_end", (event,ctx) => {
    if (event.message.role === "assistant") {
      log({kind:"pi_message", attempt, usage:event.message.usage, stopReason:event.message.stopReason});
      if(recordLookupTurn(root,event.message))ctx.abort();
    }
  });
}
