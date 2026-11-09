"""Run the complete registered offline suite in isolated module processes."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

BASE=Path(__file__).resolve().parents[2]
RUNTIME=BASE/'runtime'
sys.path.insert(0,str(RUNTIME))
from verify_sessions import MODULES,hashes
OUT=Path(__file__).resolve().parent
child='''import json,sys,unittest
suite=unittest.defaultTestLoader.loadTestsFromName(sys.argv[1])
result=unittest.TextTestRunner(stream=sys.stderr,verbosity=2).run(suite)
print("OFFLINE_RESULT="+json.dumps({"module":sys.argv[1],"passed":result.wasSuccessful(),"tests_run":result.testsRun,"failures":len(result.failures),"errors":len(result.errors),"skipped":len(result.skipped)}))
raise SystemExit(0 if result.wasSuccessful() else 1)
'''

def run(module):
    env={k:v for k,v in os.environ.items() if not k.endswith('_API_KEY')}
    with (OUT/(module+'.log')).open('w') as stream:
        result=subprocess.run([sys.executable,'-c',child,module],cwd=RUNTIME,env=env,stdout=stream,stderr=subprocess.STDOUT,text=True)
    log=(OUT/(module+'.log')).read_text()
    rows=[json.loads(line.removeprefix('OFFLINE_RESULT=')) for line in log.splitlines() if line.startswith('OFFLINE_RESULT=')]
    if not rows:raise RuntimeError(module+' did not produce a test result; inspect its log')
    row=rows[-1];row['exit_code']=result.returncode
    row['passed']=row['passed'] and result.returncode==0
    return row

before=hashes();started=datetime.now(timezone.utc).isoformat();rows=[]
old=RUNTIME/'session-controls-receipt.json'
if old.exists():shutil.copyfile(old,OUT/'previous-session-controls-receipt.json')
with ThreadPoolExecutor(max_workers=2) as pool:
    futures=[pool.submit(run,module) for module in MODULES]
    for future in as_completed(futures):
        row=future.result();rows.append(row)
        print(json.dumps(row),flush=True)
        (OUT/'full-suite-progress.json').write_text(json.dumps(rows,indent=2)+'\n')
after=hashes()
receipt={'scope':'Complete registered offline native Session/REPL and actual Pi transport suite; no model calls',
 'execution':'Two isolated module subprocesses at a time; each module uses the unchanged unittest suite',
 'technical_seed_id':'real-plane-algebra-v1','started_at':started,'completed_at':datetime.now(timezone.utc).isoformat(),
 'passed':all(r['passed'] for r in rows) and {r['module'] for r in rows}==set(MODULES) and before==after,
 'tests_run':sum(r['tests_run'] for r in rows),'failures':sum(r['failures'] for r in rows),
 'errors':sum(r['errors'] for r in rows),'skipped':sum(r['skipped'] for r in rows),
 'source_unchanged_during_checks':before==after,'source_sha256':before,'model_calls':0,'formal_benchmark_result':False,
 'log':'../validation/proof-layout-fix/full-suite.log','modules':rows}
log='\n\n'.join((OUT/(module+'.log')).read_text() for module in MODULES)
(OUT/'full-suite.log').write_text(log)
(OUT/'full-suite-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
if receipt['passed']:
    old.write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({k:receipt[k] for k in ['passed','tests_run','failures','errors','source_unchanged_during_checks','model_calls']}),flush=True)
raise SystemExit(0 if receipt['passed'] else 1)
