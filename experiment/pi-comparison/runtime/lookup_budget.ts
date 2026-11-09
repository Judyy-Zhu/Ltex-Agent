/** Bound information-only model turns, not verifier time or mathematical content. */
import {existsSync,readFileSync,writeFileSync,renameSync} from "node:fs";
import {createHash} from "node:crypto";

const read=(root:string,name:string,fallback:any)=>existsSync(`${root}/${name}`)?JSON.parse(readFileSync(`${root}/${name}`,"utf8")):fallback;
export function lookupPhase(root:string){
  const job=read(root,"job.json",{});
  const rounds=read(root,"task-rounds.json",{rounds:[]});
  const candidateSeen=rounds.rounds.some((r:any)=>r.kind==="candidate");
  const limit=job.direct_protocol && job.direct_candidate_ready && !candidateSeen?0:job.compact_protocol?job.lookup_turn_limit:null;
  const cycle=`${rounds.window_start??0}:${rounds.rounds.length}`;
  const state=read(root,"lookup-budget.json",{turns:[],violations:[]});
  const used=state.turns.filter((v:any)=>v.cycle===cycle).length;
  return {limit:typeof limit==="number"?limit:null,cycle,used,remaining:typeof limit==="number"?Math.max(0,limit-used):null,
    candidate_required:typeof limit==="number"&&used>=limit};
}

export function recordLookupTurn(root:string,message:{timestamp:number,content:any[]}){
  const phase=lookupPhase(root);
  const calls=message.content.filter(part=>part.type==="toolCall");
  if(phase.limit===null || !calls.length || calls.some(call=>call.name==="submit_candidate"))return false;
  const state=read(root,"lookup-budget.json",{turns:[],violations:[]});
  const id=createHash("sha256").update(JSON.stringify([message.timestamp,message.content])).digest("hex");
  if(state.turns.some((v:any)=>v.id===id))return state.violations.some((v:any)=>v.id===id);
  const event={id,cycle:phase.cycle,tools:calls.map(call=>call.name),utc:new Date().toISOString()};
  state.turns.push(event);
  const violation=phase.used>=phase.limit;
  if(violation)state.violations.push(event);
  writeFileSync(`${root}/lookup-budget.json.tmp`,JSON.stringify(state));renameSync(`${root}/lookup-budget.json.tmp`,`${root}/lookup-budget.json`);
  return violation;
}

export function boundLookupPayload(root:string,payload:any){
  if(!lookupPhase(root).candidate_required)return payload;
  return {...payload,tools:payload.tools?.filter((tool:any)=>tool.function?.name==="submit_candidate"),
    tool_choice:{type:"function",function:{name:"submit_candidate"}}};
}
