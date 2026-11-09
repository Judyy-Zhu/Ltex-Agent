import unittest
import json
import sys
from pathlib import Path
import tempfile
import time
from audit_candidate import parse_axioms,safe_symbol
from audit_candidate import audit

sys.path.insert(0,str(Path(__file__).resolve().parent/'runtime'))
from prepare import prepare_job,write_json
from tool_host import Host
from seed_support import assemble_final


class AuditControls(unittest.TestCase):
    def test_symbols_cannot_inject_commands(self):
        for name in ('Euclid.prop1','foo_1','Geo.等边','root_test\''):
            self.assertTrue(safe_symbol(name),name)
        for name in ('a\n#print axioms sorryAx','a; b','../secret','9x',''):
            self.assertFalse(safe_symbol(name),name)

    def test_axiom_reports_are_required_and_preserved(self):
        output = "'Geo.main' depends on axioms: [propext,\n Classical.choice, sorryAx]\n'Geo.id' does not depend on any axioms\n"
        axioms,missing = parse_axioms(output,['Geo.main','Geo.id','Geo.absent'])
        self.assertIn('sorryAx',axioms['Geo.main'])
        self.assertEqual(axioms['Geo.id'],[])
        self.assertEqual(missing,['Geo.absent'])

    def test_real_saved_candidates_and_stale_rejection(self):
        with tempfile.TemporaryDirectory() as temporary:
            for language in ('lean','litex'):
                root = Path(temporary)/language
                job=prepare_job(root,language,120,smoke=True)
                write_json(root/'state.json',{'deadline_monotonic':time.monotonic()+120,
                                            'checks':0,'last_final_receipt':None})
                write_json(root/'manifest.json',{'status':'settled','elapsed_seconds':1})
                host = Host(root)
                path = 'main.lean' if language=='lean' else 'main.lit'
                source = ("namespace AuditFixture\ntheorem identity' (n : Nat) : n = n := by rfl\nend AuditFixture\n"
                          if language=='lean' else 'thm audit_identity:\n    ? forall x R:\n        x = x\n    x = x\n')
                symbol = "AuditFixture.identity'" if language=='lean' else 'audit_identity'
                source=assemble_final(job,source)
                host.dispatch('write_source',{'path':path,'content':source})
                host.dispatch('write_source',{'path':'interfaces.json','content':'{}'})
                receipt = host.dispatch('check',{'path':path,'mode':'final'})
                self.assertTrue(receipt['passed'],receipt)
                host.dispatch('submit',{'submission':{
                    'task_id':'TOOL.SMOKE','language':language,'agent_claim':'complete','source_files':[path],
                    'interfaces_file':'interfaces.json','final_receipt_id':receipt['receipt_id'],
                    'clause_mapping':[{'clause_id':'toy','declarations':[symbol],'explanation':'test only'}],
                    'dependencies':[],'assumptions':[],'unfinished':[],
                }})
                checked = audit(root)
                self.assertEqual(checked['machine_status'],'pass',checked)
                self.assertEqual(checked['proof_assumption_status'],'pass',checked)
                self.assertEqual(checked['semantic_status'],'pending')
                (root/'work'/path).write_text(source+'\n')
                stale = audit(root)
                self.assertEqual(stale['machine_status'],'fail')
                self.assertIn('differs',stale['errors'][0])


if __name__=='__main__':
    unittest.main()
