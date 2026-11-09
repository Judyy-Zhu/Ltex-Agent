#!/usr/bin/env python3
"""Standalone read-only language monitor, outside the frozen experiment runtime."""
from __future__ import annotations
import argparse
import collections
from datetime import datetime,timezone,timedelta
import json
import os
from pathlib import Path
import re
import shutil
import sys
import textwrap
import time

BASE=Path(__file__).resolve().parent


def read_json(path):
    try:return json.loads(path.read_text())
    except (OSError,ValueError):return None


def jsonl(path,tail_bytes=None):
    """Ignore an incomplete append, including the first cut line of a tail."""
    try:
        with path.open('rb') as stream:
            if tail_bytes:
                size=path.stat().st_size
                if size>tail_bytes:
                    stream.seek(size-tail_bytes);stream.readline()
            lines=stream.read().decode('utf-8',errors='replace').splitlines()
    except OSError:return []
    result=[]
    for line in lines:
        try:
            value=json.loads(line)
            if isinstance(value,dict):result.append(value)
        except ValueError:continue
    return result


def safe_text(value):
    text=str(value)
    text=re.sub(r'sk-[A-Za-z0-9_-]+','[REDACTED]',text)
    text=re.sub(r'(?i)(authorization\s*:\s*bearer\s+)\S+',r'\1[REDACTED]',text)
    return ''.join(c if c in '\n\t' or (ord(c)>=32 and not 127<=ord(c)<=159) else '?' for c in text)


def number(value):
    return value if isinstance(value,(int,float)) and not isinstance(value,bool) and value>=0 else None


def live_usage(path):
    requests=set();usage={};responses=collections.Counter()
    last=None
    for row in jsonl(path):
        kind=row.get('kind');identifier=row.get('attempt')
        if kind=='request':requests.add(identifier)
        elif kind=='usage' and isinstance(row.get('usage'),dict):usage[identifier]=row['usage']
        elif kind=='response':responses[str(row.get('status'))]+=1
        if kind in ('request','response','usage','pi_message'):
            last={k:row[k] for k in ('utc','kind','status','stopReason') if k in row}
    totals={'input':0,'output':0,'total':0}
    incomplete=0
    for raw in usage.values():
        prompt=number(raw.get('prompt_tokens'));completion=number(raw.get('completion_tokens'))
        total=number(raw.get('total_tokens'))
        if total is None and prompt is not None and completion is not None:total=prompt+completion
        for field,value in (('input',prompt),('output',completion),('total',total)):
            if value is not None:totals[field]+=value
        incomplete+=total is None
    return {'requests':len(requests|usage.keys()),'known_tokens':totals,
            'missing_usage':len(requests-usage.keys())+incomplete,
            'http_responses':dict(responses),'last_event':last}


def receipt_issue(receipt):
    if not receipt:return None
    if receipt.get('error'):return safe_text(receipt['error'])
    for frame in receipt.get('native_frames',[]):
        if frame.get('replay'):continue
        native=frame.get('native',{})
        for error in native.get('errors',[]):
            message=error.get('message') or error.get('obligation') or str(error)
            obligation=error.get('obligation')
            if obligation and obligation!=message:message+='\n'+str(obligation)
            return safe_text((str(error.get('phase'))+': ' if error.get('phase') else '')+str(message))
        for error in native.get('messages',[]):
            if error.get('severity')=='error':return safe_text(error.get('data',error))
    for field in ('stdout','stderr'):
        value=receipt.get(field)
        if value and not receipt.get('passed'):return safe_text(value)
    return None


def latest_tool_failure(attempt):
    files=sorted((attempt/'tool-results').glob('*.json'),key=lambda p:p.stat().st_mtime,reverse=True)
    for path in files:
        stored=read_json(path) or {}
        result=stored.get('result',{})
        if result.get('isError'):
            error=result.get('details',{}).get('error')
            if error is None:error='\n'.join(str(v.get('text','')) for v in result.get('content',[]))
            return safe_text(error)
    return None


def snapshot(root,language):
    """Read selected language only; never call the runner, verifier or an API."""
    worker=root/'workers'/language
    state=read_json(worker/'state.json')
    plan=read_json(worker/'plan.json')
    output={'batch':root.name,'language':language,
            'updated_at':datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S Asia/Shanghai')}
    if state is None or plan is None:
        return {**output,'state_available':False,'status':'unavailable','message':'Worker state is not available yet.'}
    records=list(state.get('records',{}).values())
    finished=[r for r in records if r.get('status')=='finished']
    active=[r for r in records if r.get('status')!='finished']
    passed=sum(bool(r.get('published')) for r in finished)
    output.update(state_available=True,status=state.get('status'),total_tasks=len(plan.get('slots',[])),
                  finished=len(finished),passed=passed,failed=len(finished)-passed,
                  finished_pass_rate=passed/len(finished) if finished else None,
                  worker_seconds=state.get('elapsed_execution_seconds',0))
    known=0;missing=0
    for record in finished:
        field=(record.get('usage') or {}).get('fields',{}).get('token_total',{})
        known+=field.get('known_subtotal') or field.get('value') or 0
        missing+=field.get('missing_requests',0)
    current=active[-1] if active else records[-1] if records else None
    output['known_worker_tokens']=known
    output['missing_worker_usage']=missing
    if not current:
        output['current']=None
        return output
    relative=Path(current['attempt'])
    if relative.is_absolute() or '..' in relative.parts:
        output['current']={'task_id':current['task_id'],'status':'invalid attempt path'}
        return output
    attempt=worker/relative
    manifest=read_json(attempt/'manifest.json') or {}
    rounds=read_json(attempt/'task-rounds.json') or {'rounds':[]}
    history=rounds.get('rounds',[])
    window=history[rounds.get('window_start',0):]
    tools=jsonl(attempt/'tools.jsonl',tail_bytes=64000)
    events=jsonl(attempt/'rpc.jsonl',tail_bytes=256000)
    latest_tool=next((e for e in reversed(events) if e.get('type') in ('tool_execution_start','tool_execution_end')),None)
    receipts=sorted((attempt/'receipts').glob('check-*.json'))
    latest=read_json(receipts[-1]) if receipts else None
    checker_seconds=sum((read_json(path) or {}).get('seconds',0) for path in receipts)
    checker_seconds+=sum(row.get('seconds',0) for row in jsonl(attempt/'submission-gates.jsonl'))
    completion=read_json(attempt/'auto-finalization.json') or {}
    usage=live_usage(attempt/'provider.jsonl')
    if current.get('status')!='finished':
        output['known_worker_tokens']+=usage['known_tokens']['total']
        output['missing_worker_usage']+=usage['missing_usage']
    rpc=attempt/'rpc.jsonl'
    try:rpc_age=max(0,time.time()-rpc.stat().st_mtime)
    except OSError:rpc_age=None
    issue=receipt_issue(latest)
    if manifest.get('status') in ('waiting_network','blocked_provider'):
        issue=safe_text(manifest.get('last_transport_error') or issue or 'Waiting for the API.')
    output['current']={
        'task_id':current['task_id'],'record_status':current.get('status'),
        'status':manifest.get('status','preparing'),'attempt_directory':str(attempt),
        'attempt_window_used':len(window),'attempt_limit':rounds.get('limit',plan.get('budget',{}).get('max_task_rounds')),
        'cumulative_attempts':len(history),'attempt_types':dict(collections.Counter(r.get('kind','candidate') for r in window)),
        'latest_attempt':{k:window[-1].get(k) for k in ('window_round','kind','status','passed')} if window else None,
        'elapsed_seconds':manifest.get('known_elapsed_seconds',manifest.get('elapsed_seconds')),
        'elapsed_complete':manifest.get('elapsed_seconds_complete',True),
        'checker_seconds':checker_seconds,'auto_finalization_status':completion.get('status'),
        'non_checker_seconds':manifest.get('non_checker_seconds'),
        'network_retries':manifest.get('network_retry_count',0),'network_wait_seconds':manifest.get('network_wait_seconds',0),
        'resume_count':manifest.get('resume_count',0),'usage':usage,
        'recent_tools':[{'tool':r.get('tool'),'seconds':r.get('seconds'),'error':r.get('error',False)} for r in tools[-5:]],
        'latest_tool':{'tool':latest_tool.get('toolName'),'phase':latest_tool.get('type')} if latest_tool else None,
        'last_check':{'receipt_id':latest.get('receipt_id'),'mode':latest.get('mode'),'passed':latest.get('passed')} if latest else None,
        'issue':issue,'last_tool_error':latest_tool_failure(attempt) if any(r.get('error') for r in tools) else None,
        'rpc_age_seconds':rpc_age}
    return output


def duration(seconds):
    if seconds is None:return 'not recorded yet'
    seconds=max(0,int(seconds));hours,rest=divmod(seconds,3600);minutes,seconds=divmod(rest,60)
    return f'{hours:02}:{minutes:02}:{seconds:02}'


def render(data,width=110):
    lines=[f"{data['language'].upper()} | {data['batch']} | {data['updated_at']}",
           '-'*min(width,110)]
    if not data.get('state_available'):return '\n'.join(lines+[data['message']])
    rate='n/a' if data['finished_pass_rate'] is None else f"{100*data['finished_pass_rate']:.1f}%"
    lines.extend([
        f"Worker: {data['status']} | elapsed {duration(data['worker_seconds'])}",
        f"Finished {data['finished']}/{data['total_tasks']} | passed {data['passed']} | failed {data['failed']} | pass rate among finished {rate}",
        f"Known worker tokens >= {data['known_worker_tokens']:,} | usage not returned/incomplete for {data['missing_worker_usage']} request(s)",
        ''])
    current=data.get('current')
    if not current:return '\n'.join(lines+['No task has started.'])
    if 'attempt_window_used' not in current:return '\n'.join(lines+[str(current)])
    lines.extend([
        f"Task: {current['task_id']} | {current['status']} | record {current['record_status']}",
        f"Attempts in current window: {current['attempt_window_used']}/{current['attempt_limit']} | cumulative {current['cumulative_attempts']}",
        f"Attempt types: {current['attempt_types'] or 'none yet'}",
        f"Task elapsed: {duration(current['elapsed_seconds'])}"+(' (known lower bound)' if not current['elapsed_complete'] else ''),
        f"Connection retries: {current['network_retries']} | network wait {duration(current['network_wait_seconds'])} | task resumes {current['resume_count']}",
        f"Current task known tokens >= {current['usage']['known_tokens']['total']:,} | observed requests {current['usage']['requests']} | usage pending/missing {current['usage']['missing_usage']}",
    ])
    if 'checker_seconds' in current:
        lines.append(f"Verifier time so far: {current['checker_seconds']:.3f}s | local finalization: {current.get('auto_finalization_status') or 'not started'}")
    if current.get('non_checker_seconds') is not None:
        lines.append(f"Non-verifier time (model/network/orchestration): {current['non_checker_seconds']:.3f}s")
    if current.get('latest_tool'):
        tool=current['latest_tool'];phase='running' if tool['phase']=='tool_execution_start' else 'completed'
        lines.append(f"Latest observed tool: {tool['tool']} ({phase})")
    if current.get('last_check'):
        check=current['last_check']
        lines.append(f"Latest kernel check: {check['receipt_id']} | {check['mode']} | {'PASS' if check['passed'] else 'FAIL'}")
    if current.get('latest_attempt'):
        attempt=current['latest_attempt']
        lines.append(f"Latest attempt: {attempt.get('kind')} | {attempt.get('status')}")
    if current.get('recent_tools'):
        lines.append('Recent completed tools: '+' -> '.join(str(t['tool'])+(' [error]' if t['error'] else '') for t in current['recent_tools']))
    if current['rpc_age_seconds'] is not None:
        lines.append(f"RPC log updated {current['rpc_age_seconds']:.1f}s ago")
    if current.get('issue'):
        lines.append('')
        lines.append('Latest diagnostic:')
        for line in safe_text(current['issue']).splitlines()[:10]:
            lines.extend(textwrap.wrap(line,width=max(40,width),replace_whitespace=False)[:3] or [''])
    if current.get('last_tool_error'):
        lines.append('')
        lines.append('Most recent tool error (may already be under repair):')
        for line in current['last_tool_error'].splitlines()[:6]:
            lines.extend(textwrap.wrap(line,width=max(40,width))[:3] or [''])
    lines.extend(['', 'Read-only monitor. Ctrl+C closes this monitor; the experiment keeps running.'])
    return '\n'.join(safe_text(line) for line in lines)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('language',choices=('lean','litex'))
    parser.add_argument('--name',default='local-compact-01')
    parser.add_argument('--interval',type=float,default=2)
    parser.add_argument('--once',action='store_true',help='Print a single snapshot and exit')
    parser.add_argument('--json',action='store_true',help='Emit JSON snapshots instead of the terminal dashboard')
    args=parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,79}',args.name):parser.error('Invalid batch name')
    if args.interval<.5:parser.error('Refresh interval must be at least 0.5 seconds')
    root=BASE/'batches'/args.name
    if not root.exists():parser.error('Batch does not exist: '+args.name)
    tty=sys.stdout.isatty() and not args.json
    try:
        while True:
            data=snapshot(root,args.language)
            if tty:sys.stdout.write('\033[2J\033[H')
            text=json.dumps(data,ensure_ascii=False) if args.json else render(data,shutil.get_terminal_size((110,40)).columns)
            print(text,flush=True)
            if args.once:break
            time.sleep(args.interval)
    except KeyboardInterrupt:
        if tty:print('\nMonitor closed. Experiment continues.')


if __name__=='__main__':main()
