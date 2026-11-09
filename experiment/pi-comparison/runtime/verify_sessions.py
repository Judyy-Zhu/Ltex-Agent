#!/usr/bin/env python3
"""Record the offline regression suite for the persistent verifier adapters."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parent
MODULES=['test_paths','test_english_inputs','test_text_inputs','test_parallel','test_batch','test_seeds','test_native_sessions','test_session_failures','test_verifier_feedback','test_item_tracking','test_runtime','test_pi_transport','test_task_rounds','test_checkpointing','test_auto_finalize','test_context_tools','test_compact_protocol','test_replay_benchmark','test_lookup_budget','test_aligned_guides','test_repl_framing','test_direct_protocol','test_final_timing','test_generic_language','test_proof_layout_repair']


def hashes():
    paths=[p for p in ROOT.iterdir() if p.suffix in ('.py','.ts')]
    paths.extend(p for p in (ROOT/'fixtures').iterdir() if p.is_file())
    paths.extend(p for p in (ROOT.parent/'seeds').iterdir() if p.is_file())
    paths.extend(p for p in (ROOT.parent/'agent-kit').rglob('*') if p.is_file() and p.suffix in ('.py','.md','.txt','.json','.lean','.lit'))
    return {str(p.relative_to(ROOT.parent)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def main():
    before=hashes()
    started=datetime.now(timezone.utc).isoformat()
    suite=unittest.defaultTestLoader.loadTestsFromNames(MODULES)
    with (ROOT/'session-controls.log').open('w') as output:
        result=unittest.TextTestRunner(stream=output,verbosity=2).run(suite)
    after=hashes()
    receipt={'scope':'offline native Session/REPL and actual Pi tool transport; no model calls',
             'technical_seed_id':'real-plane-algebra-v1',
             'started_at':started,'completed_at':datetime.now(timezone.utc).isoformat(),
             'passed':result.wasSuccessful() and before==after,'tests_run':result.testsRun,
             'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),
             'source_unchanged_during_checks':before==after,'source_sha256':before,'model_calls':0,
             'log':'session-controls.log','formal_benchmark_result':False}
    (ROOT/'session-controls-receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:receipt[k] for k in ('passed','tests_run','failures','errors','model_calls','source_unchanged_during_checks')}))
    if not receipt['passed']:
        print((ROOT/'session-controls.log').read_text())
        raise SystemExit(1)


if __name__=='__main__':main()
