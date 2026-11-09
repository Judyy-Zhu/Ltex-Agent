import importlib.util
import json
from pathlib import Path
import unittest
from prepare import WORKSPACE,BASE
from verifier_feedback import native_feedback,process_status


class NativeFeedbackControls(unittest.TestCase):
    def test_matches_legacy_formatter_on_actual_success_and_failure(self):
        path = Path(__file__).parent/'fixtures/legacy_litex_llm_formatter.py'
        spec = importlib.util.spec_from_file_location('legacy_litex_formatter',path)
        legacy = importlib.util.module_from_spec(spec);spec.loader.exec_module(legacy)
        roots = [Path(__file__).parent/'fixtures'/name for name in ('litex-success.json','litex-failure.json')]
        for path in roots:
            receipt = json.loads(path.read_text())
            raw = json.loads(receipt['stdout'])
            result = native_feedback('litex',receipt)
            self.assertEqual(result['text'],legacy.format_for_llm(raw))
            self.assertEqual(result['data']['statement_results'],raw['statement_results'])
            self.assertEqual(result['data']['errors'],raw['errors'])

    def test_preserves_proof_traces_without_slicing_json(self):
        statement = {'statement_result':'accepted','statement':'x = x',
                     'proof_method':{'rule_name':'test'},'stores':['x=x'],'infers':['x=x']}
        raw = {'run_result':'success','statement_results':[statement],
               'errors':[{'phase':'proof_body','obligation':'x=x','message':'a'*9000}],
               'session_terminated':True,'termination':{'reason':'test'}}
        receipt = {'stdout':json.dumps(raw),'stderr':'native stderr','exit_code':1}
        feedback = native_feedback('litex',receipt)
        self.assertEqual(json.loads(feedback['text'])['statement_results'][0],statement)
        self.assertEqual(len(feedback['data']['errors'][0]['message']),9000)
        self.assertTrue(process_status('litex',receipt)['session_terminated'])
        self.assertEqual(feedback['stderr'],'native stderr')

    def test_lean_and_transport_errors_keep_own_formats(self):
        receipt = {'stdout':'main.lean:3:2: error: unsolved goals\nx : Nat\n⊢ x = 1\n',
                   'stderr':'compiler stderr','exit_code':1}
        feedback = native_feedback('lean',receipt)
        self.assertEqual(feedback['stdout'],receipt['stdout'])
        self.assertEqual(feedback['stderr'],receipt['stderr'])
        self.assertNotIn('statement_results',feedback)
        malformed = native_feedback('litex',{'stdout':'partial {','error':'checker_timeout'})
        self.assertEqual(malformed['format'],'litex-invalid-json')
        self.assertTrue(process_status('litex',{'error':'checker_timeout'})['timed_out'])


if __name__=='__main__':
    unittest.main()
