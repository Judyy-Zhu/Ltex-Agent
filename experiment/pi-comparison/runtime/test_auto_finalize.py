"""Real native kernels and real Pi transport; no external model/API requests."""
import json
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from prepare import BASE,prepare_job,write_json
from tool_host import Host
from prompts import build_prompts


class AutomaticCompletionControls(unittest.TestCase):
    def host(self,root,language):
        job=prepare_job(root,language,None,smoke=True,max_checks=None,check_timeout=None,
                        max_rounds=5,checkpoint_resume=True,auto_finalize=True)
        job.update(item_tracking_required=True,require_submission_gate=True,required_clause_ids=['source_content','encoding'])
        write_json(root/'job.json',job)
        write_json(root/'state.json',{'checks':0,'deadline_monotonic':None,'last_final_receipt':None})
        return Host(root)

    def candidate(self,host,source=None):
        language=host.job['language'];path='candidate.'+('lean' if language=='lean' else 'lit')
        source=source or ('namespace Geometry\nstructure Line where\n  point : GeoPoint\ntheorem equalSelf (p : GeoPoint) : p = p := by rfl\nend Geometry\n'
                         if language=='lean' else 'prop equalSelf(x R):\n    x = x\n')
        host.dispatch('write_source',{'path':path,'content':source})
        return path

    def test_fifth_attempt_native_pass_auto_saves_without_encoding_metadata_or_extra_kernel_gate(self):
        with tempfile.TemporaryDirectory() as temporary:
            for language in ('lean','litex'):
                root=Path(temporary)/language;host=self.host(root,language)
                try:
                    for _ in range(4):host.rounds.transport_failure('offline network fixture')
                    source=(BASE/'runtime/fixtures/litex-accepted-point-definition.lit').read_text() if language=='litex' else None
                    path=self.candidate(host,source)
                    with patch('submission_gate.validate',side_effect=AssertionError('Redundant kernel gate')):
                        result=host.check({'path':path,'mode':'incremental'})
                    self.assertTrue(result['task_completed'],result)
                    self.assertEqual(host.state['checks'],2) # session candidate + ONE independent final file
                    self.assertEqual(host.rounds.summary()['used'],5)
                    self.assertFalse(host.rounds.summary()['exhausted'])
                    submission=json.loads((root/'submission.json').read_text())
                    self.assertEqual({c['clause_id'] for c in submission['clause_mapping']},{'source_content','encoding'})
                    gate=json.loads((root/'submission-gate.json').read_text())
                    self.assertTrue(gate['passed']);self.assertEqual(gate['source_hashes'],host.hashes())
                    if language=='lean':
                        self.assertIn('Geometry.Line.mk',gate['symbols'])
                        self.assertIn('Geometry.equalSelf',gate['symbols'])
                        self.assertEqual(gate['unapproved_axioms'],[])
                    else:self.assertIn('geo_has_no_part',gate['symbols'])
                    before=host.hashes()
                    host.dispatch('write_source',{'path':path,'content':'should not mutate'})
                    self.assertEqual(before,host.hashes())
                finally:host.close()

    def test_interrupted_local_finalization_recovers_same_candidate_without_another_round(self):
        with tempfile.TemporaryDirectory() as temporary:
            for language in ('lean','litex'):
                root=Path(temporary)/language;host=self.host(root,language)
                path=self.candidate(host)
                real_check=host.check
                def interrupted(args,**kwargs):
                    if args['mode']=='final':raise OSError('offline disk interruption')
                    return real_check(args,**kwargs)
                try:
                    with patch.object(host,'check',side_effect=interrupted):
                        with self.assertRaises(OSError):host.check({'path':path,'mode':'incremental'})
                    self.assertEqual(json.loads((root/'auto-finalization.json').read_text())['status'],'pending')
                finally:host.close()
                if language=='litex':(root/'auto-finalization.json').unlink() # crash before transaction creation
                host=Host(root)
                try:
                    host.recover_pending_check()
                    self.assertEqual(host.rounds.summary()['used'],1)
                    self.assertEqual(json.loads((root/'auto-finalization.json').read_text())['status'],'complete')
                finally:host.close()

    def test_failed_candidate_never_generates_a_completion_or_publishes_partial_litex_prefix(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)/'litex';host=self.host(root,'litex')
            try:
                path=self.candidate(host,'have prefixValue R = 2\nthm falseProof:\n    ? 2 = 3\n    2 = 3\n')
                checked=host.check({'path':path,'mode':'incremental'})
                self.assertFalse(checked['passed']);self.assertFalse(checked['task_completed'])
                self.assertFalse((root/'submission.json').exists())
                self.assertEqual(host.rounds.summary()['used'],1)
            finally:host.close()

    def test_independent_final_failure_cannot_be_reported_as_task_success(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)/'litex';host=self.host(root,'litex')
            try:
                path=self.candidate(host)
                native_run=subprocess.run
                def fail_final(command,**kwargs):
                    if '-f' in command:
                        return subprocess.CompletedProcess(command,1,stdout=json.dumps({'kind':'run','run_result':'error','errors':['offline final verifier failure']}),stderr='')
                    return native_run(command,**kwargs)
                with patch('tool_host.subprocess.run',side_effect=fail_final):
                    checked=host.check({'path':path,'mode':'incremental'})
                self.assertTrue(checked['passed']) # native incremental check succeeded
                self.assertFalse(checked['task_completed'])
                self.assertFalse(checked['auto_finalization']['final_check']['passed'])
                self.assertFalse((root/'submission.json').exists())
                self.assertEqual(host.rounds.summary()['used'],1)
                self.assertFalse(host.rounds.summary()['rounds'][0]['passed'])
                self.assertTrue(host.check({'path':path,'mode':'incremental'})['task_completed'])
                self.assertEqual(host.rounds.summary()['used'],2)
            finally:host.close()

    def test_unnamed_accepted_fact_returns_repair_feedback_instead_of_sticking_in_local_recovery(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)/'litex';host=self.host(root,'litex')
            try:
                path=self.candidate(host,'2 = 2\n')
                checked=host.check({'path':path,'mode':'incremental'})
                self.assertTrue(checked['passed']);self.assertFalse(checked['task_completed'])
                self.assertIn('public native declaration',checked['auto_finalization']['controller_error'])
                self.assertEqual(json.loads((root/'auto-finalization.json').read_text())['status'],'failed')
                self.assertFalse(host.rounds.summary()['rounds'][0]['passed'])
            finally:host.close()

    def test_actual_pi_stops_after_kernel_pass_before_any_followup_model_request(self):
        with tempfile.TemporaryDirectory() as temporary:
            for language in ('lean','litex'):
                root=Path(temporary)/language;host=self.host(root,language);host.close()
                job=json.loads((root/'job.json').read_text())
                job['offline_recovery_fixture']={'initial_network':True,'initial_release_after':0}
                write_json(root/'job.json',job)
                result=subprocess.run([sys.executable,str(BASE/'runtime/run.py'),'--language',language,
                    '--prepared-root',str(root),'--smoke','--offline-recovery-probe'],capture_output=True,text=True,timeout=120)
                self.assertEqual(result.returncode,0,result.stdout+'\n'+result.stderr+'\n'+(root/'stderr.log').read_text())
                manifest=json.loads((root/'manifest.json').read_text())
                self.assertEqual(manifest['status'],'settled');self.assertTrue(manifest['machine_checked_candidate'])
                self.assertEqual(len(manifest['tool_allowlist']),6);self.assertNotIn('submit',manifest['tool_allowlist'])
                schemas=json.loads((root/'offline-active-schemas.json').read_text())
                self.assertEqual(set(schemas),set(manifest['tool_allowlist']))
                self.assertEqual(set(schemas['write_source']['properties']),{'path','content','base'})
                self.assertEqual(schemas['check']['properties']['mode']['const'],'incremental')
                self.assertEqual(manifest['task_rounds']['used'],2)
                requests=[json.loads(line) for line in (root/'provider.jsonl').read_text().splitlines() if json.loads(line)['kind']=='request']
                self.assertEqual(len(requests),4) # write bad/check/write good/check; zero metadata/followup requests
                self.assertTrue(all(r['offline_stub'] for r in requests))

    def test_both_languages_receive_primary_txt_seed_and_field_guide_upfront(self):
        from batch import select_tasks,create_plan
        with tempfile.TemporaryDirectory() as temporary:
            batch=Path(temporary)/'batch'
            plan=create_plan(batch,select_tasks('1')[:1],seconds=None,max_checks=None,check_timeout=None,
                             max_rounds=5,auto_finalize=True)
            texts=[]
            for language in ('lean','litex'):
                root=Path(temporary)/language
                job=prepare_job(root,language,None,source_cache=batch/'source-cache',task_id=plan['records'][0]['id'],
                    max_checks=None,check_timeout=None,max_rounds=5,auto_finalize=True)
                system,prompt=build_prompts(job)
                primary=json.loads((root/'input/source-manifest.json').read_text())['reading_policy']['primary_text_files']
                texts.append([(root/'input'/name).read_text() for name in primary])
                self.assertTrue(all(t in prompt for t in texts[-1]));self.assertIn('task_completed=true',prompt)
                self.assertIn(Path(job['seed_path']).read_text(),prompt)
                self.assertIn(Path(job['docs']['feedback']).read_text(),prompt)
                self.assertIn('Do not write final files, interfaces, encoding labels',prompt)
                from prompts import continuation_prompt
                continuation=continuation_prompt(job,{'used':2,'limit':5})
                self.assertIn('Stop when task_completed=true',continuation)
                self.assertNotIn('finish final verification and submit it',continuation)
            self.assertEqual(*texts)

    def test_real_pi_compaction_is_local_preserves_original_text_and_makes_no_summary_request(self):
        with tempfile.TemporaryDirectory() as temporary:
            for language in ('lean','litex'):
                root=Path(temporary)/language;host=self.host(root,language);host.close()
                original='Original source fixture. A point is that which has no part.\n'
                (root/'input/original.txt').write_text(original)
                write_json(root/'input/task.json',{'task_id':'TOOL.SMOKE','statement':'Original source fixture'})
                write_json(root/'input/source-manifest.json',{'reading_policy':{'primary_text_files':['original.txt'],'context_text_files':[]}})
                job=json.loads((root/'job.json').read_text());job['offline_recovery_fixture']={'force_compaction_stop':True}
                extension='lean' if language=='lean' else 'lit'
                previous='def retainedValue : Nat := 2\n' if language=='lean' else 'have retainedValue R = 2\n'
                library_file='library.'+extension;(root/'input'/library_file).write_text(previous)
                parts=root/'input/library-parts';parts.mkdir();(parts/('previous.'+extension)).write_text(previous)
                index={'entries':[{'task_id':'RETAINED.PREDECESSOR','file':'previous.'+extension,
                    'sha256':hashlib.sha256(previous.encode()).hexdigest(),'symbols':['retainedValue'],
                    'interfaces':{'declarations':{'retainedValue':{'name':'retainedValue','type':'Nat' if language=='lean' else 'R'}}}}]}
                write_json(root/'input/library-index.json',index)
                job['library']={'input_path':library_file,'sha256':hashlib.sha256(previous.encode()).hexdigest(),
                    'index_path':'library-index.json','index_sha256':hashlib.sha256((root/'input/library-index.json').read_bytes()).hexdigest(),'index':index}
                write_json(root/'job.json',job)
                from tool_host import execute
                memory_host=Host(root)
                try:
                    execute(memory_host,'read_docs',{'topic':'logic'})
                    execute(memory_host,'read_library',{'symbols':['retainedValue']})
                finally:memory_host.close()
                result=subprocess.run([sys.executable,str(BASE/'runtime/run.py'),'--language',language,
                    '--prepared-root',str(root),'--smoke','--offline-recovery-probe','--verify-compaction'],
                    capture_output=True,text=True,timeout=120)
                self.assertEqual(result.returncode,0,result.stdout+'\n'+result.stderr+'\n'+(root/'stderr.log').read_text())
                manifest=json.loads((root/'manifest.json').read_text())
                self.assertTrue(manifest['compaction_smoke_receipt']['success'],manifest['compaction_smoke_receipt'])
                compact=[json.loads(line) for line in (root/'local-compactions.jsonl').read_text().splitlines()]
                self.assertTrue(compact);self.assertTrue(all(row['model_calls']==0 for row in compact))
                requests=[json.loads(line) for line in (root/'provider.jsonl').read_text().splitlines() if json.loads(line)['kind']=='request']
                self.assertEqual(len(requests),3) # write/check/stop; NO background summary request
                entries=[json.loads(line) for line in (root/'pi-session.jsonl').read_text().splitlines()]
                summary=next(row['summary'] for row in reversed(entries) if row['type']=='compaction')
                self.assertIn(original,summary);self.assertIn('receipt:check-0001',summary)
                for name in ('foundation.json','seed-interface.json','seed.'+('lean' if language=='lean' else 'lit')):
                    self.assertIn((root/'input'/name).read_text(),summary)
                self.assertIn('OWN-LANGUAGE PUBLISHED LIBRARY',summary)
                self.assertIn('RETAINED.PREDECESSOR',summary)
                memory_text=summary.split('MATERIAL ALREADY RETRIEVED AND RECENT PATH ERRORS:\n',1)[1].split('\n\nATTEMPT HISTORY:',1)[0]
                self.assertEqual(json.loads(memory_text)['last_retrieved_library_source']['source'],previous)
                self.assertIn('symbol_metadata',summary);self.assertIn('"logic"',summary)
                self.assertIn('core language guide',summary)


if __name__=='__main__':unittest.main()
