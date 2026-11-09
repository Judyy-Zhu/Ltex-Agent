"""Offline aggregation and explicit source-fidelity review certificates."""
from __future__ import annotations
import csv
import io
import json
from pathlib import Path
from batch import load,save,now,read
from task_inputs import digest
from verification_timing import aggregate

TOKEN_FIELDS=('input_total','input_uncached','cache_read','cache_write','output_total','reasoning_subset','token_total')
CERTIFICATES=('source_complete','encoding_valid','assumptions_valid','dependencies_valid')


def report(root):
    plan,state=load(root);rows=[];item_rows=[]
    automatic=plan.get('success_policy',{}).get('criterion')=='machine_verification'
    if plan.get('execution',{}).get('mode')=='parallel':
        from parallel_batch import refresh
        refresh(root,plan,state)
    for slot in plan['slots']:
        record=state['records'].get(slot['key'],{})
        review=state.get('reviews',{}).get(slot['key'])
        candidate=bool(record.get('published'))
        semantic=review['status'] if review else ('pending' if candidate else 'not_a_candidate')
        correct=(semantic=='pass') if candidate and semantic in ('pass','fail') else None
        retries=record.get('retry_statistics') or {}
        rounds=record.get('task_rounds')
        task_attempts=len(rounds['rounds']) if rounds is not None else None
        for item in retries.get('items',[]):
            item_rows.append({'repetition':slot['repetition'],'task_id':slot['task_id'],
                              'language':slot['language'],'attempt':record.get('attempt'),**item})
        rows.append({**slot,'status':record.get('status','unattempted'),
                     'credential_alias':plan.get('credential_bindings',{}).get(slot['language'],'primary'),
                     'controller_status':record.get('controller_status'),
                     'passed':candidate if record.get('status')=='finished' else None,
                     'machine_candidate':candidate,'semantic_status':semantic,'verified_correct':correct,
                     'elapsed_seconds':record.get('elapsed_seconds'),'setup_seconds':record.get('setup_seconds'),
                     'check_calls':record.get('check_calls'),'telemetry_complete':record.get('telemetry_complete',False),
                     'checker_seconds':record.get('checker_seconds'),
                     'verification_timing':record.get('verification_timing'),
                     'startup_excluded_seconds':record.get('startup_excluded_seconds'),
                     'independent_final_initialization_seconds':(record.get('verification_timing') or {}).get('independent_final_initialization_seconds'),
                     'independent_final_verification_seconds':(record.get('verification_timing') or {}).get('independent_final_verification_seconds'),
                     'session_initialization_seconds':(record.get('verification_timing') or {}).get('session_initialization_seconds'),
                     'warm_candidate_seconds':(record.get('verification_timing') or {}).get('incremental_candidate_seconds'),
                     'replay_seconds':(record.get('verification_timing') or {}).get('replay_seconds'),
                     'fresh_file_seconds':(record.get('verification_timing') or {}).get('independent_final_file_seconds'),
                     'non_checker_seconds':record.get('non_checker_seconds'),
                     'api_request_count':(record.get('usage') or {}).get('request_attempts'),
                     'resume_count':record.get('resume_count',0),'connection_status':record.get('connection_status'),
                     'network_retry_count':record.get('network_retry_count',0),'network_wait_seconds':record.get('network_wait_seconds',0),
                     'retry_statistics':retries,
                     'task_rounds':rounds,'task_attempt_count':task_attempts,
                     'attempt_window_used':task_attempts-rounds.get('window_start',0) if rounds is not None else None,
                     'task_retry_count':max(0,task_attempts-1) if task_attempts is not None else None,
                     **{field:retries.get(field) for field in ('main_attempt_count','main_retry_count','attempt_count',
                                                              'retry_count','definition_retry_count','proof_retry_count')},
                     'usage':record.get('usage'),'attempt':record.get('attempt'),
                     'infrastructure_error':record.get('infrastructure_error') or record.get('publication_error'),
                     'execution_start_seconds':record.get('execution_start_seconds'),
                     'execution_end_seconds':record.get('execution_end_seconds')})
    groups=[]
    for repetition in range(1,plan['repetitions']+1):
        for language in ('lean','litex'):
            selected=[r for r in rows if r['repetition']==repetition and r['language']==language]
            props=[r for r in selected if r['kind']=='proposition'];n=len(props)
            tokens={}
            for field in TOKEN_FIELDS:
                values=[((r['usage'] or {}).get('fields',{}).get(field,{})) for r in selected]
                attempted=[v for r,v in zip(selected,values) if r['status']!='unattempted']
                missing=sum(v.get('missing_requests',0) for v in attempted)
                unknown_attempts=sum(not r['telemetry_complete'] for r in selected if r['status']!='unattempted')
                subtotal=sum(v.get('known_subtotal',0) for v in attempted)
                tokens[field]={'value':subtotal if not missing and not unknown_attempts else None,
                               'known_subtotal':subtotal,'missing_reported_requests':missing,
                               'incomplete_attempt_telemetry':unknown_attempts}
            pending=sum(r['machine_candidate'] and r['semantic_status']=='pending' for r in props)
            correct=sum(r['verified_correct'] is True for r in props)
            machine=sum(r['machine_candidate'] for r in props)
            primary=machine if automatic else correct
            completed=sum(r['status']=='finished' for r in selected)==len(selected)
            known_time=[r['elapsed_seconds'] for r in selected if r['status']!='unattempted' and r['elapsed_seconds'] is not None]
            unknown_time=sum(r['status']!='unattempted' and r['elapsed_seconds'] is None for r in selected)
            attempted=[r for r in selected if r['status']!='unattempted']
            unknown_retries=sum(not r['retry_statistics'].get('counts_complete',False) for r in attempted)
            known_retries=sum(r['retry_statistics'].get('known_retry_count',0) for r in attempted)
            curve=[{'task_id':r['task_id'],'correct_count':i+1,'execution_seconds':r['execution_end_seconds']}
                   for i,r in enumerate(r for r in props if r['verified_correct'] is True)]
            primary_curve=[{'task_id':r['task_id'],'passed_count':i+1,'execution_seconds':r['execution_end_seconds']}
                           for i,r in enumerate(r for r in props if r['machine_candidate'])] if automatic else curve
            kinds=sorted({r['kind'] for r in selected})
            groups.append({'repetition':repetition,'language':language,'proposition_denominator':n,
                           'tasks_total':len(selected),'tasks_finished':sum(r['status']=='finished' for r in selected),
                           'unattempted_tasks':sum(r['status']=='unattempted' for r in selected),
                           'machine_propositions':machine,
                           'machine_pass_rate':machine/n if n else None,
                           'passed_tasks':sum(r['machine_candidate'] for r in selected),
                           'task_pass_rate':sum(r['machine_candidate'] for r in selected)/len(selected) if selected else None,
                           'task_pass_rates_by_kind':{kind:sum(r['machine_candidate'] for r in selected if r['kind']==kind)/sum(r['kind']==kind for r in selected) for kind in kinds},
                           'reviewed_correct_propositions':correct,'pending_proposition_reviews':pending,
                           'accuracy':machine/n if automatic and n else (correct/n if completed and not pending and n else None),
                           'accuracy_definition':'machine_verification_pass_rate' if automatic else 'legacy_reviewed_semantic_accuracy',
                           'accuracy_is_final':completed,
                           'semantic_accuracy':correct/n if completed and not pending and n else None,
                           'verified_coverage_lower_bound':correct/n if n else None,
                           'machine_candidates_by_kind':{kind:sum(r['machine_candidate'] for r in selected if r['kind']==kind)
                                                         for kind in sorted({r['kind'] for r in selected})},
                           'solver_seconds':None if unknown_time else sum(known_time),'known_solver_seconds':sum(known_time),
                           'startup_excluded_solver_seconds':sum(r['startup_excluded_seconds'] for r in selected)
                               if completed and all(r['startup_excluded_seconds'] is not None for r in selected) else None,
                           'attempts_with_unknown_time':unknown_time,
                           'setup_seconds':sum(r['setup_seconds'] or 0 for r in selected),
                           'check_calls':sum(r['check_calls'] or 0 for r in selected),
                           'retry_count':None if unknown_retries else known_retries,
                           'known_retry_count':known_retries,'tasks_with_unknown_retry_counts':unknown_retries,
                           'known_checker_seconds':sum(r['checker_seconds'] or 0 for r in selected),
                           'verification_phases':aggregate(selected),
                           'tokens':tokens,'tokens_per_correct_proposition':tokens['token_total']['value']/primary
                            if primary and tokens['token_total']['value'] is not None else None,
                           'tokens_per_machine_passed_proposition':tokens['token_total']['value']/machine
                            if machine and tokens['token_total']['value'] is not None else None,
                           'primary_success_coverage_curve':primary_curve,'reviewed_correct_coverage_curve':curve})
    joint=[];joint_machine=[];joint_reviewed=[]
    for repetition in range(1,plan['repetitions']+1):
        lean={r['task_id']:r for r in rows if r['repetition']==repetition and r['language']=='lean' and r['kind']=='proposition'}
        litex={r['task_id']:r for r in rows if r['repetition']==repetition and r['language']=='litex' and r['kind']=='proposition'}
        for task_id,left in lean.items():
            if task_id not in litex:continue
            right=litex[task_id]
            pair={'repetition':repetition,'task_id':task_id,'lean_seconds':left['elapsed_seconds'],
                              'litex_seconds':right['elapsed_seconds'],
                              'lean_over_litex':left['elapsed_seconds']/right['elapsed_seconds']
                              if left['elapsed_seconds'] is not None and right['elapsed_seconds'] else None}
            if left['machine_candidate'] and right['machine_candidate']:joint_machine.append(pair)
            if left['verified_correct'] is True and right['verified_correct'] is True:joint_reviewed.append(pair)
    joint=joint_machine if automatic else joint_reviewed
    summary={'batch':root.name,'status':state['status'],'formal_result':False,
             'input_modality':plan.get('input_modality','historical_mixed'),'images_allowed':plan.get('images_allowed'),
             'instruction_language':plan.get('instruction_language','historical_mixed'),
             'success_policy':plan.get('success_policy',{'criterion':'legacy_reviewed_semantic_accuracy'}),
             'recovery_policy':plan.get('recovery_policy'),
             'semantic_review_required_for_success':False,
             'semantic_review_required_for_primary_score':not automatic,
             'execution':plan.get('execution',{'mode':'serial','resource_conditions':'serial_interleaved'}),
             'credential_bindings':plan.get('credential_bindings',{}),'workers':state.get('workers',{}),
             'offline_fixture':state.get('offline_fixture',False),
             'tasks':len(plan['records']),'agent_attempts':len(plan['slots']),
             'finished_attempts':sum(r['status']=='finished' for r in rows),
             'elapsed_execution_seconds':state['elapsed_execution_seconds'],
             'language_startup_excluded_seconds':{language:(state.get('workers',{}).get(language) or {}).get('startup_excluded_seconds') for language in ('litex','lean')},
             'startup_excluded_time_definition':'Language worker wall time minus directly measured initialization/loading of candidate sessions and independent final sessions. Model/API, retries and both actual verification stages remain included. Unknown historical final startup is never estimated.',
             'run_budget_seconds':plan['budget']['run_seconds'],'groups':groups,
             'time_accounting':'Batch elapsed is measured parent wall time. Worker/task intervals may overlap; do not add them to obtain wall time.',
             'joint_primary_successful_propositions':len(joint),
             'joint_machine_passed_propositions':len(joint_machine),
             'joint_reviewed_correct_propositions':len(joint_reviewed),
             'interpretation':'Primary accuracy follows the frozen success policy. In machine-verification mode, semantic annotations never block passing, publication or primary scoring. Unattempted registered propositions remain in the denominator; unknown usage remains unknown. Semantic accuracy is a separate optional metric.'}
    result={'generated_at':now(),'summary':summary,'rows':rows,'items':item_rows,'joint_successes':joint,
            'joint_machine_successes':joint_machine,'joint_semantically_reviewed_successes':joint_reviewed}
    save(root/'report.json',result)
    output=io.StringIO();fields=['repetition','task_id','kind','language','credential_alias','status','controller_status','passed','machine_candidate',
                               'semantic_status','verified_correct','elapsed_seconds','setup_seconds','check_calls','attempt',
                               'resume_count','network_retry_count','network_wait_seconds','attempt_window_used','task_attempt_count','task_retry_count','main_attempt_count','main_retry_count','attempt_count','retry_count',
                               'definition_retry_count','proof_retry_count','checker_seconds','session_initialization_seconds',
                               'warm_candidate_seconds','replay_seconds','fresh_file_seconds','independent_final_initialization_seconds','independent_final_verification_seconds','startup_excluded_seconds','non_checker_seconds','api_request_count']+list(TOKEN_FIELDS)
    writer=csv.DictWriter(output,fieldnames=fields);writer.writeheader()
    for row in rows:
        writer.writerow({**{k:row.get(k) for k in fields if k not in TOKEN_FIELDS},
                         **{k:((row['usage'] or {}).get('fields',{}).get(k,{}).get('value')) for k in TOKEN_FIELDS}})
    (root/'results.csv').write_text(output.getvalue())
    output=io.StringIO()
    fields=['repetition','task_id','language','attempt','item_id','item_kind','is_primary','current_path','status',
            'attempt_count','retry_count','known_attempt_count','known_retry_count','counts_complete','pending_checks',
            'failed_candidate_count','cached_checks','preparation_failures','source_versions','check_seconds']
    writer=csv.DictWriter(output,fieldnames=fields,extrasaction='ignore');writer.writeheader();writer.writerows(item_rows)
    (root/'items.csv').write_text(output.getvalue())
    return result


def review_template(root):
    plan,state=load(root);items=[]
    for slot in plan['slots']:
        record=state['records'].get(slot['key'],{})
        if not record.get('published'):continue
        attempt=root/record['attempt'];submission=read(attempt/'submission.json')
        receipt=read(attempt/'receipts'/(submission['final_receipt_id']+'.json'))
        items.append({'key':slot['key'],'task_id':slot['task_id'],'language':slot['language'],
                      'source_sha256':digest(attempt/'work'/receipt['entry']),
                      'status':'pending','reviewer':'','reason':'',
                      **{name:False for name in CERTIFICATES},
                      'evidence_files':[str(attempt/'input/task.json'),str(attempt/'input/source-manifest.json'),
                                        str(attempt/'work'/receipt['entry']),str(attempt/'submission-gate.json')]})
    path=root/'review-template.json'
    # Never overwrite human edits to a previously generated template.
    if path.exists():path=root/('review-template-'+now().replace(':','').replace('.','')+'.json')
    save(path,{'plan_sha256':state['plan_sha256'],'reviews':items})
    return str(path)


def import_reviews(root,path):
    plan,state=load(root);data=read(path)
    if data['plan_sha256']!=state['plan_sha256']:raise ValueError('Review belongs to another frozen plan')
    updates={};slots={s['key']:s for s in plan['slots']}
    for review in data['reviews']:
        if review['status']=='pending':continue
        key=review['key'];slot=slots[key];record=state['records'][key]
        if not record.get('published') or record['status']!='finished':raise ValueError('Review requires a published candidate')
        if review['task_id']!=slot['task_id'] or review['language']!=slot['language']:raise ValueError('Review identity mismatch')
        attempt=root/record['attempt'];submission=read(attempt/'submission.json')
        receipt=read(attempt/'receipts'/(submission['final_receipt_id']+'.json'))
        if digest(attempt/'work'/receipt['entry'])!=review['source_sha256']:raise ValueError('Reviewed source changed')
        if review['status'] not in ('pass','fail') or not review['reviewer'].strip() or not review['reason'].strip():
            raise ValueError('Review requires pass/fail, reviewer and evidence-based reason')
        if review['status']=='pass' and not all(review.get(k) is True for k in CERTIFICATES):
            raise ValueError('Pass requires all four semantic certificates')
        updates[key]={**review,'imported_at':now(),'review_file_sha256':digest(path)}
    state.setdefault('reviews',{}).update(updates)
    audit=root/'reviews';audit.mkdir(exist_ok=True)
    save(audit/(now().replace(':','').replace('.','')+'.json'),{'source_sha256':digest(path),'reviews':updates})
    save(root/'state.json',state)
