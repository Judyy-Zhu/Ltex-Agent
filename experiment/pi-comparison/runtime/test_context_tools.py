"""Own-language lookup and durable context prevent ceremonial reread loops."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from prepare import prepare_job,write_json
from tool_host import Host,execute


class ContextToolControls(unittest.TestCase):
    def host(self,root,language):
        job=prepare_job(root,language,None,smoke=True,max_checks=None,check_timeout=None,
                        max_rounds=5,checkpoint_resume=True,auto_finalize=True)
        extension='lean' if language=='lean' else 'lit'
        body='def priorValue : Nat := 2\n' if language=='lean' else 'have priorValue R = 2\n'
        parts=root/'input/library-parts';parts.mkdir();path=parts/('prior.'+extension);path.write_text(body)
        metadata={'name':'priorValue','type':'Nat' if language=='lean' else 'R'}
        entry={'task_id':'PRIOR','file':path.name,'sha256':hashlib.sha256(body.encode()).hexdigest(),
               'symbols':['priorValue'],'interfaces':{'declarations':{'priorValue':metadata}}}
        job['library']={'index':{'entries':[entry]}}
        write_json(root/'job.json',job)
        write_json(root/'state.json',{'checks':0,'deadline_monotonic':None,'last_final_receipt':None})
        return Host(root),body,metadata

    def test_real_symbol_lookup_returns_source_native_signature_and_seed_not_false_missing(self):
        with tempfile.TemporaryDirectory() as temporary:
            for language in ('lean','litex'):
                root=Path(temporary)/language;host,body,metadata=self.host(root,language)
                try:
                    value=host.dispatch('read_library',{'symbols':['priorValue','geo_vec','missingValue']})
                    self.assertEqual(value['selected_entries']['PRIOR'],body)
                    self.assertEqual(value['symbol_matches']['priorValue']['native_metadata'],metadata)
                    self.assertIn('priorValue',value['accepted_geometry_symbols'])
                    self.assertIn('geo_vec',value['seed_symbol_matches'])
                    self.assertEqual(value['unresolved_symbols'],['missingValue'])
                    self.assertEqual(value['seed_source'],Path(host.job['seed_path']).read_text())
                    self.assertTrue(value['library_is_loaded_in_verifier'])
                finally:host.close()

    def test_read_history_and_retrieved_signatures_survive_without_changing_work_hashes(self):
        with tempfile.TemporaryDirectory() as temporary:
            for language in ('lean','litex'):
                root=Path(temporary)/language;host,body,metadata=self.host(root,language)
                try:
                    before=host.hashes()
                    for _ in range(3):
                        execute(host,'read_input',{'path':'seed-interface.json'})
                        execute(host,'read_docs',{'topic':'logic'})
                        execute(host,'read_library',{'symbols':['priorValue']})
                    memory=json.loads((root/'context-memory.json').read_text())
                    self.assertEqual(memory['read_inputs'],['seed-interface.json'])
                    self.assertEqual(memory['read_docs'],['logic'])
                    self.assertEqual(memory['library_queries'],[['priorValue']])
                    self.assertEqual(memory['symbol_metadata']['priorValue']['native_metadata'],metadata)
                    self.assertEqual(memory['last_retrieved_library_source']['source'],body)
                    self.assertEqual(before,host.hashes())
                finally:host.close()

    def test_wrong_input_path_explains_work_file_tool_instead_of_sending_agent_to_missing_input(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)/'litex';host,_,_=self.host(root,'litex')
            try:
                host.dispatch('write_source',{'path':'candidate.lit','content':'have currentValue R = 2\n',
                                              'item_id':'obsolete-helper','item_kind':'proof'})
                self.assertEqual(host.items.lookup('candidate.lit'),host.job['primary_item_id'])
                result=execute(host,'read_input',{'path':'candidate.lit'})
                self.assertTrue(result['isError']);self.assertIn('read_library',result['details']['error'])
                self.assertIn('file:candidate.lit',result['details']['error'])
            finally:host.close()


if __name__=='__main__':unittest.main()
