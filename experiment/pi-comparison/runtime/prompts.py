"""Actual English system/user prompts, also available for offline inspection."""
import json
from pathlib import Path
from paths import BASE
from agent_language import require_english

KIT=BASE/'agent-kit'


def continuation_prompt(job,stats):
    common=('Continue the same source task. '+str(stats['used'])+' of '+str(stats['limit'])+
            ' total task attempts have been used. Read the last native feedback, repair the complete candidate at the same path, and call check(incremental). ')
    if job.get('compact_protocol'):
        return ('Continue the same task. Read the last native feedback and repair the complete candidate with submit_candidate({code}). ' 
                'Retain every helper needed by the complete replacement; earlier rejected candidate declarations are not published predecessors. '
                'All seed and published library source is already loaded; query only a specific unresolved issue. Five total attempts include API failures. ' 
                'Controller finalization is automatic; stop when task_completed=true.')
    if job.get('auto_finalize'):
        return common+('Read auto_finalization diagnostics if present. The controller owns indexing, final-file verification and submission. '
                       'Do not write interfaces, clause labels or final files. Stop when task_completed=true. No time limit applies. Keep explanations brief.')
    return common+'If the candidate has passed, finish final verification and submit it. No time limit applies. Keep explanations brief and use the tools.'


def build_prompts(job,*,smoke=False):
    if job.get('compact_protocol'):return compact_prompts(job)
    system='\n'.join((KIT/name).read_text() for name in
                     ('common-system.txt',job['language']+'-card.txt','feedback-common.txt','runtime-instructions.txt'))
    if job.get('candidate_protocol')=='whole_task' and not smoke:
        language=job['language']
        core=KIT/('guides/litex_short_guide.md' if language=='litex' else 'guides/lean-core.md')
        basics=KIT/f'guides/examples/basics.{"lit" if language=="litex" else "lean"}'
        system='\n\n'.join(((KIT/'common-system.txt').read_text(),(KIT/('auto-task-runtime.txt' if job.get('auto_finalize') else 'whole-task-runtime.txt')).read_text(),
            'Assigned formal language: '+language+'. Use only this language and its pinned verifier.',
            (KIT/'feedback-common.txt').read_text(),core.read_text(),basics.read_text(),
            'The examples in this approved guide are permitted reference material. Experiment rules remain binding: '
            'no axiom/trust fallback, no historical try wrappers, at most five whole-task candidate submissions, '
            'and no task or verifier time limit. Use native diagnostics to resolve historical syntax conflicts.'))
    if smoke:
        prompt=(
            'This is a real Pi tool-transport smoke test, not a Euclid proof experiment. '
            'Prove only n=n for Nat in Lean, or 2+2=4 in Litex. Do not expand the problem. '
            'Call remaining_budget, read_docs(core) and read_library([]). Save the identity as an incremental '
            'fragment and call check(incremental). Read read_library(["accepted_prefix"]) and save a complete '
            'standalone final module. Write interfaces.json before check(final), then call submit. '
            'Use task_id TOOL.SMOKE and language '+job['language']+'. '
            'clause_mapping, dependencies, assumptions and unfinished may be empty arrays. A prose-only answer is insufficient.')
    elif job.get('candidate_protocol')=='whole_task':
        prompt=(
            'Complete source-to-library formalization-translation task '+job['task_id']+'. '
            'Read task.json, source-manifest.json, every primary source TXT listed there, foundation.json, '
            'seed-interface.json and the assigned-language seed using read_input. The original source text includes '
            'statements, proofs and notes; all input is English and text-only. Read read_library([]) for your own-language '
            'published library. The complete language guide and basic examples are already in the system prompt; '
            'read_docs(core) returns that same reference. read_docs(logic) provides checked generic proof examples. '
            'Read read_docs(feedback) for the native diagnostic fields and read_docs(items) for the whole-task round protocol. '
            'Use a minimal complete translation: definitions require definitions and well-definedness, while proof tasks require checked proofs. '
            'Do not add unrequested semantic-bridge theorems. '
            'Save the complete new increment with necessary helpers in candidate.lean or candidate.lit, base="none", '
            'without repeating the frozen seed or predecessor library. The controller supplies primary item ID '+job['primary_item_id']+'. '
            'Call check(incremental), read the native feedback, and repair the complete candidate at the same path. '
            'There are '+str(job['max_task_rounds'])+' whole-task candidate rounds TOTAL, first attempt included; '
            'network/API failures also consume this shared allowance; helpers and alternate file names do not reset it. There is no time limit. '
            'After the whole candidate passes, save interfaces.json covering each required_clause with real declaration names, '
            'assemble a separate final file with base="accepted" and empty content, call check(final), and submit. '
            'Final checking and publication do not consume candidate rounds. Semantic review is optional and never blocks passing. '
            'Use English throughout; keep planning brief and submit actual code.')
    else:
        prompt=(
            'Complete the source_to_library formalization-translation task '+job['task_id']+'. '
            'First read task.json, foundation.json, seed-interface.json, the assigned-language seed source, '
            'and source-manifest.json using read_input. This is an English, text-only experiment. '
            'Read every file listed in source-manifest.reading_policy.primary_text_files. '
            'The task specification and source TXT determine the mathematical requirements. '
            'The source TXT includes the original statements, original proof text and source notes. '
            'No PNG, initial figure, auxiliary proof diagram or screenshot is provided or readable. '
            'Report missing or ambiguous initial conditions as a source-material problem; do not invent premises or seek image fallback. '
            'Retrieve needed predecessor definition texts using context_task_ids and reading_policy.context_text_files. '
            'Use read_library([]) to inspect the accumulated own-language library. Prove missing predecessor results within this budget. '
            'Read read_docs(feedback) and read_docs(items), then consult core, basics, roots, workflow, domains and seed as needed. '
            'The primary_item_id is '+job['primary_item_id']+' and primary_item_kind is '+job['primary_item_kind']+'. '
            'Use that stable ID for the main item and distinct stable IDs for auxiliary items. '
            'Write interfaces.json with declaration names, precise types, mathematical meanings, definition expansions, '
            'source-clause correspondence and encoding bridges. Cover every required_clause in task.json (C1-C5 for I.1). '
            'Preserve the frozen seed and predecessor library in the final module. Complete final checking and submit. '
            'Submission checks declarations and axiom dependencies within the remaining budget, so reserve time and checker calls. '
            'Model and prove source postulates in the selected analytic model; do not introduce unchecked assumptions. '
            'Build missing representations, including higher-dimensional objects and ratios. '
            'Automatic task success is determined by the controller final/submission checks. '
            'Semantic review is an optional post-run annotation, not a prerequisite for completion, library publication or the primary score. '
            'Do not wait for or request a human review before submitting complete work that passes the machine checks. '
            'Machine acceptance does not independently certify source fidelity. '
            'Use English for all explanations, comments, interface metadata and submission text.')
    if job.get('auto_finalize') and not smoke:
        system+='\n\nCHECKED GENERIC PROOF STRUCTURES (reference only; no Euclid task answers):\n'+Path(job['docs']['logic']).read_text()
        system+='\n\nIn this job only six tools are active. write_source accepts only path/content and optional base=none. There is no submit tool and no manual item_id/item_kind. After writing a complete candidate, check it; use on-demand reads only to answer a specific unresolved question. Seed, source, guide and library information already supplied in the prompt or checkpoint do not require ceremonial rereading. Published predecessors are already loaded in the native session and final module; never redeclare them.'
        system+='\n\nDefinition tasks can finish with checked definitions alone. Native domain/type checking suffices for formation of total definitions. Do not turn a source definition into an additional project proving existence, universal characterizations or validity of an invented interpretation. Add a proof only when the current source explicitly asserts that mathematical claim or when defining a partial operation/subtype constructor actually requires it. Proposition/proof tasks still require complete checked proofs.'
        system=system.replace('4. Actually use the checking tools to iterate, and request final checking before submission.',
            '4. Use check(incremental) to iterate; the controller performs final verification and submission automatically.')
        system=system.replace('8. Submit complete replayable source files, a public interface index, actual dependencies and assumptions, a source-clause-to-declaration mapping, the final check receipt_id and unfinished items. Follow submission.schema.json.',
            '8. Write only the complete candidate and call check(incremental). The controller owns metadata, independent final verification and submission.')
        system=system.replace('Use one file per logical definition/proof. The first write_source needs stable item_id/item_kind; keep the ID when repairing.',
            'Use one complete candidate file per original task, including all helpers. The primary item ID is automatic.')
        inputs=Path(job['seed_path']).parent
        manifest=json.loads((inputs/'source-manifest.json').read_text())
        files=['task.json','source-manifest.json',*manifest['reading_policy']['primary_text_files'],
               'foundation.json','seed-interface.json',Path(job['seed_path']).name]
        parts=['Complete formalization-translation task '+job['task_id']+' in '+job['language']+'. '+
               'The following frozen text is the actual task input, including the original proof when present. '+
               'Preserve its mathematical content. Write the complete new increment to candidate.'+
               ('lean' if job['language']=='lean' else 'lit')+' with base=none and call check(incremental). '+
               'The controller automatically verifies and saves the final result. Stop when task_completed=true. '+
               'Five total attempts, shared with API failures, first included. No time limit applies. '+
               'Do not write final files, interfaces, encoding labels or submit metadata.']
        parts.extend('INPUT '+name+'\n'+(inputs/name).read_text() for name in dict.fromkeys(files))
        entries=job.get('library',{}).get('index',{}).get('entries',[])
        parts.append('OWN-LANGUAGE LIBRARY INDEX (latest 10; full library is loaded in the verifier):\n'+
                     json.dumps({'total':len(entries),'entries':[{k:v for k,v in e.items() if k!='interfaces'} for e in entries[-10:]]}))
        parts.append('NATIVE FEEDBACK FIELD GUIDE:\n'+Path(job['docs']['feedback']).read_text())
        prompt='\n\n'.join(parts)
    require_english(system,'System prompt');require_english(prompt,'User prompt')
    return system,prompt


def compact_prompts(job):
    inputs=Path(job['seed_path']).parent
    manifest=json.loads((inputs/'source-manifest.json').read_text()) if (inputs/'source-manifest.json').exists() else {'reading_policy':{'primary_text_files':[],'context_text_files':[]}}
    system=(KIT/'compact-system.txt').read_text()+'\n\nASSIGNED LANGUAGE: '+job['language']+'\n\n'+Path(job['docs']['operation']).read_text()
    if job.get('direct_protocol'):
        from direct_context import procedures
        start=system.index('Use references for a SPECIFIC unresolved question.')
        end=system.index('Read both the controller envelope',start)
        system=system[:start]+('DIRECT CANDIDATE PROTOCOL: Your first model response must submit the complete candidate when direct_candidate_ready=true. '
            'The actual predecessor code, original context and checked procedures are provided below; do not perform initialization reads. '
            'After a rejected candidate, use the attached local repair hints and full native error to repair immediately. At most ONE information-only assistant turn is allowed between attempts, followed by a required submit_candidate call. '
            'Batch any indispensable lookup. Do not request a documentation index merely to begin. '
            'Five TOTAL attempts still include network/API failures. Keep comments and explanations brief; preserve every required mathematical claim. '
            'Do not add optional characterization, converse or helper theorems without a source obligation or actual dependency. '
            'Check that your representation has the intended objects and conditions; well-typed empty classes or vacuous implications do not establish source fidelity.\n\n')+system[end:]
        system+='\n\nCHECKED GENERIC PROCEDURES (reference only; not preloaded declarations or task answers):\n'+ '\n\n'.join(p['id']+': '+p['instruction']+'\n'+p['code'] for p in procedures(job))
        system+=('\n\nIn this direct job, error feedback already includes the relevant checked procedure and a complete guide section. '
            'Read diagnostic.source_context for the located source line and preserve the original native error. '
            'A bare read_docs(topic) returns sections linked to the latest error when available; section="index" explicitly lists sections. '
            'Use a supplied section directly before requesting another lookup. '
            'Explicit query, sections=[IDs], section=ID and section="all" remain available; use only one selector.')
    task=json.loads((inputs/'task.json').read_text()) if (inputs/'task.json').exists() else {'task_id':job['task_id'],'kind':'proof','instruction':'Offline tool fixture only.'}
    administrative={'status','instruction_language','source','success_policy','required_outputs','semantic_audit','primary_denominator','acceptance'}
    contract={k:v for k,v in task.items() if k not in administrative}
    contract.setdefault('kind',job.get('task_kind','proof'))
    parts=['TASK CONTRACT (complete mathematical requirements; administrative metadata is controller-owned):\n'+json.dumps(contract,ensure_ascii=False)]
    for name in manifest['reading_policy']['primary_text_files']:
        parts.append('ORIGINAL PRIMARY SOURCE '+name+' (verbatim, including original proof when present):\n'+(inputs/name).read_text())
    for name in ('foundation.json','seed-interface.json',Path(job['seed_path']).name):
        parts.append('ALREADY PROVIDED INPUT '+name+':\n'+(inputs/name).read_text())
    entries=job.get('library',{}).get('index',{}).get('entries',[])
    parts.append('OWN-LANGUAGE LIBRARY ALREADY LOADED IN THE VERIFIER:\n'+json.dumps({'total_entries':len(entries),'latest_entries':[{'task_id':e['task_id'],'symbols':e.get('symbols',[])} for e in entries[-10:]]}))
    parts.append('OPTIONAL ORIGINAL CONTEXT TXT FILES: '+json.dumps(manifest['reading_policy'].get('context_text_files',[])))
    if job.get('direct_protocol'):
        context=json.loads((inputs/'direct-context.json').read_text())
        parts.append('READY-TO-USE OWN-LANGUAGE CONTEXT (no initialization lookup needed if complete):\n'+json.dumps({k:v for k,v in context.items() if k not in ('library_code','original_context')},ensure_ascii=False)+'\nPUBLISHED LIBRARY CODE:\n'+context['library_code'])
        for name,text in context['original_context'].items():parts.append('ORIGINAL CONTEXT '+name+' (verbatim):\n'+text)
        parts.append('direct_candidate_ready='+str(job.get('direct_candidate_ready',False)).lower()+'. Submit the complete candidate now when ready. Do not restate the source as a long commentary. Existing library declarations above are already loaded; do not redeclare them.')
    parts.append('Begin by producing the complete candidate unless a specific missing signature or syntax rule needs lookup. Call submit_candidate({code}); inspect its full native feedback and repair as needed. There is no separate write/check/submit sequence.')
    prompt='\n\n'.join(parts)
    require_english(system,'Compact system prompt');require_english(prompt,'Compact user prompt')
    return system,prompt
