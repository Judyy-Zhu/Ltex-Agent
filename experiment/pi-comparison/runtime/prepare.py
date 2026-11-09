"""Prepare bounded paired source inputs, frozen seeds and own-language library."""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path
import subprocess
import pdfplumber

from paths import BASE,PROJECT,WORKSPACE,PI,LEAN_PROJECT,LAKE,REPL,LITEX
from agent_language import require_english,SUCCESS_POLICY
from recovery import save as durable_save,POLICY
KIT = BASE/'agent-kit'
SEEDS = BASE/'seeds'
IMPORTS = ['Mathlib.Analysis.Real.Sqrt','Mathlib.Tactic.Ring',
           'Mathlib.Tactic.Linarith','Mathlib.Tactic.NormNum',
           'Mathlib.Tactic.Positivity','Mathlib.Tactic.FieldSimp']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, data):
    durable_save(path,data)


def package_source(output,task_id='EUCLID.I.P001',source_cache=None):
    from task_inputs import package_task
    return package_task(output,task_id,source_cache)


def prepare_job(root, language, seconds, smoke=False, *, task_id="EUCLID.I.P001", source_cache=None,
                library=None, max_checks=60, check_timeout=180, max_rounds=None, checkpoint_resume=False, auto_finalize=False, compact_protocol=False, lookup_turn_limit=3, direct_protocol=False, split_final_timing=False):
    root.mkdir(parents=True,exist_ok=False)
    for folder in ('work','input','receipts','pi-state'):
        (root/folder).mkdir()
    if not smoke:
        package_source(root/'input',task_id,source_cache)
    extension='lean' if language=='lean' else 'lit'
    seed_path=root/'input'/f'seed.{extension}'
    seed_path.write_bytes((SEEDS/f'plane.{extension}').read_bytes())
    interface_path=root/'input/seed-interface.json'
    interface_path.write_bytes((SEEDS/'interface.json').read_bytes())
    interface=json.loads(interface_path.read_text())
    foundation = {'status':'approved_for_development_only_transitive_foundation_audit_pending',
                  'math_model':'real coordinate plane with a fixed technical plane-algebra seed; Euclid-specific geometry is agent-built',
                  'language':language,'geometry_definitions_preloaded':False,
                  'approved_geometry_symbols':[],
                  'approved_seed_symbols':[entry['name'] for entry in interface['exports']],
                  'seed':{'id':interface['seed_id'],'input_path':seed_path.name,'sha256':sha(seed_path),
                          'interface_input_path':interface_path.name,'interface_sha256':sha(interface_path),
                          'kind':'technical_plane_algebra','proposition_proofs_provided':False,
                          'agent_tasks_credited':[]}}
    if language=='lean':
        foundation.update(allowed_imports=IMPORTS,
                          coordinate_equality_rule='Prod.ext',
                          point_carrier='ℝ × ℝ',
                          standard_logical_axioms=['propext','Classical.choice','Quot.sound'],
                          mathlib_revision='56a005855ea17e0b0958f73ec801ae140b0a1679')
    else:
        foundation.update(point_carrier='cart(R, R)',strict=True,
                          coordinate_equality_rule='tuple_equal_from_coordinates; native premises must verify',
                          binary_sha256=sha(LITEX))
    job = {'status':'development_smoke' if smoke else 'development_pilot',
           'input_modality':'text_only','images_allowed':False,
           'instruction_language':'en',
           'success_policy':dict(SUCCESS_POLICY),
           'max_task_rounds':max_rounds,'candidate_protocol':'whole_task' if max_rounds is not None else 'tracked_fragments',
           'checkpoint_resume':checkpoint_resume,'recovery_policy':dict(POLICY) if checkpoint_resume else None,
           'auto_finalize':auto_finalize,'compact_protocol':compact_protocol,
           'direct_protocol':direct_protocol,
           'split_final_timing':split_final_timing,
           'lookup_turn_limit':lookup_turn_limit if compact_protocol else None,
           'task_id':'TOOL.SMOKE' if smoke else task_id,'language':language,
           'task_deadline_seconds':seconds,'max_check_calls':max_checks,'single_check_timeout_seconds':check_timeout,
           'foundation':foundation,'required_clause_ids':[],
           'seed_path':str(seed_path),
           'lake':str(LAKE),'lean_project':str(LEAN_PROJECT),
           'lean_repl':str(REPL),'litex':str(LITEX),
           'docs':{'core':str(KIT/f'guides/{language}-aligned-core.md'),
                   'basics':str(KIT/f'guides/examples/basics.{"lean" if language=="lean" else "lit"}'),
                   'roots':str(KIT/f'guides/{language}-roots.md'),
                   'seed':str(SEEDS/'README.md'),
                   'workflow':str(KIT/f'guides/{language}-workflow.md'),
                   'feedback':str(KIT/f'guides/{language}-feedback.md'),
                   'items':str(KIT/'guides/item-protocol.md'),
                   'logic':str(KIT/f'guides/staging/proof-structure.{"lean" if language=="lean" else "lit"}'),
                   'operation':str(KIT/f'guides/{language}-operation-card.md'),
                   'domains':str(KIT/f'guides/{language}-domains.md')}}
    if compact_protocol and (not auto_finalize or max_rounds is None):raise ValueError('Compact protocol requires automatic completion and whole-task rounds')
    if split_final_timing and not auto_finalize:raise ValueError('Split final timing requires controller-owned finalization and dependency inspection')
    if direct_protocol:
        if not compact_protocol:raise ValueError('Direct protocol requires compact candidates')
        job['lookup_turn_limit']=1
        job['docs']['procedures']=str(KIT/f'guides/{language}-procedures.json')
    if compact_protocol and (type(lookup_turn_limit) is not int or lookup_turn_limit<1):raise ValueError('Information-turn allowance must be a positive integer')
    if max_rounds is not None:
        job['docs']['items']=str(KIT/'guides/task-rounds.md')
        job['docs']['workflow']=str(KIT/'guides/task-rounds.md')
    if auto_finalize:
        job['docs']['items']=str(KIT/'auto-task-runtime.txt')
        job['docs']['workflow']=str(KIT/'auto-task-runtime.txt')
        if not smoke:
            task=json.loads((root/'input/task.json').read_text())
            acceptance=list(task.get('acceptance',[]))
            automatic_rule='Provide the complete source formalization. The controller generates interface metadata and unreviewed clause associations, independently verifies the final file and saves submission automatically.'
            if acceptance:acceptance[0]=automatic_rule
            else:acceptance=[automatic_rule]
            task['acceptance']=acceptance
            if 'required_outputs' in task:task['required_outputs']=['complete candidate source; controller owns interface metadata, clause associations, final receipts and publication']
            if task.get('kind')=='definition':
                task['instruction']+=' A definition task can finish with checked definitions alone. For total definitions, native checking of domains and types establishes formation/well-definedness. Do not add existence, universal-characterization, or reference-model-validity theorems unless the current source explicitly asserts them or a partial operation/subtype constructor requires their proofs.'
            write_json(root/'input/task.json',task)
    job.update(item_tracking_required=not smoke,primary_item_id=job['task_id']+':main',
               primary_item_kind='proof')
    if not smoke:
        from task_inputs import required_clauses,catalog
        job['required_clause_ids']=required_clauses(json.loads((root/'input/task.json').read_text()))
        record=next(r for r in catalog()[0] if r['id']==task_id)
        job['task_kind']=record['kind']
        job['primary_item_kind']='definition' if record['kind']=='definition' else 'proof'
    if library:
        import shutil
        if sha(Path(library['source']))!=library['sha256'] or sha(Path(library['index']))!=library['index_sha256']:
            raise ValueError('Published predecessor checkpoint changed')
        source=root/'input'/('library.'+extension)
        shutil.copyfile(library['source'],source)
        index=json.loads(Path(library['index']).read_text())
        parts=root/'input/library-parts';parts.mkdir()
        for entry in index['entries']:
            origin=Path(library['parts'])/entry['file']
            if Path(entry['file']).name!=entry['file'] or sha(origin)!=entry['sha256']:
                raise ValueError('Library increment changed')
            shutil.copyfile(origin,parts/entry['file'])
        write_json(root/'input/library-index.json',index)
        job['library']={'input_path':source.name,'sha256':sha(source),
                        'index_path':'library-index.json','index_sha256':sha(root/'input/library-index.json'),
                        'index':index}
    job['require_submission_gate']=not smoke
    if direct_protocol:
        from direct_context import prepare_context
        prepare_context(root,job)
    # Each task reads fixed guide copies, even if the checkout is later edited.
    import shutil
    (root/'docs').mkdir()
    for topic,original in list(job['docs'].items()):
        target=root/'docs'/(topic+Path(original).suffix)
        shutil.copyfile(original,target);job['docs'][topic]=str(target)
    write_json(root/'input/foundation.json',foundation)
    write_json(root/'input/submission-schema.json',json.loads((KIT/'submission.schema.json').read_text()))
    for folder in (root/'input',root/'docs'):
        for path in folder.rglob('*'):
            if path.is_file():require_english(path.read_text(),str(path.relative_to(root)))
    job['language_specific_input_files']=['foundation.json',seed_path.name]+(['library.'+extension,'library-index.json'] if library else [])+(['direct-context.json'] if direct_protocol else [])
    job['shared_input_files']=sorted(p.name for p in (root/'input').iterdir()
                                    if p.is_file() and p.name not in job['language_specific_input_files'])
    write_json(root/'job.json',job)
    return job
