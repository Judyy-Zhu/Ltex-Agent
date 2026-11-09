"""Candidate retries vs cache/replay/final, using BOTH real kernels offline."""
import csv
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from prepare import prepare_job,write_json
from tool_host import Host
from item_tracking import summary,validate_unit


class ItemTrackingControls(unittest.TestCase):
    def host(self,root,language):
        job=prepare_job(root,language,180,smoke=True)
        job.update(item_tracking_required=True,primary_item_id='TOOL.SMOKE:main',primary_item_kind='proof')
        write_json(root/'job.json',job)
        write_json(root/'state.json',{'checks':0,'deadline_monotonic':time.monotonic()+180,'last_final_receipt':None})
        return Host(root)

    def test_real_definition_and_proof_repairs_keep_ids_across_restart_and_move(self):
        with tempfile.TemporaryDirectory() as temporary:
            for language in ('lean','litex'):
                with self.subTest(language=language):
                    root=Path(temporary)/language;host=self.host(root,language)
                    ext='lean' if language=='lean' else 'lit'
                    def write(path,text,item_id=None,kind=None):
                        args={'path':path,'content':text}
                        if item_id:args.update(item_id=item_id,item_kind=kind)
                        return host.dispatch('write_source',args)
                    def check(path,mode='incremental'):return host.dispatch('check',{'path':path,'mode':mode})
                    definition='TOOL.SMOKE:aux:value';main='TOOL.SMOKE:main'
                    bad=('def retryValue : Nat := True\n' if language=='lean' else 'have retryValue R = true\n')
                    write('definition.'+ext,bad,definition,'definition')
                    self.assertFalse(check('definition.'+ext)['passed'])
                    host.close();host=Host(root)  # durable counts across broker restart
                    good='def retryValue : Nat := 2\n' if language=='lean' else 'have retryValue R = 2\n'
                    write('fixed-definition.'+ext,good,definition,'definition')
                    self.assertTrue(check('fixed-definition.'+ext)['passed'])
                    with self.assertRaises(ValueError):write('fixed-definition.'+ext,good,'new-id','definition')
                    bad='theorem retryProof : retryValue = 3 := by rfl\n' if language=='lean' else 'retryValue = 3\n'
                    write('proof.'+ext,bad,main,'proof')
                    failed=check('proof.'+ext);self.assertFalse(failed['passed'])
                    self.assertEqual(failed['item_tracking']['attempt_count'],1)
                    good='theorem retryProof : retryValue = 2 := by rfl\n' if language=='lean' else 'retryValue = 2\n'
                    write('proof.'+ext,good)
                    passed=check('proof.'+ext);self.assertTrue(passed['passed'],passed)
                    self.assertEqual(passed['item_tracking']['retry_count'],1)
                    host.ledger.close()  # replay accepted definitions/proofs, then cache hit
                    cached=check('proof.'+ext);self.assertTrue(cached['passed'],cached)
                    stats=summary(root)
                    self.assertEqual(stats['attempt_count'],4)
                    self.assertEqual(stats['retry_count'],2)
                    self.assertEqual(stats['definition_retry_count'],1)
                    self.assertEqual(stats['proof_retry_count'],1)
                    self.assertEqual(next(i for i in stats['items'] if i['is_primary'])['cached_checks'],1)
                    write('proof.'+ext,good+'\n')
                    self.assertEqual(next(i for i in summary(root)['items'] if i['is_primary'])['status'],'not_accepted')
                    write('proof.'+ext,good)
                    host.dispatch('write_source',{'path':'interfaces.json','content':'{}'})
                    host.dispatch('write_source',{'path':'final.'+ext,'content':'','base':'accepted'})
                    final=check('final.'+ext,'final');self.assertTrue(final['passed'],final)
                    self.assertEqual(summary(root)['retry_count'],2)
                    extra='def untracked : Nat := 9\n' if language=='lean' else 'have untracked R = 9\n'
                    host.dispatch('write_source',{'path':'final.'+ext,'content':extra,'base':'accepted'})
                    self.assertFalse(check('final.'+ext,'final')['passed'])
                    self.assertEqual(summary(root)['attempt_count'],4)
                    host.close()

    def test_protocol_failure_preparation_failure_and_pending_are_distinct(self):
        with tempfile.TemporaryDirectory() as temporary:
            for language in ('lean','litex'):
                root=Path(temporary)/language;host=self.host(root,language)
                ext='lean' if language=='lean' else 'lit';path='main.'+ext
                bad='theorem a : True := by trivial\ntheorem b : True := by trivial\n' if language=='lean' else '2 = 2\n3 = 3\n'
                host.dispatch('write_source',{'path':path,'content':bad,'item_id':'TOOL.SMOKE:main','item_kind':'proof'})
                receipt=host.check({'path':path,'mode':'incremental'})
                self.assertFalse(receipt['passed']);self.assertEqual(summary(root)['main_attempt_count'],1)
                good='theorem a : True := by trivial\n' if language=='lean' else '2 = 2\n'
                host.dispatch('write_source',{'path':path,'content':good})
                with patch.object(host.ledger,'_ensure',side_effect=OSError('kernel unavailable')):
                    failed=host.check({'path':path,'mode':'incremental'})
                self.assertFalse(failed['passed']);self.assertEqual(summary(root)['main_retry_count'],0)
                self.assertEqual(summary(root)['items'][0]['preparation_failures'],1)
                def candidate_timeout(*args):
                    host.ledger.candidate_requests=1
                    raise TimeoutError('Interrupted after candidate dispatch')
                with patch.object(host.ledger,'check',side_effect=candidate_timeout):
                    failed=host.check({'path':path,'mode':'incremental'})
                self.assertTrue(failed['process_status']['timed_out'])
                self.assertEqual(summary(root)['main_attempt_count'],2)
                self.assertEqual(failed['feedback']['data']['frames'],[])
                self.assertIn('interrupted before its response',failed['feedback']['data']['note'])
                host.items.begin(path,'check-interrupted',good)
                stats=summary(root)
                self.assertIsNone(stats['main_attempt_count']);self.assertIsNone(stats['main_retry_count'])
                self.assertEqual(stats['items'][0]['known_attempt_count'],2)
                self.assertEqual(stats['items'][0]['pending_checks'],1)
                host.close()

    def test_batch_report_exports_main_and_auxiliary_items(self):
        import batch
        from batch_report import report
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)/'batch'
            with patch('batch.freeze_sources'):batch.create_plan(root,batch.select_tasks('1')[:1],seconds=1)
            plan,state=batch.load(root);slot=plan['slots'][0]
            state['records'][slot['key']]={**slot,'status':'finished','published':False,
                'retry_statistics':{'available':True,'counts_complete':True,'known_retry_count':2,
                  'retry_count':2,'main_retry_count':1,'items':[
                    {'item_id':'main','item_kind':'proof','is_primary':True,'retry_count':1},
                    {'item_id':'aux','item_kind':'definition','is_primary':False,'retry_count':1}]}}
            batch.save(root/'state.json',state)
            result=report(root)
            self.assertEqual(len(result['items']),2)
            self.assertEqual(result['rows'][0]['main_retry_count'],1)
            with (root/'items.csv').open() as stream:rows=list(csv.DictReader(stream))
            self.assertEqual([r['retry_count'] for r in rows],['1','1'])


if __name__=='__main__':unittest.main()
