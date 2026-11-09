#!/usr/bin/env python3
"""Export a credential-free receipt; development runs are not accuracy scores."""
from datetime import datetime, timezone
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent


def load(path):
    return json.loads(path.read_text())


def main():
    records = []
    manifests = {}
    for path in sorted((BASE/'runs').glob('*/manifest.json')):
        manifest = load(path)
        if manifest.get('status')=='running':
            continue
        manifests[manifest['run_id']] = manifest
        ledger_path = path.parent/'provider.jsonl'
        ledger = [json.loads(line) for line in ledger_path.read_text().splitlines()] if ledger_path.exists() else []
        raw = {r['attempt']:r['usage'] for r in ledger if r['kind']=='usage'}
        pi = {r['attempt']:r['usage'] for r in ledger if r['kind']=='pi_message'}
        mismatches = []
        for attempt in sorted(raw.keys() & pi.keys()):
            a,b = raw[attempt],pi[attempt]
            if (a.get('prompt_tokens')!=b.get('input',0)+b.get('cacheRead',0)+b.get('cacheWrite',0)
                    or a.get('completion_tokens')!=b.get('output')):
                mismatches.append(attempt)
        fields = manifest['usage']['summary']['fields']
        records.append({
            'run_id':manifest['run_id'],'task_id':manifest['task_id'],'language':manifest['language'],
            'runtime_revision':manifest.get('runtime_revision','development-v1-no-compaction'),
            'seed':manifest.get('seed'),'native_session':manifest.get('native_session'),
            'controller_status':manifest['status'],'seconds':manifest.get('elapsed_seconds'),
            'checks':manifest.get('check_calls'),'submission_received':manifest.get('submission_received'),
            'machine_checked_candidate':manifest.get('machine_checked_candidate'),
            'request_attempts':manifest['usage']['summary']['request_attempts'],
            'token_fields':fields,'pi_usage_mismatch_attempts':mismatches,
            'raw_usage_requests_without_pi_message':sorted(raw.keys()-pi.keys()),
            'manual_compaction_success':(manifest.get('compaction_smoke_receipt') or {}).get('success'),
            'semantic_status':'not_scored_development', 'accuracy':None,
        })
    pair_ids = ['20261108T072346567230Z-lean-I1','20261108T072839099280Z-litex-I1']
    lean,litex = [manifests[identifier] for identifier in pair_ids]
    lean_input = {k:v for k,v in lean['input_sha256'].items() if k!='foundation.json'}
    litex_input = {k:v for k,v in litex['input_sha256'].items() if k!='foundation.json'}
    assert lean_input==litex_input, 'Paired raw input differs'
    assert lean['model_config']==litex['model_config'], 'Paired model config differs'
    assert lean['settings']==litex['settings'], 'Paired Pi settings differ'
    assert lean['runtime_sha256']==litex['runtime_sha256'], 'Paired runtime differs'
    receipt = {
        'observed_at':datetime.now(timezone.utc).isoformat(),'formal_result':False,'formal_ready':False,
        'offline_controls':{'runtime_test_methods_passed':3,'real_compiler_invocations':8,
                            'scope':'path/trust guards; false targets; stale receipts; paired roots examples'},
        'runs':records,
        'I1_development_pair':{
            'run_ids':pair_ids,'seed_for_order':20261108,'language_order':['lean','litex'],
            'seconds_budget_each':300,'identical_common_input_hashes':True,
            'identical_model_settings_and_runtime':True,
            'outcome':'Neither submitted a complete I.1; both ended with length and one output token.',
            'interpretation':'Context/output-budget calibration failure; no language-performance ranking.',
            'limitation':'v1 did not log actual max_tokens; Pi local context clamping is an inference from local code and observed output, not a captured gateway limit.'},
        'remaining_formal_gates':[
            'Rerun I.1 with v2 and obtain complete, source-faithful artifacts.',
            'Audit equivalent foundations, transitive imports and actual theorem assumptions; add server-controlled Lean #print axioms gate.',
            'Complete paired curriculum and semantic contracts for the selected slice.',
            'Implement multi-task independent prefixes, publication and failed-task rollback.',
            'Freeze parameters after I.1-I.8; implement semantic adjudication and paired formal score export.',
        ],
    }
    (BASE/'development-receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'runs_exported':len(records),'paired_input_match':True,
                      'usage_mismatches':sum(len(r['pi_usage_mismatch_attempts']) for r in records),
                      'formal_result':False}))


if __name__=='__main__':
    main()
