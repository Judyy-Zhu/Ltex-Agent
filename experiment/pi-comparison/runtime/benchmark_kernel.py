#!/usr/bin/env python3
"""Paired checked generic operations, no agent/API/credentials or target answers.

Measure native request-response separately from initialization and fresh files.
This diagnostic complements the full agent experiment; it does not score Euclid.
"""
import argparse
import csv
from datetime import datetime,timezone
import json
from pathlib import Path
import random

from prepare import BASE,prepare_job
from direct_context import procedures
from replay_benchmark import sample,summarize,sha,save
from seed_support import assemble_final

MEANINGS={
 'function_layout':'Define f(x)=x+1; prove f(x)-1=x for every real x.',
 'exist_elimination':'For every real t, extract an existing witness of x=t and provide a witness of y=t.',
 'not_exist':'For every real t, no real x satisfies x=t and x!=t.',
 'coordinate_equality':'Two real coordinate pairs with both corresponding coordinates equal are equal.',
 'predicate_definition':'Define the real predicate x=3.',
 'quantifier_composition':'Define exists t=t0 such that every x>=t has a real successor y=x+1, through named predicates.',
 'sets_membership':'Define a singleton level set, element membership and set inclusion; prove t belongs to its own level set.',
 'parameter_constraints':'Define reciprocal on nonzero real inputs and prove f(x)*x=1 on that domain.',
 'logical_composition':'Define a nonzero disjunction, then conjoin it with a+b=1 through named predicates.'}


def benchmark(output,repetitions=3,warmups=1,patterns=None):
    if repetitions<1 or warmups<0:raise ValueError('Invalid repetition count')
    selected=list(MEANINGS) if patterns is None else patterns
    if not selected or len(set(selected))!=len(selected) or any(k not in MEANINGS for k in selected):raise ValueError('Unknown or duplicate operation')
    output.mkdir(parents=True,exist_ok=False);(output/'samples').mkdir();artifacts={}
    for language in ('litex','lean'):
        root=output/('prepared-'+language)
        job=prepare_job(root,language,None,smoke=True,max_checks=None,check_timeout=None,max_rounds=5,
                        auto_finalize=True,compact_protocol=True,direct_protocol=True)
        collection={p['id']:p['code'] for p in procedures(job)}
        if set(collection)!=set(MEANINGS):raise ValueError('Paired procedure coverage differs')
        for key in selected:
            path=root/'work'/(key+('.lit' if language=='litex' else '.lean'))
            path.write_text(assemble_final(job,collection[key]))
            artifacts[(language,key)]={'job':job,'candidate':collection[key],'final_path':path,'root':root,'final_sha256':sha(path)}
    result={'scope':'native verifier diagnostic on paired generic mathematical operations',
        'source_fidelity':'Not a Euclid translation score; the mathematical specifications of these generic cases are explicit.',
        'model_calls':0,'preparation_model_calls':0,'repetitions':repetitions,'warmups':warmups,
        'meanings':{k:MEANINGS[k] for k in selected},'rows':[],
        'policy':'New native Session/REPL for every sample, no acceptance cache, sequential randomized language order. Initialization, warm candidate and fresh-file checking are separate wall-clock phases. Failures are retained.',
        'runner_sha256':{p.name:sha(p) for p in [Path(__file__),BASE/'runtime/replay_benchmark.py',BASE/'runtime/native_sessions.py']},
        'kernel_sha256':{str(Path(p).resolve()):sha(Path(p)) for v in artifacts.values() for p in ([v['job']['litex']] if v['job']['language']=='litex' else [v['job']['lake'],v['job']['lean_repl'],str(Path(v['job']['lean_project'])/'lean-toolchain'),str(Path(v['job']['lean_project'])/'lake-manifest.json')])},
        'artifacts':[{'language':l,'operation':k,'final_sha256':v['final_sha256'],'path':str(v['final_path'])} for (l,k),v in artifacts.items()]}
    rng=random.Random(20261109)
    for key in selected:
        for number in range(warmups+repetitions):
            order=['lean','litex'];rng.shuffle(order)
            for language in order:
                row={'task_id':key,'language':language,'warmup':number<warmups,'replay_index':number-warmups+1,
                    **sample(artifacts[(language,key)],output/'samples'/f'{len(result["rows"])+1:04}-{language}')}
                result['rows'].append(row);save(output/'results.json',result)
                print(json.dumps({k:row.get(k) for k in ['task_id','language','warmup','passed','session_initialization_seconds','warm_candidate_seconds','fresh_file_seconds']}),flush=True)
    result.update(passed=all(r['passed'] for r in result['rows']),completed_at=datetime.now(timezone.utc).isoformat(),summary=summarize(result['rows']))
    result['per_operation']={k:summarize([r for r in result['rows'] if r['task_id']==k]) for k in selected}
    save(output/'results.json',result)
    with (output/'results.csv').open('w') as stream:
        fields=['task_id','language','warmup','replay_index','passed','session_initialization_seconds','warm_candidate_seconds','fresh_file_seconds']
        writer=csv.DictWriter(stream,fieldnames=fields,extrasaction='ignore');writer.writeheader();writer.writerows(result['rows'])
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--repetitions',type=int,default=3);p.add_argument('--warmups',type=int,default=1)
    p.add_argument('--patterns',help='Optional comma-separated operation IDs; default: all registered operations')
    a=p.parse_args();result=benchmark(a.output.resolve(),a.repetitions,a.warmups,a.patterns.split(',') if a.patterns else None)
    print(json.dumps({'passed':result['passed'],'model_calls':0,'summary':result['summary']}))
    if not result['passed']:raise SystemExit(1)


if __name__=='__main__':main()
