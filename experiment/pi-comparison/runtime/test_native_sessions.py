from pathlib import Path
import tempfile
import time
import unittest
import json
import subprocess
import sys
from prepare import prepare_job
from prepare import write_json
from native_sessions import SessionLedger,litex_blocks


class NativeSessionControls(unittest.TestCase):
    def test_persistent_tool_broker_preserves_session_and_final_is_independent(self):
        with tempfile.TemporaryDirectory() as temporary:
            for language in ('lean','litex'):
                root=Path(temporary)/language;prepare_job(root,language,180,smoke=True)
                write_json(root/'state.json',{'deadline_monotonic':time.monotonic()+180,
                                            'checks':0,'last_final_receipt':None})
                process=subprocess.Popen([sys.executable,str(Path(__file__).parent/'tool_host.py'),str(root),'--server'],
                                         stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
                sequence=0
                def call(tool,arguments):
                    nonlocal sequence
                    sequence+=1
                    process.stdin.write(json.dumps({'id':sequence,'tool':tool,'arguments':arguments})+'\n')
                    process.stdin.flush()
                    response=json.loads(process.stdout.readline())
                    self.assertEqual(response['id'],sequence)
                    self.assertFalse(response['result'].get('isError'),response)
                    return response['result']['details']
                try:
                    ext='lean' if language=='lean' else 'lit'
                    source='def brokerProbe : Nat := 2\n' if language=='lean' else 'have brokerProbe R = 2\n'
                    call('write_source',{'path':'one.'+ext,'content':source})
                    first=call('check',{'path':'one.'+ext,'mode':'incremental'})
                    self.assertTrue(first['passed'],first)
                    pid=first['session']['session_pid']
                    blocked_source='theorem badGuard : False := by sorry\n' if language=='lean' else 'trust 2 = 5\n'
                    call('write_source',{'path':'guard.'+ext,'content':blocked_source})
                    guard=call('check',{'path':'guard.'+ext,'mode':'incremental'})
                    self.assertFalse(guard['passed'])
                    self.assertEqual(guard['session']['session_pid'],pid)
                    self.assertTrue(guard['session']['session_alive'])
                    self.assertEqual(guard['feedback']['data']['frames'],[])
                    fragment='example : brokerProbe = 2 := by rfl\n' if language=='lean' else 'brokerProbe = 2\n'
                    call('write_source',{'path':'two.'+ext,'content':fragment})
                    second=call('check',{'path':'two.'+ext,'mode':'incremental'})
                    self.assertTrue(second['passed'],second)
                    self.assertEqual(second['session']['session_pid'],pid)
                    library=call('read_library',{'symbols':['accepted_prefix']})
                    call('write_source',{'path':'final.'+ext,'content':library['session']['accepted_source']})
                    final=call('check',{'path':'final.'+ext,'mode':'final'})
                    self.assertTrue(final['passed'],final)
                    again=call('check',{'path':'two.'+ext,'mode':'incremental'})
                    self.assertEqual(again['session']['session_pid'],pid)
                    self.assertTrue(again['passed'],again)
                    self.assertEqual(again['feedback']['data']['frames'],[])
                finally:
                    process.stdin.close();process.wait(timeout=5)
                    errors=process.stderr.read()
                    self.assertEqual(process.returncode,0,errors)
                    process.stdout.close();process.stderr.close()

    def run_fragment(self,ledger,root,path,source):
        (root/'work'/path).write_text(source)
        return ledger.check(path,source,time.monotonic()+90)

    def test_litex_soft_failure_parse_recovery_partial_prefix_and_replay(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)/'litex';job=prepare_job(root,'litex',120,smoke=True)
            ledger=SessionLedger(root,job)
            try:
                first=self.run_fragment(ledger,root,'one.lit','have a R = 2\n')
                self.assertTrue(first['passed'],first)
                pid=first['session_pid']
                failed=self.run_fragment(ledger,root,'two.lit','a = 3\n')
                self.assertFalse(failed['passed']);self.assertEqual(failed['session_pid'],pid)
                repaired=self.run_fragment(ledger,root,'two.lit','a + 1 = 3\n')
                self.assertTrue(repaired['passed'],repaired)
                self.assertEqual(repaired['session_pid'],pid)
                malformed=self.run_fragment(ledger,root,'bad.lit','have fn bad(x R) R = x +\n')
                self.assertFalse(malformed['passed'])
                self.assertTrue(self.run_fragment(ledger,root,'three.lit','a + 2 = 4\n')['passed'])
                self.assertEqual(ledger.native.io.process.pid,pid)
                mixed=self.run_fragment(ledger,root,'mixed.lit','have b R = 4\nb = 5\nhave not_executed R = 7\n')
                self.assertFalse(mixed['passed']);self.assertEqual(len(mixed['frames']),2)
                self.assertEqual(mixed['frames'][0]['native']['statement_results'][0]['statement_result'],'accepted')
                self.assertTrue(self.run_fragment(ledger,root,'useb.lit','b = 4\n')['passed'])
                # Preserve the first accepted block while fixing a later block
                # in the same file. Do not reload or redeclare b.
                repaired=self.run_fragment(ledger,root,'mixed.lit','have b R = 4\nb = 4\n')
                self.assertTrue(repaired['passed'],repaired)
                self.assertEqual(repaired['session_pid'],pid)
                ledger.native.io.process.kill();ledger.native.io.process.wait()
                replay=self.run_fragment(ledger,root,'after_restart.lit','a + b = 6\n')
                self.assertTrue(replay['passed'],replay)
                self.assertNotEqual(replay['session_pid'],pid)
                self.assertGreater(replay['replayed_blocks'],0)
            finally:ledger.close()

    def test_lean_env_rollback_namespaces_and_restart(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)/'lean';job=prepare_job(root,'lean',120,smoke=True)
            ledger=SessionLedger(root,job)
            try:
                first=self.run_fragment(ledger,root,'one.lean','def probeA : Nat := 2\n')
                self.assertTrue(first['passed'],first);pid=first['session_pid']
                failed=self.run_fragment(ledger,root,'two.lean','theorem falseProbe : probeA = 3 := by decide\n')
                self.assertFalse(failed['passed'],failed)
                env=failed['frames'][-1]['environment_transition']
                self.assertEqual(env['before'],env['after'])
                self.assertFalse(env['adopted_returned_env'])
                self.assertIn('messages',failed['frames'][-1]['native'])
                fixed=self.run_fragment(ledger,root,'two.lean','theorem goodProbe : probeA = 2 := by rfl\n')
                self.assertTrue(fixed['passed'],fixed);self.assertEqual(fixed['session_pid'],pid)
                for path,source in [('open.lean','namespace ProbeNamespace\n'),
                                    ('inside.lean','theorem identity (x : Nat) : x = x := by rfl\n'),
                                    ('close.lean','end ProbeNamespace\n')]:
                    self.assertTrue(self.run_fragment(ledger,root,path,source)['passed'])
                ledger.native.io.process.kill();ledger.native.io.process.wait()
                replay=self.run_fragment(ledger,root,'after_restart.lean',
                                         'example : probeA = 2 := goodProbe\nexample : (3:Nat) = 3 := ProbeNamespace.identity 3\n')
                self.assertTrue(replay['passed'],replay)
                self.assertNotEqual(replay['session_pid'],pid)
            finally:ledger.close()

    def test_edit_invalidates_dependents_in_both_languages(self):
        with tempfile.TemporaryDirectory() as temporary:
            for language in ('lean','litex'):
                root=Path(temporary)/language;job=prepare_job(root,language,120,smoke=True)
                ledger=SessionLedger(root,job)
                try:
                    ext='lean' if language=='lean' else 'lit'
                    one='def editProbe : Nat := 2\n' if language=='lean' else 'have editProbe R = 2\n'
                    two='example : editProbe = 2 := by rfl\n' if language=='lean' else 'editProbe = 2\n'
                    self.assertTrue(self.run_fragment(ledger,root,'one.'+ext,one)['passed'])
                    self.assertTrue(self.run_fragment(ledger,root,'two.'+ext,two)['passed'])
                    (root/'work'/('one.'+ext)).write_text(one.replace('2','4'))
                    blocked=self.run_fragment(ledger,root,'two.'+ext,two)
                    self.assertFalse(blocked['passed']);self.assertIn('prerequisite',blocked['controller_error'])
                    self.assertTrue(self.run_fragment(ledger,root,'one.'+ext,one.replace('2','4'))['passed'])
                    self.assertFalse(self.run_fragment(ledger,root,'two.'+ext,two)['passed'])
                finally:ledger.close()

    def test_litex_frame_split_comments_and_nested_block(self):
        source='# intro\nhave a R = 2\n\nthm t:\n    ? a = 2\n\n    a = 2\n# tail\na = 2\n'
        blocks=litex_blocks(source)
        self.assertEqual(len(blocks),3)
        self.assertIn('thm t:',blocks[1]['text'])
        self.assertIn('    a = 2',blocks[1]['text'])

    def test_litex_comment_frames_do_not_shift_native_responses(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)/'litex';job=prepare_job(root,'litex',90,smoke=True)
            ledger=SessionLedger(root,job)
            source='"""\nA non-executable block comment\n"""\n# a line comment\nhave commentProbe R = 2\n# trailing comment\n'
            try:
                first=self.run_fragment(ledger,root,'comments.lit',source)
                self.assertTrue(first['passed'],first)
                self.assertEqual(len(first['frames']),1)
                frame=first['frames'][0]
                self.assertEqual(frame['native']['statement_results'][0]['statement'],'have commentProbe R = 2')
                self.assertEqual(frame['frame_line_to_block_line'],[5])
                self.assertTrue(self.run_fragment(ledger,root,'use.lit','commentProbe = 2\n')['passed'])
                with self.assertRaisesRegex(ValueError,'Unclosed'):
                    ledger.check('bad-comment.lit','"""\nunclosed\n',time.monotonic()+10)
                self.assertTrue(ledger.native.alive)
            finally:ledger.close()


if __name__=='__main__':unittest.main()
