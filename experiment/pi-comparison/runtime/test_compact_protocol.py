"""Compact prompts, one-call candidates, and exactly-once local recovery; no API."""
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from prepare import BASE,prepare_job,write_json
from tool_host import Host,execute
from prompts import build_prompts
from task_rounds import TaskRounds
from doc_sections import sections,retrieve


class CompactProtocolControls(unittest.TestCase):
    def host(self,root,language):
        job=prepare_job(root,language,None,smoke=True,max_checks=None,check_timeout=None,max_rounds=5,
                        checkpoint_resume=True,auto_finalize=True,compact_protocol=True)
        job.update(item_tracking_required=True,require_submission_gate=True,required_clause_ids=['source_content','encoding'])
        write_json(root/'job.json',job);write_json(root/'state.json',{'checks':0,'last_final_receipt':None,'deadline_monotonic':None})
        return Host(root)

    def source(self,language,good=True):
        return ('theorem atomicProof : (2 : Nat) = '+('2' if good else '3')+' := by decide\n') if language=='lean' else ('thm atomicProof:\n    ? 2 = '+('2' if good else '3')+'\n    2 = '+('2' if good else '3')+'\n')

    def test_section_lookup_preserves_reference_and_ignores_headings_inside_code(self):
        text='# One\nText.\n```lit\n# a code comment, not a heading\n```\n## Two\nOther.\n'
        values=sections(text)
        self.assertEqual([v['title'] for v in values],['One','Two'])
        self.assertEqual(''.join(v['text'] for v in values),text)
        self.assertNotIn('text',retrieve(text,'core')['sections'][0])
        self.assertEqual(retrieve(text,'core','all')['text'],text)
        self.assertEqual(retrieve(text,'core','s01')['text'],'## Two\nOther.\n')

    def test_short_profile_keeps_full_original_primary_text_and_intact_on_demand_guide(self):
        with tempfile.TemporaryDirectory() as temporary:
            lengths=[]
            for language in ('lean','litex'):
                root=Path(temporary)/language
                job=prepare_job(root,language,None,task_id='EUCLID.I.P001',max_checks=None,check_timeout=None,max_rounds=5,
                                auto_finalize=True,compact_protocol=True)
                write_json(root/'state.json',{'checks':0,'deadline_monotonic':None,'last_final_receipt':None})
                system,prompt=build_prompts(job);lengths.append(len(system))
                guide=Path(job['docs']['core']).read_text()
                self.assertNotIn(guide,system);self.assertLess(len(system),9500)
                manifest=json.loads((root/'input/source-manifest.json').read_text())
                for name in manifest['reading_policy']['primary_text_files']:self.assertIn((root/'input'/name).read_text(),prompt)
                task=json.loads((root/'input/task.json').read_text())
                for clause in task['required_conclusions']:self.assertIn(clause['statement'],prompt)
                for requirement in task['construction_requirements']:self.assertIn(requirement,prompt)
                self.assertIn(Path(job['seed_path']).read_text(),prompt);self.assertIn('submit_candidate',system)
                host=Host(root)
                try:
                    listed=host.dispatch('read_docs',{'topic':'core'})
                    self.assertNotIn('text',listed);self.assertTrue(listed['sections'])
                    self.assertEqual(host.dispatch('read_docs',{'topic':'core','section':'all'})['text'],guide)
                finally:host.close()
            self.assertLess(max(lengths)/min(lengths),1.25)

    def test_real_operation_cards_fifth_success_and_duplicate_operation_use_one_round(self):
        with tempfile.TemporaryDirectory() as temporary:
            for language in ('lean','litex'):
                root=Path(temporary)/language;host=self.host(root,language)
                try:
                    for _ in range(4):host.rounds.transport_failure('offline transport fixture')
                    code='\n\n'.join(re.findall(r'```(?:lean|lit)\n(.*?)```',Path(host.job['docs']['operation']).read_text(),re.S))
                    first=execute(host,'submit_candidate',{'code':code},'same-call')
                    self.assertTrue(first['details']['task_completed'],first)
                    self.assertEqual(host.rounds.summary()['used'],5);self.assertEqual(host.state['checks'],2)
                    self.assertEqual(execute(host,'submit_candidate',{'code':code},'same-call'),first)
                    conflict=execute(host,'submit_candidate',{'code':code+'\n'},'same-call')
                    self.assertTrue(conflict['isError']);self.assertEqual(host.rounds.summary()['used'],5)
                finally:host.close()

    def test_restart_after_save_before_check_reuses_pending_atomic_transaction(self):
        with tempfile.TemporaryDirectory() as temporary:
            for language in ('lean','litex'):
                root=Path(temporary)/language;host=self.host(root,language);code=self.source(language)
                try:
                    with patch.object(host,'check',side_effect=KeyboardInterrupt):
                        with self.assertRaises(KeyboardInterrupt):execute(host,'submit_candidate',{'code':code},'interrupted')
                    self.assertEqual(host.rounds.summary()['used'],0)
                finally:host.close()
                host=Host(root)
                try:
                    host.recover_pending_check()
                    restored=execute(host,'submit_candidate',{'code':code},'interrupted')
                    self.assertTrue(restored['details']['task_completed']);self.assertEqual(host.rounds.summary()['used'],1)
                finally:host.close()

    def test_failed_receipt_before_result_commit_is_restored_without_a_second_check(self):
        import atomic_candidate
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)/'litex';host=self.host(root,'litex');code=self.source('litex',False)
            real_save=atomic_candidate.save
            def interrupted(path,value):
                if path.parent.name=='candidate-transactions' and value.get('status')=='done':raise KeyboardInterrupt
                return real_save(path,value)
            try:
                with patch('atomic_candidate.save',side_effect=interrupted):
                    with self.assertRaises(KeyboardInterrupt):execute(host,'submit_candidate',{'code':code},'failed-check')
            finally:host.close()
            host=Host(root)
            try:
                with patch.object(host,'check',side_effect=AssertionError('Duplicate kernel invocation')):host.recover_pending_check()
                restored=execute(host,'submit_candidate',{'code':code},'failed-check')
                self.assertFalse(restored['details']['passed']);self.assertTrue(restored['details']['operation_restored'])
                self.assertEqual(host.state['checks'],1);self.assertEqual(host.rounds.summary()['used'],1)
            finally:host.close()

    def test_stale_failed_finalization_marker_does_not_hide_new_accepted_candidate_after_crash(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)/'litex';host=self.host(root,'litex');code=self.source('litex')
            write_json(root/'auto-finalization.json',{'status':'failed','candidate_receipt_id':'older-rejected-candidate'})
            try:
                with patch('auto_finalize.complete',side_effect=KeyboardInterrupt):
                    with self.assertRaises(KeyboardInterrupt):execute(host,'submit_candidate',{'code':code},'accepted-gap')
                self.assertTrue((root/'receipts/check-0001.json').exists())
            finally:host.close()
            host=Host(root)
            try:
                host.recover_pending_check()
                result=execute(host,'submit_candidate',{'code':code},'accepted-gap')
                self.assertTrue(result['details']['task_completed']);self.assertEqual(host.rounds.summary()['used'],1)
            finally:host.close()

    def test_actual_pi_needs_two_model_messages_for_bad_and_good_complete_candidates(self):
        with tempfile.TemporaryDirectory() as temporary:
            for language in ('lean','litex'):
                root=Path(temporary)/language;host=self.host(root,language);host.close()
                job=json.loads((root/'job.json').read_text());job['offline_recovery_fixture']={'initial_network':True,'initial_release_after':0};write_json(root/'job.json',job)
                result=subprocess.run([sys.executable,str(BASE/'runtime/run.py'),'--language',language,'--prepared-root',str(root),'--smoke','--offline-recovery-probe'],capture_output=True,text=True,timeout=120)
                self.assertEqual(result.returncode,0,result.stdout+'\n'+result.stderr+'\n'+(root/'stderr.log').read_text())
                manifest=json.loads((root/'manifest.json').read_text());self.assertTrue(manifest['machine_checked_candidate'])
                self.assertEqual(manifest['status'],'settled');self.assertEqual(manifest['task_rounds']['used'],2)
                self.assertEqual(set(manifest['tool_allowlist']),{'read_input','read_docs','read_library','submit_candidate','remaining_budget'})
                self.assertEqual(manifest['usage']['summary']['request_attempts'],2)
                schema=json.loads((root/'offline-active-schemas.json').read_text())
                self.assertEqual(set(schema['submit_candidate']['properties']),{'code'})
                self.assertIn('section',schema['read_docs']['properties'])
                phases=manifest['verification_timing'];self.assertGreater(phases['incremental_candidate_seconds'],0)
                self.assertGreater(phases['independent_final_file_seconds'],0)
                self.assertAlmostEqual(sum(phases[k] for k in ('session_initialization_seconds','incremental_candidate_seconds','replay_seconds','independent_final_file_seconds','declaration_gate_seconds','other_verifier_seconds')),manifest['checker_seconds'],places=5)


if __name__=='__main__':unittest.main()
