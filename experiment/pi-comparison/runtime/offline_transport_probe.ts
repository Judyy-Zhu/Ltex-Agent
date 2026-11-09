/** Offline test entry: execute the REAL extension tools through Pi, no LLM. */
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import registerTools,{assertTextOnlyPayload,assertTaskRoundsAvailable} from "./tools.ts";

type DynamicTool={name:string;execute:(...args:unknown[])=>Promise<unknown>};

export default function(pi:ExtensionAPI){
  const registered=new Map<string,DynamicTool>();
  const capture=Object.create(pi) as ExtensionAPI;
  capture.registerTool=definition=>{
    registered.set(definition.name,definition as unknown as DynamicTool);
    pi.registerTool(definition);
  };
  registerTools(capture);
  // An accidental model request fails locally, before any network operation.
  pi.registerProvider("paratera",{api:"openai-completions",streamSimple(){throw new Error("Offline transport test forbids model calls");}});
  pi.registerCommand("offline-transport-probe",{
    description:"Offline test of actual persistent tool transport",
    async handler(_args,ctx){
      const root=process.env.EUCLID_RUN_ROOT;
      const language=process.env.EUCLID_TEST_LANGUAGE;
      if(!root || !language)throw new Error("Offline fixture missing");
      const job=JSON.parse(readFileSync(`${root}/job.json`,"utf8")) as {task_id:string;required_clause_ids:string[];primary_item_id:string;primary_item_kind:string;candidate_protocol?:string;offline_round_failure?:boolean};
      const symbol="transportProbe_"+job.task_id.replace(/[^A-Za-z0-9_]/g,"_");
      const call=async(name:string,args:Record<string,unknown>)=>{
        const tool=registered.get(name);
        if(!tool)throw new Error("Tool not registered: "+name);
        const reply=await tool.execute("offline",args,new AbortController().signal,undefined,ctx) as {isError?:boolean;details:Record<string,unknown>};
        if(reply.isError)throw new Error(JSON.stringify(reply.details));
        return reply.details;
      };
      const ext=language==="lean"?"lean":"lit";
      if(job.candidate_protocol==="whole_task"){
        const budget=await call("remaining_budget",{});
        if(budget.deadline_remaining_seconds!==null || budget.check_calls_remaining!==null)throw new Error("Unexpected time or check-count cap");
        const source=(good:boolean)=>language==="lean"?
          `def ${symbol} : Nat := 2\ntheorem ${symbol}_proof : ${symbol} = ${good?2:3} := by rfl\n`:
          `have ${symbol} R = 2\nthm ${symbol}_proof:\n    ? ${symbol} = ${good?2:3}\n    ${symbol} = ${good?2:3}\n`;
        for(let round=1;round<=5;round++){
          await call("write_source",{path:`candidate.${ext}`,content:source(round===5&&!job.offline_round_failure)});
          const checked=await call("check",{path:`candidate.${ext}`,mode:"incremental"});
          if(Boolean(checked.passed)!==(round===5&&!job.offline_round_failure))throw new Error("Unexpected candidate outcome");
        }
        if(job.offline_round_failure){
          let blocked=false;try{assertTaskRoundsAvailable(root);}catch{blocked=true;}
          if(!blocked)throw new Error("Sixth model request was not blocked");
        }else{
          assertTaskRoundsAvailable(root);
          await call("write_source",{path:"interfaces.json",content:"{}"});
          await call("write_source",{path:`final.${ext}`,content:"",base:"accepted"});
          const final=await call("check",{path:`final.${ext}`,mode:"final"});
          if(!final.passed)throw new Error("Fifth-round success cannot finalize");
          await call("submit",{submission:{task_id:job.task_id,language,agent_claim:"complete",source_files:[`final.${ext}`],
            interfaces_file:"interfaces.json",clause_mapping:[],dependencies:[],assumptions:[],unfinished:[],final_receipt_id:final.receipt_id}});
        }
        writeFileSync(`${root}/offline-pi.json`,JSON.stringify({passed:true,language,whole_task_rounds:5,model_calls:0}));
        return;
      }
      assertTextOnlyPayload({messages:[{content:[{type:"text"}]}]});
      for(const type of ["image_url","input_image","image"]){
        let blocked=false;
        try{assertTextOnlyPayload({messages:[{content:[{type}]}]});}catch{blocked=true;}
        if(!blocked)throw new Error("Image payload bypassed the text-only guard");
      }
      await call("remaining_budget",{});
      await call("read_input",{path:"seed-interface.json"});
      const textInputsRead:string[]=[];
      if(existsSync(`${root}/input/source-manifest.json`)){
        const manifestReply=await call("read_input",{path:"source-manifest.json"});
        const manifest=JSON.parse(String(manifestReply.text)) as {reading_policy:{primary_text_files:string[]}};
        for(const path of manifest.reading_policy.primary_text_files){
          const reply=await call("read_input",{path});
          if(!path.endsWith(".txt") || typeof reply.text!=="string" || !reply.text.trim())throw new Error("Missing primary text input");
          textInputsRead.push(path);
        }
      }
      await call("read_docs",{topic:"workflow"});
      await call("read_docs",{topic:"feedback"});
      await call("read_docs",{topic:"items"});
      await call("write_source",{path:`one.${ext}`,content:language==="lean"?`def ${symbol} : Nat := 2\n`:`have ${symbol} R = 2\n`,
        item_id:job.primary_item_kind==="definition"?job.primary_item_id:job.task_id+":aux:value",item_kind:"definition"});
      const first=await call("check",{path:`one.${ext}`,mode:"incremental"});
      await call("write_source",{path:`two.${ext}`,content:language==="lean"?`example : ${symbol} = 2 := by rfl\n`:`${symbol} = 2\n`,
        item_id:job.primary_item_kind==="proof"?job.primary_item_id:job.task_id+":aux:proof",item_kind:"proof"});
      const second=await call("check",{path:`two.${ext}`,mode:"incremental"});
      const firstSession=first.session as {session_pid:number};
      const secondSession=second.session as {session_pid:number};
      if(!first.passed || !second.passed || firstSession.session_pid!==secondSession.session_pid)throw new Error("Native session was not preserved across Pi tools");
      const library=await call("read_library",{symbols:["accepted_prefix"]});
      const source=(library.session as {accepted_source:string}).accepted_source;
      if(!source.includes("geo_det"))throw new Error("Frozen seed missing from source export");
      await call("write_source",{path:"interfaces.json",content:"{}"});
      await call("write_source",{path:`final.${ext}`,content:"",base:"accepted"});
      const final=await call("check",{path:`final.${ext}`,mode:"final"});
      const submission=await call("submit",{submission:{task_id:job.task_id,language,agent_claim:"complete",
        source_files:[`final.${ext}`],interfaces_file:"interfaces.json",clause_mapping:job.required_clause_ids.map(clause_id=>({clause_id,declarations:[symbol],explanation:"Offline fixture only, not a Euclid proof"})),
        dependencies:[],assumptions:[],unfinished:[],final_receipt_id:final.receipt_id}});
      if(!submission.received)throw new Error("Submission transport failed");
      const after=await call("check",{path:`two.${ext}`,mode:"incremental"});
      const retries=await call("read_library",{symbols:["retry_stats"]});
      if(retries.attempt_count!==2 || retries.retry_count!==0)throw new Error("Final/replay/cache incorrectly counted as retries");
      if(!final.passed || (after.session as {session_pid:number}).session_pid!==firstSession.session_pid)throw new Error("Final check changed the incremental session");
      writeFileSync(`${root}/offline-pi.json`,JSON.stringify({passed:true,language,native_pid:firstSession.session_pid,final_passed:final.passed,text_inputs_read:textInputsRead,image_payload_guard:true,model_calls:0}));
    },
  });
}
