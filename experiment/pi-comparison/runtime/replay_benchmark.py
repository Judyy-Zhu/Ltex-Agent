#!/usr/bin/env python3
"""Offline native-verifier replay of hash-bound, jointly accepted task artifacts.

Fresh processes and warm Session/REPL candidate checks are reported separately.
No Pi, credentials, model requests, or source rewriting are involved.
"""
import argparse
import csv
from datetime import datetime,timezone
import hashlib
import json
import math
import os
from pathlib import Path
import random
import statistics
import subprocess
import time
from native_sessions import LeanSession,LitexSession,litex_blocks
from seed_support import starting_source,require_seed_prefix
from tool_host import bounded,source_guard


def read(path):return json.loads(path.read_text())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')


def artifact(batch,slot,record):
    root=bounded(batch,record['attempt'])
    job=read(root/'job.json');manifest=read(root/'manifest.json');submission=read(root/'submission.json')
    if manifest.get('job_sha256')!=sha(root/'job.json'):raise ValueError('Frozen artifact job changed')
    if manifest.get('offline_fixture') or manifest.get('status')!='settled' or not manifest.get('machine_checked_candidate'):
        raise ValueError('Replay requires a completed real machine-accepted task')
    if job['language']!=slot['language'] or job['task_id']!=slot['task_id']:raise ValueError('Artifact identity mismatch')
    if submission.get('agent_claim')!='complete' or submission.get('unfinished'):raise ValueError('Incomplete artifact')
    rid=submission['final_receipt_id'];receipt=read(bounded(root/'receipts',rid+'.json'));gate=read(root/'submission-gate.json')
    actual={str(p.relative_to(root/'work')):sha(p) for p in (root/'work').rglob('*') if p.is_file()}
    if receipt['mode']!='final' or not receipt['passed'] or receipt['source_hashes']!=actual:
        raise ValueError('Final artifact failed or changed')
    if not gate.get('passed') or gate.get('source_hashes')!=actual or gate.get('final_receipt_id')!=rid:
        raise ValueError('Declaration/axiom gate failed or changed')
    source_path=bounded(root/'work',receipt['entry']);source=source_path.read_text()
    require_seed_prefix(job,source);source_guard(source,job['language'],job['foundation'].get('allowed_imports',[]))
    prefix=starting_source(job).rstrip();candidate=source[len(prefix):].lstrip('\n')
    if not candidate.strip():raise ValueError('Empty accepted increment')
    plan=read(batch/'plan.json');sealed=plan['environment']['files']
    paths=[Path(job['litex'])] if job['language']=='litex' else [Path(job['lake']),Path(job['lean_repl']),Path(job['lean_project'])/'lean-toolchain',Path(job['lean_project'])/'lake-manifest.json']
    kernel_hashes={}
    for path in paths:
        resolved=str(path.resolve());value=sha(path)
        if sealed.get(resolved)!=value:raise ValueError('Pinned verifier component changed: '+str(path))
        kernel_hashes[resolved]=value
    return {'root':root,'job':job,'candidate':candidate,'final_path':source_path,
            'final_sha256':sha(source_path),'job_sha256':sha(root/'job.json'),'kernel_sha256':kernel_hashes}


def select(batch,limit=None):
    plan=read(batch/'plan.json');state=read(batch/'state.json');records=state['records'];pairs={};excluded=[]
    if state.get('plan_sha256')!=sha(batch/'plan.json'):raise ValueError('Frozen source batch plan changed')
    if state.get('status') in ('running','waiting_network'):raise ValueError('Stop the agent batch before an isolated verifier replay')
    for slot in plan['slots']:
        record=records.get(slot['key'],{})
        key=(slot['repetition'],slot['task_id'])
        if record.get('status')=='finished' and record.get('published'):
            pairs.setdefault(key,{})[slot['language']]=(slot,record)
    chosen=[]
    seen=set()
    for slot in plan['slots']:
        key=(slot['repetition'],slot['task_id'])
        if key in seen:continue
        seen.add(key)
        if set(pairs.get(key,{}))!={'lean','litex'}:
            excluded.append({'repetition':key[0],'task_id':key[1],'reason':'not machine-accepted in both languages'})
            continue
        chosen.append((key,{lang:artifact(batch,*pairs[key][lang]) for lang in ('lean','litex')}))
    if limit is not None:chosen=chosen[:limit]
    if not chosen:raise ValueError('No jointly machine-accepted task artifacts to replay')
    return chosen,excluded,len(seen)


def sample(value,scratch):
    job=value['job'];language=job['language'];result={'passed':False,'candidate_native_requests':0}
    scratch.mkdir();(scratch/'work').mkdir()
    native=None
    try:
        start=time.perf_counter()
        # Baseline is newly loaded each repetition. No controller journal/cache can
        # return a previous candidate's success or redeclare it in a used env.
        cls=LeanSession if language=='lean' else LitexSession
        native=cls({**job,'auto_finalize':False},scratch,math.inf)
        result['session_initialization_seconds']=time.perf_counter()-start
        blocks=litex_blocks(value['candidate']) if language=='litex' else [{'text':value['candidate']}]
        start=time.perf_counter();passed=True
        for block in blocks:
            result['candidate_native_requests']+=1
            passed,response=native.send(block['text'],math.inf)
            if not passed:
                result['candidate_failure']=response;break
        result['warm_candidate_seconds']=time.perf_counter()-start
        result['candidate_passed']=passed
    except (OSError,RuntimeError,ValueError) as error:
        result['candidate_error']=str(error)
    finally:
        if native:native.close()
    env={k:v for k,v in os.environ.items() if not k.endswith('_API_KEY')}
    command=([job['lake'],'env','lean',str(value['final_path'])] if language=='lean' else
             [job['litex'],'-strict','-lang','en','-f',str(value['final_path'])])
    cwd=job['lean_project'] if language=='lean' else str(value['root']/'work')
    start=time.perf_counter()
    try:
        process=subprocess.run(command,cwd=cwd,env=env,capture_output=True,text=True)
        result['fresh_file_seconds']=time.perf_counter()-start
        raw={'command':command,'exit_code':process.returncode,'stdout':process.stdout,'stderr':process.stderr}
        save(scratch/'fresh-file-receipt.json',raw)
        passed=process.returncode==0
        if language=='litex':
            output=json.loads(process.stdout)
            passed=passed and output.get('kind')=='run' and output.get('run_result')=='success' and not output.get('errors') and not output.get('session_terminated') and output.get('termination') is None
        elif any(s in process.stdout+process.stderr for s in ('sorry','sorryAx','declaration uses')):passed=False
        result['fresh_file_passed']=bool(passed)
    except (OSError,ValueError) as error:
        result['fresh_file_seconds']=time.perf_counter()-start;result['fresh_file_error']=str(error)
    result['passed']=bool(result.get('candidate_passed') and result.get('fresh_file_passed'))
    result['final_sha256_after']=sha(value['final_path'])
    if result['final_sha256_after']!=value['final_sha256']:raise ValueError('Artifact changed during replay')
    return result


def summarize(rows):
    result={}
    for language in ('lean','litex'):
        selected=[r for r in rows if r['language']==language and not r['warmup']]
        result[language]={'samples':len(selected),'passed':sum(r['passed'] for r in selected)}
        for metric in ('session_initialization_seconds','warm_candidate_seconds','fresh_file_seconds'):
            values=[r[metric] for r in selected if metric in r]
            result[language][metric]={'median':statistics.median(values) if values else None,
                                     'mean':statistics.mean(values) if values else None,'samples_with_timing':len(values)}
    return result


def benchmark(batch,output,repetitions=3,warmups=1,limit=None,random_seed=20261109):
    if repetitions<1 or warmups<0 or (limit is not None and limit<1):raise ValueError('Invalid replay sample count')
    chosen,excluded,registered=select(batch,limit)
    output.mkdir(parents=True,exist_ok=False);(output/'samples').mkdir()
    result={'scope':'native verifier replay only','model_calls':0,
        'runner_sha256':{p.name:sha(p) for p in (Path(__file__),Path(__file__).with_name('native_sessions.py'),Path(__file__).with_name('seed_support.py'))},'source_batch':str(batch),'registered_task_pairs':registered,
        'selection':'jointly machine-accepted artifacts; same original tasks for both languages, no source rewriting',
        'selected_tasks':[{'repetition':key[0],'task_id':key[1]} for key,_ in chosen],
        'excluded_tasks':excluded,'limit_tasks':limit,'repetitions':repetitions,'warmups':warmups,'random_seed':random_seed,
        'semantic_review':'optional and not certified by this replay',
        'timing_policy':'Sequential, randomized paired language order. Fresh process is not a flushed OS cache. Warm candidate excludes separately timed seed/library initialization. Each repetition uses a new Session/REPL and actually submits every candidate block. Failures and warmups are retained in raw rows; measured summaries exclude warmups only.',
        'rows':[],'artifacts':[{'task_id':key[1],'language':language,'final_path':str(v['final_path']),
            'final_sha256':v['final_sha256'],'job_sha256':v['job_sha256'],'kernel_sha256':v['kernel_sha256']}
            for key,pair in chosen for language,v in pair.items()]}
    rng=random.Random(random_seed)
    for key,pair in chosen:
        for index in range(warmups+repetitions):
            order=['lean','litex'];rng.shuffle(order)
            for language in order:
                identity=f'{len(result["rows"])+1:04}-{language}'
                row={'task_id':key[1],'source_repetition':key[0],'language':language,'warmup':index<warmups,
                     'replay_index':index-warmups+1,'final_sha256':pair[language]['final_sha256'],
                     **sample(pair[language],output/'samples'/identity)}
                result['rows'].append(row);save(output/'results.json',result)
                print(json.dumps({k:row.get(k) for k in ('task_id','language','warmup','passed','warm_candidate_seconds','fresh_file_seconds')}),flush=True)
    result.update(completed_at=datetime.now(timezone.utc).isoformat(),passed=all(r['passed'] for r in result['rows']),summary=summarize(result['rows']))
    save(output/'results.json',result)
    with (output/'results.csv').open('w') as stream:
        fields=['task_id','source_repetition','language','warmup','replay_index','passed','candidate_native_requests','session_initialization_seconds','warm_candidate_seconds','fresh_file_seconds','final_sha256']
        writer=csv.DictWriter(stream,fieldnames=fields,extrasaction='ignore');writer.writeheader();writer.writerows(result['rows'])
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--batch',required=True,type=Path);parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--repetitions',type=int,default=3);parser.add_argument('--warmups',type=int,default=1)
    parser.add_argument('--limit-tasks',type=int)
    args=parser.parse_args()
    result=benchmark(args.batch.resolve(),args.output.resolve(),args.repetitions,args.warmups,args.limit_tasks)
    print(json.dumps({'passed':result['passed'],'model_calls':0,'summary':result['summary']}))
    if not result['passed']:raise SystemExit(1)


if __name__=='__main__':main()
