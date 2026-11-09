"""Regression for queued Litex errors being attributed to later candidates."""
import json
from pathlib import Path
import tempfile
import unittest

from prepare import prepare_job,write_json
from native_sessions import litex_frame,litex_repl_turns,SessionFault,SessionLedger
from tool_host import Host,execute


class LitexReplFramingControls(unittest.TestCase):
    def test_native_boundary_model_distinguishes_colon_blocks_from_multiline_functions(self):
        frame,mapping=litex_frame('# comment\nhave fn framing_bad(x R) R =\n    x + 1\n')
        turns=litex_repl_turns(frame)
        self.assertEqual(len(turns),2)
        self.assertEqual(turns[0]['text'],'have fn framing_bad(x R) R =\n\n')
        self.assertEqual([mapping[i-1] for i in turns[0]['frame_lines']],[2])
        frame,_=litex_frame('thm framing_ok:\n    ? 2 = 2\n    2 = 2\n')
        self.assertEqual(len(litex_repl_turns(frame)),1)

    def test_repeated_parse_errors_then_corrected_candidate_have_no_stale_diagnostics(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)/'litex'
            job=prepare_job(root,'litex',None,smoke=True,max_checks=None,check_timeout=None,max_rounds=5,
                checkpoint_resume=True,auto_finalize=True,compact_protocol=True)
            job.update(item_tracking_required=True,require_submission_gate=True,required_clause_ids=['source_content','encoding'])
            write_json(root/'job.json',job)
            write_json(root/'state.json',{'checks':0,'last_final_receipt':None,'deadline_monotonic':None})
            host=Host(root)
            try:
                for number in range(3):
                    name='framing_bad_'+str(number)
                    code='have fn '+name+'(x R) R =\n    x + 1\n'
                    result=execute(host,'submit_candidate',{'code':code},'bad-'+str(number))['details']
                    self.assertFalse(result['passed'])
                    frames=result['feedback']['data']['frames']
                    self.assertEqual(len(frames),1)
                    frame=frames[0]
                    self.assertIn(name,frame['native']['errors'][0]['statement'])
                    self.assertEqual(frame['native']['errors'][0]['phase'],'parse')
                    self.assertEqual(frame['submitted_source'],'have fn '+name+'(x R) R =\n\n')
                    self.assertEqual(frame['frame_line_to_block_line'],[1])
                    self.assertEqual(host.ledger.data['entries'],[])
                code='have fn framing_correct(x R) R = x + 1\n'
                result=execute(host,'submit_candidate',{'code':code},'correct')['details']
                self.assertTrue(result['task_completed'],result)
                native=result['feedback']['data']['frames'][0]['native']
                self.assertIn('framing_correct',native['statement_results'][0]['statement'])
                self.assertEqual(native['errors'],[])
                self.assertEqual(host.rounds.summary()['used'],4)
                self.assertEqual(host.ledger.data['starts'],1)
                self.assertEqual(host.ledger.data['restarts'],0)
                self.assertEqual(json.loads((root/'submission.json').read_text())['agent_claim'],'complete')
            finally:host.close()

    def test_successful_first_turn_cannot_silently_hide_unchecked_remainder(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)/'litex';job=prepare_job(root,'litex',None,smoke=True)
            ledger=SessionLedger(root,job)
            bad='have fn framing_partial(x R) R = x + 1\n    2 = 3\n'
            (root/'work/candidate.lit').write_text(bad)
            try:
                with self.assertRaisesRegex(SessionFault,'multiple native REPL turns'):
                    ledger.check('candidate.lit',bad,float('inf'))
                self.assertEqual(ledger.data['entries'],[])
                self.assertFalse(ledger.native.alive)
                good='have fn framing_partial(x R) R = x + 1\n'
                (root/'work/candidate.lit').write_text(good)
                result=ledger.check('candidate.lit',good,float('inf'))
                self.assertTrue(result['passed'],result)
                self.assertEqual(ledger.data['restarts'],1)
                self.assertIn('framing_partial',result['frames'][0]['native']['statement_results'][0]['statement'])
            finally:ledger.close()

    def test_accepted_prefix_survives_multiline_parse_error_and_corrected_suffix(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)/'litex';job=prepare_job(root,'litex',None,smoke=True)
            ledger=SessionLedger(root,job)
            prefix='have framing_prefix R = 2\n'
            bad=prefix+'have fn framing_suffix(x R) R =\n    x + framing_prefix\n'
            (root/'work/candidate.lit').write_text(bad)
            try:
                rejected=ledger.check('candidate.lit',bad,float('inf'))
                self.assertFalse(rejected['passed']);self.assertEqual(rejected['accepted_blocks'],1)
                pid=rejected['session_pid']
                self.assertIn('framing_suffix',rejected['frames'][-1]['native']['errors'][0]['statement'])
                good=prefix+'have fn framing_suffix(x R) R = x + framing_prefix\n'
                (root/'work/candidate.lit').write_text(good)
                accepted=ledger.check('candidate.lit',good,float('inf'))
                self.assertTrue(accepted['passed'],accepted);self.assertEqual(accepted['session_pid'],pid)
                self.assertEqual(accepted['replayed_blocks'],0);self.assertEqual(accepted['accepted_blocks'],2)
                self.assertEqual(len(accepted['frames']),1)
                self.assertIn('framing_suffix',accepted['frames'][0]['native']['statement_results'][0]['statement'])
            finally:ledger.close()


if __name__=='__main__':unittest.main()
