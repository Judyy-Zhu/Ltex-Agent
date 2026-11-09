"""Bound rereading loops with durable, symmetric candidate-phase transitions; no API."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from prepare import BASE,prepare_job,write_json
from task_rounds import TaskRounds
from lookup_budget import recover_violations
from doc_sections import retrieve


class LookupBudgetControls(unittest.TestCase):
    def test_retrieval_batches_complete_sections_and_keeps_full_reference_available(self):
        text='# Definitions\nA definition.\n# Theorems\nA theorem proof.\n# Other\nAnother topic.\n'
        selected=retrieve(text,'core',selected_sections=['s00','s01'])
        self.assertEqual(''.join(v['text'] for v in selected['sections']),text[:text.index('# Other')])
        self.assertIn('A theorem proof.',retrieve(text,'core',query='theorem proof')['sections'][0]['text'])
        self.assertEqual(retrieve(text,'core','all')['text'],text)
        with self.assertRaises(ValueError):retrieve(text,'core','all',query='proof')
        with self.assertRaises(ValueError):retrieve(text,'core',selected_sections=['missing'])

    def test_violations_charge_once_and_never_create_sixth_attempt(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);rounds=TaskRounds(root,{'max_task_rounds':5})
            write_json(root/'lookup-budget.json',{'violations':[{'id':str(i)} for i in range(8)]})
            recover_violations(root,rounds);recover_violations(root,rounds)
            summary=rounds.summary()
            self.assertEqual(summary['used'],5);self.assertTrue(summary['exhausted'])
            self.assertFalse(summary['transport_only_exhausted'])
            self.assertEqual(len({v['api_attempt_id'] for v in summary['rounds']}),5)

    def test_real_pi_lookup_limit_forces_candidate_and_preserves_native_feedback(self):
        with tempfile.TemporaryDirectory() as temporary:
            for language,violate in [('lean',False),('litex',True)]:
                root=Path(temporary)/language
                job=prepare_job(root,language,None,smoke=True,max_checks=None,check_timeout=None,
                    max_rounds=5,checkpoint_resume=True,auto_finalize=True,compact_protocol=True)
                job.update(item_tracking_required=True,require_submission_gate=True,
                    required_clause_ids=['source_content','encoding'],
                    offline_recovery_fixture={'lookup_turns':3,'lookup_violation':violate})
                write_json(root/'job.json',job)
                result=subprocess.run([sys.executable,str(BASE/'runtime/run.py'),'--language',language,
                    '--prepared-root',str(root),'--smoke','--offline-recovery-probe'],capture_output=True,text=True,timeout=150)
                self.assertEqual(result.returncode,0,result.stdout+'\n'+result.stderr+'\n'+(root/'stderr.log').read_text())
                manifest=json.loads((root/'manifest.json').read_text())
                self.assertTrue(manifest['machine_checked_candidate']);self.assertEqual(manifest['status'],'settled')
                self.assertEqual(manifest['task_rounds']['used'],2 if violate else 1)
                payloads=[json.loads(v) for v in (root/'offline-lookup-payloads.jsonl').read_text().splitlines()]
                self.assertEqual(len(payloads),5 if violate else 4)
                self.assertEqual([v['function']['name'] for v in payloads[3]['tools']],['submit_candidate'])
                self.assertEqual(payloads[3]['tool_choice']['function']['name'],'submit_candidate')
                if violate:self.assertGreater(len(payloads[4]['tools']),1)
                lookup=json.loads((root/'lookup-budget.json').read_text())
                self.assertEqual(len(lookup['violations']),int(violate))
                self.assertEqual(len(lookup['turns']),4 if violate else 3)
                rounds=TaskRounds(root,job);before=rounds.summary()['used'];recover_violations(root,rounds)
                self.assertEqual(rounds.summary()['used'],before)
                self.assertEqual(manifest['native_session']['candidate_requests'],1)
                self.assertEqual(json.loads((root/'submission.json').read_text())['agent_claim'],'complete')


if __name__=='__main__':unittest.main()
