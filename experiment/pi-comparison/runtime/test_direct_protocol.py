"""Direct Litex candidates, real generic procedures and zero-model local repairs."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from direct_context import code_without_comments,prepare_context,procedures,repair_hints
from prepare import BASE,prepare_job,write_json
from prompts import build_prompts
from tool_host import Host,execute


class DirectProtocolControls(unittest.TestCase):
    def job(self,root,language='litex'):
        job=prepare_job(root,language,None,smoke=True,max_checks=None,check_timeout=None,max_rounds=5,
            checkpoint_resume=True,auto_finalize=True,compact_protocol=True,direct_protocol=True)
        job.update(item_tracking_required=True,require_submission_gate=True,required_clause_ids=['source_content','encoding'])
        write_json(root/'job.json',job)
        write_json(root/'state.json',{'checks':0,'last_final_receipt':None,'deadline_monotonic':None})
        return job

    def test_comment_display_preserves_strings_and_nested_comments(self):
        lean='/- outer /- nested -/ hidden -/\ndef sample := "-- literal /- text -/" -- remove\n'
        result=code_without_comments(lean,'lean')
        self.assertIn('"-- literal /- text -/"',result);self.assertNotIn('hidden',result);self.assertNotIn('remove',result)
        litex='# remove\n"""\nblock text\n"""\nhave sample R = 2 # remove\n'
        self.assertEqual(code_without_comments(litex,'litex'),'have sample R = 2\n')
        self.assertIn('"# literal"',code_without_comments('have text = "# literal" # remove\n','litex'))

    def test_library_display_does_not_change_verifier_source_and_large_library_allows_lookup(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)/'litex';job=self.job(root)
            original='# Long mathematical commentary.\nhave previous_value R = 2\n'
            (root/'input/library.lit').write_text(original);write_json(root/'input/library-index.json',{'entries':[]})
            job['library']={'input_path':'library.lit','sha256':hashlib.sha256(original.encode()).hexdigest(),
                'index_path':'library-index.json','index_sha256':hashlib.sha256((root/'input/library-index.json').read_bytes()).hexdigest(),
                'index':{'entries':[]}}
            prepare_context(root,job)
            context=json.loads((root/'input/direct-context.json').read_text())
            self.assertEqual(context['library_code'],'have previous_value R = 2\n')
            self.assertEqual((root/'input/library.lit').read_text(),original)
            self.assertTrue(job['direct_candidate_ready'])
            prepare_context(root,job,limit=2)
            self.assertFalse(job['direct_candidate_ready'])
            self.assertFalse(json.loads((root/'input/direct-context.json').read_text())['library_complete'])

    def test_direct_prompt_preserves_entire_original_proof_and_provides_operations_upfront(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)/'litex'
            job=prepare_job(root,'litex',None,task_id='EUCLID.I.P001',max_checks=None,check_timeout=None,max_rounds=5,
                checkpoint_resume=True,auto_finalize=True,compact_protocol=True,direct_protocol=True)
            system,user=build_prompts(job)
            manifest=json.loads((root/'input/source-manifest.json').read_text())
            for name in manifest['reading_policy']['primary_text_files']:self.assertIn((root/'input'/name).read_text(),user)
            self.assertIn('obtain u from exist',system)
            self.assertIn('fast_tuple_equal',system)
            self.assertIn('direct_candidate_ready=true',user)
            self.assertIn('ONE information-only',system)
            self.assertIn('direct-context.json',job['language_specific_input_files'])

    def test_all_litex_procedures_then_lean_counterparts_pass_real_final_gates(self):
        with tempfile.TemporaryDirectory() as temporary:
            for language in ('litex','lean'):
                root=Path(temporary)/language;job=self.job(root,language);host=Host(root)
                try:
                    result=execute(host,'submit_candidate',{'code':'\n\n'.join(p['code'] for p in procedures(job))},'checked-procedures')
                    self.assertTrue(result['details']['task_completed'],result)
                    self.assertEqual(host.rounds.summary()['used'],1)
                finally:host.close()

    def test_actual_error_receives_matching_checked_repair_without_changing_native_json(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)/'litex';job=self.job(root);host=Host(root)
            try:
                result=execute(host,'submit_candidate',{'code':'prop broken(x R):\n    not exist y R st y = x\n'},'bad-syntax')['details']
                self.assertFalse(result['passed'])
                repair=result['repair'];self.assertEqual(repair['model_calls'],0)
                self.assertIn('not_exist',[p['id'] for p in repair['reference_patterns']])
                self.assertTrue(any('exist ... st' in action for action in repair['actions']))
                receipt=json.loads((root/'receipts'/(result['receipt_id']+'.json')).read_text())
                self.assertEqual(result['feedback']['data']['frames'][0]['native'],receipt['native_frames'][0]['native'])
                self.assertTrue((root/'last-direct-repair.json').exists())
            finally:host.close()

    def routed(self,root,language,error,*,replay=None):
        docs=BASE/'agent-kit/guides'/f'{language}-procedures.json'
        native={'errors':[error]} if language=='litex' else {'messages':[error]}
        frames=[] if replay is None else [{'replay':True,'native':replay}]
        frames.append({'replay':False,'block_index':2,'native':native})
        receipt={'passed':False,'native_frames':frames}
        before=json.dumps(receipt,sort_keys=True)
        result=repair_hints({'language':language,'direct_protocol':True,'docs':{'procedures':str(docs)}},receipt)
        self.assertEqual(json.dumps(receipt,sort_keys=True),before)
        self.assertEqual(result['model_calls'],0)
        return result

    def test_parse_message_overrides_misleading_identifiers_and_domains(self):
        result=self.routed(None,'litex',{'phase':'parse','message':'undefined name `Prop`',
            'statement':'have fn witness_for_point(p GeoPoint) Prop = witness_for_point(p, p)'})
        self.assertEqual(result['matched_rule'],'predicate_definition')
        self.assertEqual([p['id'] for p in result['reference_patterns']],['predicate_definition'])
        self.assertTrue(any('prop name' in action for action in result['actions']))
        missing=self.routed(None,'litex',{'phase':'parse','message':'undefined name `TrainingCarrier`',
            'statement':'prop witness_shape(p GeoPoint, S TrainingCarrier):\n    exist x R st {x = 2}'})
        self.assertEqual(missing['reference_patterns'],[])
        self.assertEqual(missing['matched_rule'],'undefined_symbol')
        self.assertIn('COMPLETE replacement',' '.join(missing['actions']))

    def test_quantifier_composition_has_priority_over_unrelated_layout_examples(self):
        for error in [
            {'phase':'parse','message':'nested `forall` is not allowed here','statement':'prop training(x R): forall y R: forall z R: z = z'},
            {'phase':'parse','message':'unexpected indent','statement':'prop training(x R): exist y R st {forall z R: z = z}'},
        ]:
            result=self.routed(None,'litex',error)
            self.assertEqual([p['id'] for p in result['reference_patterns']],['quantifier_composition'])
            self.assertIn('preserve quantifier order',' '.join(result['actions']))

    def test_lean_error_messages_are_routed_and_replay_is_ignored(self):
        result=self.routed(None,'lean',{'severity':'error','data':"Unknown identifier `training_helper`",'pos':{'line':4,'column':2}},
            replay={'errors':[{'message':'undefined name `Prop`'}]})
        self.assertEqual(result['matched_rule'],'undefined_symbol')
        self.assertEqual(result['diagnostic']['frame_index'],1)
        self.assertEqual(result['diagnostic']['source_location'],{'line':4,'column':2})
        self.assertIn('Retain every helper',' '.join(result['actions']))
        self.assertEqual(result['reference_patterns'],[])

    def test_source_names_do_not_select_proof_patterns_and_preview_is_bounded(self):
        result=self.routed(None,'litex',{'phase':'proof_body','message':'Cannot establish the current fact. '+'x'*2000,
            'statement':'$witness_for_point(p GeoPoint)'})
        self.assertEqual(result['reference_patterns'],[])
        self.assertEqual(len(result['diagnostic']['message']),512)
        self.assertTrue(result['diagnostic']['message_truncated'])
        result=self.routed(None,'lean',{'severity':'error','data':'Unable to extract an existential witness'})
        self.assertEqual([p['id'] for p in result['reference_patterns']],['exist_elimination'])

    def test_real_pi_needs_one_successful_generation_or_two_for_failure_and_repair(self):
        with tempfile.TemporaryDirectory() as temporary:
            for bad,lookup in [(False,False),(True,False),(True,True)]:
                root=Path(temporary)/(str(bad)+str(lookup));job=self.job(root)
                job['offline_recovery_fixture']={'direct_candidate_probe':True,'direct_bad_first':bad,'direct_lookup_after_failure':lookup}
                write_json(root/'job.json',job)
                result=subprocess.run([sys.executable,str(BASE/'runtime/run.py'),'--language','litex','--prepared-root',str(root),
                    '--smoke','--offline-recovery-probe'],capture_output=True,text=True,timeout=60)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr+(root/'stderr.log').read_text())
                manifest=json.loads((root/'manifest.json').read_text())
                self.assertTrue(manifest['machine_checked_candidate']);self.assertEqual(manifest['status'],'settled')
                self.assertEqual(manifest['task_rounds']['used'],2 if bad else 1)
                self.assertEqual(manifest['usage']['summary']['request_attempts'],3 if lookup else 2 if bad else 1)
                payloads=[json.loads(line) for line in (root/'offline-direct-payloads.jsonl').read_text().splitlines()]
                self.assertEqual([v['function']['name'] for v in payloads[0]['tools']],['submit_candidate'])
                self.assertEqual(payloads[0]['tool_choice']['function']['name'],'submit_candidate')
                if lookup:
                    self.assertGreater(len(payloads[1]['tools']),1)
                    self.assertEqual([v['function']['name'] for v in payloads[2]['tools']],['submit_candidate'])


if __name__=='__main__':unittest.main()
