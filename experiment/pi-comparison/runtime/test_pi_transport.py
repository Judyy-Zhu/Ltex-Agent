"""Run actual Pi extension dispatch offline, without provider credentials."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from prepare import BASE,PI,prepare_job,write_json
from agent_language import require_english


class PiTransportControls(unittest.TestCase):
    def test_single_task_runner_lifecycle_offline(self):
        with tempfile.TemporaryDirectory(prefix='pi-runner-offline-') as temporary:
            for language in ('lean','litex'):
                root=Path(temporary)/language;prepare_job(root,language,120,smoke=True)
                result=subprocess.run([sys.executable,str(BASE/'runtime/run.py'),'--language',language,
                                       '--prepared-root',str(root),'--smoke','--offline-probe'],
                                      cwd=BASE,capture_output=True,text=True,timeout=150)
                self.assertEqual(result.returncode,0,result.stdout+'\n'+result.stderr)
                manifest=json.loads((root/'manifest.json').read_text())
                self.assertTrue(manifest['machine_checked_candidate'])
                self.assertEqual(manifest['model_config']['providers']['paratera']['models'][0]['input'],['text'])
                self.assertEqual(manifest['input_modality'],'text_only')
                self.assertFalse(manifest['images_allowed'])
                self.assertEqual(manifest['instruction_language'],'en')
                require_english((root/'system-prompt.txt').read_text())
                self.assertEqual((root/'user-prompt.txt').read_text(),'/offline-transport-probe')
                self.assertEqual(manifest['usage']['summary']['request_attempts'],0)
                self.assertFalse((root/'provider.jsonl').exists())

    def test_both_languages_through_real_pi_tools_without_model_calls(self):
        receipt={'scope':'actual Pi extension transport; deterministic local fixtures; no model calls','checks':[]}
        with tempfile.TemporaryDirectory(prefix='pi-native-transport-') as temporary:
            for language in ('lean','litex'):
                root=Path(temporary)/language;prepare_job(root,language,120,smoke=True)
                write_json(root/'state.json',{'deadline_monotonic':time.monotonic()+120,
                                            'checks':0,'last_final_receipt':None})
                models=json.loads((BASE/'models.smoke.json').read_text())
                models['providers']['paratera']['models'][0]['input']=['text']
                write_json(root/'pi-state/models.json',models)
                write_json(root/'pi-state/settings.json',{'retry':{'enabled':False},'compaction':{'enabled':False}})
                env=dict(os.environ)
                for key in list(env):
                    if key.endswith('_API_KEY'):del env[key]
                env.update(PI_CODING_AGENT_DIR=str(root/'pi-state'),EUCLID_RUN_ROOT=str(root),
                           EUCLID_PYTHON=sys.executable,EUCLID_TEST_LANGUAGE=language,
                           PARATERA_API_KEY='offline-fixture-never-transmitted')
                command=['bash',str(PI/'pi-test.sh'),'--mode','rpc','--offline','--no-session',
                         '--no-extensions','--no-skills','--no-mcp','--no-context-files','--no-prompt-templates',
                         '--no-approve','-e',str(BASE/'runtime/offline_transport_probe.ts'),
                         '--provider','paratera','--model','DeepSeek-V4.1-Flash',
                         '--tools','read_input,read_docs,read_library,write_source,check,remaining_budget,submit']
                with (root/'stdout.log').open('w') as stdout,(root/'stderr.log').open('w') as stderr:
                    process=subprocess.Popen(command,cwd=root/'work',env=env,stdin=subprocess.PIPE,stdout=stdout,stderr=stderr,text=True)
                    try:
                        process.stdin.write(json.dumps({'id':'offline','type':'prompt','message':'/offline-transport-probe'})+'\n')
                        process.stdin.flush()
                        deadline=time.monotonic()+90
                        while not (root/'offline-pi.json').exists() and process.poll() is None and time.monotonic()<deadline:
                            time.sleep(.05)
                        self.assertTrue((root/'offline-pi.json').exists(),
                                        (root/'stderr.log').read_text()+'\n'+(root/'stdout.log').read_text()[-3000:])
                        result=json.loads((root/'offline-pi.json').read_text())
                        self.assertTrue(result['passed']);self.assertTrue(result['image_payload_guard']);receipt['checks'].append(result)
                        self.assertFalse((root/'provider.jsonl').exists(),'Unexpected model request')
                    finally:
                        if process.poll() is None:process.terminate()
                        try:process.wait(timeout=5)
                        except subprocess.TimeoutExpired:process.kill();process.wait()
                        process.stdin.close()
        receipt['result']='passed'
        write_json(BASE/'runtime/pi-transport-receipt.json',receipt)


if __name__=='__main__':unittest.main()
