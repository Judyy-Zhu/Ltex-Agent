"""Two independent language processes, one parent wall clock, no shared writes."""
from __future__ import annotations
from copy import deepcopy
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import uuid
from batch import (BASE,load,read,save,now,locked,verify_environment,verify_sources,
                   verify_libraries,verify_regression,stop_orphan,run_batch)
from process_control import identity,stop_owned
from task_inputs import digest
from credentials import validate_pair
from budgets import run_remaining

LANGUAGES=('lean','litex')


def prepare_workers(root,plan):
    parent_hash=digest(root/'plan.json')
    for language in LANGUAGES:
        worker=root/'workers'/language;worker.mkdir(parents=True)
        (worker/'source-cache').symlink_to(root/'source-cache',target_is_directory=True)
        child=deepcopy(plan)
        child.update(name=plan['name']+'-'+language,worker_language=language,parent_plan_sha256=parent_hash,
                     credential_alias=plan['credential_bindings'][language],
                     execution={**plan['execution'],'mode':'parallel_worker','max_workers':1},
                     slots=[s for s in plan['slots'] if s['language']==language])
        save(worker/'plan.json',child)
        save(worker/'state.json',{'schema_version':plan['schema_version'],'plan_sha256':digest(worker/'plan.json'),
             'status':'prepared','elapsed_execution_seconds':0,'records':{},'libraries':{},'reviews':{}})


def verify_workers(root,plan):
    for language in LANGUAGES:
        worker=root/'workers'/language;child,state=load(worker)
        if child['parent_plan_sha256']!=digest(root/'plan.json') or child['worker_language']!=language:
            raise ValueError('Worker parent/language mismatch')
        if child['credential_alias']!=plan['credential_bindings'][language]:raise ValueError('Worker credential binding changed')
        if child['execution']!={**plan['execution'],'mode':'parallel_worker','max_workers':1}:
            raise ValueError('Worker execution mode changed')
        if child['slots']!=[s for s in plan['slots'] if s['language']==language]:raise ValueError('Worker task order changed')
        for name in ('records','source_files','environment','budget','model','repetitions','input_modality','images_allowed','instruction_language','prompt_language','success_policy','checkpoint_resume','recovery_policy','auto_finalize','compact_protocol'):
            if child[name]!=plan[name]:raise ValueError('Worker common contract changed: '+name)
        if child.get('lookup_turn_limit')!=plan.get('lookup_turn_limit'):raise ValueError('Worker information-turn allowance changed')
        if child.get('direct_protocol')!=plan.get('direct_protocol'):raise ValueError('Worker direct-candidate policy changed')
        if child.get('split_final_timing',False)!=plan.get('split_final_timing',False):raise ValueError('Worker final timing policy changed')
        if (worker/'source-cache').resolve()!=(root/'source-cache').resolve():raise ValueError('Worker source snapshot changed')
        verify_libraries(state)


def refresh(root,plan,state):
    merged={};libraries={};workers={}
    for language in LANGUAGES:
        worker=root/'workers'/language
        _,child=load(worker)
        child_records=list(child['records'].values())
        timing_complete=(child['status']=='complete' and len(child_records)==len(plan['records'])*plan['repetitions'] and
                         all(r.get('status')=='finished' and (r.get('verification_timing') or {}).get('initialization_exclusion_complete')
                             for r in child_records))
        initialization=sum(r['verification_timing']['total_initialization_seconds'] for r in child_records) if timing_complete else None
        for key,record in child['records'].items():
            item=deepcopy(record)
            if item.get('attempt'):item['attempt']=str(Path('workers')/language/item['attempt'])
            item['credential_alias']=plan['credential_bindings'][language]
            item['execution_clock']='language_worker'
            merged[key]=item
        libraries.update(child['libraries'])
        workers[language]={'status':child['status'],'elapsed_execution_seconds':child['elapsed_execution_seconds'],
                           'initialization_seconds':initialization,
                           'startup_excluded_seconds':child['elapsed_execution_seconds']-initialization if initialization is not None else None,
                           'finished_attempts':sum(r['status']=='finished' for r in child['records'].values()),
                           'credential_alias':plan['credential_bindings'][language],
                           'current_tasks':[{'task_id':r['task_id'],'status':r['status'],'connection_status':r.get('connection_status')}
                                            for r in child['records'].values() if r['status']!='finished']}
    state.update(records=merged,libraries=libraries,workers=workers)
    return state


def stop_worker_children(root):
    for language in LANGUAGES:
        worker=root/'workers'/language
        _,state=load(worker)
        for record in state['records'].values():
            if record['status']=='active':stop_orphan(worker/record['attempt'])


def worker_main(root,token,offline_probe=False):
    root=root.resolve();until=time.monotonic()+30
    plan,_=load(root)
    if plan.get('execution',{}).get('mode')!='parallel_worker':raise ValueError('Internal worker requires a language-worker plan')
    while True:
        path=root/'worker-launch.json'
        if path.exists() and read(path).get('token')==token:break
        if time.monotonic()>until:raise ValueError('Worker launch uncommitted; no API call made')
        time.sleep(.05)
    run_batch(root,offline_probe=offline_probe)


def run_parallel(root,offline_probe=False,interrupt_after_seconds=None):
    """offline_probe blocks provider access; interruption injection is tests only."""
    root=Path(root).resolve()
    with locked(root):
        plan,state=load(root)
        verify_environment(plan);verify_sources(root,plan);verify_workers(root,plan)
        if not offline_probe:verify_regression();validate_pair(plan['credential_bindings'])
        if 'offline_fixture' in state and bool(state['offline_fixture'])!=bool(offline_probe):
            raise ValueError('Cannot mix offline fixtures with model attempts')
        if offline_probe:state['offline_fixture']=True
        base_elapsed=state['elapsed_execution_seconds'];start=time.monotonic()
        processes={};outputs=[]
        def checkpoint():
            state['elapsed_execution_seconds']=base_elapsed+time.monotonic()-start
            refresh(root,plan,state);save(root/'state.json',state)
        state['status']='running';save(root/'state.json',state)
        try:
            # First stop any workers left by a killed parent. Their own stop
            # handlers terminate task controllers and native verifier groups.
            for record in state.get('worker_processes',{}).values():stop_owned(record)
            stop_worker_children(root)
            state['worker_processes']={};checkpoint()
            if run_remaining(plan['budget'],state['elapsed_execution_seconds'])<=0:
                state['status']='budget_exhausted';return state
            for language in LANGUAGES:
                worker=root/'workers'/language;_,child=load(worker)
                if child['status']=='complete':continue
                token=uuid.uuid4().hex
                command=[sys.executable,str(BASE/'runtime/batch.py'),'_worker','--root',str(worker),'--start-token',token]
                if offline_probe:command.append('--offline-probe')
                out=(worker/'worker.stdout.log').open('a');err=(worker/'worker.stderr.log').open('a');outputs.extend([out,err])
                process=subprocess.Popen(command,cwd=BASE,stdout=out,stderr=err,start_new_session=True)
                processes[language]=process
                state['worker_processes'][language]=identity(process.pid)
                state.setdefault('worker_launch_history',[]).append({'language':language,'at':now(),
                     'batch_execution_seconds':base_elapsed+time.monotonic()-start,'pid':process.pid})
                # Durable ownership precedes permission to send model requests.
                save(root/'state.json',state);save(worker/'worker-launch.json',{'token':token})
            deadline_hit=False;checkpoint_stop=False;last_progress=None
            while any(p.poll() is None for p in processes.values()):
                time.sleep(.25)
                if interrupt_after_seconds is not None and time.monotonic()-start>=interrupt_after_seconds:raise KeyboardInterrupt
                if run_remaining(plan['budget'],base_elapsed+time.monotonic()-start)<=0:
                    deadline_hit=True;break
                if plan.get('checkpoint_resume') and any(
                        p.poll() is not None and load(root/'workers'/language)[1]['status'] in ('checkpointed','blocked_provider')
                        for language,p in processes.items()):
                    checkpoint_stop=True;break
                if base_elapsed+time.monotonic()-start-state['elapsed_execution_seconds']>=1:
                    checkpoint()
                    progress={language:worker['finished_attempts'] for language,worker in state['workers'].items()}
                    if progress!=last_progress:
                        completed={language:[r for r in state['records'].values() if r['language']==language and r['status']=='finished'] for language in LANGUAGES}
                        def total(language,field,phase=False):
                            values=[(r.get('verification_timing') or {}).get(field) if phase else r.get(field) for r in completed[language]]
                            return round(sum(values),6) if all(isinstance(v,(int,float)) for v in values) else None
                        print(json.dumps({'execution':'parallel','finished':progress,
                              'wall_seconds':round(state['elapsed_execution_seconds'],2),
                              'finished_task_verifier_seconds':{l:total(l,'checker_seconds') for l in LANGUAGES},
                              'finished_task_startup_excluded_seconds':{l:total(l,'startup_excluded_seconds') for l in LANGUAGES},
                              'finished_task_warm_kernel_seconds':{l:total(l,'incremental_candidate_seconds',True) for l in LANGUAGES}}),flush=True)
                        last_progress=progress
            checkpoint()
            if checkpoint_stop:state['status']='checkpointed'
            elif deadline_hit:state['status']='budget_exhausted'
            elif all(v['status']=='complete' for v in state['workers'].values()) and all(p.returncode==0 for p in processes.values()):state['status']='complete'
            elif any(v['status']=='budget_exhausted' for v in state['workers'].values()):state['status']='budget_exhausted'
            else:state['status']='worker_failed'
        except KeyboardInterrupt:state['status']='interrupted'
        except (OSError,ValueError,subprocess.SubprocessError) as error:
            state.update(status='worker_failed',controller_error=str(error));raise
        finally:
            # Request both stops before waiting, so stopping one lane does not
            # grant the other an unmeasured extension.
            for process in processes.values():
                if process.poll() is None:process.terminate()
            for process in processes.values():
                try:process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    try:os.killpg(process.pid,signal.SIGKILL)
                    except ProcessLookupError:pass
                    process.wait()
            stop_worker_children(root)
            for output in outputs:output.close()
            checkpoint()
            state['worker_exit_codes']={language:p.returncode for language,p in processes.items()}
            save(root/'state.json',state)
            from batch_report import report
            report(root)
        return state
