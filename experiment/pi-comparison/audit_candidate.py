#!/usr/bin/env python3
"""Independent postrun machine/assumption audit, never a source-fidelity oracle.

Audit time is reported separately from the already frozen solver interval.
It cannot repair a submission or turn a development run into a formal result.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

BASE = Path(__file__).resolve().parent


def read_json(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe_symbol(name):
    return isinstance(name,str) and len(name)<=250 and bool(
        re.fullmatch(r"[^\W\d][\w']*(?:\.[^\W\d][\w']*)*",name,re.UNICODE))


def parse_axioms(stdout, symbols):
    found = {}
    for match in re.finditer(r"'([^\n]+)' depends on axioms:\s*\[([^\]]*)\]",stdout,re.S):
        found[match[1]] = [value.strip() for value in match[2].split(',') if value.strip()]
    for match in re.finditer(r"'([^\n]+)' does not depend on any axioms",stdout):
        found[match[1]] = []
    missing = sorted(set(symbols)-found.keys())
    return found,missing


def audit(root):
    start = time.monotonic()
    root = Path(root).resolve()
    result = {'run_id':root.name,'observed_at':datetime.now(timezone.utc).isoformat(),
              'scope':'postrun_development_audit','formal_result':False,
              'machine_status':'fail','proof_assumption_status':'pending',
              'foundation_equivalence_status':'pending','semantic_status':'pending',
              'errors':[]}
    folder = root/'audit'; folder.mkdir(exist_ok=True)
    try:
        manifest = read_json(root/'manifest.json')
        if manifest['status']=='running':
            raise ValueError('Cannot audit an active run')
        if not (root/'submission.json').exists():
            result.update(machine_status='no_submission',proof_assumption_status='not_audited')
            return result
        submission = read_json(root/'submission.json')
        job = read_json(root/'job.json')
        if submission['agent_claim']!='complete':
            result.update(machine_status='incomplete_submission',proof_assumption_status='not_audited')
            return result
        if submission['task_id']!=job['task_id'] or submission['language']!=job['language']:
            raise ValueError('Submission identity mismatch')
        rid = submission['final_receipt_id']
        if not re.fullmatch(r'check-\d{4,}',rid or ''):
            raise ValueError('Invalid final receipt ID')
        receipt = read_json(root/'receipts'/f'{rid}.json')
        if receipt['mode']!='final' or not receipt['passed']:
            raise ValueError('Missing successful final receipt')
        actual = {str(p.relative_to(root/'work')):sha(p) for p in sorted((root/'work').rglob('*')) if p.is_file()}
        if receipt['source_hashes']!=actual:
            raise ValueError('Saved source differs from final receipt')
        spec = importlib.util.spec_from_file_location('benchmark_host',BASE/'runtime/tool_host.py')
        if str(BASE/'runtime') not in sys.path:
            sys.path.insert(0,str(BASE/'runtime'))
        host = importlib.util.module_from_spec(spec); spec.loader.exec_module(host)
        from seed_support import require_seed_prefix
        path = host.bounded(root/'work',receipt['entry'])
        if receipt['entry'] not in submission['source_files']:
            raise ValueError('Checked entry not submitted')
        source = path.read_text()
        require_seed_prefix(job,source)
        host.source_guard(source,job['language'],job['foundation'].get('allowed_imports',[]))
        symbols = sorted({name for clause in submission['clause_mapping'] for name in clause['declarations']})
        if not symbols or not all(safe_symbol(name) for name in symbols):
            raise ValueError('Mapped declarations must be valid qualified identifiers')
        clauses = {c['clause_id'] for c in submission['clause_mapping'] if c['declarations']}
        if not set(job['required_clause_ids']).issubset(clauses):
            raise ValueError('Required clauses missing')
        result.update(source_hashes=actual,mapped_symbols=symbols,final_receipt_id=rid,
                      solver_elapsed_seconds=manifest['elapsed_seconds'])
        env = dict(os.environ)
        for key in list(env):
            if key.endswith('_API_KEY'):
                del env[key]
        if job['language']=='lean':
            suffix = '\n\n'+'\n'.join(f'#check {name}\n#print axioms {name}' for name in symbols)+'\n'
            with tempfile.TemporaryDirectory(prefix='euclid-postrun-audit-') as temporary:
                audited = Path(temporary)/'CandidateAudit.lean'
                audited.write_text(source+suffix)
                process = subprocess.run([job['lake'],'env','lean',str(audited)],cwd=job['lean_project'],
                                         env=env,capture_output=True,text=True,timeout=180)
            result.update(exit_code=process.returncode,stdout=process.stdout,stderr=process.stderr)
            axioms,missing = parse_axioms(process.stdout,symbols)
            allowed = set(job['foundation']['standard_logical_axioms'])
            unapproved = sorted({axiom for values in axioms.values() for axiom in values}-allowed)
            result.update(declaration_axioms=axioms,missing_axiom_reports=missing,unapproved_axioms=unapproved)
            result['machine_status'] = 'pass' if process.returncode==0 and not missing else 'fail'
            result['proof_assumption_status'] = 'pass' if result['machine_status']=='pass' and not unapproved else 'fail'
        else:
            if sha(Path(job['litex']))!=job['foundation']['binary_sha256']:
                raise ValueError('Litex binary changed since run preparation')
            process = subprocess.run([job['litex'],'-strict','-lang','en','-f',str(path)],cwd=root/'work',
                                     env=env,capture_output=True,text=True,timeout=180)
            result.update(exit_code=process.returncode,stdout=process.stdout,stderr=process.stderr)
            parsed = json.loads(process.stdout)
            declarations = set()
            for item in parsed.get('statement_results',[]):
                if item.get('statement_result')!='accepted':
                    continue
                match = re.match(r'(?:thm|prop|have fn|have)\s+([^\s(:]+)',item.get('statement',''))
                if match:
                    declarations.add(match[1])
            missing = sorted(set(symbols)-declarations)
            passed = (process.returncode==0 and parsed.get('kind')=='run' and parsed.get('run_result')=='success'
                      and not parsed.get('errors') and not parsed.get('session_terminated')
                      and parsed.get('termination') is None and not missing)
            result.update(machine_status='pass' if passed else 'fail',missing_declarations=missing,
                          proof_assumption_status='pass' if passed else 'fail',
                          assumption_scope='Fixed native verifier, strict and source guard; foundational equivalence remains pending.')
    except (ValueError,KeyError,OSError,subprocess.TimeoutExpired) as error:
        result['errors'].append(str(error))
        result['machine_status'] = 'fail'
    finally:
        result['audit_seconds'] = time.monotonic()-start
        (folder/'machine.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run',type=Path)
    args = parser.parse_args()
    result = audit(args.run)
    print(json.dumps({key:result[key] for key in ('run_id','machine_status','proof_assumption_status',
                                                'semantic_status','audit_seconds','errors')},ensure_ascii=False))


if __name__=='__main__':
    main()
