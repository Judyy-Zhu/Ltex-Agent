"""Current-task recovery and exactly-once saved tool results, with no HTTP."""
import json
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from prepare import BASE,prepare_job,write_json
from recovery import error_kind,jsonl_boundary,recover_interrupted_transport,recover_completed_submission
from tool_host import Host,execute


class CheckpointControls(unittest.TestCase):
    def test_crash_after_reserving_attempt_before_check_counter_is_committed(self):
        import hashlib
        with tempfile.TemporaryDirectory() as temporary:
            for language in ('lean','litex'):
                root=Path(temporary)/language;host=self.host(root,language)
                name='candidate.'+('lean' if language=='lean' else 'lit')
                body='theorem reservedProof : (2 : Nat) = 2 := by rfl\n' if language=='lean' else 'thm reservedProof:\n    ? 2 = 2\n    2 = 2\n'
                host.dispatch('write_source',{'path':name,'content':body})
                for _ in range(4):host.rounds.unused_generation('length')
                host.rounds.begin('check-0001',source={'path':name,'source_sha256':hashlib.sha256(body.encode()).hexdigest()})
                host.close();host=Host(root)
                try:
                    host.recover_pending_check()
                    self.assertEqual(host.state['checks'],1)
                    self.assertEqual(host.rounds.summary()['used'],5)
                    self.assertTrue(json.loads((root/'receipts/check-0001.json').read_text())['passed'])
                finally:host.close()

    def test_unknown_inflight_request_is_counted_once_and_only_all_api_windows_reopen(self):
        from task_rounds import TaskRounds
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);rounds=TaskRounds(root,{'max_task_rounds':5})
            for identifier in range(1,6):
                with (root/'provider.jsonl').open('a') as stream:
                    stream.write(json.dumps({'kind':'request','attempt':identifier})+'\n')
                recover_interrupted_transport(root,rounds)
                recover_interrupted_transport(root,rounds)
                self.assertEqual(rounds.summary()['used'],identifier)
            self.assertTrue(rounds.summary()['transport_only_exhausted'])
            self.assertTrue(rounds.reopen_transport_window())
            self.assertEqual(rounds.summary()['used'],0)
            self.assertEqual(rounds.summary()['total_used'],5)
            recover_interrupted_transport(root,rounds)
            self.assertEqual(rounds.summary()['used'],0)
            rounds.unused_generation('length')
            for _ in range(4):rounds.transport_failure('network')
            self.assertTrue(rounds.summary()['exhausted'])
            self.assertFalse(rounds.reopen_transport_window())

    def test_saved_complete_submission_recovers_without_model_but_tampering_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            for language in ('lean','litex'):
                root=Path(temporary)/language;host=self.host(root,language)
                host.job['require_submission_gate']=True;write_json(root/'job.json',host.job)
                ext='lean' if language=='lean' else 'lit'
                source='theorem durableProof : (2 : Nat) = 2 := by rfl\n' if language=='lean' else 'thm durableProof:\n    ? 2 = 2\n    2 = 2\n'
                try:
                    host.dispatch('write_source',{'path':'candidate.'+ext,'content':source})
                    self.assertTrue(host.check({'path':'candidate.'+ext,'mode':'incremental'})['passed'])
                    host.dispatch('write_source',{'path':'interfaces.json','content':'{}'})
                    host.dispatch('write_source',{'path':'final.'+ext,'content':'','base':'accepted'})
                    receipt=host.check({'path':'final.'+ext,'mode':'final'})
                    self.assertTrue(receipt['passed'])
                    host.submit({'task_id':'TOOL.SMOKE','language':language,'agent_claim':'complete','source_files':['final.'+ext],
                        'interfaces_file':'interfaces.json','final_receipt_id':receipt['receipt_id'],'unfinished':[],
                        'dependencies':[],'assumptions':[],'clause_mapping':[{'clause_id':'source_content','declarations':['durableProof'],'explanation':'Offline fixture only'}]})
                    write_json(root/'manifest.json',{'status':'running','machine_checked_candidate':False})
                    self.assertTrue(recover_completed_submission(root))
                    self.assertEqual(json.loads((root/'manifest.json').read_text())['status'],'settled')
                    (root/'work'/('candidate.'+ext)).write_text(source+'\n')
                    self.assertFalse(recover_completed_submission(root))
                finally:host.close()

    def fixture(self,root,language,settings):
        job=prepare_job(root,language,None,smoke=True,max_checks=None,check_timeout=None,max_rounds=5,checkpoint_resume=True)
        job.update(item_tracking_required=True,offline_recovery_fixture={'retry_delay':.01,**settings})
        write_json(root/'job.json',job)
        return [sys.executable,str(BASE/'runtime/run.py'),'--language',language,'--prepared-root',str(root),'--smoke','--offline-recovery-probe']

    def run_fixture(self,command,root,expected=0):
        result=subprocess.run(command,cwd=BASE,capture_output=True,text=True,timeout=90)
        self.assertEqual(result.returncode,expected,result.stdout+'\n'+result.stderr+'\n'+(root/'stderr.log').read_text()[-3000:])
        return json.loads((root/'manifest.json').read_text())

    def test_initial_network_errors_then_kernel_success_still_pass_within_five_total_attempts(self):
        with tempfile.TemporaryDirectory() as temporary:
            for language in ('lean','litex'):
                root=Path(temporary)/language
                command=self.fixture(root,language,{'initial_network':True,'initial_release_after':2})
                manifest=self.run_fixture(command,root)
                self.assertEqual(manifest['status'],'settled')
                self.assertTrue(manifest['machine_checked_candidate'])
                self.assertEqual(manifest['task_rounds']['used'],4)  # two API failures + bad and corrected candidates
                self.assertEqual([r['kind'] for r in manifest['task_rounds']['rounds']],['transport','transport','candidate','candidate'])
                self.assertTrue((root/'restored-context.json').exists())
                self.assertFalse(manifest['task_rounds']['exhausted'])

    def test_five_api_errors_checkpoint_same_task_then_explicit_resume_keeps_history_and_usage(self):
        with tempfile.TemporaryDirectory() as temporary:
            for language in ('lean','litex'):
                root=Path(temporary)/language
                command=self.fixture(root,language,{'initial_network':True})
                first=self.run_fixture(command,root,expected=75)
                self.assertEqual(first['status'],'blocked_provider')
                self.assertEqual(first['task_rounds']['used'],5)
                self.assertTrue(first['task_rounds']['transport_only_exhausted'])
                self.assertEqual(first['check_calls'],0)
                self.assertFalse(first['machine_checked_candidate'])
                initial_id=json.loads((root/'pi-session.jsonl').read_text().splitlines()[0])['id']
                provider_prefix=(root/'provider.jsonl').read_bytes()
                (root/'reconnect.allow').touch()
                second=self.run_fixture(command+['--resume-task'],root)
                self.assertEqual(second['status'],'settled')
                self.assertEqual(second['resume_count'],1)
                self.assertEqual(second['task_rounds']['used'],2)
                self.assertEqual(second['task_rounds']['total_used'],7)
                self.assertTrue(second['machine_checked_candidate'])
                self.assertEqual(json.loads((root/'pi-session.jsonl').read_text().splitlines()[0])['id'],initial_id)
                self.assertTrue((root/'provider.jsonl').read_bytes().startswith(provider_prefix))
                requests=[json.loads(line) for line in (root/'provider.jsonl').read_text().splitlines() if json.loads(line).get('kind')=='request']
                ids=[r['attempt'] for r in requests]
                self.assertEqual(len(ids),len(set(ids)))
                self.assertTrue(all(r['offline_stub'] for r in requests),'A test used a real transport')
                tokens=second['usage']['summary']['fields']['token_total']
                self.assertIsNone(tokens['value'])
                self.assertEqual(tokens['missing_requests'],5)
                self.assertGreater(tokens['known_subtotal'],0)

    def test_manual_interruption_in_network_wait_resumes_saved_conversation_and_remaining_attempts(self):
        with tempfile.TemporaryDirectory() as temporary:
            for language in ('lean','litex'):
                root=Path(temporary)/language
                command=self.fixture(root,language,{'hold_network':True,'retry_delay':5})
                with (root/'fixture.stdout.log').open('w') as out,(root/'fixture.stderr.log').open('w') as err:
                    process=subprocess.Popen(command,cwd=BASE,stdout=out,stderr=err)
                    try:
                        deadline=time.monotonic()+60
                        while time.monotonic()<deadline:
                            manifest=json.loads((root/'manifest.json').read_text()) if (root/'manifest.json').exists() else {}
                            if manifest.get('status')=='waiting_network':break
                            if process.poll() is not None:self.fail((root/'stderr.log').read_text())
                            time.sleep(.05)
                        else:self.fail('Fixture did not reach network wait')
                        process.send_signal(signal.SIGTERM);process.wait(timeout=12)
                    finally:
                        if process.poll() is None:process.terminate();process.wait(timeout=12)
                before=json.loads((root/'manifest.json').read_text())
                self.assertEqual(before['status'],'interrupted')
                self.assertEqual(before['task_rounds']['used'],2)
                saved_receipt=(root/'receipts/check-0001.json').read_bytes()
                (root/'reconnect.allow').touch()
                after=self.run_fixture(command+['--resume-task'],root)
                self.assertEqual(after['task_rounds']['used'],3)
                self.assertTrue(after['machine_checked_candidate'])
                self.assertEqual((root/'receipts/check-0001.json').read_bytes(),saved_receipt)
                self.assertTrue((root/'restored-context.json').exists())

    def host(self,root,language):
        job=prepare_job(root,language,None,smoke=True,max_checks=None,check_timeout=None,max_rounds=5,checkpoint_resume=True)
        job['item_tracking_required']=True;write_json(root/'job.json',job)
        write_json(root/'state.json',{'checks':0,'deadline_monotonic':None,'last_final_receipt':None})
        return Host(root)

    def test_transport_classification_and_torn_log_record_are_not_fabricated_usage(self):
        self.assertEqual(error_kind('fetch failed: ECONNRESET'),'waiting_network')
        self.assertEqual(error_kind('HTTP 503 unavailable'),'waiting_network')
        self.assertEqual(error_kind('HTTP 401 invalid API key'),'blocked_provider')
        self.assertIsNone(error_kind('Tactic rewrite failed'))
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'provider.jsonl'
            raw=b'{"kind":"request","attempt":1}\n{"kind":"usage","attempt":1'
            path.write_bytes(raw);jsonl_boundary(path)
            self.assertEqual(path.read_bytes(),raw+b'\n')

    def test_completed_tool_operation_is_not_reexecuted_after_host_restart(self):
        with tempfile.TemporaryDirectory() as temporary:
            for language in ('lean','litex'):
                root=Path(temporary)/language;host=self.host(root,language)
                path='candidate.'+('lean' if language=='lean' else 'lit')
                body='theorem savedProof : (2 : Nat) = 2 := by rfl\n' if language=='lean' else 'thm savedProof:\n    ? 2 = 2\n    2 = 2\n'
                execute(host,'write_source',{'path':path,'content':body},'assistant-1:write')
                first=execute(host,'check',{'path':path,'mode':'incremental'},'assistant-2:check')
                self.assertTrue(first['details']['passed'],first)
                host.close();host=Host(root)
                try:
                    second=execute(host,'check',{'path':path,'mode':'incremental'},'assistant-2:check')
                    self.assertEqual(first,second)
                    self.assertEqual(host.state['checks'],1)
                    self.assertEqual(host.rounds.summary()['used'],1)
                    conflict=execute(host,'write_source',{'path':path,'content':body+'\n'},'assistant-1:write')
                    self.assertTrue(conflict['isError'])
                    self.assertEqual((root/'work'/path).read_text(),body)
                finally:host.close()

    def test_interrupted_fifth_local_verification_reuses_reserved_round_and_receipt(self):
        from item_tracking import summary
        with tempfile.TemporaryDirectory() as temporary:
            for language in ('lean','litex'):
                root=Path(temporary)/language;host=self.host(root,language)
                path='candidate.'+('lean' if language=='lean' else 'lit')
                body='theorem pendingProof : (2 : Nat) = 2 := by rfl\n' if language=='lean' else 'thm pendingProof:\n    ? 2 = 2\n    2 = 2\n'
                host.dispatch('write_source',{'path':path,'content':body})
                for _ in range(4):host.rounds.unused_generation('length')
                host.rounds.begin('check-0001');host.state['checks']=1;write_json(root/'state.json',host.state)
                host.items.begin(path,'check-0001',body)
                self.assertTrue(host.ledger.check(path,body,float('inf'))['passed'])
                host.close()  # crash after native acceptance, before saving its tool receipt
                host=Host(root)
                try:
                    host.recover_pending_check()
                    self.assertEqual(host.state['checks'],1)
                    self.assertEqual(host.rounds.summary()['used'],5)
                    self.assertFalse(host.rounds.summary()['exhausted'])
                    self.assertTrue(json.loads((root/'receipts/check-0001.json').read_text())['passed'])
                    self.assertEqual(summary(root)['main_attempt_count'],1)
                finally:host.close()

    def test_batch_resume_runs_the_same_current_task_before_advancing(self):
        import batch
        from task_rounds import TaskRounds
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)/'batch'
            batch.create_plan(root,batch.select_tasks('1')[:1],seconds=None,max_checks=None,check_timeout=None,max_rounds=5,checkpoint_resume=True)
            seen=[]
            def interrupted(attempt,slot):
                seen.append((attempt,slot['key']))
                (attempt/'work/saved.txt').write_text('preserve this source work')
                rounds=TaskRounds(attempt,json.loads((attempt/'job.json').read_text()))
                rounds.unused_generation('length')
                raise KeyboardInterrupt
            state=batch.run_batch(root,interrupted)
            self.assertEqual(state['status'],'interrupted')
            first_path,first_key=seen[0]
            calls=[]
            def resumed(attempt,slot):
                calls.append(slot['key'])
                if slot['key']==first_key:
                    self.assertEqual(attempt,first_path)
                    self.assertEqual((attempt/'work/saved.txt').read_text(),'preserve this source work')
                    self.assertEqual(TaskRounds(attempt,json.loads((attempt/'job.json').read_text())).summary()['used'],1)
                write_json(attempt/'manifest.json',{'status':'settled','machine_checked_candidate':False,'elapsed_seconds':1,'telemetry_complete':True})
            state=batch.run_batch(root,resumed)
            self.assertEqual(calls[0],first_key)
            self.assertEqual(len(calls),2)
            self.assertEqual(state['status'],'complete')


if __name__=='__main__':unittest.main()
