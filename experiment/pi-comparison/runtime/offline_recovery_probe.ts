/** Deterministic agent-loop stream fixtures. No HTTP client or model request. */
import { appendFileSync,existsSync,readFileSync,writeFileSync } from "node:fs";
import { createAssistantMessageEventStream,type AssistantMessage } from "@earendil-works/pi-ai";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import registerTools,{providerAttemptOffset,assertTaskRoundsAvailable,activeToolSchemas} from "./tools.ts";
import {boundLookupPayload} from "./lookup_budget.ts";

export default function(pi:ExtensionAPI){
  registerTools(pi);
  const root=process.env.EUCLID_RUN_ROOT!;
  const job=JSON.parse(readFileSync(`${root}/job.json`,"utf8"));
  if(job.auto_finalize)writeFileSync(`${root}/offline-active-schemas.json`,JSON.stringify(activeToolSchemas(job)));
  const settings=job.offline_recovery_fixture??{};
  const statePath=`${root}/offline-stream-state.json`;
  let attempt=providerAttemptOffset(root);
  const log=(entry:object)=>appendFileSync(`${root}/provider.jsonl`,JSON.stringify({utc:new Date().toISOString(),offline_stub:true,...entry})+"\n");
  pi.registerProvider("paratera",{api:"openai-completions",streamSimple(model,context){
    assertTaskRoundsAvailable(root);
    const stream=createAssistantMessageEventStream();
    queueMicrotask(()=>{
      const state=existsSync(statePath)?JSON.parse(readFileSync(statePath,"utf8")):{step:0};
      const initiallyReleased=existsSync(`${root}/reconnect.allow`) ||
        (settings.initial_release_after!==undefined && (state.initial_failures??0)>=settings.initial_release_after);
      const initialFailure=Boolean(settings.initial_network && !initiallyReleased);
      const gapStep=job.compact_protocol?1:2;
      const goodStep=job.compact_protocol?2:3;
      if(settings.initial_network && !initialFailure && state.step===gapStep)state.step=goodStep;
      const id=++attempt;
      log({kind:"request",attempt:id});
      const failure=initialFailure || (!settings.direct_candidate_probe && settings.lookup_turns===undefined && !settings.initial_network && (state.step===gapStep && !settings.force_compaction_stop || (state.step===goodStep && settings.hold_network && !existsSync(`${root}/reconnect.allow`))));
      const message:AssistantMessage={role:"assistant",content:[],api:"openai-completions",provider:"paratera",model:model.id,
        timestamp:Date.now(),stopReason:failure?"error":"toolUse",usage:{input:10,output:2,cacheRead:0,cacheWrite:0,totalTokens:12,
          cost:{input:0,output:0,cacheRead:0,cacheWrite:0,total:0}}};
      if(failure){
        if(initialFailure)state.initial_failures=(state.initial_failures??0)+1;
        else state.step=goodStep;
        writeFileSync(statePath,JSON.stringify(state));
        message.errorMessage=settings.auth_error?"HTTP 401 invalid API key (offline fixture)":"fetch failed: network connection lost (offline fixture)";
        log({kind:"response",attempt:id,status:settings.auth_error?401:503});
        stream.push({type:"error",reason:"error",error:message});stream.end();return;
      }
      log({kind:"response",attempt:id,status:200});
      log({kind:"usage",attempt:id,usage:{prompt_tokens:10,completion_tokens:2,total_tokens:12}});
      const ext=job.language==="lean"?"lean":"lit";
      if(settings.initial_network && state.step===0){
        if(!JSON.stringify(context).includes('TOOL.SMOKE'))throw new Error('Original source task prompt was not restored');
        writeFileSync(`${root}/initial-context-restored.json`,JSON.stringify({original_task:true}));
      }
      const source=(good:boolean)=>job.language==="lean"?
        `theorem checkpointProof : (2 : Nat) = ${good?2:3} := by ${good?"rfl":"decide"}\n`:
        `thm checkpointProof:\n    ? 2 = ${good?2:3}\n    2 = ${good?2:3}\n`;
      let name="",args:Record<string,unknown>={};
      if(settings.direct_candidate_probe){
        const payload=boundLookupPayload(root,{tools:Object.keys(activeToolSchemas(job)).map(name=>({type:"function",function:{name}}))});
        appendFileSync(`${root}/offline-direct-payloads.jsonl`,JSON.stringify(payload)+"\n");
        if(state.step>0 && !JSON.stringify(context).includes("deterministic_local_error_routing"))throw new Error("Local repair hints were not delivered with the native failure");
        if(settings.direct_lookup_after_failure && state.step===1){name="read_docs";args={topic:"core",query:"theorem proof"};}
        else{name="submit_candidate";args={code:source(!settings.direct_bad_first || state.step>0)};}
      }else if(settings.lookup_turns!==undefined){
        const payload=boundLookupPayload(root,{tools:Object.keys(activeToolSchemas(job)).map(name=>({type:"function",function:{name}}))});
        appendFileSync(`${root}/offline-lookup-payloads.jsonl`,JSON.stringify(payload)+"\n");
        const lookup=state.step<settings.lookup_turns || state.step===settings.lookup_turns && settings.lookup_violation;
        name=lookup?"read_docs":"submit_candidate";
        args=lookup?{topic:"core",query:"theorem proof"}:{code:source(true)};
      }else if(job.compact_protocol){
        switch(state.step){
          case 0:message.content.push({type:"text",text:"checkpoint-fixture-marker"+(settings.force_compaction_stop?" Offline long-context fixture.".repeat(1000):"")});name="submit_candidate";args={code:source(Boolean(settings.compact_good_first))};break;
          case 1:message.stopReason="stop";message.content.push({type:"text",text:"Offline local compaction fixture."});break;
          case 2:{
            const text=JSON.stringify(context);
            if(!text.includes("checkpoint-fixture-marker") || !text.includes("toolResult"))throw new Error("Saved atomic candidate feedback was not restored");
            writeFileSync(`${root}/restored-context.json`,JSON.stringify({marker:true,tool_results:true}));
            name="submit_candidate";args={code:source(true)};break;
          }
          default:message.stopReason="stop";message.content.push({type:"text",text:"Offline compact fixture finished."});
        }
      }else{
      switch(state.step){
        case 0:message.content.push({type:"text",text:"checkpoint-fixture-marker"+(settings.force_compaction_stop?" Offline long-context fixture.".repeat(1000):"")});name="write_source";args={path:`candidate.${ext}`,content:source(false)};break;
        case 1:name="check";args={path:`candidate.${ext}`,mode:"incremental"};break;
        case 2:message.stopReason="stop";message.content.push({type:"text",text:"Offline fixture requests local compaction."});break;
        case 3:{
          const text=JSON.stringify(context);
          if(!text.includes("checkpoint-fixture-marker") || !text.includes("toolResult"))throw new Error("Saved agent conversation was not restored");
          writeFileSync(`${root}/restored-context.json`,JSON.stringify({marker:true,tool_results:true}));
          name="write_source";args={path:`candidate.${ext}`,content:source(true)};break;
        }
        case 4:name="check";args={path:`candidate.${ext}`,mode:"incremental"};break;
        case 5:name="write_source";args={path:"interfaces.json",content:"{}"};break;
        case 6:name="write_source";args={path:`final.${ext}`,content:"",base:"accepted"};break;
        case 7:name="check";args={path:`final.${ext}`,mode:"final"};break;
        case 8:{
          const control=JSON.parse(readFileSync(`${root}/state.json`,"utf8"));
          name="submit";args={submission:{task_id:job.task_id,language:job.language,agent_claim:"complete",source_files:[`final.${ext}`],
            interfaces_file:"interfaces.json",clause_mapping:[],dependencies:[],assumptions:[],unfinished:[],final_receipt_id:control.last_final_receipt}};break;
        }
        default:message.stopReason="stop";message.content.push({type:"text",text:"Offline recovery fixture completed."});
      }
      }
      if(name)message.content.push({type:"toolCall",id:`offline-recovery-${state.step}`,name,arguments:args});
      state.step++;writeFileSync(statePath,JSON.stringify(state));
      stream.push({type:"done",reason:message.stopReason as "stop"|"toolUse",message});stream.end();
    });
    return stream;
  }});
}
