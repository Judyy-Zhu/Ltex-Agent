#!/usr/bin/env python3
"""Prepare offline, then explicitly run paired full-catalog Pi experiments."""
from __future__ import annotations
import argparse
from contextlib import contextmanager
from datetime import datetime,timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import random
import shutil
import signal
import subprocess
import sys
import time
import uuid
from process_control import identity,stop_owned
from prepare import BASE,WORKSPACE,PI,LEAN_PROJECT,LAKE,REPL,LITEX,prepare_job
from seed_support import starting_source,require_seed_prefix
from task_inputs import catalog,source_pdf,freeze_sources,digest,copy_text_pack
from tool_host import source_guard,bounded
from agent_language import english_record,SUCCESS_POLICY
from budgets import run_remaining,task_seconds
from recovery import POLICY,RESUMABLE,recover_completed_submission

BATCHES=BASE/'batches'
SCHEMA=1


def now():return datetime.now(timezone.utc).isoformat()


def read(path):return json.loads(Path(path).read_text())


def save(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix('.'+str(os.getpid())+'.tmp')
    with temp.open('w') as stream:
        stream.write(json.dumps(value,ensure_ascii=False,indent=2)+'\n');stream.flush();os.fsync(stream.fileno())
    temp.replace(path)


def folder(name):
    import re
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,79}',name):raise ValueError('Use a simple batch name, without paths')
    return BATCHES/name


@contextmanager
def locked(root):
    with (root/'.lock').open('a') as stream:
        try:fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise ValueError('Another controller is using this batch')
        try:yield
        finally:fcntl.flock(stream,fcntl.LOCK_UN)


def environment_seal():
    paths=list((BASE/'runtime').glob('*.py'))+list((BASE/'runtime').glob('*.ts'))
    paths+=list((BASE/'seeds').glob('*'))+list((BASE/'runtime/fixtures').glob('*'))
    paths+=[p for p in (BASE/'agent-kit').rglob('*') if p.is_file() and
            p.suffix in ('.md','.txt','.json','.lean','.lit','.py') and '__pycache__' not in p.parts]
    paths+=[BASE/'models.smoke.json',BASE/'config.draft.json',BASE/'audit_candidate.py',
            BASE.parents[1]/'tasks/catalog.json',BASE.parents[1]/'tasks/tasks.jsonl',
            LITEX,REPL,LAKE,LEAN_PROJECT/'lean-toolchain',LEAN_PROJECT/'lake-manifest.json']
    files={str(p.resolve()):digest(p) for p in paths if p.is_file()}
    pi=PI
    # Freeze the local Pi sources and installed dependency lock, not credentials.
    for package in ('coding-agent','agent','ai'):
        for path in (pi/'packages'/package/'src').rglob('*'):
            if path.is_file():files[str(path.resolve())]=digest(path)
    for path in (pi/'package-lock.json',pi/'pi-test.sh'):
        files[str(path.resolve())]=digest(path)
    return {'files':files,'pi_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=pi,text=True).strip()}


def verify_environment(plan):
    for name,value in plan['environment']['files'].items():
        if digest(Path(name))!=value:raise ValueError('Frozen experiment file changed: '+name+'; create a new batch for new code')
    pi=PI
    if subprocess.check_output(['git','rev-parse','HEAD'],cwd=pi,text=True).strip()!=plan['environment']['pi_commit']:
        raise ValueError('Pi revision changed')


def verify_regression():
    receipt=read(BASE/'runtime/session-controls-receipt.json')
    if not receipt.get('passed') or receipt.get('model_calls')!=0:raise ValueError('Offline regression has not passed')
    for name,value in receipt['source_sha256'].items():
        if digest(BASE/name)!=value:raise ValueError('Offline regression is stale; run python3 runtime/verify_sessions.py')


def select_tasks(books,limit=None):
    rows,_=catalog()
    if books=='all':numbers=set(range(1,14))
    else:
        numbers=set()
        for part in books.split(','):
            ends=[int(n) for n in part.split('-')]
            if len(ends)==1:numbers.add(ends[0])
            elif len(ends)==2 and ends[0]<=ends[1]:numbers.update(range(ends[0],ends[1]+1))
            else:raise ValueError('Invalid book range')
        if not numbers or not numbers<=set(range(1,14)):raise ValueError('Books must be 1..13')
    chosen=[];count=0
    for record in rows:
        if record['book'] not in numbers:continue
        if record['kind']=='proposition':
            if limit is not None and count>=limit:break
            count+=1
        chosen.append(english_record(record))
    if not chosen or (limit is not None and limit<1):raise ValueError('Empty task selection')
    return chosen


def create_plan(root,records,seconds=1200,repetitions=1,random_seed=20261108,run_hours=None,max_checks=60,check_timeout=180,source_cache=None,execution='serial',max_rounds=None,checkpoint_resume=False,auto_finalize=False,compact_protocol=False,lookup_turn_limit=3,direct_protocol=False,split_final_timing=False):
    if direct_protocol:
        if not compact_protocol or not auto_finalize or max_rounds is None:raise ValueError('Direct protocol requires compact automatic whole-task candidates')
        lookup_turn_limit=1
    records=[english_record(record) for record in records]
    if root.exists():raise ValueError('Batch already exists; run/resume it or choose a new name')
    if (seconds is not None and not 1<=seconds<=86400) or repetitions<1 or (max_checks is not None and max_checks<1) or (check_timeout is not None and check_timeout<1) or (max_rounds is not None and max_rounds<1):raise ValueError('Invalid budget')
    if execution not in ('serial','parallel'):raise ValueError('Unknown execution mode')
    if compact_protocol and (type(lookup_turn_limit) is not int or lookup_turn_limit<1):raise ValueError('Information-turn allowance must be a positive integer')
    root.mkdir(parents=True)
    preparation_start=time.monotonic();started=now()
    save(root/'preparation.json',{'status':'preparing','started_at':started,'model_calls':0})
    rng=random.Random(random_seed);slots=[]
    for repetition in range(1,repetitions+1):
        for record in records:
            order=['lean','litex'];rng.shuffle(order)
            for language in order:
                slots.append({'key':f"r{repetition:03}:{record['id']}:{language}",
                              'number':len(slots)+1,'repetition':repetition,'task_id':record['id'],
                              'kind':record['kind'],'language':language})
    hours=run_hours if run_hours is not None else (None if seconds is None else len(slots)*(seconds+60)/3600)
    if hours is not None and hours<=0:raise ValueError('Run hours must be positive')
    if source_cache:
        for record in records:
            copy_text_pack(Path(source_cache)/record['id'],root/'source-cache'/record['id'],record)
    freeze_sources(root/'source-cache',records)
    source_files={str(p.relative_to(root)):digest(p) for p in (root/'source-cache').rglob('*') if p.is_file()}
    plan={'schema_version':SCHEMA,'name':root.name,'created_at':now(),
          'execution':{'mode':execution,'max_workers':2 if execution=='parallel' else 1,
                       'resource_conditions':'shared_host_concurrent' if execution=='parallel' else 'serial_interleaved',
                       'coverage_clock':'language_worker_execution_seconds' if execution=='parallel' else 'batch_execution_seconds'},
          'credential_bindings':{'lean':'primary','litex':'secondary'} if execution=='parallel' else {'lean':'primary','litex':'primary'},
          'mode':'source_to_library_full_catalog_exploration','formal_result':False,
          'agent_interface':'direct_candidate_with_local_repair_v1' if direct_protocol else 'compact_atomic_bounded_lookup_v2' if compact_protocol else 'historical_reference',
          'direct_protocol':direct_protocol,
          'split_final_timing':split_final_timing,
          'startup_excluded_time_policy':'Subtract measured candidate-session and independent-final-session initialization only; retain model/API, retries, all actual verification, cleanup and orchestration. Historical CLI final startup is unknown.' if split_final_timing else 'Historical final CLI startup is not separately measured.',
          'lookup_turn_limit':lookup_turn_limit if compact_protocol else None,
          'performance_policy':'Report session initialization, warm native candidate request-response, replay, fresh-file verification and end-to-end time separately. Offline paired accepted-artifact replay isolates native verification from model/network/tool-choice overhead; it does not change pass rates.',
          'input_modality':'text_only','images_allowed':False,
          'instruction_language':'en','prompt_language':'en',
          'success_policy':dict(SUCCESS_POLICY),
          'compact_protocol':compact_protocol,'auto_finalize':auto_finalize,'checkpoint_resume':checkpoint_resume,'recovery_policy':dict(POLICY) if checkpoint_resume else None,
          'mathematical_review_status':'source targets and transitive foundation equivalence remain reviewable, not certified',
          'source_pdf':str(source_pdf()),'source_sha256':digest(source_pdf()),
          'records':records,'slots':slots,'repetitions':repetitions,'random_seed':random_seed,
          'primary_denominator_per_language_per_repetition':sum(r['kind']=='proposition' for r in records),
          'budget':{'task_seconds':seconds,'run_seconds':None if hours is None else hours*3600,'max_checks':max_checks,'check_timeout':check_timeout,'max_task_rounds':max_rounds,
                    'round_definition':'Five total attempts per task window, including candidate, generation and network/API failures. Final verification/publication are excluded after candidate acceptance. All-API exhausted windows checkpoint the same task for explicit restart with full history retained.'},
          'model':{'provider':'paratera','id':'DeepSeek-V4.1-Flash','thinking':'disabled','context_window':32768,
                   'max_output_tokens':8192,'input_modalities':['text'],'retry':False,
                   'compaction_reserve':8192 if auto_finalize else 14000,'compaction_keep_recent':512 if auto_finalize else 6000,
                   'compaction_policy':'local_durable_task_checkpoint_zero_model_calls' if auto_finalize else 'provider_summary'},
          'library_policy':'Complete, final-checked, declaration/axiom-gated tasks pass and publish automatically. Optional semantic annotations never block publication or the primary score. Failed increments are discarded.',
          'resume_policy':('Resume the unfinished current task from its durable Pi conversation, files, receipts, native journal and remaining shared attempts. Network/API errors consume the same five-attempt allowance. Five all-API failures checkpoint this task; explicit restart opens a fresh window while retaining history.' if checkpoint_resume else 'Do not repeat interrupted or failed model attempts. Recover a finished durable submission when possible; otherwise record interruption and advance.'),
          'source_files':source_files,'environment':environment_seal()}
    save(root/'plan.json',plan)
    save(root/'state.json',{'schema_version':SCHEMA,'plan_sha256':digest(root/'plan.json'),
                          'status':'prepared','elapsed_execution_seconds':0,'records':{},'libraries':{},'reviews':{}})
    if execution=='parallel':
        from parallel_batch import prepare_workers
        prepare_workers(root,plan)
    save(root/'preparation.json',{'status':'complete','started_at':started,'completed_at':now(),
                                 'setup_seconds':time.monotonic()-preparation_start,'model_calls':0,'source_packs':len(records)})
    return plan


def load(root):
    plan=read(root/'plan.json');state=read(root/'state.json')
    if digest(root/'plan.json')!=state['plan_sha256']:raise ValueError('Frozen plan changed')
    return plan,state


def verify_sources(root,plan):
    if digest(plan['source_pdf'])!=plan['source_sha256']:raise ValueError('Source PDF changed')
    for name,value in plan['source_files'].items():
        if digest(root/name)!=value:raise ValueError('Frozen source input changed: '+name)


def verify_libraries(state):
    for key,library in state['libraries'].items():
        if digest(library['source'])!=library['sha256'] or digest(library['index'])!=library['index_sha256']:
            raise ValueError('Published library changed: '+key)
        for entry in read(library['index'])['entries']:
            if digest(Path(library['parts'])/entry['file'])!=entry['sha256']:
                raise ValueError('Published library increment changed: '+entry['task_id'])


def recover_metrics(attempt):
    from run import usage_summary
    from item_tracking import summary as retry_summary
    manifest=read(attempt/'manifest.json') if (attempt/'manifest.json').exists() else {}
    try:usage=usage_summary(attempt)['summary']
    except (ValueError,KeyError):usage={'request_attempts':None,'fields':{}}
    return {'controller_status':manifest.get('status','interrupted'),
            'elapsed_seconds':manifest.get('elapsed_seconds'),
            'check_calls':manifest.get('check_calls'),
            'checker_seconds':manifest.get('checker_seconds'),
            'non_checker_seconds':manifest.get('non_checker_seconds'),
            'verification_timing':manifest.get('verification_timing'),
            'startup_excluded_seconds':manifest.get('startup_excluded_seconds'),
            'native_session':manifest.get('native_session'),
            'task_rounds':read(attempt/'task-rounds.json') if (attempt/'task-rounds.json').exists() else None,
            'resume_count':manifest.get('resume_count',0),'network_retry_count':manifest.get('network_retry_count',0),
            'network_wait_seconds':manifest.get('network_wait_seconds',0),
            'known_elapsed_seconds':manifest.get('known_elapsed_seconds',manifest.get('elapsed_seconds')),
            'retry_statistics':retry_summary(attempt),
            'telemetry_complete':manifest.get('telemetry_complete',False),
            'usage':usage}


def publish(root,slot,attempt,library):
    """Verify durable solver evidence, then atomically publish a new immutable version."""
    job=read(attempt/'job.json');manifest=read(attempt/'manifest.json')
    if manifest.get('offline_fixture'):return None
    if manifest['status']!='settled' or not manifest.get('machine_checked_candidate'):return None
    submission=read(attempt/'submission.json')
    if submission['task_id']!=slot['task_id'] or submission['language']!=slot['language']:raise ValueError('Wrong submission identity')
    rid=submission['final_receipt_id']
    if not isinstance(rid,str) or not rid.startswith('check-') or Path(rid).name!=rid:raise ValueError('Invalid receipt')
    receipt=read(attempt/'receipts'/(rid+'.json'))
    actual={str(p.relative_to(attempt/'work')):digest(p) for p in (attempt/'work').rglob('*') if p.is_file()}
    if receipt['mode']!='final' or not receipt['passed'] or receipt['source_hashes']!=actual:raise ValueError('Final receipt stale or failed')
    gate=read(attempt/'submission-gate.json')
    if not gate['passed'] or gate['source_hashes']!=actual or gate['final_receipt_id']!=rid:raise ValueError('Submission gate failed or stale')
    if submission['agent_claim']!='complete' or submission['unfinished']:return None
    clauses={c['clause_id'] for c in submission['clause_mapping'] if c['declarations']}
    if not set(job['required_clause_ids'])<=clauses:raise ValueError('Missing task clauses')
    path=bounded(attempt/'work',receipt['entry']);source=path.read_text()
    require_seed_prefix(job,source);source_guard(source,slot['language'],job['foundation'].get('allowed_imports',[]))
    prefix=starting_source(job).rstrip();delta=source[len(prefix):].lstrip('\n')
    if not delta.strip():raise ValueError('Empty task increment')
    ext='lean' if slot['language']=='lean' else 'lit'
    version=root/'libraries'/f"r{slot['repetition']:03}"/slot['language']/f"v{slot['number']:04}"
    version.mkdir(parents=True,exist_ok=True);parts=version/'parts';parts.mkdir(exist_ok=True)
    entries=[];previous=''
    if library:
        previous=Path(library['source']).read_text();entries=read(library['index'])['entries']
        if job.get('library',{}).get('sha256')!=digest(library['source']):raise ValueError('Predecessor checkpoint mismatch')
        for entry in entries:
            origin=Path(library['parts'])/entry['file']
            if digest(origin)!=entry['sha256']:raise ValueError('Published predecessor changed')
            shutil.copyfile(origin,parts/entry['file'])
    filename=slot['task_id']+'.'+ext;(parts/filename).write_text(delta)
    symbols=sorted({name for c in submission['clause_mapping'] for name in c['declarations']})
    entries=entries+[{'task_id':slot['task_id'],'file':filename,'sha256':digest(parts/filename),
                     'symbols':symbols,'interfaces':read(bounded(attempt/'work',submission['interfaces_file'])),
                     'semantic_status':'pending','attempt':str(attempt.relative_to(root))}]
    source_path=version/('library.'+ext);source_path.write_text(previous.rstrip()+'\n\n'+delta)
    save(version/'index.json',{'entries':entries})
    return {'source':str(source_path),'sha256':digest(source_path),'index':str(version/'index.json'),
            'index_sha256':digest(version/'index.json'),'parts':str(parts),'task_id':slot['task_id']}


def finish_slot(root,state,slot,attempt):
    record=state['records'][slot['key']];key=f"r{slot['repetition']:03}:{slot['language']}"
    record.update(recover_metrics(attempt),completed_at=now(),status='finished',published=False)
    try:
        if (attempt/'manifest.json').exists():
            published=publish(root,slot,attempt,state['libraries'].get(key))
            if published:
                state['libraries'][key]=published;record.update(published=True,library=published)
    except (ValueError,KeyError,OSError) as error:record['publication_error']=str(error)
    record['semantic_status']='pending' if record['published'] else 'not_a_candidate'
    record['passed']=bool(record['published'])
    record['success_criterion']='machine_verification'
    save(root/'state.json',state)


def stop_orphan(attempt):
    controller=attempt/'controller-process.json'
    if controller.exists():stop_owned(read(controller))
    manifest=attempt/'manifest.json'
    if manifest.exists():stop_owned(read(manifest).get('pi_process',{}))


def run_batch(root,executor=None,offline_probe=False):
    """executor injection is for deterministic offline integration tests only."""
    initial_plan,_=load(root)
    if initial_plan.get('execution',{}).get('mode')=='parallel':
        if executor:raise ValueError('Parallel integration tests must use the blocked-provider offline probe')
        from parallel_batch import run_parallel
        return run_parallel(root,offline_probe=offline_probe)
    with locked(root):
        plan,state=load(root);verify_environment(plan);verify_sources(root,plan);verify_libraries(state)
        alias=plan.get('credential_alias','primary')
        if executor is None and not offline_probe:
            verify_regression()
            from credentials import read_credential
            read_credential(alias)
        if offline_probe:state['offline_fixture']=True
        state['status']='running';save(root/'state.json',state)
        base_elapsed=state['elapsed_execution_seconds'];session_start=time.monotonic()
        def checkpoint():
            state['elapsed_execution_seconds']=base_elapsed+time.monotonic()-session_start
            for record in state['records'].values():
                path=root/record['attempt']/'manifest.json'
                if record['status']=='active' and path.exists():
                    current=read(path)
                    record['connection_status']=current.get('status')
                    record['network_wait_seconds']=current.get('network_wait_seconds',0)
            save(root/'state.json',state)
        try:
            for slot in plan['slots']:
                old=state['records'].get(slot['key'])
                if old and old['status']=='finished':continue
                resuming=False
                if old:
                    attempt=root/old['attempt']
                    stop_orphan(attempt)
                    completed=recover_completed_submission(attempt) if plan.get('checkpoint_resume') else False
                    prior=read(attempt/'manifest.json') if (attempt/'manifest.json').exists() else {}
                    if not plan.get('checkpoint_resume') or completed or prior.get('status') not in RESUMABLE|{None}:
                        finish_slot(root,state,slot,attempt);continue
                    resuming=(attempt/'job.json').exists()
                    old['status']='active';old.pop('infrastructure_error',None)
                checkpoint();remaining=run_remaining(plan['budget'],state['elapsed_execution_seconds'])
                if remaining<1:state['status']='budget_exhausted';break
                verify_environment(plan)
                attempt=root/'attempts'/f"{slot['number']:04}-{slot['language']}" if not old else root/old['attempt']
                if not old:state['records'][slot['key']]={**slot,'status':'active','attempt':str(attempt.relative_to(root)),
                                               'started_at':now(),'execution_start_seconds':state['elapsed_execution_seconds']}
                save(root/'state.json',state)
                library_key=f"r{slot['repetition']:03}:{slot['language']}"
                library=state['libraries'].get(library_key)
                if library and (digest(library['source'])!=library['sha256'] or digest(library['index'])!=library['index_sha256']):
                    raise ValueError('Published library changed')
                try:
                    prepare_start=time.monotonic()
                    if not resuming:
                        if attempt.exists():raise ValueError('Incomplete task preparation preserved; inspect before resuming')
                        prepare_job(attempt,slot['language'],task_seconds(plan['budget'],state['elapsed_execution_seconds']),
                                    task_id=slot['task_id'],source_cache=root/'source-cache',library=library,
                                    max_checks=plan['budget']['max_checks'],check_timeout=plan['budget']['check_timeout'],
                                    max_rounds=None if offline_probe else plan['budget'].get('max_task_rounds'),
                                    checkpoint_resume=plan.get('checkpoint_resume',False),auto_finalize=plan.get('auto_finalize',False),compact_protocol=plan.get('compact_protocol',False),lookup_turn_limit=plan.get('lookup_turn_limit',3),direct_protocol=plan.get('direct_protocol',False),split_final_timing=plan.get('split_final_timing',False))
                        state['records'][slot['key']]['setup_seconds']=time.monotonic()-prepare_start
                    checkpoint()
                    # Preparation also consumes the global run allowance.
                    available=run_remaining(plan['budget'],state['elapsed_execution_seconds'])
                    if available<1:raise ValueError('Global deadline reached during preparation')
                    if not resuming:
                        job=read(attempt/'job.json');job['task_deadline_seconds']=task_seconds(plan['budget'],state['elapsed_execution_seconds'])
                        save(attempt/'job.json',job)
                    if executor:executor(attempt,slot)
                    else:
                        token=uuid.uuid4().hex
                        command=[sys.executable,str(BASE/'runtime/run.py'),'--language',slot['language'],'--prepared-root',str(attempt),'--start-token',token,'--credential-alias',alias]
                        if resuming:command.append('--resume-task')
                        if offline_probe:command+=['--smoke','--offline-probe']
                        with (attempt/'controller.stdout.log').open('a') as out,(attempt/'controller.stderr.log').open('a') as err:
                            process=subprocess.Popen(command,cwd=BASE,stdout=out,stderr=err,start_new_session=True)
                            save(attempt/'controller-process.json',identity(process.pid))
                            save(attempt/'launch.json',{'token':token})
                            try:
                                while process.poll() is None:
                                    time.sleep(.25)
                                    if run_remaining(plan['budget'],time.monotonic()-session_start+base_elapsed)<=0:break
                                    if time.monotonic()-session_start+base_elapsed-state['elapsed_execution_seconds']>=5:checkpoint()
                            finally:
                                if process.poll() is None:
                                    process.terminate()
                                    try:process.wait(timeout=8)
                                    except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait()
                                manifest_path=attempt/'manifest.json'
                                if manifest_path.exists():stop_owned(read(manifest_path).get('pi_process',{}))
                except (ValueError,OSError,subprocess.SubprocessError) as error:
                    state['records'][slot['key']]['infrastructure_error']=str(error)
                checkpoint()
                if plan.get('checkpoint_resume'):
                    manifest=read(attempt/'manifest.json') if (attempt/'manifest.json').exists() else {}
                    if manifest.get('status') in RESUMABLE|{None}:
                        record=state['records'][slot['key']]
                        record.update(recover_metrics(attempt),status='checkpointed')
                        state['status']='blocked_provider' if manifest.get('status')=='blocked_provider' else 'checkpointed'
                        break
                state['records'][slot['key']]['execution_end_seconds']=state['elapsed_execution_seconds']
                finish_slot(root,state,slot,attempt);checkpoint()
                print(json.dumps({'slot':slot['number'],'total':len(plan['slots']),'task':slot['task_id'],
                                  'language':slot['language'],'published':state['records'][slot['key']]['published']},ensure_ascii=False),flush=True)
            else:state['status']='complete'
        except KeyboardInterrupt:
            state['status']='interrupted'
        finally:
            checkpoint();save(root/'state.json',state)
            from batch_report import report
            report(root)
        return state


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    prep=sub.add_parser('prepare',help='Offline: freeze plan, source packs and experiment files; no API calls')
    prep.add_argument('--name',required=True);prep.add_argument('--books',default='all')
    prep.add_argument('--limit-tasks',type=int,help='Select exactly the first N original catalog tasks, including definitions')
    prep.add_argument('--limit-propositions',type=int);prep.add_argument('--seconds',type=int,default=None,help='Optional legacy task deadline; omitted means no time limit')
    prep.add_argument('--repetitions',type=int,default=1);prep.add_argument('--random-seed',type=int,default=20261108)
    prep.add_argument('--run-hours',type=float);prep.add_argument('--max-checks',type=int,default=None)
    prep.add_argument('--check-timeout',type=int,default=None)
    prep.add_argument('--max-rounds',type=int,default=5,help='Total task attempts per window, including code candidates and network/API failures')
    prep.add_argument('--source-cache',type=Path,help='Optional existing verified source packs; copied into the new batch')
    prep.add_argument('--execution',choices=['serial','parallel'],default='serial')
    prep.add_argument('--reference-protocol',action='store_true',help='Use the previous optional-read protocol instead of direct candidates with local repair hints')
    prep.add_argument('--split-final-timing',action='store_true',help='Independently recheck final source in a fresh native Session/REPL and directly measure initialization separately from verification')
    for name in ('run','resume','status','report','preflight','review-template'):
        sub.add_parser(name).add_argument('--name',required=True)
    review=sub.add_parser('review');review.add_argument('--name',required=True);review.add_argument('--file',required=True,type=Path)
    worker=sub.add_parser('_worker',help=argparse.SUPPRESS)
    worker.add_argument('--root',type=Path,required=True);worker.add_argument('--start-token',required=True)
    worker.add_argument('--offline-probe',action='store_true')
    args=parser.parse_args()
    if args.command=='_worker':
        from parallel_batch import worker_main
        worker_main(args.root,args.start_token,args.offline_probe);return
    root=folder(args.name)
    if args.command=='prepare':
        verify_regression()
        if args.limit_tasks is not None and (args.limit_tasks<1 or args.limit_propositions is not None):parser.error('Use a positive --limit-tasks or --limit-propositions, not both')
        records=select_tasks(args.books,args.limit_propositions)
        if args.limit_tasks is not None:records=records[:args.limit_tasks]
        plan=create_plan(root,records,args.seconds,args.repetitions,
                         args.random_seed,args.run_hours,args.max_checks,args.check_timeout,args.source_cache,args.execution,args.max_rounds,True,True,True,1 if not args.reference_protocol else 3,not args.reference_protocol,args.split_final_timing)
        print(json.dumps({'prepared':str(root),'tasks':len(plan['records']),'agent_attempts':len(plan['slots']),
                          'propositions_per_language':plan['primary_denominator_per_language_per_repetition'],'model_calls':0}))
    elif args.command in ('run','resume'):run_batch(root)
    elif args.command=='preflight':
        verify_regression()
        with locked(root):
            plan,state=load(root);verify_environment(plan);verify_sources(root,plan);verify_libraries(state)
            if plan.get('execution',{}).get('mode')=='parallel':
                from parallel_batch import verify_workers
                from credentials import validate_pair
                verify_workers(root,plan);validate_pair(plan['credential_bindings'])
        print(json.dumps({'passed':True,'model_calls':0,'tasks':len(plan['records']),'formal_result':False}))
    else:
        from batch_report import report,review_template,import_reviews
        if args.command=='review-template':print(review_template(root))
        elif args.command=='review':
            with locked(root):import_reviews(root,args.file)
            print(json.dumps(report(root)['summary'],ensure_ascii=False))
        else:print(json.dumps(report(root)['summary'],ensure_ascii=False,indent=2))


if __name__=='__main__':
    def terminate(_signum,_frame):raise KeyboardInterrupt
    signal.signal(signal.SIGTERM,terminate)
    if hasattr(signal,'SIGHUP'):signal.signal(signal.SIGHUP,terminate)
    try:main()
    except (ValueError,KeyError,OSError) as error:
        print(str(error),file=sys.stderr);raise SystemExit(2)
