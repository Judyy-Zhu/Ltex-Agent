"""Actual native replay, uncached candidate submissions and hash-bound selection."""
import json
from pathlib import Path
import tempfile
import unittest
import test_compact_protocol as fixtures
from tool_host import execute
from prepare import write_json
from replay_benchmark import benchmark,select,sha,summarize
from verification_timing import measure


class ReplayBenchmarkControls(unittest.TestCase):
    def test_actual_paired_replay_keeps_warmups_and_never_uses_session_acceptance_cache(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)/'batch';root.mkdir();slots=[];records={};files={};finals=[]
            helper=fixtures.CompactProtocolControls()
            for language in ('lean','litex'):
                relative='workers/'+language+'/attempts/one';attempt=root/relative;host=helper.host(attempt,language)
                try:
                    result=execute(host,'submit_candidate',{'code':helper.source(language)},'accepted-fixture')
                    self.assertTrue(result['details']['task_completed'])
                    job=host.job
                    paths=[Path(job['litex'])] if language=='litex' else [Path(job['lake']),Path(job['lean_repl']),Path(job['lean_project'])/'lean-toolchain',Path(job['lean_project'])/'lake-manifest.json']
                    files.update({str(p.resolve()):sha(p) for p in paths})
                    final=attempt/'work'/('final.lean' if language=='lean' else 'final.lit');finals.append((final,sha(final)))
                finally:host.close()
                write_json(attempt/'manifest.json',{'status':'settled','machine_checked_candidate':True,'offline_fixture':False,'job_sha256':sha(attempt/'job.json')})
                key='r1:TOOL.SMOKE:'+language;slots.append({'key':key,'task_id':'TOOL.SMOKE','language':language,'repetition':1})
                records[key]={'status':'finished','published':True,'attempt':relative}
            write_json(root/'plan.json',{'slots':slots,'environment':{'files':files}})
            write_json(root/'state.json',{'records':records,'status':'complete','plan_sha256':sha(root/'plan.json')})
            result=benchmark(root,Path(temporary)/'replay',repetitions=1,warmups=1)
            self.assertTrue(result['passed']);self.assertEqual(result['model_calls'],0);self.assertEqual(len(result['rows']),4)
            self.assertEqual(sum(row['warmup'] for row in result['rows']),2)
            for row in result['rows']:self.assertGreater(row['candidate_native_requests'],0)
            for language in ('lean','litex'):self.assertEqual(result['summary'][language]['samples'],1)
            for path,value in finals:self.assertEqual(sha(path),value)
            finals[0][0].write_text(finals[0][0].read_text()+'\n')
            with self.assertRaisesRegex(ValueError,'changed'):select(root)

    def test_phase_accounting_includes_startup_request_failures_and_keeps_other_cost(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);(root/'receipts').mkdir()
            write_json(root/'receipts/final.json',{'mode':'final','seconds':0.6,'native_process_seconds':0.5})
            write_json(root/'receipts/incremental.json',{'mode':'incremental','seconds':0.4})
            events=[{'kind':'session_start_error','seconds':0.2},
                    {'kind':'native_error','seconds':0.1,'replay':False},
                    {'kind':'native_response','seconds':0.05,'replay':True}]
            result=measure(root,events,1.0)
            self.assertEqual(result['native_request_errors'],1)
            self.assertEqual(result['independent_final_file_seconds'],0.5)
            self.assertAlmostEqual(result['other_verifier_seconds'],0.15)
            orphan=measure(root,events+[{'kind':'native_response','seconds':0.3,'replay':True}],1.0)
            self.assertAlmostEqual(orphan['unreceipted_native_seconds'],0.15)
            self.assertAlmostEqual(orphan['accounted_verifier_seconds'],1.15)

    def test_replay_summary_does_not_discard_failed_measured_samples(self):
        result=summarize([{'language':'litex','warmup':False,'passed':False,'warm_candidate_seconds':0.1},
                          {'language':'litex','warmup':False,'passed':True,'warm_candidate_seconds':0.3},
                          {'language':'litex','warmup':True,'passed':True,'warm_candidate_seconds':99}])
        self.assertEqual(result['litex']['samples'],2);self.assertEqual(result['litex']['passed'],1)
        self.assertAlmostEqual(result['litex']['warm_candidate_seconds']['mean'],0.2)


if __name__=='__main__':unittest.main()
