"""Actual two-process scheduling with a provider that forbids model requests."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from batch import create_plan,select_tasks,load,read,save
from parallel_batch import run_parallel,verify_workers,refresh
from batch_report import report
from credentials import read_credential,validate_pair


class ParallelControls(unittest.TestCase):
    def test_private_distinct_credential_bindings_without_exposing_keys(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            for name,key in [('api_config.json','fixture-one'),('api_config.secondary.json','fixture-two')]:
                path=root/name;path.write_text(json.dumps({'api_key':key}));path.chmod(0o600)
            bindings={'lean':'primary','litex':'secondary'}
            result=validate_pair(bindings,root)
            self.assertTrue(result['distinct_keys_configured'])
            self.assertNotIn('fixture',json.dumps(result))
            (root/'api_config.secondary.json').write_text(json.dumps({'api_key':'fixture-one'}))
            with self.assertRaisesRegex(ValueError,'distinct'):validate_pair(bindings,root)
            (root/'api_config.json').chmod(0o644)
            with self.assertRaisesRegex(ValueError,'private'):read_credential('primary',root)

    def test_worker_contracts_partition_source_order_and_protect_bindings(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary).resolve()/'batch'
            plan=create_plan(root,select_tasks('1')[:2],execution='parallel')
            verify_workers(root,plan)
            for language in ('lean','litex'):
                child,state=load(root/'workers'/language)
                self.assertEqual({s['language'] for s in child['slots']},{language})
                self.assertEqual([s['task_id'] for s in child['slots']],['EUCLID.I.D001','EUCLID.I.D002'])
                self.assertEqual(child['source_files'],plan['source_files'])
                self.assertEqual(child['model'],plan['model'])
                self.assertEqual((root/'workers'/language/'source-cache').resolve(),root/'source-cache')
            child_path=root/'workers/litex/plan.json';child=read(child_path);child['credential_alias']='primary';save(child_path,child)
            # Both the leaf plan hash and its parent binding are enforced.
            with self.assertRaisesRegex(ValueError,'plan changed'):verify_workers(root,plan)

    def test_actual_parallel_workers_overlap_isolate_and_make_no_model_calls(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary).resolve()/'batch'
            create_plan(root,select_tasks('1')[:2],seconds=90,run_hours=.1,execution='parallel')
            state=run_parallel(root,offline_probe=True)
            self.assertEqual(state['status'],'complete',state)
            self.assertEqual(len(state['records']),4)
            self.assertFalse(state['libraries'])
            intervals={}
            for language in ('lean','litex'):
                child,worker=load(root/'workers'/language)
                records=list(worker['records'].values())
                self.assertTrue(all(r['status']=='finished' and not r['published'] for r in records))
                attempt=root/'workers'/language/records[0]['attempt']
                manifest=read(attempt/'manifest.json');control=read(attempt/'state.json')
                intervals[language]=(control['start_monotonic'],control['start_monotonic']+manifest['elapsed_seconds'])
                for record in records:
                    attempt=root/'workers'/language/record['attempt'];manifest=read(attempt/'manifest.json')
                    self.assertEqual(manifest['credential_alias'],child['credential_alias'])
                    self.assertTrue(manifest['offline_fixture'])
                    self.assertEqual(manifest['usage']['summary']['request_attempts'],0)
                    self.assertEqual(record['retry_statistics']['attempt_count'],2)
                    self.assertEqual(record['retry_statistics']['retry_count'],0)
                    self.assertEqual(record['retry_statistics']['main_attempt_count'],1)
                    probe=read(attempt/'offline-pi.json')
                    self.assertTrue(probe['passed'])
                    self.assertEqual(probe['text_inputs_read'],[record['task_id']+'.txt'])
                    self.assertFalse((attempt/'provider.jsonl').exists())
            left,right=intervals.values()
            self.assertLess(max(left[0],right[0]),min(left[1],right[1]),'Actual language task lifetimes must overlap')
            before=len(state['worker_launch_history'])
            second=run_parallel(root,offline_probe=True)
            self.assertEqual(len(second['worker_launch_history']),before,'Finished workers must not run again')
            result=report(root);summary=result['summary']
            self.assertEqual(len(result['items']),8)
            self.assertTrue(all(row['main_retry_count']==0 for row in result['rows']))
            self.assertTrue((root/'items.csv').is_file())
            self.assertEqual(summary['execution']['mode'],'parallel')
            self.assertTrue(summary['offline_fixture'])
            self.assertEqual(summary['finished_attempts'],4)

    def test_parallel_stop_and_resume_retains_interrupted_attempts(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary).resolve()/'batch'
            create_plan(root,select_tasks('1')[:1],seconds=90,run_hours=.1,execution='parallel')
            first=run_parallel(root,offline_probe=True,interrupt_after_seconds=1)
            self.assertEqual(first['status'],'interrupted')
            saved={k:r['attempt'] for k,r in first['records'].items()}
            second=run_parallel(root,offline_probe=True)
            self.assertEqual(second['status'],'complete',second)
            self.assertEqual(len(second['records']),2)
            for key,attempt in saved.items():self.assertEqual(second['records'][key]['attempt'],attempt)
            self.assertFalse(any(r['published'] for r in second['records'].values()))

    def test_parallel_reports_wall_time_without_adding_overlapping_workers(self):
        record=next(r for r in select_tasks('1') if r['kind']=='proposition')
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary).resolve()/'batch'
            with patch('batch.freeze_sources'):plan=create_plan(root,[record],execution='parallel')
            for language,cost in [('lean',100),('litex',80)]:
                worker=root/'workers'/language;child,state=load(worker);slot=child['slots'][0]
                state.update(status='complete',elapsed_execution_seconds=cost)
                state['records'][slot['key']]={**slot,'status':'finished','published':False,'elapsed_seconds':cost,'telemetry_complete':True,
                     'usage':{'fields':{'token_total':{'value':10,'known_subtotal':10,'missing_requests':0}}}}
                save(worker/'state.json',state)
                # A single-language report must not require the other language.
                self.assertEqual(report(worker)['summary']['finished_attempts'],1)
            _,state=load(root);state.update(status='complete',elapsed_execution_seconds=100);save(root/'state.json',state)
            result=report(root)['summary']
            self.assertEqual(result['elapsed_execution_seconds'],100)
            self.assertEqual(sum(w['elapsed_execution_seconds'] for w in result['workers'].values()),180)
            self.assertEqual([g['tokens']['token_total']['value'] for g in result['groups']],[10,10])

    def test_parallel_global_deadline_leaves_unattempted_propositions_registered(self):
        record=next(r for r in select_tasks('1') if r['kind']=='proposition')
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary).resolve()/'batch'
            create_plan(root,[record],seconds=1,run_hours=.000001,execution='parallel')
            state=run_parallel(root,offline_probe=True)
            self.assertEqual(state['status'],'budget_exhausted')
            self.assertFalse(state['records'])
            result=report(root)['summary']
            self.assertEqual([g['proposition_denominator'] for g in result['groups']],[1,1])
            self.assertEqual([g['unattempted_tasks'] for g in result['groups']],[1,1])


if __name__=='__main__':unittest.main()
