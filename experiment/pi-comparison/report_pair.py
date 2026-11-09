#!/usr/bin/env python3
"""Compare a frozen development pair without treating compile pass as accuracy."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent


def load(path):
    return json.loads(path.read_text())


def shared_input_hashes(manifest):
    names=manifest.get('shared_input_files')
    if names is None:
        return {k:v for k,v in manifest['input_sha256'].items() if k!='foundation.json'}
    return {name:manifest['input_sha256'][name] for name in names}


def report(lean_root,litex_root):
    manifests = [load(root/'manifest.json') for root in (lean_root,litex_root)]
    left,right = manifests
    if any(m['status']=='running' for m in manifests):
        raise ValueError('Pair is still running')
    checks = {
        'same_common_inputs':shared_input_hashes(left)==shared_input_hashes(right),
        'same_seed_contract':(left.get('seed') or {}).get('interface_sha256')==(right.get('seed') or {}).get('interface_sha256'),
        'same_model':left['model_config']==right['model_config'],
        'same_pi_settings':left['settings']==right['settings'],
        'same_runtime':left['runtime_sha256']==right['runtime_sha256'],
        'same_pi_commit':left['pi_commit']==right['pi_commit'],
        'same_tools':left['tool_allowlist']==right['tool_allowlist'],
        'same_deadline':left['deadline_seconds']==right['deadline_seconds'],
    }
    if not all(checks.values()):
        raise ValueError(f'Frozen pair mismatch: {checks}')
    rows = []
    for root,m in zip((lean_root,litex_root),manifests):
        events = [json.loads(line) for line in (root/'rpc.jsonl').read_text().splitlines()]
        tool_events = [e for e in events if e.get('type')=='tool_execution_start']
        raw = [json.loads(line) for line in (root/'provider.jsonl').read_text().splitlines()]
        requests = [r for r in raw if r['kind']=='request']
        usage = {r['attempt']:r['usage'] for r in raw if r['kind']=='usage'}
        by_tool = {name:sum(e.get('toolName')==name for e in tool_events) for name in m['tool_allowlist']}
        audit_path = root/'audit/machine.json'
        semantic_path = root/'audit/semantic.json'
        audit = load(audit_path) if audit_path.exists() else None
        semantic = load(semantic_path) if semantic_path.exists() else None
        rows.append({
            'run_id':root.name,'language':m['language'],'controller_status':m['status'],
            'seed':m.get('seed'),'native_session':m.get('native_session'),
            'machine_checked_candidate':m['machine_checked_candidate'],'submission_received':m['submission_received'],
            'elapsed_seconds':m['elapsed_seconds'],'setup_seconds':m['setup_seconds'],
            'check_calls':m['check_calls'],'tool_calls':by_tool,
            'request_attempts':len(requests),'usage_observed_requests':len(usage),
            'max_tokens_range':[min(r['max_tokens'] for r in requests),max(r['max_tokens'] for r in requests)],
            'compaction_count':sum(e.get('type')=='compaction_end' and not e.get('errorMessage') for e in events),
            'token_fields':m['usage']['summary']['fields'],
            'machine_audit_status':audit['machine_status'] if audit else 'pending',
            'proof_assumption_status':audit['proof_assumption_status'] if audit else 'pending',
            'postrun_audit_seconds':audit['audit_seconds'] if audit else None,
            'semantic_status':semantic['status'] if semantic else 'pending',
            'semantic_review':semantic,
            'formal_accuracy':None,
        })
    return {'observed_at':datetime.now(timezone.utc).isoformat(),'task_id':'EUCLID.I.P001',
            'formal_result':False,'scope':'one development task pair; no statistical or language ranking claim',
            'pair_checks':checks,'languages':rows,'joint_success_time_ratio':None,
            'interpretation':'A successful compile is a machine candidate. Complete task acceptance additionally requires source and encoding certificates. Unknown usage is not zero.',
            'remaining_gates':['Complete I.1 with required explicit encoding bridges in both languages.',
                               'Expand/freeze paired language guides; current syntax/proof-structure examples are staged only.',
                               'Audit foundations; implement multi-task prefixes and rollback before a formal book run.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('lean_run');parser.add_argument('litex_run')
    parser.add_argument('--output',type=Path,default=BASE/'I1-v2-pair.json')
    args = parser.parse_args()
    result = report(BASE/'runs'/args.lean_run,BASE/'runs'/args.litex_run)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'output':str(args.output),'pair_checks':result['pair_checks'],
                      'statuses':[{k:r[k] for k in ('language','machine_audit_status','semantic_status')} for r in result['languages']]}))


if __name__=='__main__':
    main()
