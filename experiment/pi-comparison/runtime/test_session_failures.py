from pathlib import Path
import sys
import tempfile
import time
import unittest
from prepare import prepare_job
from native_sessions import JsonProcess,SessionFault,SessionLedger


class SessionFailureControls(unittest.TestCase):
    def test_input_timeout_is_bounded_and_process_can_be_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            script=Path(temporary)/'unresponsive.py'
            script.write_text('import time\ntime.sleep(5)\n')
            process=JsonProcess([sys.executable,str(script)],temporary)
            start=time.monotonic()
            try:
                with self.assertRaises(TimeoutError):
                    process.exchange('x'*500000+'\n',time.monotonic()+.15)
                self.assertLess(time.monotonic()-start,1.5)
            finally:process.close()
            self.assertFalse(process.alive)

    def test_json_reader_handles_braces_inside_strings(self):
        with tempfile.TemporaryDirectory() as temporary:
            script=Path(temporary)/'echo.py'
            script.write_text('import sys,json\nfor line in sys.stdin:\n print(json.dumps({"text":"} { \\\"", "request":line},indent=2),flush=True)\n')
            process=JsonProcess([sys.executable,str(script)],temporary)
            try:
                for value in ('first','second'):
                    response=process.exchange(value+'\n',time.monotonic()+5)
                    self.assertEqual(response['request'],value+'\n')
                    self.assertIn('} {',response['text'])
            finally:process.close()

    def test_replay_failure_blocks_continuation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)/'litex';job=prepare_job(root,'litex',90,smoke=True)
            ledger=SessionLedger(root,job)
            source='have replayProbe R = 2\n';(root/'work/one.lit').write_text(source)
            try:
                self.assertTrue(ledger.check('one.lit',source,time.monotonic()+30)['passed'])
                ledger.close()
                # Simulate a formerly accepted entry no longer replaying under
                # its verifier. Do not let a partial rebuild continue silently.
                ledger.data['entries'][0]['text']='2 = 3\n'
                with self.assertRaisesRegex(SessionFault,'failed replay'):
                    ledger.check('one.lit',source,time.monotonic()+30)
                self.assertIsNone(ledger.native)
                self.assertFalse(ledger.frames[-1]['passed'])
                self.assertTrue(ledger.frames[-1]['replay'])
            finally:ledger.close()


if __name__=='__main__':unittest.main()
