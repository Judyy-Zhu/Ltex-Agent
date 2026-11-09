"""Offline integration controls for the new experiment, not Pi's test suite."""
from pathlib import Path
import tempfile
import time
import unittest
import re
from prepare import KIT, prepare_job, write_json
from tool_host import Host, bounded, source_guard
from seed_support import assemble_final


class RuntimeControls(unittest.TestCase):
    def test_interrupted_provider_log_preserves_prior_known_usage(self):
        import json
        from run import usage_summary
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            rows=[{'kind':'request','attempt':1},{'kind':'usage','attempt':1,
                   'usage':{'prompt_tokens':100,'completion_tokens':20}},
                  {'kind':'request','attempt':2}]
            (root/'provider.jsonl').write_text('\n'.join(json.dumps(r) for r in rows)+'\n{"kind":"usage","attempt":2')
            result=usage_summary(root)
            self.assertEqual(result['summary']['request_attempts'],2)
            tokens=result['summary']['fields']['token_total']
            self.assertIsNone(tokens['value']);self.assertEqual(tokens['known_subtotal'],120)
            self.assertEqual(tokens['missing_requests'],1);self.assertEqual(len(result['log_issues']),1)

    def test_roots_guide_examples(self):
        with tempfile.TemporaryDirectory() as temporary:
            for language in ('lean','litex'):
                root = Path(temporary)/language
                job=prepare_job(root,language,90,smoke=True)
                write_json(root/'state.json',{'deadline_monotonic':time.monotonic()+90,'checks':0,
                                            'last_final_receipt':None,'submitted':False})
                host = Host(root)
                text = (KIT/f'guides/{language}-roots.md').read_text()
                code = re.search(r'```(?:lean|litex)\n(.*?)```',text,re.S).group(1)
                if language=='lean':code=re.sub(r'(?m)^import[^\n]*\n','',code)
                code=assemble_final(job,code)
                path = 'main.lean' if language=='lean' else 'main.lit'
                host.dispatch('write_source',{'path':path,'content':code})
                receipt = host.dispatch('check',{'path':path,'mode':'final'})
                self.assertTrue(receipt['passed'],receipt)

    def test_boundaries_and_trust(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for path in ('../secret','/etc/passwd','x/../../secret'):
                with self.assertRaises(ValueError):
                    bounded(root,path)
            (root/'link').symlink_to(root.parent)
            with self.assertRaises(ValueError):
                bounded(root,'link/secret')
        for source in ('theorem gap : False := by sorry','axiom gap : False',
                       'run_cmd IO.println "hello"','import Mathlib','public import Mathlib',
                       '/- leading comment -/ import Mathlib'):
            with self.assertRaises(ValueError):
                source_guard(source,'lean',[])
        for source in ('trust 2=5','axiom gap:','abstract_prop gap():','release foundation','exit','quit',':quit'):
            with self.assertRaises(ValueError):
                source_guard(source,'litex',[])
        source_guard('/- outer /- import Mathlib -/ still comment -/\n-- import Mathlib\ndef message := "import Mathlib"\n','lean',[])
        source_guard('release thm tuple_equal_from_coordinates((1,2),(1,2))\n','litex',[])
        with self.assertRaises(ValueError):
            source_guard('release thm tuple_equal_from_coordinates((1,2),(1,2)) trust 2=5\n','litex',[])

    def test_real_compilers_receipts_and_stale_edits(self):
        with tempfile.TemporaryDirectory() as temporary:
            for language in ('lean','litex'):
                root = Path(temporary)/language
                job=prepare_job(root,language,90,smoke=True)
                write_json(root/'state.json',{'deadline_monotonic':time.monotonic()+90,'checks':0,
                                            'last_final_receipt':None,'submitted':False})
                host = Host(root)
                path = 'main.lean' if language=='lean' else 'main.lit'
                good = 'theorem training_id (n : Nat) : n = n := by rfl\n' if language=='lean' else '2 + 2 = 4\n'
                bad = 'theorem training_bad : (2 : Nat) + 2 = 5 := by decide\n' if language=='lean' else '2 + 2 = 5\n'
                good=assemble_final(job,good);bad=assemble_final(job,bad)
                host.dispatch('write_source',{'path':path,'content':bad})
                failed = host.dispatch('check',{'path':path,'mode':'final'})
                self.assertFalse(failed['passed'],failed)
                host.dispatch('write_source',{'path':path,'content':good})
                passed = host.dispatch('check',{'path':path,'mode':'final'})
                self.assertTrue(passed['passed'],passed)
                host.dispatch('write_source',{'path':'interfaces.json','content':'{}'})
                submission = {'task_id':'TOOL.SMOKE','language':language,'source_files':[path],
                              'interfaces_file':'interfaces.json','agent_claim':'complete',
                              'final_receipt_id':passed['receipt_id'],'clause_mapping':[],
                              'dependencies':[],'assumptions':[],'unfinished':[]}
                with self.assertRaises(ValueError):
                    host.dispatch('submit',{'submission':submission})
                fresh = host.dispatch('check',{'path':path,'mode':'final'})
                submission['final_receipt_id'] = fresh['receipt_id']
                self.assertTrue(host.dispatch('submit',{'submission':submission})['received'])


if __name__=='__main__':
    unittest.main()
