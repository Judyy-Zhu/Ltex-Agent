"""Durable current-task recovery; transport retries are not proof rounds."""
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import re

POLICY={'mode':'same_task_checkpoint','network_retry_initial_seconds':5,'network_retry_max_seconds':60,
        'network_max_attempts':5,
        'transport_retries_consume_proof_rounds':True,'persist_pi_conversation':True,
        'all_transport_failures':'checkpoint_current_task; explicit restart opens a fresh five-attempt window and retains full history',
        'finalization_transport':'after an unchanged whole candidate passes, finalization connection retries are separate from candidate rounds'}
RESUMABLE={'running','interrupted','waiting_network','checkpointed','blocked_provider','process_exited'}


def save(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix('.'+str(os.getpid())+'.tmp')
    with temporary.open('w') as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2);stream.write('\n');stream.flush();os.fsync(stream.fileno())
    temporary.replace(path)


def append_event(root,kind,**fields):
    with (Path(root)/'recovery-events.jsonl').open('a') as stream:
        stream.write(json.dumps({'utc':datetime.now(timezone.utc).isoformat(),'kind':kind,**fields})+'\n')
        stream.flush();os.fsync(stream.fileno())


def jsonl_boundary(path):
    """Preserve a torn record as unknown, but never glue the next record to it."""
    path=Path(path)
    if path.exists() and path.stat().st_size:
        with path.open('rb+') as stream:
            stream.seek(-1,os.SEEK_END)
            if stream.read(1)!=b'\n':stream.seek(0,os.SEEK_END);stream.write(b'\n');stream.flush();os.fsync(stream.fileno())


def error_kind(message):
    value=str(message).lower()
    if re.search(r'\b(401|402|403)\b|invalid.*key|unauthori[sz]ed|insufficient.*(balance|credit)|payment required|quota exhausted',value):
        return 'blocked_provider'
    if re.search(r'\b(408|409|425|429|500|502|503|504|529)\b|fetch failed|network|econn|enotfound|eai_again|etimedout|connection|socket|broken pipe|stream.*(closed|terminated|ended|error)|timeout|timed out|rate.limit|overloaded|service unavailable',value):
        return 'waiting_network'
    return None


def provider_records(root):
    path=Path(root)/'provider.jsonl'
    if not path.exists():return []
    values=[]
    for line in path.read_text().splitlines():
        try:values.append(json.loads(line))
        except ValueError:continue
    return values


def latest_request_id(root):
    return next((r.get('attempt') for r in reversed(provider_records(root)) if r.get('kind')=='request'),None)


def recover_interrupted_transport(root,rounds):
    """An unacknowledged in-flight request must not get a free retry on restart."""
    records=provider_records(root);identifier=latest_request_id(root)
    if identifier is None or any(r.get('api_attempt_id')==identifier for r in rounds.read()['rounds']):return
    completed=any(r.get('attempt')==identifier and
                  (r.get('kind')=='usage' or (r.get('kind')=='pi_message' and r.get('stopReason') not in ('error','aborted')))
                  for r in records)
    if completed or rounds.summary()['remaining']==0 or rounds.accepted_candidate():return
    rounds.transport_failure('Request interrupted before its complete response; usage may be unknown',identifier)
    append_event(root,'inflight_api_attempt_accounted',api_attempt_id=identifier)


def resume_prompt(root,rounds):
    root=Path(root)
    receipts=sorted(p.stem for p in (root/'receipts').glob('check-*.json'))
    return ('Resume this SAME source task from its saved conversation, files and verifier journal. '
            'This is checkpoint recovery, not a new task. Attempt history is preserved; a fresh five-attempt window is opened only after an all-API-failure window. '
            f"Whole-task rounds used: {rounds['used']}; remaining: {rounds['remaining']}. "
            'Do not repeat completed tool operations or re-submit an unchanged accepted candidate. '
            'Read remaining_budget and read_library(["retry_stats"]) for the current state; '
            'read_library(["accepted_prefix"]) restores the accepted source. '
            'The native verifier will replay the saved journal if its process was restarted. '
            'Inspect the current candidate file and the last receipts before editing. '
            'If the whole candidate already passed, finish final verification and submit without another candidate round. '
            f"Saved receipt IDs: {', '.join(receipts[-5:]) or 'none'}. "
            'A request interrupted by the network may need to be sent again; its missing token usage remains unknown. '
            'Keep all existing definitions and the original source requirements, and continue using English.')


def recover_completed_submission(root):
    """A saved, hash-bound final/gate receipt can survive a controller crash."""
    import hashlib
    root=Path(root)
    try:
        submission=json.loads((root/'submission.json').read_text())
        if submission.get('agent_claim')!='complete' or submission.get('unfinished'):return False
        rid=submission['final_receipt_id']
        if not isinstance(rid,str) or not re.fullmatch(r'check-\d+',rid):return False
        receipt=json.loads((root/'receipts'/(rid+'.json')).read_text())
        gate=json.loads((root/'submission-gate.json').read_text())
        hashes={str(p.relative_to(root/'work')):hashlib.sha256(p.read_bytes()).hexdigest()
                for p in (root/'work').rglob('*') if p.is_file()}
        if not (receipt['passed'] and receipt['mode']=='final' and gate['passed'] and
                gate['final_receipt_id']==rid and receipt['source_hashes']==gate['source_hashes']==hashes):return False
        manifest=json.loads((root/'manifest.json').read_text())
        manifest.update(status='settled',machine_checked_candidate=True,submission_received=True,recovered_saved_submission=True)
        save(root/'manifest.json',manifest);return True
    except (OSError,ValueError,KeyError):return False
