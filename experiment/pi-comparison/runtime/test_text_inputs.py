"""Both languages receive text only, including tasks with construction figures."""
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import time
import unittest
from prepare import prepare_job,write_json
from task_inputs import catalog,freeze_sources,copy_text_pack,verify_pack
from tool_host import Host,execute


class TextInputControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary=tempfile.TemporaryDirectory(prefix='euclid-text-controls-')
        cls.root=Path(cls.temporary.name);cls.cache=cls.root/'cache';cls.rows=catalog()[0]
        chosen={'EUCLID.I.D001','EUCLID.I.P001','EUCLID.VII.COR001','EUCLID.XIII.LEM003'}
        tasks=[r for r in cls.rows if r['id'] in chosen];needed=set(chosen)
        for task in tasks:
            needed.update(r['id'] for r in cls.rows if r['book']==task['book'] and
                          r['source_order']<task['source_order'] and r['kind'] in ('definition','postulate','common_notion'))
        freeze_sources(cls.cache,[r for r in cls.rows if r['id'] in needed])

    @classmethod
    def tearDownClass(cls):cls.temporary.cleanup()

    def test_all_task_types_receive_paired_text_and_no_images(self):
        self.assertFalse(list(self.cache.rglob('*.png')))
        for task_id in ('EUCLID.I.D001','EUCLID.I.P001','EUCLID.VII.COR001','EUCLID.XIII.LEM003'):
            folders=[]
            for language in ('lean','litex'):
                folder=self.root/('paired-'+language+'-'+task_id);folders.append(folder)
                job=prepare_job(folder,language,60,task_id=task_id,source_cache=self.cache)
                self.assertEqual(job['input_modality'],'text_only');self.assertFalse(job['images_allowed'])
                manifest=json.loads((folder/'input/source-manifest.json').read_text())
                self.assertEqual(manifest['input_modality'],'text_only')
                self.assertFalse(manifest['images_available'])
                self.assertEqual(manifest['reading_policy']['optional_image_files'],[])
                self.assertFalse(list((folder/'input').glob('*.png')))
                self.assertTrue(all('image' not in item for item in manifest['items']))
            for name in ('source-manifest.json',task_id+'.txt'):
                self.assertEqual((folders[0]/'input'/name).read_bytes(),(folders[1]/'input'/name).read_bytes())

    def test_tools_refuse_even_mistakenly_mounted_images_in_both_languages(self):
        for language in ('lean','litex'):
            root=self.root/('blocked-'+language);prepare_job(root,language,60,smoke=True)
            write_json(root/'state.json',{'checks':0,'deadline_monotonic':time.monotonic()+60})
            (root/'input/source.txt').write_text('Text input works.\n')
            host=Host(root)
            try:
                reply=execute(host,'read_input',{'path':'source.txt'})
                self.assertEqual([part['type'] for part in reply['content']],['text'])
                self.assertEqual(reply['details']['text'],'Text input works.\n')
                for name in ('initial.png','construction.PNG','source.pdf','photo.jpg','drawing.svg'):
                    (root/'input'/name).write_bytes(b'not-for-model-input')
                    reply=execute(host,'read_input',{'path':name})
                    self.assertTrue(reply['isError'])
                    self.assertIn('Text-only',reply['details']['error'])
                    self.assertFalse(any(part['type']=='image' for part in reply['content']))
            finally:host.close()

    def test_old_cache_conversion_copies_only_verified_text(self):
        record=next(r for r in self.rows if r['id']=='EUCLID.I.D001')
        origin=self.root/'legacy';shutil.copytree(self.cache/record['id'],origin)
        pack=json.loads((origin/'pack.json').read_text());pack.pop('format')
        name=record['id']+'-old-screenshot.png';(origin/name).write_bytes(b'old PNG fixture')
        pack['files'][name]=hashlib.sha256((origin/name).read_bytes()).hexdigest()
        pack['items'][0]['image']=name
        (origin/'pack.json').write_text(json.dumps(pack))
        with self.assertRaisesRegex(ValueError,'not text-only'):verify_pack(origin,record)
        target=self.root/'converted';copy_text_pack(origin,target,record)
        converted=verify_pack(target,record)
        self.assertEqual(set(converted['files']),{record['id']+'.txt'})
        self.assertEqual((origin/(record['id']+'.txt')).read_bytes(),(target/(record['id']+'.txt')).read_bytes())
        self.assertFalse(list(target.glob('*.png')))
        (origin/(record['id']+'.txt')).write_text('tampered source')
        with self.assertRaisesRegex(ValueError,'Source pack changed'):
            copy_text_pack(origin,self.root/'invalid-copy',record)


if __name__=='__main__':unittest.main()
