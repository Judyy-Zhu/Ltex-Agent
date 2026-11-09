"""Whole-task round caps with both real kernels and no model calls."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from prepare import BASE,KIT,prepare_job,write_json
from tool_host import Host
from task_rounds import TaskRounds
from prompts import build_prompts


class WholeTaskRoundControls(unittest.TestCase):
    def test_parallel_plan_has_five_shared_rounds_and_no_hidden_clock_or_checker_cap(self):
        from batch import create_plan,select_tasks,load
        from parallel_batch import verify_workers
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)/'batch'
            plan=create_plan(root,select_tasks('1')[:1],seconds=None,max_checks=None,check_timeout=None,
                             max_rounds=5,execution='parallel')
            verify_workers(root,plan)
            for language in ('lean','litex'):
                worker,_=load(root/'workers'/language)
                self.assertEqual(worker['budget']['max_task_rounds'],5)
                for name in ('task_seconds','run_seconds','max_checks','check_timeout'):
                    self.assertIsNone(worker['budget'][name])

    def test_exact_guide_is_frozen_and_delivered_and_definitions_do_not_gain_extra_theorems(self):
        original=BASE.parents[3]/'litex_auto_build_system/prompts/litex_short_guide.md'
        self.assertEqual(original.read_bytes(),(KIT/'guides/litex_short_guide.md').read_bytes())
        with tempfile.TemporaryDirectory() as temporary:
            for language in ('lean','litex'):
                root=Path(temporary)/language
                job=prepare_job(root,language,None,smoke=True,max_checks=None,check_timeout=None,max_rounds=5,
                                checkpoint_resume=True,auto_finalize=True,compact_protocol=True)
                system,prompt=build_prompts(job)
                self.assertEqual(Path(job['docs']['items']).read_bytes(),Path(job['docs']['workflow']).read_bytes())
                self.assertIn('five',system)
                self.assertIn('submit_candidate',prompt)
                aligned=KIT/f'guides/{language}-aligned-core.md'
                self.assertEqual(Path(job['docs']['core']).read_bytes(),aligned.read_bytes())
                self.assertNotIn(aligned.read_text(),system)
                if language=='litex':
                    self.assertNotEqual(aligned.read_bytes(),original.read_bytes())
                    self.assertNotIn(original.read_text(),system)

    def test_five_whole_candidates_no_clock_partial_prefix_is_not_complete_and_sixth_is_blocked(self):
        with tempfile.TemporaryDirectory() as temporary:
            for language in ('lean','litex'):
                root=Path(temporary)/language
                job=prepare_job(root,language,None,smoke=True,max_checks=None,check_timeout=None,max_rounds=5)
                job['item_tracking_required']=True;write_json(root/'job.json',job)
                write_json(root/'state.json',{'checks':0,'deadline_monotonic':None,'last_final_receipt':None})
                host=Host(root);ext='lean' if language=='lean' else 'lit'
                candidate='def roundValue : Nat := 2\ntheorem roundProof : roundValue = 3 := by rfl\n' if language=='lean' else 'have roundValue R = 2\nthm roundProof:\n    ? roundValue = 3\n    roundValue = 3\n'
                try:
                    self.assertIsNone(host.remaining()['deadline_remaining_seconds'])
                    self.assertIsNone(host.remaining()['check_calls_remaining'])
                    for number in range(1,6):
                        host.dispatch('write_source',{'path':'candidate.'+ext,'content':candidate})
                        checked=host.check({'path':'candidate.'+ext,'mode':'incremental'})
                        self.assertFalse(checked['passed'],checked)
                        self.assertEqual(checked['task_rounds']['used'],number)
                        if number==1:
                            host.dispatch('write_source',{'path':'final.'+ext,'content':'','base':'accepted'})
                            self.assertFalse(host.check({'path':'final.'+ext,'mode':'final'})['passed'])
                            self.assertEqual(host.rounds.summary()['used'],1)
                    count=host.state['checks']
                    with self.assertRaisesRegex(ValueError,'round limit exhausted'):
                        host.check({'path':'candidate.'+ext,'mode':'incremental'})
                    self.assertEqual(host.state['checks'],count)
                    self.assertTrue(host.rounds.summary()['exhausted'])
                    host.close();host=Host(root)
                    self.assertEqual(host.rounds.summary()['used'],5)
                    with self.assertRaises(ValueError):host.check({'path':'candidate.'+ext,'mode':'incremental'})
                finally:host.close()

    def test_generation_without_submission_uses_the_same_five_rounds(self):
        with tempfile.TemporaryDirectory() as temporary:
            rounds=TaskRounds(Path(temporary),{'max_task_rounds':5})
            for _ in range(5):rounds.unused_generation('length')
            self.assertEqual(rounds.summary()['remaining'],0)
            self.assertTrue(rounds.summary()['exhausted'])
            with self.assertRaises(ValueError):rounds.unused_generation('length')

    def test_actual_pi_runner_finalizes_fifth_success_or_stops_at_fifth_failure_without_api(self):
        with tempfile.TemporaryDirectory() as temporary:
            for language in ('lean','litex'):
                for failure in (False,True):
                    root=Path(temporary)/(language+str(failure))
                    job=prepare_job(root,language,None,smoke=True,max_checks=None,check_timeout=None,max_rounds=5)
                    job['offline_round_failure']=failure;job['item_tracking_required']=True
                    write_json(root/'job.json',job)
                    result=subprocess.run([sys.executable,str(BASE/'runtime/run.py'),'--language',language,'--prepared-root',str(root),'--smoke','--offline-probe'],cwd=BASE,capture_output=True,text=True,timeout=120)
                    self.assertEqual(result.returncode,0,result.stdout+'\n'+result.stderr)
                    self.assertTrue(json.loads((root/'offline-pi.json').read_text())['passed'])
                    manifest=json.loads((root/'manifest.json').read_text())
                    self.assertEqual(manifest['status'],'round_limit_exhausted' if failure else 'settled')
                    self.assertEqual(manifest['machine_checked_candidate'],not failure)
                    self.assertEqual(manifest['task_rounds']['used'],5)
                    self.assertIsNone(manifest['deadline_seconds'])
                    self.assertEqual(manifest['usage']['summary']['request_attempts'],0)
                    self.assertFalse((root/'provider.jsonl').exists())


if __name__=='__main__':unittest.main()
