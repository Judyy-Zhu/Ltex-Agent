"""Controller-owned declaration and transitive-axiom checks within task budget."""
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time
from budgets import until,timeout_seconds,remaining


def safe_symbol(name):
    return isinstance(name,str) and len(name)<=250 and bool(re.fullmatch(r"[^\W\d][\w']*(?:\.[^\W\d][\w']*)*",name,re.UNICODE))


def litex_declarations(parsed):
    names=set()
    for item in parsed.get('statement_results',[]):
        if item.get('statement_result')!='accepted':continue
        match=re.match(r'(?:thm|prop|have fn|have)\s+([^\s(:]+)',item.get('statement',''))
        if match:names.add(match[1])
    return names


def validate(job,source,symbols,deadline):
    if not symbols or not all(safe_symbol(name) for name in symbols):
        raise ValueError('Complete task requires valid mapped declaration names')
    deadline=until({'deadline_monotonic':deadline},job)
    seconds=timeout_seconds(deadline)
    if seconds is not None and seconds<=0:raise ValueError('No task time remains for submission gate')
    env={k:v for k,v in os.environ.items() if not k.endswith('_API_KEY')}
    with tempfile.TemporaryDirectory(prefix='euclid-submission-gate-') as temporary:
        path=Path(temporary)/('Gate.lean' if job['language']=='lean' else 'Gate.lit')
        if job['language']=='lean':
            path.write_text(source+'\n\n'+'\n'.join(f'#check {n}\n#print axioms {n}' for n in symbols)+'\n')
            command=[job['lake'],'env','lean',str(path)];cwd=job['lean_project']
        else:
            path.write_text(source);command=[job['litex'],'-strict','-lang','en','-f',str(path)];cwd=temporary
        result=subprocess.run(command,cwd=cwd,env=env,capture_output=True,text=True,timeout=seconds)
    gate={'passed':False,'exit_code':result.returncode,'stdout':result.stdout,'stderr':result.stderr,'symbols':symbols}
    if job['language']=='lean':
        found={m[1]:[v.strip() for v in m[2].split(',') if v.strip()]
               for m in re.finditer(r"'([^\n]+)' depends on axioms:\s*\[([^\]]*)\]",result.stdout,re.S)}
        for m in re.finditer(r"'([^\n]+)' does not depend on any axioms",result.stdout):found[m[1]]=[]
        missing=sorted(set(symbols)-found.keys())
        bad=sorted({a for values in found.values() for a in values}-set(job['foundation']['standard_logical_axioms']))
        gate.update(declaration_axioms=found,missing_declarations=missing,unapproved_axioms=bad)
        gate['passed']=result.returncode==0 and not missing and not bad
    else:
        import json
        parsed=json.loads(result.stdout);missing=sorted(set(symbols)-litex_declarations(parsed))
        gate.update(native=parsed,missing_declarations=missing)
        gate['passed']=(result.returncode==0 and parsed.get('kind')=='run' and parsed.get('run_result')=='success'
                        and not parsed.get('errors') and not parsed.get('session_terminated')
                        and parsed.get('termination') is None and not missing)
    gate['passed']=bool(gate['passed'] and time.monotonic()<deadline)
    return gate
