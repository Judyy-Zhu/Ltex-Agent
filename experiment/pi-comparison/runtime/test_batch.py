"""Full controller tests with deterministic fixtures, real kernels, ZERO LLM calls.

Fixture statements deliberately do not solve Euclid; semantic scores stay pending.
"""
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
import batch
from batch import create_plan,run_batch,read,save,select_tasks,load
from batch_report import report,review_template,import_reviews
from task_inputs import catalog,freeze_sources,package_task,source_pdf,digest
from tool_host import Host
from prepare import prepare_job


class BatchControls(unittest.TestCase):
    def test_full_catalog_selection_and_registered_denominators(self):
        rows=select_tasks('all')
        self.assertEqual(len(rows),644)
        self.assertEqual(sum(r['kind']=='proposition' for r in rows),465)
        self.assertEqual(len(select_tasks('1')),81)
        pilot=select_tasks('1',8)
        self.assertEqual(sum(r['kind']=='proposition' for r in pilot),8)
        self.assertEqual(pilot[0]['id'],'EUCLID.I.D001')
        self.assertEqual(select_tasks('11-13')[-1]['book'],13)
        for value in ('0','14','3-1','no'):
            with self.assertRaises(ValueError):select_tasks(value)

    def test_paired_multi_page_sources_and_generic_contract(self):
        rows,_=catalog();ids=['EUCLID.V.D001','EUCLID.XI.D001','EUCLID.XIII.P018']
        records=[r for r in rows if r['id'] in ids]
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);cache=root/'cache';freeze_sources(cache,records)
            with patch('task_inputs.catalog',return_value=(records,{})):
                for record in records:
                    left=root/(record['id']+'-lean');right=root/(record['id']+'-litex')
                    a=package_task(left,record['id'],cache);b=package_task(right,record['id'],cache)
                    self.assertEqual(a,b)
                    policy=a['reading_policy']
                    self.assertEqual(policy['primary_text_files'],[record['id']+'.txt'])
                    self.assertTrue(all(name.endswith('.txt') and (left/name).is_file()
                                        for name in policy['primary_text_files']+policy['context_text_files']))
                    self.assertTrue(all(name.endswith('.png') and (left/name).is_file()
                                        for name in policy['optional_image_files']))
                    for path in left.iterdir():self.assertEqual(path.read_bytes(),(right/path.name).read_bytes())
                    self.assertEqual(read(left/'task.json')['required_clauses'][0]['clause_id'],'source_content')
                self.assertGreater(len(read(root/'EUCLID.XIII.P018-lean/source-manifest.json')['items']),1)
            changed=next(cache.rglob('*.txt'));changed.write_text('changed')
            with patch('task_inputs.catalog',return_value=(records,{})):
                with self.assertRaisesRegex(ValueError,'Source pack changed'):
                    package_task(root/'bad',changed.stem,cache)

    def fixture_executor(self,attempt,slot,*,fail_task=None,interrupt_number=None):
        if slot['number']==interrupt_number:raise KeyboardInterrupt
        job=read(attempt/'job.json');language=slot['language'];ext='lean' if language=='lean' else 'lit'
        save(attempt/'state.json',{'deadline_monotonic':time.monotonic()+120,'checks':0,'last_final_receipt':None})
        host=Host(attempt);start=time.monotonic()
        try:
            if slot['task_id']==fail_task and language=='litex':
                host.dispatch('write_source',{'path':'bad.lit','content':'2 + 2 = 5\n',
                    'item_id':job['primary_item_id'],'item_kind':job['primary_item_kind']})
                self.assertFalse(host.dispatch('check',{'path':'bad.lit','mode':'incremental'})['passed'])
                save(attempt/'manifest.json',{'status':'settled','machine_checked_candidate':False,
                     'elapsed_seconds':time.monotonic()-start,'check_calls':1,'telemetry_complete':True})
                return
            ordinal=slot['task_id'][-3:];symbol='fixture'+ordinal
            predecessor=bool(job.get('library'))
            if predecessor:
                self.assertIn('fixture001',host.dispatch('read_library',{'symbols':['entry:EUCLID.I.D001']})['selected_entries']['EUCLID.I.D001'])
            if language=='lean':
                body=f'def {symbol} (x : ℝ) : ℝ := '+('fixture001 x' if predecessor else 'x + 1')+'\n'
            else:body=f'have fn {symbol}(x R) R = '+('fixture001(x)' if predecessor else 'x + 1')+'\n'
            host.dispatch('write_source',{'path':'one.'+ext,'content':body,
                'item_id':job['primary_item_id'],'item_kind':job['primary_item_kind']})
            checked=host.dispatch('check',{'path':'one.'+ext,'mode':'incremental'})
            self.assertTrue(checked['passed'],checked)
            host.dispatch('write_source',{'path':'interfaces.json','content':json.dumps({'fixture_only':True,'symbols':[symbol]})})
            host.dispatch('write_source',{'path':'final.'+ext,'content':'','base':'accepted'})
            receipt=host.dispatch('check',{'path':'final.'+ext,'mode':'final'})
            self.assertTrue(receipt['passed'],receipt)
            submission={'task_id':job['task_id'],'language':language,'agent_claim':'complete',
                        'source_files':['final.'+ext],'interfaces_file':'interfaces.json',
                        'clause_mapping':[{'clause_id':c,'declarations':[symbol],'explanation':'Offline transport fixture, NOT Euclid proof'} for c in job['required_clause_ids']],
                        'dependencies':[],'assumptions':[],'unfinished':[],'final_receipt_id':receipt['receipt_id']}
            self.assertTrue(host.dispatch('submit',{'submission':submission})['received'])
            self.assertTrue(read(attempt/'submission-gate.json')['passed'])
            save(attempt/'manifest.json',{'status':'settled','machine_checked_candidate':True,
                 'elapsed_seconds':time.monotonic()-start,'check_calls':2,'telemetry_complete':True})
        finally:host.close()

    def test_real_kernel_publication_rollback_resume_and_review(self):
        rows=select_tasks('1')[:3]
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)/'batch'
            create_plan(root,rows,seconds=120,run_hours=1)
            state=run_batch(root,lambda p,s:self.fixture_executor(p,s,fail_task='EUCLID.I.D002'))
            self.assertEqual(state['status'],'complete')
            self.assertEqual(sum(r['published'] for r in state['records'].values()),5)
            self.assertEqual(sum(r['passed'] for r in state['records'].values()),5)
            self.assertTrue(all(r['semantic_status']=='pending' for r in state['records'].values() if r['passed']))
            lib=state['libraries']['r001:litex']
            self.assertEqual([e['task_id'] for e in read(lib['index'])['entries']],['EUCLID.I.D001','EUCLID.I.D003'])
            self.assertNotIn('fixture002',Path(lib['source']).read_text())
            for key,record in state['records'].items():
                attempt=root/record['attempt']
                self.assertFalse((attempt/'provider.jsonl').exists())
            for task in rows:
                attempts=[root/r['attempt'] for r in state['records'].values() if r['task_id']==task['id']]
                jobs=[read(a/'job.json') for a in attempts]
                self.assertEqual(jobs[0]['shared_input_files'],jobs[1]['shared_input_files'])
                for name in jobs[0]['shared_input_files']:
                    self.assertEqual((attempts[0]/'input'/name).read_bytes(),(attempts[1]/'input'/name).read_bytes())
            run_batch(root,lambda *_:self.fail('A finished attempt must not be repeated'))
            result=report(root)
            self.assertTrue(all(g['accuracy'] is None for g in result['summary']['groups']))
            review_path=Path(review_template(root));data=read(review_path)
            review=data['reviews'][0];review.update(status='pass',reviewer='offline fixture tester',reason='Fixture certificate only')
            save(review_path,data)
            with self.assertRaisesRegex(ValueError,'four semantic'):import_reviews(root,review_path)
            review.update(status='fail',reason='These fixture definitions are not Euclid formalizations')
            save(review_path,data);import_reviews(root,review_path)
            self.assertIn('fail',[r['semantic_status'] for r in report(root)['rows']])
            # Modifying published code is detected before any new model attempt.
            Path(lib['source']).write_text('tampered')
            with self.assertRaisesRegex(ValueError,'changed'):
                batch.verify_libraries(state)

    def test_interruption_is_recorded_without_automatic_retry(self):
        rows=select_tasks('1')[:1]
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)/'batch';create_plan(root,rows,seconds=120,run_hours=1)
            first=run_batch(root,lambda *_:(_ for _ in ()).throw(KeyboardInterrupt()))
            self.assertEqual(first['status'],'interrupted')
            calls=[]
            # No compiler/model is needed to demonstrate recovery of an
            # interrupted empty attempt, and no fake success is published.
            def fail(attempt,slot):
                calls.append(slot['key'])
                save(attempt/'manifest.json',{'status':'settled','machine_checked_candidate':False,
                     'elapsed_seconds':0,'check_calls':0,'telemetry_complete':True})
            second=run_batch(root,fail)
            self.assertEqual(second['status'],'complete');self.assertEqual(len(calls),1)
            self.assertEqual(len(second['records']),2)
            self.assertFalse(any(r['published'] for r in second['records'].values()))

    def test_frozen_plan_environment_and_budget_rejection(self):
        rows=select_tasks('1')[:1]
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)/'batch';create_plan(root,rows,seconds=1,run_hours=.000001)
            with patch('batch.verify_environment'):
                state=run_batch(root,lambda *_:self.fail('No task may start after exhausted budget'))
            self.assertEqual(state['status'],'budget_exhausted')
            result=report(root)
            self.assertEqual(result['summary']['finished_attempts'],0)
            plan=read(root/'plan.json');plan['budget']['task_seconds']=10;save(root/'plan.json',plan)
            with self.assertRaisesRegex(ValueError,'plan changed'):load(root)

    def test_gate_rejects_nonexistent_declaration_and_accepts_3d_definition(self):
        from submission_gate import validate
        from seed_support import assemble_final
        with tempfile.TemporaryDirectory() as temporary:
            for language in ('lean','litex'):
                root=Path(temporary)/language;job=prepare_job(root,language,120,smoke=True)
                body=('def fixture3d : ℝ × ℝ × ℝ := (1,2,3)\n' if language=='lean' else
                      'have fixture3d cart(R,R,R) = (1,2,3)\n')
                source=assemble_final(job,body)
                good=validate(job,source,['fixture3d'],time.monotonic()+90)
                self.assertTrue(good['passed'],good)
                bad=validate(job,source,['doesNotExist'],time.monotonic()+90)
                self.assertFalse(bad['passed'],bad)

    def test_owned_process_cleanup_and_pid_reuse_protection(self):
        import subprocess,sys
        from process_control import identity,stop_owned
        process=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)'],start_new_session=True)
        try:
            record=identity(process.pid)
            stop_owned({**record,'birth':'different process birth'})
            self.assertIsNone(process.poll())
            stop_owned(record)
            process.wait(timeout=5)
            self.assertIsNotNone(process.returncode)
        finally:
            if process.poll() is None:process.kill();process.wait()

    def test_report_preserves_unknown_usage_and_unattempted_denominator(self):
        record=next(r for r in select_tasks('1') if r['kind']=='proposition')
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)/'batch'
            # Source packaging is tested separately with the real PDF above.
            with patch('batch.freeze_sources'):
                create_plan(root,[record],seconds=1)
            plan,state=load(root);slot=next(s for s in plan['slots'] if s['language']=='lean')
            state['records'][slot['key']]={**slot,'status':'finished','published':True,'elapsed_seconds':13,
                 'telemetry_complete':False,'usage':{'fields':{'token_total':{'value':None,'known_subtotal':120,'missing_requests':1}}}}
            save(root/'state.json',state)
            result=report(root);lean=next(g for g in result['summary']['groups'] if g['language']=='lean')
            litex=next(g for g in result['summary']['groups'] if g['language']=='litex')
            self.assertEqual(lean['proposition_denominator'],1)
            self.assertEqual(litex['proposition_denominator'],1)
            self.assertEqual(litex['unattempted_tasks'],1)
            self.assertEqual(lean['accuracy'],1);self.assertEqual(litex['accuracy'],0)
            self.assertIsNone(lean['semantic_accuracy']);self.assertFalse(litex['accuracy_is_final'])
            self.assertEqual(lean['tokens']['token_total']['known_subtotal'],120)
            self.assertIsNone(lean['tokens']['token_total']['value'])

    def test_optional_review_never_blocks_machine_pass_score_or_paired_comparison(self):
        record=next(r for r in select_tasks('1') if r['kind']=='proposition')
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)/'batch'
            with patch('batch.freeze_sources'):create_plan(root,[record],seconds=1)
            plan,state=load(root);state['status']='complete'
            for slot in plan['slots']:
                state['records'][slot['key']]={**slot,'status':'finished','published':True,'elapsed_seconds':10,
                    'telemetry_complete':True,'usage':{'fields':{'token_total':{'value':100,'known_subtotal':100,'missing_requests':0}}}}
            save(root/'state.json',state)
            pending=report(root)
            self.assertTrue(all(row['passed'] is True and row['semantic_status']=='pending' and row['verified_correct'] is None for row in pending['rows']))
            self.assertTrue(all(g['accuracy']==1 and g['task_pass_rate']==1 and g['semantic_accuracy'] is None for g in pending['summary']['groups']))
            self.assertTrue(all(g['tokens_per_correct_proposition']==100 for g in pending['summary']['groups']))
            self.assertEqual(len(pending['joint_successes']),1)
            self.assertEqual(pending['summary']['joint_reviewed_correct_propositions'],0)
            self.assertFalse(pending['summary']['semantic_review_required_for_success'])
            # Even a later negative annotation does not rewrite the operational
            # machine-verification result or remove an already published item.
            state['reviews']={slot['key']:{'status':'fail'} for slot in plan['slots']}
            save(root/'state.json',state)
            annotated=report(root)
            self.assertTrue(all(row['passed'] is True and row['verified_correct'] is False for row in annotated['rows']))
            self.assertTrue(all(g['accuracy']==1 and g['semantic_accuracy']==0 for g in annotated['summary']['groups']))
            self.assertEqual(len(annotated['joint_successes']),1)
            self.assertTrue(all(r['published'] for r in load(root)[1]['records'].values()))


if __name__=='__main__':unittest.main()
