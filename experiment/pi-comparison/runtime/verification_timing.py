"""Non-overlapping verifier wall phases; no inference time is called kernel time."""
import json

PHASES=('session_initialization_seconds','incremental_candidate_seconds','replay_seconds',
        'independent_final_file_seconds','declaration_gate_seconds','other_verifier_seconds')


def measure(root,events,verifier_seconds):
    receipts=[json.loads(p.read_text()) for p in (root/'receipts').glob('*.json')]
    receipt_seconds=sum(v.get('seconds',0) for v in receipts)
    result={
        'session_initialization_seconds':sum(e.get('seconds',0) for e in events if e.get('kind') in ('session_start','session_start_error')),
        'incremental_candidate_seconds':sum(e.get('seconds',0) for e in events if e.get('kind') in ('native_response','native_error') and not e.get('replay')),
        'replay_seconds':sum(e.get('seconds',0) for e in events if e.get('kind') in ('native_response','native_error') and e.get('replay')),
        'independent_final_file_seconds':sum((v.get('native_process_seconds') or 0) if 'native_process_seconds' in v else v.get('seconds',0) for v in receipts if v.get('mode')=='final'),
        'declaration_gate_seconds':max(0,verifier_seconds-receipt_seconds)}
    result['other_verifier_seconds']=max(0,verifier_seconds-sum(result.values()))
    result['accounted_verifier_seconds']=sum(result[name] for name in PHASES)
    result['unreceipted_native_seconds']=max(0,result['accounted_verifier_seconds']-verifier_seconds)
    result['native_request_errors']=sum(e.get('kind')=='native_error' for e in events)
    finals=[r for r in receipts if r.get('mode')=='final']
    journal=root/'final-verification-events.jsonl'
    started=set()
    if journal.exists():
        for line in journal.read_text().splitlines():
            try:event=json.loads(line)
            except ValueError:continue
            if event.get('kind')=='final_verification_started':started.add(event['receipt_id'])
    complete=(all(isinstance(r.get('final_initialization_seconds'),(int,float)) and
                  isinstance(r.get('final_verification_seconds'),(int,float)) for r in finals)
              and started.issubset({r.get('receipt_id') for r in finals}))
    result['initialization_exclusion_complete']=complete
    result['independent_final_initialization_seconds']=sum(r['final_initialization_seconds'] for r in finals) if complete else None
    result['independent_final_verification_seconds']=sum(r['final_verification_seconds'] for r in finals) if complete else None
    result['total_initialization_seconds']=(result['session_initialization_seconds']+
        result['independent_final_initialization_seconds']) if complete else None
    result['note']='Wall-clock phases. Warm candidate timing is native Session/REPL request-response time after seed/library loading; replay and startup are separate. Fresh-file timing includes process startup/imports. These are not CPU-only times. Failures remain included. Native events left outside a completed receipt by interruption/recovery are retained as unreceipted_native_seconds; model/network/orchestration is separate.'
    if complete:
        result['note']+=' Split final initialization and verification are measured in a new independent native Session/REPL. These detail fields are subsets of independent_final_file_seconds, not additional phases. Only total_initialization_seconds is subtracted from end-to-end time; candidate and final verification remain included.'
    return result


def exclude_initialization(elapsed,timing):
    if not isinstance(elapsed,(int,float)) or not timing or not timing.get('initialization_exclusion_complete'):return None
    initialization=timing.get('total_initialization_seconds')
    if not isinstance(initialization,(int,float)) or initialization<0 or initialization>elapsed:return None
    return elapsed-initialization


def aggregate(rows):
    values=[r.get('verification_timing') for r in rows if r.get('status')!='unattempted']
    known=[v for v in values if v is not None]
    return {'known_totals':{name:sum(v.get(name,0) for v in known) for name in PHASES},
            'tasks_with_phase_data':len(known),'tasks_missing_phase_data':len(values)-len(known),
            'label':'Verifier phases only; end-to-end task wall time and provider token usage remain separate.'}
