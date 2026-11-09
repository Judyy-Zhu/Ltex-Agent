"""Finish accepted code locally; native receipts, not model-written labels, decide success."""
import json
import time
from budgets import until
from native_sessions import litex_blocks
from native_index import litex_metadata
from seed_support import assemble_final,starting_source
from recovery import save,append_event


def complete(host,candidate_receipt,round_number):
    try:return _complete(host,candidate_receipt,round_number)
    except ValueError as error:
        # A valid snippet with no public library declarations needs a code repair,
        # rather than an unrecoverable local-finalization checkpoint.
        host.rounds.finish(round_number,False,str(error))
        save(host.root/'auto-finalization.json',{'status':'failed','candidate_receipt_id':candidate_receipt['receipt_id'],
                                               'round':round_number,'error':str(error)})
        return {'completed':False,'controller_error':str(error)}


def _complete(host,candidate_receipt,round_number):
    root=host.root;job=host.job
    transaction={'status':'pending','candidate_receipt_id':candidate_receipt['receipt_id'],'round':round_number}
    save(root/'auto-finalization.json',transaction)
    started=time.monotonic()
    # All files are written before the independently saved-file receipt is hashed.
    host.ledger._ensure(until(host.state,job))
    probe=time.monotonic()
    if job['language']=='lean':
        native=host.ledger.native
        all_metadata=native.inspect_declarations(until(host.state,job))
        metadata={n:v for n,v in all_metadata.items() if n not in native.baseline_declarations}
    else:
        results=[]
        for entry in host.ledger.data['entries']:
            if 'native' not in entry:raise ValueError('Accepted native declaration metadata is missing')
            results.extend(entry['native'].get('statement_results',[]))
        metadata=litex_metadata({'statement_results':results},0,len(results))
    probe_seconds=time.monotonic()-probe
    names=sorted(metadata)
    if not names:raise ValueError('Complete task must introduce a public native declaration')
    interfaces={'generated_by':'controller_native_metadata','semantic_status':'pending',
                'source_correspondence':'Automatic task-level association only; source fidelity has not been reviewed.',
                'declarations':metadata}
    save(root/'work/interfaces.json',interfaces)
    extension='lean' if job['language']=='lean' else 'lit'
    final_path='final.'+extension
    source=host.ledger.status(include_source=True)['accepted_source']
    # The current whole candidate, not an accidentally accepted prefix, determines completion.
    candidate=(root/'work'/candidate_receipt['entry']).read_text()
    expected=assemble_final(job,candidate)
    if job['language']=='lean' and source.strip()!=expected.strip():
        raise ValueError('Accepted assembly differs from the complete candidate')
    save_source=root/'work'/final_path
    with save_source.open('w') as stream:
        import os
        stream.write(source);stream.flush();os.fsync(stream.fileno())
    final=host.check({'path':final_path,'mode':'final'})
    receipt=json.loads((root/'receipts'/(final['receipt_id']+'.json')).read_text())
    gate={'passed':False,'symbols':names,'source_hashes':host.hashes(),'final_receipt_id':final['receipt_id'],
          'origin':'reuse_native_acceptance_and_independent_final_receipt','seconds':probe_seconds}
    if job['language']=='lean':
        axioms={n:v['axioms'] for n,v in metadata.items()}
        bad=sorted({a for values in axioms.values() for a in values}-set(job['foundation']['standard_logical_axioms']))
        gate.update(declaration_axioms=axioms,unapproved_axioms=bad,missing_declarations=[])
        gate['passed']=bool(final['passed'] and not bad)
    elif final['passed']:
        if receipt.get('scope')=='independent_final_session':
            # Controller metadata view only; retain original per-turn native
            # responses rather than fabricating a single native file-run JSON.
            responses=receipt['foundation_native']+[f['native'] for f in receipt['native_frames']]
            parsed={'statement_results':[r for response in responses for r in response.get('statement_results',[])]}
            gate['independent_native_frames']=receipt['native_frames']
        else:parsed=json.loads(receipt['stdout'])
        verified=litex_metadata(parsed,len(litex_blocks(starting_source(job))),len(litex_blocks(source)))
        missing=sorted(set(names)-set(verified))
        gate.update(native=parsed,missing_declarations=missing)
        gate['passed']=not missing and set(names)==set(verified)
    save(root/'submission-gate.json',gate)
    append_event(root,'native_metadata_inspected',language=job['language'],seconds=probe_seconds,symbol_count=len(names))
    with (root/'submission-gates.jsonl').open('a') as stream:stream.write(json.dumps(gate)+'\n')
    if not gate['passed']:
        transaction.update(status='failed',final_receipt_id=final['receipt_id'],seconds=time.monotonic()-started)
        save(root/'auto-finalization.json',transaction)
        host.rounds.finish(round_number,False,'Independent final verification or native declaration/axiom gate failed')
        return {'completed':False,'final_check':final,'gate':gate}
    submission={'task_id':job['task_id'],'language':job['language'],'agent_claim':'complete',
                'source_files':[final_path],'interfaces_file':'interfaces.json',
                'clause_mapping':[{'clause_id':cid,'declarations':names,
                    'explanation':'Controller-generated task-level association; semantic review pending.'}
                    for cid in job['required_clause_ids']],
                'dependencies':list(job.get('library',{}).get('index',{}).get('entries',[])),
                'assumptions':[],'unfinished':[],'final_receipt_id':final['receipt_id'],
                'origin':'controller_auto_verified','semantic_status':'pending'}
    submission['dependencies']=[entry['task_id'] for entry in submission['dependencies']]
    save(root/'submission.json',submission)
    host.state.update(submitted=True,last_final_receipt=final['receipt_id'])
    save(root/'state.json',host.state)
    host.rounds.finish(round_number,True)
    transaction.update(status='complete',final_receipt_id=final['receipt_id'],source_hashes=host.hashes(),
                       seconds=time.monotonic()-started)
    save(root/'auto-finalization.json',transaction)
    return {'completed':True,'final_receipt_id':final['receipt_id'],'semantic_status':'pending',
            'note':'Saved-file native verification and declaration/axiom checks passed. No further model step is needed.'}


def recover(host):
    path=host.root/'auto-finalization.json'
    if host.rounds.accepted_candidate():
        record=next(r for r in reversed(host.rounds.read()['rounds']) if r.get('receipt_id'))
        previous=json.loads(path.read_text()) if path.exists() else {}
        if previous.get('candidate_receipt_id')!=record['receipt_id']:
            receipt=json.loads((host.root/'receipts'/(record['receipt_id']+'.json')).read_text())
            complete(host,receipt,record['round'])
            return
    if not path.exists():
        # A crash may land between the durable candidate receipt and transaction creation.
        if not host.rounds.accepted_candidate():return
        record=next(r for r in reversed(host.rounds.read()['rounds']) if r.get('receipt_id'))
        receipt=json.loads((host.root/'receipts'/(record['receipt_id']+'.json')).read_text())
        complete(host,receipt,record['round'])
        return
    value=json.loads(path.read_text())
    if value['status']!='pending':return
    receipt=json.loads((host.root/'receipts'/(value['candidate_receipt_id']+'.json')).read_text())
    current=host.hashes().get(receipt['entry'])
    if not receipt['passed'] or current!=receipt['source_hashes'][receipt['entry']]:
        raise ValueError('Interrupted finalization candidate changed')
    complete(host,receipt,value['round'])
