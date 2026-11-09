"""Real proof-layout failures must not suggest unrelated comma/name repairs."""
import json
from pathlib import Path
import tempfile
import unittest

from tool_host import execute
import test_generic_language as fixtures


class ProofLayoutRepairControls(unittest.TestCase):
    def test_real_cases_colon_error_preserves_header_commas_and_repairs_to_a_checked_proof(self):
        bad='''thm example_cases:
    ? forall u, v R:
        u = 0 or u = 1
        =>:
            u * (u - 1) = 0
    by cases:
        ? u = 0:
            u * (u - 1) = 0
        ? u = 1:
            u * (u - 1) = 0
'''
        fixed='''thm example_cases:
    ? forall u, v R:
        u = 0 or u = 1
        =>:
            u * (u - 1) = 0
    by cases:
        ? u * (u - 1) = 0
        case u = 0:
            u * (u - 1) = 0
        case u = 1:
            u * (u - 1) = 0
'''
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)/'litex';host=fixtures.GenericLanguageControls().host(root)
            try:
                result=execute(host,'submit_candidate',{'code':bad},'bad-case-goal')['details']
                self.assertFalse(result['passed'])
                self.assertEqual(result['repair']['matched_rule'],'proof_goal_layout')
                self.assertIn('common conclusion',' '.join(result['repair']['actions']))
                self.assertNotIn('without trailing commas',' '.join(result['repair']['actions']))
                self.assertEqual(result['repair']['reference_sections'][0]['section'],'s12')
                receipt=json.loads((root/'receipts'/(result['receipt_id']+'.json')).read_text())
                self.assertEqual(result['feedback']['data']['frames'][0]['native'],receipt['native_frames'][0]['native'])
                self.assertEqual((root/'work/candidate.lit').read_text(),bad)
                result=execute(host,'submit_candidate',{'code':fixed},'fixed-case-goal')['details']
                self.assertTrue(result['task_completed'],result)
                self.assertEqual(host.rounds.summary()['used'],2)
            finally:host.close()

    def test_real_impossible_scope_and_missing_clause_use_contradiction_reference(self):
        outside='''thm example_contra:
    ? forall t R:
        t = t
    impossible t != t
'''
        missing='''thm example_contra:
    ? forall t R:
        t = t
    by contra:
        ? t = t
        t = t
'''
        fixed='''thm example_contra:
    ? forall t R:
        t = t
    by contra:
        ? t = t
        impossible t != t
'''
        with tempfile.TemporaryDirectory() as temporary:
            host=fixtures.GenericLanguageControls().host(Path(temporary)/'litex')
            try:
                for index,code in enumerate([outside,missing]):
                    result=execute(host,'submit_candidate',{'code':code},'bad-contra-'+str(index))['details']
                    self.assertFalse(result['passed'])
                    self.assertEqual(result['repair']['matched_rule'],'contradiction_layout')
                    self.assertEqual(result['repair']['reference_sections'][0]['section'],'s12')
                    self.assertEqual(result['repair']['reference_patterns'],[])
                    self.assertNotIn('missing name',' '.join(result['repair']['actions']))
                result=execute(host,'submit_candidate',{'code':fixed},'fixed-contra')['details']
                self.assertTrue(result['task_completed'],result)
                self.assertEqual(host.rounds.summary()['used'],3)
            finally:host.close()

    def test_extra_token_is_classified_from_the_error_line_not_an_outer_signature(self):
        helper=fixtures.GenericLanguageControls()
        statement='thm example:\n    ? forall a, b R:\n        a = a\n    a = a:\n'
        result=helper.routed('litex',{'phase':'parse','message':'trailing tokens in fact: `:`',
            'source_location':{'line':4},'statement':statement},submitted_source=statement)
        self.assertEqual(result['matched_rule'],'trailing_fact_token')
        self.assertNotIn('Remove the extra trailing comma',' '.join(result['actions']))
        statement=statement.replace('a = a:\n','a = a,\n')
        result=helper.routed('litex',{'phase':'parse','message':'trailing tokens in fact: `,`',
            'source_location':{'line':4},'statement':statement},submitted_source=statement)
        self.assertEqual(result['matched_rule'],'trailing_fact_comma')
        result=helper.routed('litex',{'phase':'parse','message':'undefined name `impossible_helper`',
            'statement':'have value R = impossible_helper'})
        self.assertEqual(result['matched_rule'],'undefined_symbol')


if __name__=='__main__':unittest.main()
