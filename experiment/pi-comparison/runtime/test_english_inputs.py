"""English task/prompt coverage and real controller tool boundaries, offline."""
import json
from pathlib import Path
import tempfile
import time
import unittest
from agent_language import require_english,english_record
from task_inputs import catalog,specification,required_clauses
from prompts import build_prompts
from prepare import BASE,KIT,prepare_job,write_json
from tool_host import Host,execute


class EnglishInputControls(unittest.TestCase):
    def test_all_644_task_specs_records_and_prompt_pairs_are_english(self):
        rows,_=catalog();self.assertEqual(len(rows),644)
        for record in rows:
            localized=english_record(record);spec=specification(record)
            require_english(localized);require_english(spec)
            self.assertEqual(localized['source_span'],record['source_span'])
            self.assertFalse(any(name.endswith('_zh') for name in localized))
            self.assertEqual(spec['instruction_language'],'en')
            self.assertEqual(spec['success_policy']['criterion'],'machine_verification')
            self.assertFalse(spec['success_policy']['semantic_review_required'])
            self.assertEqual(required_clauses(spec),['C1','C2','C3','C4','C5'] if record['id']=='EUCLID.I.P001' else ['source_content','encoding'])
            prompts=[]
            for language in ('lean','litex'):
                job={'language':language,'task_id':record['id'],'primary_item_id':record['id']+':main',
                     'primary_item_kind':'definition' if record['kind']=='definition' else 'proof'}
                system,user=build_prompts(job)
                require_english(system);require_english(user);prompts.append(user)
            self.assertEqual(prompts[0],prompts[1])

    def test_all_agent_guides_seeds_and_prepared_inputs_are_english(self):
        require_english((BASE/'runtime/tools.ts').read_text(),'Actual tool definitions')
        for folder in (KIT,BASE/'seeds'):
            for path in folder.rglob('*'):
                if path.is_file() and path.suffix in ('.md','.txt','.json','.lean','.lit','.py') and '__pycache__' not in path.parts:
                    require_english(path.read_text(),str(path))
        with tempfile.TemporaryDirectory() as temporary:
            for language in ('lean','litex'):
                root=Path(temporary)/language;job=prepare_job(root,language,60,smoke=True)
                self.assertEqual(job['instruction_language'],'en')
                require_english(job)
                for folder in (root/'input',root/'docs'):
                    for path in folder.rglob('*'):
                        if path.is_file():require_english(path.read_text(),str(path))
                for text in build_prompts(job,smoke=True):require_english(text)

    def test_non_english_tool_content_is_rejected_without_kernel_or_api_calls(self):
        non_english='\u4e2d\u6587'
        with tempfile.TemporaryDirectory() as temporary:
            for language in ('lean','litex'):
                root=Path(temporary)/language;prepare_job(root,language,60,smoke=True)
                write_json(root/'state.json',{'checks':0,'deadline_monotonic':time.monotonic()+60})
                host=Host(root)
                try:
                    for path,content in [('interfaces.json',json.dumps({'meaning':non_english},ensure_ascii=False)),
                                         ('bad.lean' if language=='lean' else 'bad.lit',non_english)]:
                        result=execute(host,'write_source',{'path':path,'content':content})
                        self.assertTrue(result['isError']);require_english(result)
                        self.assertFalse((root/'work'/path).exists())
                    (root/'input/unexpected.txt').write_text(non_english)
                    result=execute(host,'read_input',{'path':'unexpected.txt'})
                    self.assertTrue(result['isError']);require_english(result)
                    result=execute(host,'submit',{'submission':{'task_id':'TOOL.SMOKE','language':language,'assumptions':[non_english]}})
                    self.assertTrue(result['isError']);require_english(result)
                    self.assertEqual(host.state['checks'],0)
                    self.assertIsNone(host.ledger.native)
                finally:host.close()


if __name__=='__main__':unittest.main()
