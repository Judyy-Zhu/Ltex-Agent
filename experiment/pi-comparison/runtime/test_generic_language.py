"""Generic syntax/domain controls, unrelated to any Euclid task answer."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from prepare import BASE,write_json
from direct_context import procedures,repair_hints
from diagnostic_context import code_only
from tool_host import Host,execute
from prompts import build_prompts
import test_final_timing as fixtures


class GenericLanguageControls(unittest.TestCase):
    def host(self,root,language='litex'):
        fixtures.IndependentFinalTimingControls().job(root,language)
        return Host(root)

    def test_paired_curriculum_is_present_upfront_and_passes_independent_final_checks(self):
        with tempfile.TemporaryDirectory() as temporary:
            identities=[]
            for language in ('litex','lean'):
                root=Path(temporary)/language;host=self.host(root,language)
                try:
                    patterns=procedures(host.job);identities.append([p['id'] for p in patterns])
                    for key in ('sets_membership','parameter_constraints','logical_composition'):
                        self.assertIn(key,identities[-1])
                    system,_=build_prompts(host.job)
                    self.assertIn('sets_membership',system);self.assertIn('parameter_constraints',system)
                    self.assertIn('section="index"',system)
                    result=execute(host,'submit_candidate',{'code':'\n\n'.join(p['code'] for p in patterns)},'generic-pack')['details']
                    self.assertTrue(result['task_completed'],result)
                    receipt=json.loads((root/'receipts'/(result['auto_finalization']['final_receipt_id']+'.json')).read_text())
                    self.assertEqual(receipt['scope'],'independent_final_session')
                    self.assertGreater(receipt['final_verification_seconds'],0)
                finally:host.close()
            self.assertEqual(identities[0],identities[1])

    def test_native_membership_error_is_located_before_the_surrounding_quantifier(self):
        code='# Unrelated forall/exist words in a comment.\nprop sample_subset(A, B power_set(R)):\n    forall z R:\n        z in A\n        =>:\n            z $in B\n'
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)/'litex';host=self.host(root)
            try:
                result=execute(host,'submit_candidate',{'code':code},'bad-membership')['details']
                self.assertFalse(result['passed']);repair=result['repair']
                self.assertEqual(repair['matched_rule'],'set_membership')
                self.assertEqual(repair['diagnostic']['source_context']['source_line'],4)
                self.assertEqual(repair['diagnostic']['source_context']['path'],'candidate.lit')
                self.assertIn('z in A',repair['diagnostic']['source_context']['text'])
                self.assertEqual([p['id'] for p in repair['reference_patterns']],['sets_membership'])
                self.assertIn('x $in S',' '.join(repair['actions']))
                self.assertEqual((root/'work/candidate.lit').read_text(),code)
                receipt=json.loads((root/'receipts'/(result['receipt_id']+'.json')).read_text())
                self.assertEqual(result['feedback']['data']['frames'][0]['native'],receipt['native_frames'][0]['native'])
                section=repair['reference_sections'][0]
                self.assertEqual(section['section'],'s06');self.assertIn('membership',section['text'])
                lookup=host.dispatch('read_docs',{'topic':'core'})
                self.assertEqual(lookup['selection_origin'],'latest_native_error')
                self.assertEqual(lookup['sections'][0]['text'],section['text'])
                index=host.dispatch('read_docs',{'topic':'core','section':'index'})
                self.assertTrue(all('text' not in v for v in index['sections']))
                explicit=host.dispatch('read_docs',{'topic':'core','section':'s11'})
                self.assertEqual(explicit['section'],'s11')
                fixed=execute(host,'submit_candidate',{'code':code.replace('z in A','z $in A')},'fixed-membership')['details']
                self.assertTrue(fixed['task_completed'],fixed)
                self.assertEqual(host.rounds.summary()['used'],2)
            finally:host.close()

    def test_native_set_builder_error_selects_binder_syntax_not_a_missing_helper(self):
        with tempfile.TemporaryDirectory() as temporary:
            host=self.host(Path(temporary)/'litex')
            try:
                code='have fn sample_level(k R) power_set(R) = {u R | u = k}\n'
                result=execute(host,'submit_candidate',{'code':code},'bad-builder')['details']
                self.assertFalse(result['passed'])
                self.assertEqual(result['repair']['matched_rule'],'set_comprehension')
                self.assertIn('vertical bar',' '.join(result['repair']['actions']))
                fixed=execute(host,'submit_candidate',{'code':code.replace('R |','R:')},'fixed-builder')['details']
                self.assertTrue(fixed['task_completed'],fixed)
            finally:host.close()

    def test_native_lean_membership_type_error_has_a_source_line_and_set_reference(self):
        with tempfile.TemporaryDirectory() as temporary:
            host=self.host(Path(temporary)/'lean','lean')
            try:
                code='-- Membership requires a set.\ndef sample_member (S : ℝ) (x : ℝ) : Prop := x ∈ S\n'
                result=execute(host,'submit_candidate',{'code':code},'bad-lean-set')['details']
                self.assertFalse(result['passed'])
                self.assertEqual(result['repair']['matched_rule'],'set_membership')
                self.assertEqual(result['repair']['diagnostic']['source_context']['source_line'],2)
                self.assertIn('Set T',' '.join(result['repair']['actions']))
                fixed=execute(host,'submit_candidate',{'code':code.replace('(S : ℝ)','(S : Set ℝ)')},'fixed-lean-set')['details']
                self.assertTrue(fixed['task_completed'],fixed)
            finally:host.close()

    def routed(self,language,error,**frame):
        job={'language':language,'direct_protocol':True,'docs':{key:str(BASE/'agent-kit/guides'/filename)
            for key,filename in [('core',f'{language}-aligned-core.md'),('procedures',f'{language}-procedures.json')]}}
        native={'errors':[error]} if language=='litex' else {'messages':[error]}
        receipt={'passed':False,'native_frames':[{'replay':False,'path':'candidate.lit','block_index':0,'native':native,**frame}]}
        before=copy.deepcopy(receipt);result=repair_hints(job,receipt)
        self.assertEqual(receipt,before);self.assertEqual(result['model_calls'],0)
        return result

    def test_precise_location_overrides_unrelated_lines_and_quoted_examples(self):
        frame='prop unused(v R):\n    v in Missing\n    lost_name\n'
        result=self.routed('litex',{'phase':'parse','message':'undefined name `lost_name`','source_location':{'line':3}},
            submitted_source=frame,source_block_start_line=10,frame_line_to_block_line=[1,3,7])
        self.assertEqual(result['matched_rule'],'undefined_symbol')
        self.assertEqual(result['diagnostic']['source_context']['source_line'],16)
        quoted='have note = "q in S and {q R | q = 1}" # q in S\n'
        result=self.routed('litex',{'phase':'parse','message':'expected comparison operator','source_location':{'line':1}},submitted_source=quoted)
        self.assertNotIn(result['matched_rule'],('set_membership','set_comprehension'))
        text='/- x in S /- {z R | z=1} -/ -/\n"x in S" -- forall\ndef actual := 2\n'
        masked=code_only(text,'lean')
        self.assertEqual(len(masked),len(text));self.assertEqual(masked.count('\n'),text.count('\n'))
        self.assertNotIn('in S',masked);self.assertIn('def actual := 2',masked)

    def test_formation_and_dependent_argument_errors_preserve_conditions(self):
        for language,error in [('litex',{'phase':'predicate_signature','category':'well_defined','message':'Could not prove that the statement is well-defined.'}),
                               ('lean',{'severity':'error','data':'Type mismatch: explicit proof argument is required'})]:
            result=self.routed(language,error)
            self.assertEqual(result['matched_rule'],'parameter_constraints')
            self.assertIn('Do not delete source conditions',' '.join(result['actions']))
            self.assertEqual([p['id'] for p in result['reference_patterns']],['parameter_constraints'])

    def test_parenthesized_logical_fact_gets_a_logical_pattern_before_existential_advice(self):
        with tempfile.TemporaryDirectory() as temporary:
            host=self.host(Path(temporary)/'litex')
            try:
                result=execute(host,'submit_candidate',{'code':'prop sample_flags(a, b R):\n    a + b = 1 and (a != 0 or b != 0)\n'},'bad-logic')['details']
                self.assertFalse(result['passed'])
                self.assertEqual(result['repair']['matched_rule'],'logical_composition')
                self.assertEqual([p['id'] for p in result['repair']['reference_patterns']],['logical_composition'])
            finally:host.close()

    def test_reserved_quantifier_in_an_invalid_expression_is_not_a_missing_library_name(self):
        source='prop sample(k R):\n    exist y R st {y = k and (forall z R: z = z)}\n'
        result=self.routed('litex',{'phase':'parse','message':'undefined name `forall`','source_location':{'line':2}},submitted_source=source)
        self.assertEqual(result['matched_rule'],'quantifier_composition')
        self.assertEqual([p['id'] for p in result['reference_patterns']],['quantifier_composition'])

    def test_lean_doc_comment_placement_is_fixed_without_changing_mathematics(self):
        result=self.routed('lean',{'severity':'error','data':"unexpected token '/--'; expected 'lemma'"})
        self.assertEqual(result['matched_rule'],'declaration_layout')
        self.assertIn('before the complete declaration',' '.join(result['actions']))
        self.assertEqual(result['reference_patterns'],[])
        with tempfile.TemporaryDirectory() as temporary:
            host=self.host(Path(temporary)/'lean','lean')
            try:
                bad='noncomputable /-- A generic constant. -/\ndef sample_constant : ℝ := 1\n'
                result=execute(host,'submit_candidate',{'code':bad},'bad-comment')['details']
                self.assertFalse(result['passed'])
                self.assertEqual(result['repair']['matched_rule'],'declaration_layout')
                fixed='/-- A generic constant. -/\nnoncomputable def sample_constant : ℝ := 1\n'
                result=execute(host,'submit_candidate',{'code':fixed},'fixed-comment')['details']
                self.assertTrue(result['task_completed'],result)
            finally:host.close()


if __name__=='__main__':unittest.main()
