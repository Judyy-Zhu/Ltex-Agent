#!/usr/bin/env bash
# Offline server acceptance and plan preparation. Never start batch run/resume.
set -euo pipefail
bundle_root="$(cd "${1:?Usage: verify_linux.sh BUNDLE_ROOT}" && pwd)"
source "$bundle_root/server-env.sh"
experiment="$bundle_root/litex-Stoicheia/experiment/pi-comparison"
cd "$experiment"
python runtime/verify_sessions.py
python -m unittest -v test_audit_candidate.py agent-kit/tests/test_usage_accounting.py
if [[ ! -f batches/full-01/plan.json ]]; then
  python runtime/batch.py prepare --name full-01 --books all --seconds 1200 --run-hours 500 --source-cache "$bundle_root/source-cache"
fi
python runtime/batch.py preflight --name full-01
python runtime/batch.py status --name full-01 > "$bundle_root/deploy-logs/full-01-status.json"
python - "$bundle_root" <<'PY'
from datetime import datetime,timezone
import hashlib,json,os,platform,stat,subprocess,sys
from pathlib import Path
root=Path(sys.argv[1]);exp=root/'litex-Stoicheia/experiment/pi-comparison'
def output(args,cwd=None):return subprocess.check_output(args,cwd=cwd,text=True).strip()
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
state=json.loads((exp/'batches/full-01/state.json').read_text())
regression=json.loads((exp/'runtime/session-controls-receipt.json').read_text())
assert regression['passed'] and regression['model_calls']==0
assert state['status']=='prepared' and not state['records'],'Deployment must not start model tasks'
credential=exp/'private/api_config.json'
receipt={'completed_at':datetime.now(timezone.utc).isoformat(),'platform':platform.platform(),
 'bundle_root':str(root),'model_api_calls':0,'batch_status':state['status'],'model_tasks_started':0,
 'regression_tests':regression['tests_run'],'regression_passed':regression['passed'],
 'litex_version':output([os.environ['EUCLID_LITEX'],'--version']),
 'litex_commit':output(['git','rev-parse','HEAD'],root/'LitexGeo/golitex'),
 'litex_binary_sha256':sha(Path(os.environ['EUCLID_LITEX'])),
 'lean_version':output([str(root/'.tools/lean-4.35.0-linux/bin/lean'),'--version']),
 'repl_binary_sha256':sha(Path(os.environ['EUCLID_LEAN_REPL'])),
 'mathlib_commit':output(['git','rev-parse','HEAD'],root/'Lean/.lake/packages/mathlib'),
 'pi_commit':output(['git','rev-parse','HEAD'],root/'pi'),'node_version':output(['node','--version']),
 'credential_present':credential.exists(),
 'credential_mode':oct(stat.S_IMODE(credential.stat().st_mode)) if credential.exists() else None,
 'plan_sha256':sha(exp/'batches/full-01/plan.json')}
(root/'deployment-receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(receipt,ensure_ascii=False,indent=2))
PY
