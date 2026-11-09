"""Real independent rechecks and exact, non-overlapping startup subtraction."""
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path
import tempfile
import unittest

from prepare import BASE,prepare_job,write_json
from tool_host import Host,execute
from final_verification import verify
from seed_support import assemble_final
from verification_timing import measure,exclude_initialization
import test_compact_protocol as fixtures


class IndependentFinalTimingControls(unittest.TestCase):
    def job(self,root,language):
        job=prepare_job(root,language,None,smoke=True,max_checks=None,check_timeout=None,max_rounds=5,
            checkpoint_resume=True,auto_finalize=True,compact_protocol=True,direct_protocol=True,split_final_timing=True)
        job.update(item_tracking_required=True,require_submission_gate=True,required_clause_ids=['source_content','encoding'])
        write_json(root/'job.json',job);write_json(root/'state.json',{'checks':0,'last_final_receipt':None,'deadline_monotonic':None})
        return job

    def test_real_fresh_final_sessions_preserve_complete_code_and_both_final_gates(self):
        with tempfile.TemporaryDirectory() as temporary:
            for language in ('litex','lean'):
                root=Path(temporary)/language;job=self.job(root,language);host=Host(root)
                try:
                    result=execute(host,'submit_candidate',{'code':fixtures.CompactProtocolControls().source(language)},'split-timing')['details']
                    self.assertTrue(result['task_completed'],result)
                    final=json.loads((root/'receipts'/(result['auto_finalization']['final_receipt_id']+'.json')).read_text())
                    self.assertEqual(final['scope'],'independent_final_session')
                    self.assertNotEqual(final['independent_session_id'],host.ledger.native.identity)
                    self.assertNotEqual(final['independent_pid'],host.ledger.native.io.process.pid)
                    source=(root/'work'/final['entry']).read_bytes()
                    self.assertEqual(hashlib.sha256(source).hexdigest(),final['verified_source_sha256'])
                    self.assertGreater(final['final_initialization_seconds'],0)
                    self.assertGreater(final['final_verification_seconds'],0)
                    self.assertGreaterEqual(final['native_process_seconds'],final['final_initialization_seconds']+final['final_verification_seconds'])
                    self.assertTrue(final['native_frames']);self.assertFalse(final['session']['reuses_candidate_environment'])
                    self.assertTrue(json.loads((root/'submission-gate.json').read_text())['passed'])
                    self.assertEqual(host.rounds.summary()['used'],1)
                finally:host.close()

    def test_final_does_not_inherit_an_unrecorded_helper_from_the_candidate_session(self):
        with tempfile.TemporaryDirectory() as temporary:
            for language in ('litex','lean'):
                root=Path(temporary)/language;job=self.job(root,language);host=Host(root)
                try:
                    host.ledger._ensure(math.inf)
                    hidden='have hidden_number R = 2\n' if language=='litex' else 'def hidden_number : ℝ := 2\n'
                    candidate='have visible_number R = hidden_number\n' if language=='litex' else 'def visible_number : ℝ := hidden_number\n'
                    self.assertTrue(host.ledger.native.send(hidden,math.inf)[0])
                    self.assertTrue(host.ledger.native.send(candidate,math.inf)[0])
                    receipt={'receipt_id':'check-test','entry':'final.'+('lit' if language=='litex' else 'lean')}
                    verify(job,root,assemble_final(job,candidate),math.inf,receipt)
                    self.assertFalse(receipt['passed'])
                    self.assertIn('hidden_number',json.dumps(receipt['native_frames']))
                finally:host.close()

    def test_subtraction_keeps_actual_final_verification_and_legacy_is_unknown(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);(root/'receipts').mkdir()
            final={'receipt_id':'final','mode':'final','seconds':10,'native_process_seconds':10,
                   'final_initialization_seconds':4,'final_verification_seconds':5}
            write_json(root/'receipts/final.json',final)
            write_json(root/'receipts/incremental.json',{'mode':'incremental','seconds':5})
            events=[{'kind':'session_start','seconds':3},{'kind':'native_response','seconds':1,'replay':False}]
            timing=measure(root,events,15)
            self.assertTrue(timing['initialization_exclusion_complete'])
            self.assertEqual(timing['total_initialization_seconds'],7)
            self.assertEqual(exclude_initialization(20,timing),13)
            self.assertEqual(timing['independent_final_verification_seconds'],5)
            self.assertEqual(timing['accounted_verifier_seconds'],15)
            final.pop('final_initialization_seconds');final.pop('final_verification_seconds')
            write_json(root/'receipts/final.json',final)
            timing=measure(root,events,15)
            self.assertFalse(timing['initialization_exclusion_complete'])
            self.assertIsNone(exclude_initialization(20,timing))

    def test_interrupted_final_startup_never_produces_an_invented_adjusted_time(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);(root/'receipts').mkdir()
            (root/'final-verification-events.jsonl').write_text(json.dumps({'kind':'final_verification_started','receipt_id':'missing-receipt'})+'\n')
            timing=measure(root,[],0)
            self.assertFalse(timing['initialization_exclusion_complete'])
            self.assertIsNone(exclude_initialization(20,timing))

    def test_actual_pi_records_both_initializations_and_retains_final_verification(self):
        with tempfile.TemporaryDirectory() as temporary:
            for language in ('litex','lean'):
                root=Path(temporary)/language;job=self.job(root,language)
                job['offline_recovery_fixture']={'direct_candidate_probe':True}
                write_json(root/'job.json',job)
                result=subprocess.run([sys.executable,str(BASE/'runtime/run.py'),'--language',language,
                    '--prepared-root',str(root),'--smoke','--offline-recovery-probe'],capture_output=True,text=True,timeout=120)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                manifest=json.loads((root/'manifest.json').read_text());timing=manifest['verification_timing']
                self.assertTrue(manifest['offline_fixture']);self.assertTrue(manifest['machine_checked_candidate'])
                self.assertTrue(timing['initialization_exclusion_complete'])
                self.assertGreater(timing['independent_final_initialization_seconds'],0)
                self.assertGreater(timing['independent_final_verification_seconds'],0)
                self.assertAlmostEqual(manifest['startup_excluded_seconds'],manifest['elapsed_seconds']-
                    timing['session_initialization_seconds']-timing['independent_final_initialization_seconds'])
                self.assertGreater(manifest['startup_excluded_seconds'],timing['independent_final_verification_seconds'])
                self.assertEqual(manifest['task_rounds']['used'],1)

    def test_language_report_subtracts_initializations_from_worker_wall_time(self):
        from unittest.mock import patch
        from batch import create_plan,select_tasks,load,save
        from batch_report import report
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)/'batch';record=next(r for r in select_tasks('1') if r['kind']=='proposition')
            with patch('batch.freeze_sources'):create_plan(root,[record],execution='parallel',split_final_timing=True)
            for language,wall,first,final in [('lean',100,10,5),('litex',80,2,1)]:
                worker=root/'workers'/language;plan,state=load(worker);slot=plan['slots'][0]
                state.update(status='complete',elapsed_execution_seconds=wall)
                state['records'][slot['key']]={**slot,'status':'finished','published':False,
                    'elapsed_seconds':wall-2,'startup_excluded_seconds':wall-2-first-final,
                    'verification_timing':{'initialization_exclusion_complete':True,'total_initialization_seconds':first+final},
                    'telemetry_complete':True,'usage':{'fields':{'token_total':{'value':10,'known_subtotal':10,'missing_requests':0}}}}
                save(worker/'state.json',state)
            _,state=load(root);state.update(status='complete',elapsed_execution_seconds=100);save(root/'state.json',state)
            result=report(root)
            self.assertEqual(result['summary']['language_startup_excluded_seconds'],{'lean':85,'litex':77})
            self.assertEqual([g['startup_excluded_solver_seconds'] for g in result['summary']['groups']],[83,75])


if __name__=='__main__':unittest.main()
