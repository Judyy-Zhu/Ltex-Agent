"""Paired reference coverage, indexed retrieval and actual checked teaching examples."""
import hashlib
import json
from pathlib import Path
import re
import tempfile
import unittest

from prepare import BASE,KIT,prepare_job,write_json
from doc_sections import sections
from tool_host import Host,execute


class AlignedGuideControls(unittest.TestCase):
    def test_same_chapter_ids_topics_example_categories_and_bounded_size_difference(self):
        curriculum=json.loads((KIT/'guides/paired-curriculum.json').read_text())
        pair={language:sections((KIT/'guides'/filename).read_text()) for language,filename in curriculum['runtime_core_files'].items()}
        self.assertEqual(len(pair['lean']),18)
        self.assertEqual([(s['id'],s['title']) for s in pair['lean']],[(s['id'],s['title']) for s in pair['litex']])
        self.assertEqual([s['section'] for s in curriculum['sections']],[s['id'] for s in pair['lean']])
        totals={language:sum(s['characters'] for s in values) for language,values in pair.items()}
        self.assertLess(max(totals.values())/min(totals.values()),1.15)
        for left,right,row in zip(pair['lean'],pair['litex'],curriculum['sections']):
            self.assertEqual(left['characters'],row['lean_characters'])
            self.assertEqual(right['characters'],row['litex_characters'])
            self.assertLess(max(left['characters'],right['characters'])/min(left['characters'],right['characters']),1.5)
            self.assertEqual(len(re.findall(r'^```lean\n',left['text'],re.M)),len(re.findall(r'^```lit\n',right['text'],re.M)))
        for filename,digest in curriculum['source_references'].items():
            self.assertEqual(hashlib.sha256((KIT/'guides'/filename).read_bytes()).hexdigest(),digest)

    def test_frozen_core_retrieval_uses_same_ids_and_does_not_mount_legacy_reference(self):
        with tempfile.TemporaryDirectory() as temporary:
            for language in ('lean','litex'):
                root=Path(temporary)/language
                job=prepare_job(root,language,None,smoke=True,max_checks=None,check_timeout=None,max_rounds=5,
                    checkpoint_resume=True,auto_finalize=True,compact_protocol=True)
                write_json(root/'state.json',{'checks':0,'last_final_receipt':None,'deadline_monotonic':None})
                host=Host(root)
                try:
                    guide=Path(job['docs']['core']).read_text()
                    listing=host.dispatch('read_docs',{'topic':'core'})
                    self.assertEqual(len(listing['sections']),18)
                    self.assertNotIn('text',listing['sections'][1])
                    part=host.dispatch('read_docs',{'topic':'core','section':'s11'})
                    self.assertEqual(part['title'],'11. Existential witnesses and their properties')
                    self.assertNotEqual(part['text'],guide)
                    batch=host.dispatch('read_docs',{'topic':'core','sections':['s06','s11']})
                    self.assertEqual([v['id'] for v in batch['sections']],['s06','s11'])
                    found=host.dispatch('read_docs',{'topic':'core','query':'existential witness'})
                    self.assertIn('s11',[v['id'] for v in found['sections']])
                    self.assertEqual(host.dispatch('read_docs',{'topic':'core','section':'all'})['text'],guide)
                    self.assertEqual(Path(job['docs']['core']).name,'core.md')
                    self.assertFalse(any('original' in k or 'legacy' in k for k in job['docs']))
                finally:host.close()

    def test_every_example_in_the_new_core_passes_both_real_kernels_and_final_gate(self):
        with tempfile.TemporaryDirectory() as temporary:
            for language in ('lean','litex'):
                root=Path(temporary)/language
                job=prepare_job(root,language,None,smoke=True,max_checks=None,check_timeout=None,max_rounds=5,
                    checkpoint_resume=True,auto_finalize=True,compact_protocol=True)
                job.update(item_tracking_required=True,require_submission_gate=True,required_clause_ids=['source_content','encoding'])
                write_json(root/'job.json',job)
                write_json(root/'state.json',{'checks':0,'last_final_receipt':None,'deadline_monotonic':None})
                text=Path(job['docs']['core']).read_text()
                code='\n\n'.join(re.findall(r'```(?:lean|lit)\n(.*?)```',text,re.S))
                self.assertIn('guide_witness',code);self.assertIn('guide_root',code)
                host=Host(root)
                try:
                    result=execute(host,'submit_candidate',{'code':code},'aligned-guide-examples')
                    self.assertTrue(result['details'].get('task_completed'),result)
                    self.assertEqual(host.rounds.summary()['used'],1)
                    self.assertTrue(json.loads((root/'submission-gate.json').read_text())['passed'])
                finally:host.close()


if __name__=='__main__':unittest.main()
