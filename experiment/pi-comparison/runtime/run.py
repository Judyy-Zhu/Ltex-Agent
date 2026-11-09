#!/usr/bin/env python3
"""Run the actual pinned Pi RPC loop with seven restricted tools.

Single-task executor, also used by the full-catalog batch controller.
Source-fidelity review is separate from machine checking.
"""
from __future__ import annotations
import argparse
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import selectors
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from prepare import BASE, KIT, WORKSPACE, PI, prepare_job, sha, write_json
from task_rounds import TaskRounds
from recovery import (POLICY,RESUMABLE,error_kind,resume_prompt,jsonl_boundary,append_event,
                      latest_request_id,recover_interrupted_transport)

TOOLS = ['read_input','read_docs','read_library','write_source','check','remaining_budget','submit']


def usage_summary(root):
    spec = importlib.util.spec_from_file_location('usage_accounting',KIT/'usage_accounting.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    attempts = {}; pi_messages = {}; issues=[]
    path = root/'provider.jsonl'
    if path.exists():
        for index,line in enumerate(path.read_text().splitlines(),1):
            try:record = json.loads(line); number = record['attempt']
            except (ValueError,KeyError):
                issues.append({'line':index,'error':'Incomplete or invalid provider log record'});continue
            if record['kind']=='request':
                attempts[number] = None
            if record['kind']=='usage':
                attempts[number] = record['usage']
            if record['kind']=='pi_message':
                pi_messages[number] = record
    records=[]
    for n,raw in sorted(attempts.items()):
        try:normalized=module.normalize_raw(raw)
        except ValueError as error:
            issues.append({'attempt':n,'error':str(error)});normalized=module.normalize_raw(None)
        records.append({'attempt_id':str(n),'usage':normalized})
    return {'source':'provider_raw_final_usage_per_attempt', 'summary':module.summarize(records),
            'pi_messages_crosscheck':pi_messages,'log_issues':issues,
            'note':'Missing provider usage stays unknown, including interrupted requests. Cost is not inferred from tokens.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--language',choices=['lean','litex'],required=True)
    parser.add_argument('--credential-alias',choices=['primary','secondary'],default='primary')
    parser.add_argument('--seconds',type=int,default=None)
    parser.add_argument('--max-rounds',type=int,default=5)
    parser.add_argument('--task-id',default='EUCLID.I.P001')
    parser.add_argument('--prepared-root',type=Path,help='Controller-prepared job, used by batch.py')
    parser.add_argument('--resume-task',action='store_true',help='Resume the same unfinished task and saved Pi conversation')
    parser.add_argument('--start-token',help='Batch launch barrier; no API call before durable PID ownership is recorded')
    parser.add_argument('--max-checks',type=int,default=None)
    parser.add_argument('--check-timeout',type=int,default=None)
    parser.add_argument('--smoke',action='store_true')
    parser.add_argument('--offline-probe',action='store_true',help='Smoke only: deterministic real Pi tools; provider blocks all model requests')
    parser.add_argument('--offline-recovery-probe',action='store_true',help='Smoke only: deterministic model-stream fixtures, no network')
    parser.add_argument('--verify-compaction',action='store_true',help='Smoke only: explicitly compact once and verify auxiliary usage capture')
    args = parser.parse_args()
    if args.resume_task and not args.prepared_root:parser.error('--resume-task requires --prepared-root')
    if args.offline_probe and not args.smoke:parser.error('--offline-probe requires --smoke')
    if args.offline_recovery_probe and not args.smoke:parser.error('--offline-recovery-probe requires --smoke')
    if args.offline_probe and args.verify_compaction:parser.error('Offline probe cannot request model compaction')
    if args.verify_compaction and not args.smoke:
        parser.error('--verify-compaction is a tool-smoke diagnostic only')
    if args.seconds is not None and not 1<=args.seconds<=86400:
        parser.error('Task deadline must be within 1..86400 seconds')
    prepare_start=time.monotonic()
    if args.prepared_root:
        root=args.prepared_root.resolve()
        job=json.loads((root/'job.json').read_text())
        if job['language']!=args.language:parser.error('Prepared job language mismatch')
        if (root/'manifest.json').exists() and not args.resume_task:parser.error('Refusing to overwrite an existing task attempt; use --resume-task for checkpoint recovery')
        args.seconds=job['task_deadline_seconds']
    else:
        run_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-'+args.language+('-smoke' if args.smoke else '-'+args.task_id)
        root=BASE/'runs'/run_id
        job=prepare_job(root,args.language,args.seconds,args.smoke,task_id=args.task_id,
                        max_checks=args.max_checks,check_timeout=args.check_timeout,
                        max_rounds=None if args.smoke else args.max_rounds,checkpoint_resume=not args.smoke,auto_finalize=not args.smoke,compact_protocol=not args.smoke,direct_protocol=not args.smoke)
    checkpoint=bool(job.get('checkpoint_resume'))
    active_tools=['read_input','read_docs','read_library','submit_candidate','remaining_budget'] if job.get('compact_protocol') else [name for name in TOOLS if name!='submit'] if job.get('auto_finalize') else TOOLS
    if args.resume_task and not checkpoint:parser.error('This historical task has no current-task checkpoint policy')
    lock=(root/'.runner.lock').open('a')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:parser.error('Another controller owns this task; no duplicate API call permitted')
    previous=json.loads((root/'manifest.json').read_text()) if args.resume_task and (root/'manifest.json').exists() else {}
    if previous and previous.get('status') not in RESUMABLE:parser.error('This task already has a terminal result; it cannot be restarted')
    if previous:
        if previous.get('credential_alias')!=args.credential_alias:parser.error('Checkpoint credential alias changed')
        for name,value in previous.get('runtime_sha256',{}).items():
            if sha(BASE/'runtime'/name)!=value:parser.error('Frozen runtime changed; refusing checkpoint recovery')
        for field,folder in (('guide_sha256',root/'docs'),('input_sha256',root/'input')):
            for name,value in previous.get(field,{}).items():
                path=Path(job['docs'][name]) if field=='guide_sha256' else folder/name
                if sha(path)!=value:parser.error('Frozen task input/guide changed; refusing checkpoint recovery')
        if previous.get('job_sha256') and sha(root/'job.json')!=previous['job_sha256']:
            parser.error('Frozen task job changed; refusing checkpoint recovery')
    for path in root.glob('*.jsonl'):jsonl_boundary(path)
    run_id=root.name
    setup_seconds=time.monotonic()-prepare_start
    if args.start_token:
        deadline=time.monotonic()+30
        while True:
            launch=root/'launch.json'
            if launch.exists() and json.loads(launch.read_text()).get('token')==args.start_token:break
            if time.monotonic()>=deadline:raise ValueError('Batch launch was not committed; no API call made')
            time.sleep(.05)
    from credentials import read_credential
    offline=args.offline_probe or args.offline_recovery_probe
    credentials = {'api_key':'offline-fixture-never-transmitted'} if offline else read_credential(args.credential_alias)
    env = dict(os.environ)
    env['PARATERA_API_KEY'] = credentials['api_key']
    env.update(PI_CODING_AGENT_DIR=str(root/'pi-state'),EUCLID_RUN_ROOT=str(root),EUCLID_PYTHON=sys.executable,EUCLID_TEST_LANGUAGE=args.language)
    # No personal credentials or provider auto-selection in this process.
    for key in list(env):
        if key.endswith('_API_KEY') and key!='PARATERA_API_KEY':
            del env[key]
    models = json.loads((BASE/'models.smoke.json').read_text())
    model = models['providers']['paratera']['models'][0]
    model.update(input=['text'],contextWindow=32768,maxTokens=2048 if args.smoke else 8192,
                 name='DeepSeek-V4.1-Flash (development cap; thinking disabled)')
    write_json(root/'pi-state/models.json',models)
    settings = {'retry':{'enabled':False,'provider':{'maxRetries':0}},
                'compaction':{'enabled':True,'reserveTokens':8192 if job.get('auto_finalize') else 14000,
                              'keepRecentTokens':1000 if args.verify_compaction else 512 if job.get('auto_finalize') else 6000},
                'cacheWarming':{'mode':'off'}}
    write_json(root/'pi-state/settings.json',settings)
    from prompts import build_prompts,continuation_prompt
    system,prompt=build_prompts(job,smoke=args.smoke)
    if args.offline_probe:prompt='/offline-transport-probe'
    (root/'system-prompt.txt').write_text(system)
    (root/'user-prompt.txt').write_text(prompt)
    session_args=['--session',str(root/'pi-session.jsonl'),'--session-dir',str(root/'pi-sessions')] if checkpoint else ['--no-session']
    extension='offline_recovery_probe.ts' if args.offline_recovery_probe else 'offline_transport_probe.ts' if args.offline_probe else 'tools.ts'
    command = ['bash',str(PI/'pi-test.sh'),'--mode','rpc',*session_args,'--offline',
               '--no-extensions','--no-skills','--no-mcp','--no-prompt-templates','--no-context-files','--no-approve',
               '-e',str(BASE/'runtime'/extension),'--tools',','.join(active_tools),
               '--provider','paratera','--model','DeepSeek-V4.1-Flash','--system-prompt',system]
    start = time.monotonic()
    base_elapsed=previous.get('known_elapsed_seconds',previous.get('elapsed_seconds')) or 0
    timing_complete=previous.get('elapsed_seconds_complete',True) and previous.get('status') not in ('running','waiting_network')
    base_wait=previous.get('network_wait_seconds',0);network_wait=base_wait;waiting_since=None;retry_at=None
    network_retries=previous.get('network_retry_count',0);network_consecutive=0;last_error=None;blocked=False
    control=json.loads((root/'state.json').read_text()) if previous and (root/'state.json').exists() else {'checks':0,'submitted':False,'last_final_receipt':None}
    control.update(start_monotonic=start,deadline_monotonic=None if args.seconds is None else start+max(.01,args.seconds-base_elapsed))
    write_json(root/'state.json',control)
    manifest = {'run_id':run_id,'status':'running','language':args.language,'task_id':job['task_id'],
                'credential_alias':args.credential_alias,'offline_fixture':offline,
                'deadline_seconds':args.seconds,'setup_seconds':setup_seconds,
                'runtime_revision':'v25-correct-proof-layout-diagnostics',
                'split_final_timing':job.get('split_final_timing',False),
                'checkpoint_resume':checkpoint,'job_sha256':sha(root/'job.json'),
                'resume_count':previous.get('resume_count',0)+(1 if previous else 0),
                'segments':previous.get('segments',[]),
                'max_task_rounds':job.get('max_task_rounds'),'candidate_protocol':job.get('candidate_protocol'),
                'direct_protocol':job.get('direct_protocol',False),'direct_candidate_ready':job.get('direct_candidate_ready',False),
                'lookup_turn_limit_after_candidate':job.get('lookup_turn_limit'),
                'input_modality':'text_only','images_allowed':False,'instruction_language':'en',
                'success_policy':job['success_policy'],
                'prompt_sha256':{name:sha(root/name) for name in ('system-prompt.txt','user-prompt.txt')},
                'seed':job['foundation']['seed'],'library':job.get('library'),
                'shared_input_files':job['shared_input_files'],
                'language_specific_input_files':job['language_specific_input_files'],
                'pi_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=PI,text=True).strip(),
                'runtime_sha256':{p.name:sha(p) for p in (BASE/'runtime').glob('*') if p.suffix in ('.py','.ts')},
                'guide_sha256':{name:sha(Path(path)) for name,path in job['docs'].items()},
                'input_sha256':{p.name:sha(p) for p in (root/'input').iterdir() if p.is_file()},
                'hydrated_model_data_sha256':{p.name:sha(p) for p in (PI/'packages/ai/src/providers/data').glob('*.json')},
                'tool_allowlist':active_tools,'model_config':models,'settings':settings,
                'formal_result':False,'semantic_status':'pending','assumption_audit':'pending'}
    if previous and previous.get('status') in ('running','waiting_network') and manifest['segments']:
        manifest['segments'][-1]['status']='interrupted_unknown_end'
    segment={'started_at':datetime.now(timezone.utc).isoformat(),'status':'running'}
    manifest['segments'].append(segment)
    write_json(root/'manifest.json',manifest)
    print(json.dumps({'run_id':run_id,'root':str(root),'status':'starting'}),flush=True)
    settled = False; interrupted=False; errors = list(previous.get('controller_errors',[])); buffers = {}; last_stop = None
    rounds=TaskRounds(root,job);rounds_at_prompt=rounds.summary()['used'];round_limit_exhausted=False
    from lookup_budget import recover_violations
    recover_violations(root,rounds)
    if previous:
        recover_interrupted_transport(root,rounds)
        if rounds.reopen_transport_window():
            append_event(root,'transport_attempt_window_reopened',total_previous_attempts=rounds.summary()['total_used'])
        rounds_at_prompt=rounds.summary()['used']
        from tool_host import Host
        recovery_host=Host(root)
        try:recovery_host.recover_pending_check()
        finally:recovery_host.close()
        prompt=resume_prompt(root,rounds.summary())
        with (root/'continuation-prompts.jsonl').open('a') as prompts:
            prompts.write(json.dumps({'kind':'checkpoint_resume','message':prompt})+'\n')
        append_event(root,'task_resumed',resume_count=manifest['resume_count'],rounds_used=rounds_at_prompt)
        if rounds.summary()['exhausted']:settled=True;round_limit_exhausted=True
    def automatic_status():
        path=root/'auto-finalization.json'
        status=json.loads(path.read_text()).get('status') if job.get('auto_finalize') and path.exists() else None
        if status=='complete':return status
        if job.get('compact_protocol'):
            from atomic_candidate import pending
            if pending(root):return 'pending'
        return status
    if automatic_status()=='complete':settled=True;round_limit_exhausted=False
    last_heartbeat=0
    def heartbeat(force=False):
        nonlocal last_heartbeat
        if not checkpoint:return
        now=time.monotonic()
        if not force and now-last_heartbeat<1:return
        last_heartbeat=now
        segment['elapsed_seconds']=now-start
        manifest.update(known_elapsed_seconds=base_elapsed+now-start,
                        elapsed_seconds=base_elapsed+now-start if timing_complete else None,
                        elapsed_seconds_complete=timing_complete,network_retry_count=network_retries,
                        consecutive_api_failures=network_consecutive,
                        network_wait_seconds=network_wait+(now-waiting_since if waiting_since is not None else 0),
                        task_rounds=rounds.summary(),last_checkpoint_at=datetime.now(timezone.utc).isoformat())
        write_json(root/'manifest.json',manifest)
        session_file=root/'pi-session.jsonl'
        if session_file.exists():
            with session_file.open('rb') as stream:os.fsync(stream.fileno())
    def transport_failure(message):
        nonlocal last_error,blocked,retry_at,waiting_since,network_consecutive
        if rounds.summary()['exhausted'] or automatic_status()=='pending':return
        last_error=str(message).replace(credentials['api_key'],'[REDACTED]')[:1600]
        kind=error_kind(last_error) or 'blocked_provider'
        manifest.update(status='waiting_network',last_transport_error=last_error,api_error_class=kind)
        if retry_at is None and not blocked:
            network_consecutive+=1
            policy=job.get('recovery_policy') or POLICY
            if policy.get('transport_retries_consume_proof_rounds',True) and rounds.limit is not None and not rounds.accepted_candidate():
                rounds.transport_failure(last_error,latest_request_id(root))
                stats=rounds.summary()
                if stats['exhausted']:
                    if stats['transport_only_exhausted']:
                        blocked=True;manifest.update(status='blocked_provider',checkpoint_reason='five_api_attempts_failed')
                    append_event(root,'task_attempts_exhausted',transport_only=stats['transport_only_exhausted'],rounds_used=stats['used'])
                    heartbeat(True);return
            if network_consecutive>=policy.get('network_max_attempts',5):
                blocked=True;manifest.update(status='blocked_provider',checkpoint_reason='five_api_attempts_failed')
                append_event(root,'api_attempts_exhausted',attempts=network_consecutive,rounds_used=rounds.summary()['used'])
                heartbeat(True);return
            now=time.monotonic();waiting_since=now
            delay=min(policy['network_retry_max_seconds'],policy['network_retry_initial_seconds']*2**min(network_consecutive-1,5))
            if args.offline_recovery_probe:delay=job.get('offline_recovery_fixture',{}).get('retry_delay',.1)
            retry_at=now+delay
            append_event(root,'network_wait',error=last_error,retry_in_seconds=delay,rounds_used=rounds.summary()['used'])
        heartbeat(True)
    compact_requested = False; compact_receipt = None
    with (root/'rpc.jsonl').open('a' if checkpoint else 'w') as output, (root/'stderr.log').open('a' if checkpoint else 'w') as stderr:
        process = subprocess.Popen(command,cwd=root/'work',env=env,stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        selector = selectors.DefaultSelector()
        try:
            from process_control import identity
            manifest['pi_process']=identity(process.pid)
            write_json(root/'manifest.json',manifest)
            if not settled:
                process.stdin.write((json.dumps({'id':'solve','type':'prompt','message':prompt},ensure_ascii=False)+'\n').encode())
                process.stdin.flush()
            for stream,kind in ((process.stdout,'out'),(process.stderr,'err')):
                os.set_blocking(stream.fileno(),False)
                selector.register(stream,selectors.EVENT_READ,kind); buffers[kind]=b''
            while (args.seconds is None or time.monotonic()-start<args.seconds) and not settled:
                heartbeat()
                if automatic_status()=='complete':
                    settled=True;round_limit_exhausted=False;break
                if blocked:break
                if retry_at is not None and time.monotonic()>=retry_at:
                    network_wait+=time.monotonic()-waiting_since;waiting_since=None;retry_at=None
                    network_retries+=1;last_error=None
                    manifest['status']='running';continuation=resume_prompt(root,rounds.summary())
                    with (root/'continuation-prompts.jsonl').open('a') as prompts:
                        prompts.write(json.dumps({'kind':'network_retry','message':continuation})+'\n')
                    process.stdin.write((json.dumps({'id':'reconnect-'+str(network_retries),'type':'prompt','message':continuation})+'\n').encode())
                    process.stdin.flush();rounds_at_prompt=rounds.summary()['used'];heartbeat(True)
                    append_event(root,'network_retry',retry=network_retries,rounds_used=rounds_at_prompt)
                if args.offline_probe and (root/'offline-pi.json').exists():
                    settled=True;break
                if process.poll() is not None and not selector.get_map():
                    break
                for key,_ in selector.select(timeout=1 if args.seconds is None else min(1,max(.01,args.seconds-(time.monotonic()-start)))):
                    chunk = os.read(key.fileobj.fileno(),65536)
                    if not chunk:
                        selector.unregister(key.fileobj); continue
                    if key.data=='err':
                        stderr.write(chunk.decode(errors='replace')); stderr.flush(); continue
                    buffers['out'] += chunk
                    while b'\n' in buffers['out']:
                        line,buffers['out'] = buffers['out'].split(b'\n',1)
                        try:
                            event = json.loads(line)
                        except ValueError:
                            stderr.write(line.decode(errors='replace')+'\n'); continue
                        output.write(json.dumps(event,ensure_ascii=False)+'\n'); output.flush()
                        if event.get('type')=='message_end' and event.get('message',{}).get('role')=='assistant':
                            last_stop = event['message'].get('stopReason')
                            if checkpoint and last_stop=='error':
                                last_error=event['message'].get('errorMessage','Provider response failed')
                            elif checkpoint:network_consecutive=0
                        if event.get('type')=='response' and event.get('success') is False:
                            errors.append(event)
                            if checkpoint:transport_failure(event.get('error',event))
                            elif event.get('id')=='solve':
                                settled=True
                        if automatic_status()=='complete':
                            settled=True;round_limit_exhausted=False;break
                        if event.get('type')=='agent_settled':
                            recover_violations(root,rounds)
                            if automatic_status()=='pending':
                                errors.append({'kind':'local_finalization_pending','error':'Resume to finish local verification; no extra model request or attempt charged'})
                                break
                            if args.verify_compaction and not compact_requested:
                                compact_requested = True
                                process.stdin.write((json.dumps({'id':'compact-smoke','type':'compact'})+'\n').encode())
                                process.stdin.flush()
                            elif not args.verify_compaction:
                                if checkpoint and (last_stop=='error' or last_error is not None):
                                    transport_failure(last_error or 'Provider response failed')
                                    continue
                                saved=root/'submission.json'
                                complete=saved.exists() and json.loads(saved.read_text()).get('agent_claim')=='complete'
                                if job.get('max_task_rounds') is not None and not complete:
                                    if rounds.summary()['used']==rounds_at_prompt and rounds.summary()['remaining']>0 and not rounds.accepted_candidate():
                                        rounds.unused_generation('Generation ended without a candidate check: '+str(last_stop))
                                    stats=rounds.summary()
                                    if stats['exhausted'] or stats['remaining']==0:
                                        settled=True;round_limit_exhausted=True
                                    else:
                                        continuation=continuation_prompt(job,stats)
                                        with (root/'continuation-prompts.jsonl').open('a') as prompts:
                                            prompts.write(json.dumps({'after_round':stats['used'],'message':continuation})+'\n')
                                        process.stdin.write((json.dumps({'id':'continue-'+str(stats['used']),'type':'prompt','message':continuation})+'\n').encode())
                                        process.stdin.flush();rounds_at_prompt=stats['used']
                                else:settled=True
                        if event.get('type')=='response' and event.get('id')=='compact-smoke':
                            compact_receipt = event
                            settled=True
                if automatic_status()=='pending' and errors and errors[-1].get('kind')=='local_finalization_pending':break
                if automatic_status()=='complete':settled=True;round_limit_exhausted=False
                elif rounds.summary()['exhausted']:
                    settled=True;round_limit_exhausted=True
        except KeyboardInterrupt:
            interrupted=True
        except (OSError,ValueError) as error:
            errors.append({'kind':'controller_exception','error':str(error)})
        finally:
            # Kill the process group: no checker/model call may continue outside
            # the measured interval or leak into the other language's run.
            try:os.killpg(process.pid,signal.SIGTERM)
            except ProcessLookupError:pass
            try:process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                try:os.killpg(process.pid,signal.SIGKILL)
                except ProcessLookupError:pass
                process.wait()
            for stream in (process.stdin,process.stdout,process.stderr):stream.close()
            selector.close()
    state = json.loads((root/'state.json').read_text())
    submission_path = root/'submission.json'
    submission = json.loads(submission_path.read_text()) if submission_path.exists() else None
    round_limit_exhausted=(round_limit_exhausted or rounds.summary()['exhausted']) and automatic_status()!='complete'
    status = 'interrupted' if interrupted else 'blocked_provider' if blocked else 'round_limit_exhausted' if round_limit_exhausted else 'settled' if settled else ('deadline' if args.seconds is not None and time.monotonic()-start>=args.seconds else 'checkpointed' if checkpoint else 'process_exited')
    journal_path=root/'session-journal.json'
    journal=json.loads(journal_path.read_text()) if journal_path.exists() else {}
    native_events_path=root/'session-events.jsonl'
    native_events=[json.loads(line) for line in native_events_path.read_text().splitlines()] if native_events_path.exists() else []
    native_summary={'mode':'native_persistent','starts':journal.get('starts',0),'restarts':journal.get('restarts',0),
                    'accepted_blocks':len(journal.get('entries',[])),
                    'candidate_requests':sum(e.get('kind')=='native_request' and not e.get('replay') for e in native_events),
                    'replay_requests':sum(e.get('kind')=='native_request' and bool(e.get('replay')) for e in native_events),
                    'startup_seconds':sum(e.get('seconds',0) for e in native_events if e.get('kind')=='session_start')}
    gate_checks=state.get('submission_gate_checks',0)
    checker_seconds=sum(json.loads(p.read_text()).get('seconds',0) for p in (root/'receipts').glob('*.json'))
    if (root/'submission-gates.jsonl').exists():
        checker_seconds+=sum(json.loads(line).get('seconds',0) for line in (root/'submission-gates.jsonl').read_text().splitlines())
    from verification_timing import measure
    verification_timing=measure(root,native_events,checker_seconds)
    checker_seconds=verification_timing['accounted_verifier_seconds']
    usage=usage_summary(root)
    from item_tracking import summary as retry_summary
    segment.update(status=status,ended_at=datetime.now(timezone.utc).isoformat(),elapsed_seconds=time.monotonic()-start)
    if waiting_since is not None:network_wait+=time.monotonic()-waiting_since
    manifest.update(status=status,elapsed_seconds=base_elapsed+time.monotonic()-start if timing_complete else None,
                    known_elapsed_seconds=base_elapsed+time.monotonic()-start,elapsed_seconds_complete=timing_complete,
                    network_wait_seconds=network_wait,network_retry_count=network_retries,
                    consecutive_api_failures=network_consecutive,
                    check_calls=state['checks']+gate_checks,
                    task_rounds=rounds.summary(),
                    tool_check_calls=state['checks'],submission_gate_checks=gate_checks,checker_seconds=checker_seconds,verification_timing=verification_timing,
                    non_checker_seconds=max(0,base_elapsed+time.monotonic()-start-checker_seconds) if timing_complete else None,
                    finalization_origin='controller_auto_verified' if automatic_status()=='complete' else None,
                    last_assistant_stop_reason=last_stop,
                    compaction_smoke_receipt=compact_receipt,
                    native_session=native_summary,
                    compaction_policy='local_durable_task_checkpoint_zero_model_calls' if job.get('auto_finalize') else 'provider_summary',
                    retry_statistics=retry_summary(root),
                    machine_checked_candidate=bool(submission and submission['agent_claim']=='complete'),
                    telemetry_complete=bool(settled and not interrupted and timing_complete and not usage['log_issues']),
                    submission_received=bool(submission),controller_errors=errors,
                    usage=usage)
    from verification_timing import exclude_initialization
    manifest['startup_excluded_seconds']=exclude_initialization(manifest['elapsed_seconds'],verification_timing)
    write_json(root/'manifest.json',manifest)
    print(json.dumps({'run_id':run_id,'status':status,'seconds':round(manifest['known_elapsed_seconds'],3),
                      'checks':state['checks'],'candidate':manifest['machine_checked_candidate'],
                      'usage':manifest['usage']['summary']},ensure_ascii=False),flush=True)
    if blocked:sys.exit(75)
    if not settled:
        sys.exit(1)


if __name__=='__main__':
    def terminate(_signum,_frame):raise KeyboardInterrupt
    signal.signal(signal.SIGTERM,terminate)
    if hasattr(signal,'SIGHUP'):signal.signal(signal.SIGHUP,terminate)
    main()
