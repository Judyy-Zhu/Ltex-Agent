#!/usr/bin/env python3
"""Check small paired teaching examples and important rejection boundaries.

This is an offline language/adapter preparation check, not a theorem benchmark.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import time

ROOT=Path(__file__).resolve().parent
WORKSPACE=ROOT.parents[5]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lean-project',type=Path,default=WORKSPACE/'Lean')
    parser.add_argument('--lake',type=Path,default=Path.home()/'.elan/bin/lake')
    parser.add_argument('--litex',type=Path,default=WORKSPACE/'LitexGeo/golitex/target/release/litex')
    args=parser.parse_args()
    receipt={'observed_at':datetime.now(timezone.utc).isoformat(),
             'scope':'small guide examples only; no model or Euclid proof run','checks':[]}

    def run(name,command,cwd,stdin=None):
        start=time.monotonic()
        result=subprocess.run([str(x) for x in command],cwd=cwd,input=stdin,capture_output=True,text=True,timeout=45)
        entry={'name':name,'exit_code':result.returncode,'seconds':round(time.monotonic()-start,3),
               'stdout':result.stdout,'stderr':result.stderr}
        receipt['checks'].append(entry)
        return entry

    def litex_pass(entry):
        try: r=json.loads(entry['stdout'])
        except ValueError: return False
        return entry['exit_code']==0 and r.get('run_result')=='success' and not r.get('errors') and not r.get('session_terminated') and r.get('termination') is None

    litex_hash=hashlib.sha256(args.litex.read_bytes()).hexdigest()
    with tempfile.TemporaryDirectory(prefix='euclid-guide-smoke-') as tmp:
        tmp=Path(tmp)
        lean=run('lean_paired_basics',[args.lake,'env','lean',ROOT/'examples/basics.lean'],args.lean_project)
        assert lean['exit_code']==0 and not lean['stdout'].strip() and not lean['stderr'].strip(), lean
        litex=run('litex_paired_basics',[args.litex,'-strict','-f',ROOT/'examples/basics.lit'],tmp)
        assert litex_pass(litex),litex
        bad_lean=tmp/'false.lean';bad_lean.write_text('theorem training_false : (2 : Nat) + 2 = 5 := by decide\n')
        bad_litex=tmp/'false.lit';bad_litex.write_text('2 + 2 = 5\n')
        lean_false=run('lean_false_rejected',[args.lake,'env','lean',bad_lean],args.lean_project)
        litex_false=run('litex_false_rejected',[args.litex,'-strict','-f',bad_litex],tmp)
        assert lean_false['exit_code']!=0
        assert litex_false['exit_code']!=0 and not litex_pass(litex_false)
        placeholder=tmp/'placeholder.lean'
        placeholder.write_text('theorem training_gap : (2 : Nat) + 2 = 5 := by sorry\n#print axioms training_gap\n')
        gap=run('lean_sorry_requires_extra_guard',[args.lake,'env','lean',placeholder],args.lean_project)
        assert gap['exit_code']==0 and 'sorryAx' in gap['stdout'],gap
        ax=tmp/'axiom.lit';ax.write_text('axiom training_gap:\n    ? forall x R:\n        x = x + 1\n')
        ax_result=run('litex_strict_axiom_rejected',[args.litex,'-strict','-f',ax],tmp)
        assert ax_result['exit_code']!=0 and not litex_pass(ax_result),ax_result
        version=run('lean_version',[args.lake,'env','lean','--version'],args.lean_project)
        litex_version=run('litex_version',[args.litex,'-version'],tmp)
        receipt['versions']={'lean':version['stdout'].strip(),'litex':litex_version['stdout'].strip()}
    assert hashlib.sha256(args.litex.read_bytes()).hexdigest()==litex_hash,'Litex binary changed during checks'
    receipt['litex_sha256']=litex_hash
    receipt['example_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'examples').glob('basics.*')}
    receipt['result']='passed'
    receipt['limitations']=['Only basic tutorial constructs tested, not all guide claims.',
                            'No Lean REPL/Pi integration test in this receipt.',
                            'Compiler acceptance is not source-fidelity scoring.']
    (ROOT/'smoke-receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'result':'passed','checks':len(receipt['checks']),'versions':receipt['versions']},ensure_ascii=False))


if __name__=='__main__': main()
