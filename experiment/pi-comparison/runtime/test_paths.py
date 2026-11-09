"""Relocation checks independent of compiler availability and credentials."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


class PortablePathsControls(unittest.TestCase):
    def test_self_contained_bundle_detection_and_explicit_overrides(self):
        with tempfile.TemporaryDirectory() as temporary:
            bundle=Path(temporary).resolve()/'bundle'
            runtime=bundle/'litex-Stoicheia/experiment/pi-comparison/runtime';runtime.mkdir(parents=True)
            for name in ('Lean','LitexGeo','pi','repl'):(bundle/name).mkdir()
            shutil.copyfile(Path(__file__).parent/'paths.py',runtime/'paths.py')
            env={k:v for k,v in os.environ.items() if not k.startswith('EUCLID_') and not k.endswith('_API_KEY')}
            code='import json;from paths import WORKSPACE,PI,REPL;print(json.dumps([str(WORKSPACE),str(PI),str(REPL)]))'
            result=subprocess.run([sys.executable,'-c',code],cwd=runtime,env=env,capture_output=True,text=True,check=True)
            self.assertEqual(json.loads(result.stdout),[str(bundle),str(bundle/'pi'),str(bundle/'repl/.lake/build/bin/repl')])
            env.update(EUCLID_WORKSPACE=str(bundle/'other'),EUCLID_PI_CHECKOUT=str(bundle/'fixed-pi'),EUCLID_LEAN_REPL=str(bundle/'fixed-repl'))
            result=subprocess.run([sys.executable,'-c',code],cwd=runtime,env=env,capture_output=True,text=True,check=True)
            self.assertEqual(json.loads(result.stdout),[str(bundle/'other'),str(bundle/'fixed-pi'),str(bundle/'fixed-repl')])


if __name__=='__main__':unittest.main()
