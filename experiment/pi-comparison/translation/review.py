#!/usr/bin/env python3
"""Prepare hash-bound independent source-fidelity reviews. Never calls a model.

Mechanical evidence binding is NOT a semantic oracle and never changes kernel scores.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

BASE=Path(__file__).resolve().parents[1]
HERE=Path(__file__).resolve().parent
DIMENSIONS=('meaning_and_representation','domains_and_conditions','assumption_boundary')
STATUSES={'unreviewed','pass','fail','uncertain'}


def read(path):return json.loads(path.read_text())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
def normalize(text):return re.sub(r'\s+',' ',text).strip()


def contains_quote(quote,text):
    variants=(text,re.sub(r'-\s*\n\s*','-',text),re.sub(r'-\s*\n\s*','',text))
    return any(normalize(quote) in normalize(v) for v in variants)


def bounded(root,name):
    path=(root/name).resolve()
    if not path.is_relative_to(root.resolve()) or path==root.resolve():raise ValueError('Path escapes review area')
    return path


def validate_contract(contract,base=BASE):
    source=bounded(base,contract['source']['path'])
    if sha(source)!=contract['source']['sha256'] or source.read_text()!=contract['source']['text']:
        raise ValueError('Contract original source changed')
    claims=contract['source_claims']+contract.get('source_proof_steps',[])
    if not claims or len({c['id'] for c in claims})!=len(claims):raise ValueError('Missing or duplicate source clauses')
    for clause in claims+contract.get('permitted_model_refinements',[]):
        if not clause.get('requirement') or not clause.get('source_quote','').strip() or not contains_quote(clause['source_quote'],source.read_text()):
            raise ValueError('Clause does not bind an actual original source quote: '+clause['id'])
    for annotation in contract.get('source_annotations',[]):
        if not annotation.get('source_quote','').strip() or not contains_quote(annotation['source_quote'],source.read_text()):
            raise ValueError('Editorial annotation is absent from original source')
    reference=contract.get('existing_target_reference')
    if reference and sha(bounded(base,reference['path']))!=reference['sha256']:
        raise ValueError('Referenced mathematical target changed')
    if contract['status']=='approved':
        approval=contract.get('approval') or {}
        if not approval.get('reviewer') or not approval.get('reason'):raise ValueError('Contract approval requires a reviewer and rationale')
        if any(d.get('status')!='resolved' or not d.get('decision') for d in contract['interpretation_decisions']):
            raise ValueError('An approved contract cannot have unresolved interpretation decisions')
    elif contract['status']!='draft_requires_interpretation_review':raise ValueError('Unknown contract status')
    return contract


def template(packet,packet_sha):
    contract=packet['contract'];claims=contract['source_claims']+contract.get('source_proof_steps',[])
    return {'schema_version':1,'packet_sha256':packet_sha,'task_id':packet['task_id'],'language':packet['language'],
        'formal_sha256':packet['formal_sha256'],'contract_sha256':packet['contract_sha256'],
        'reviewer':{'kind':'','identity':'','model':None},
        'claims':[{'id':c['id'],'status':'unreviewed','reason':'','evidence':[]} for c in claims],
        'dimensions':{name:{'status':'unreviewed','reason':'','evidence':[]} for name in DIMENSIONS},
        'proof_route':{'status':'unreviewed' if contract['proof_route_required'] else 'not_applicable','reason':'','evidence':[]},
        'model_refinements':[],'review_seconds':None,'provider_usage':None,
        'note':'Evidence binding is mechanical; semantic judgments must come from an independent reviewer.'}


def evidence_valid(evidence,packet):
    if not isinstance(evidence,list) or not evidence:raise ValueError('Reviewed judgments need formal-source evidence')
    for item in evidence:
        excerpt=item.get('formal_excerpt','').strip()
        if not excerpt or excerpt not in packet['formal_source']:raise ValueError('Formal evidence excerpt is absent from the bound module')
        symbol=item.get('declaration')
        if symbol and symbol not in packet['native_declarations']:raise ValueError('Evidence names an unknown native declaration')


def evaluate(packet,review,packet_sha):
    for key in ('task_id','language','formal_sha256','contract_sha256'):
        if review.get(key)!=packet[key]:raise ValueError('Review binding mismatch: '+key)
    if review.get('packet_sha256')!=packet_sha:raise ValueError('Review belongs to a different packet')
    claims=packet['contract']['source_claims']+packet['contract'].get('source_proof_steps',[])
    expected={c['id'] for c in claims};actual=review.get('claims',[])
    if len(actual)!=len(expected) or {c['id'] for c in actual}!=expected:raise ValueError('Each original source clause/step needs its own judgment')
    judgments=list(actual)
    if set(review.get('dimensions',{}))!=set(DIMENSIONS):raise ValueError('Missing semantic review dimensions')
    judgments+=list(review['dimensions'].values())
    statuses=[]
    for judgment in judgments:
        status=judgment.get('status')
        if status not in STATUSES:raise ValueError('Unknown judgment status')
        statuses.append(status)
        if status in ('pass','fail'):
            if not judgment.get('reason','').strip():raise ValueError('Pass/fail requires an evidence-based reason')
            evidence_valid(judgment.get('evidence'),packet)
    route=review.get('proof_route',{});route_status=route.get('status')
    reviewed=any(s in ('pass','fail','uncertain') for s in statuses) or route_status not in ('unreviewed','uncertain','not_applicable') or bool(review.get('model_refinements'))
    reviewer=review.get('reviewer',{})
    if reviewed and (reviewer.get('kind') not in ('human','model') or not reviewer.get('identity','').strip()):
        raise ValueError('An assessment needs an identified independent reviewer')
    if reviewed and reviewer['kind']=='model' and not reviewer.get('model'):raise ValueError('Model-assessed results must identify the evaluator model')
    proof=packet['contract']['proof_route_required']
    if proof:
        if route_status not in ('unreviewed','uncertain','faithful','faithful_with_model_refinements','alternative','fail'):
            raise ValueError('A proof task requires a source-route judgment')
        if route_status not in ('unreviewed','uncertain') and not route.get('reason','').strip():raise ValueError('Proof-route decision requires a reason')
        if route_status not in ('unreviewed','uncertain'):evidence_valid(route.get('evidence'),packet)
        if route_status=='faithful_with_model_refinements' and not review.get('model_refinements'):raise ValueError('Label and justify the additional model arguments')
        if review.get('model_refinements') and route_status=='faithful':raise ValueError('Disclose model refinements in the proof-route status')
    elif route_status!='not_applicable':raise ValueError('A definition without source proof must not invent a proof-route requirement')
    for refinement in review.get('model_refinements',[]):
        if not refinement.get('introduced_fact') or not refinement.get('justification') or not refinement.get('source_gap_or_model_change'):
            raise ValueError('Model refinements need their fact, necessity/source gap and justification')
        evidence_valid(refinement.get('evidence'),packet)
    if 'fail' in statuses or (proof and route_status in ('alternative','fail')):assessment='fail'
    elif all(s=='pass' for s in statuses) and (not proof or route_status in ('faithful','faithful_with_model_refinements')):assessment='pass'
    else:assessment='uncertain' if reviewed else 'unreviewed'
    approved=packet['contract']['status']=='approved'
    final=assessment if approved else ('provisional_'+assessment if assessment in ('pass','fail') else assessment)
    claim_ids={c['id'] for c in packet['contract']['source_claims']}
    meaning_statuses=[c['status'] for c in actual if c['id'] in claim_ids]+[c['status'] for c in review['dimensions'].values()]
    meaning='fail' if 'fail' in meaning_statuses else 'pass' if all(s=='pass' for s in meaning_statuses) else 'unknown'
    return {'assessed_fidelity':assessment,'translation_status':final,'contract_approved':approved,
            'verified_faithful_translation':(assessment=='pass') if approved and assessment in ('pass','fail') else None,
            'meaning_preservation_assessment':meaning,'proof_route_assessment':route_status,
            'verified_meaning_preservation':(meaning=='pass') if approved and meaning in ('pass','fail') else None,
            'reviewer_kind':reviewer.get('kind') or None}


def make_packets(batch,output,contracts=HERE/'contracts',base=BASE):
    plan=read(batch/'plan.json');state=read(batch/'state.json')
    if state['plan_sha256']!=sha(batch/'plan.json'):raise ValueError('Frozen source plan changed')
    if state['status'] in ('running','waiting_network'):raise ValueError('Prepare reviews after stopping the agent run')
    policy=read(HERE/'policy.json');index={'batch':str(batch.resolve()),'plan_sha256':sha(batch/'plan.json'),
        'policy':policy,'protocol_timing':'retrospective diagnostic; these drafts were not the original pilot acceptance gate',
        'model_calls':0,'registered_batch_slots':len(plan['slots']),'slots_without_contract':[],'rows':[]}
    prepared=[]
    for slot in plan['slots']:
        contract_path=contracts/(slot['task_id']+'.json')
        if not contract_path.exists():
            index['slots_without_contract'].append(slot['key']);continue
        contract=validate_contract(read(contract_path),base)
        record=state['records'].get(slot['key'],{})
        kernel='pass' if record.get('status')=='finished' and record.get('published') else 'fail' if record.get('status')=='finished' else 'unknown'
        row={k:slot[k] for k in ('key','task_id','language','repetition')};row['kernel_status']=kernel
        if kernel!='pass':index['rows'].append(row);continue
        attempt=bounded(batch,record['attempt']);job=read(attempt/'job.json');manifest=read(attempt/'manifest.json')
        if sha(attempt/'job.json')!=manifest['job_sha256']:raise ValueError('Frozen task job changed')
        if job['task_id']!=slot['task_id'] or job['language']!=slot['language']:raise ValueError('Task job identity mismatch')
        for name,digest in manifest['input_sha256'].items():
            if sha(bounded(attempt/'input',name))!=digest:raise ValueError('Frozen task input changed: '+name)
        submission=read(attempt/'submission.json');rid=submission['final_receipt_id'];receipt=read(bounded(attempt/'receipts',rid+'.json'))
        hashes={str(p.relative_to(attempt/'work')):sha(p) for p in (attempt/'work').rglob('*') if p.is_file()}
        gate=read(attempt/'submission-gate.json')
        if submission['task_id']!=slot['task_id'] or submission['language']!=slot['language'] or submission.get('agent_claim')!='complete':raise ValueError('Submission identity/completeness mismatch')
        if receipt.get('receipt_id')!=rid or gate.get('final_receipt_id')!=rid or not receipt.get('passed') or receipt.get('mode')!='final' or receipt['source_hashes']!=hashes or not gate.get('passed') or gate.get('source_hashes')!=hashes:
            raise ValueError('Machine artifact failed or changed')
        source_manifest=read(attempt/'input/source-manifest.json')
        primary=source_manifest['reading_policy']['primary_text_files']
        if len(primary)!=1 or sha(bounded(attempt/'input',primary[0]))!=contract['source']['sha256']:
            raise ValueError('Common contract and solver original text differ')
        formal=bounded(attempt/'work',receipt['entry']);interfaces=read(bounded(attempt/'work',submission['interfaces_file']))
        native=interfaces.get('declarations',{})
        if isinstance(native,list):native={d['name']:d for d in native}
        packet={'schema_version':1,'task_id':slot['task_id'],'language':slot['language'],'contract':contract,
            'contract_sha256':sha(contract_path),'formal_sha256':sha(formal),'formal_source':formal.read_text(),
            'native_declarations':native,'kernel_status':'pass','source_original_text':contract['source']['text'],
            'prior_original_context':{name:bounded(attempt/'input',name).read_text() for name in source_manifest['reading_policy']['context_text_files']},
            'target_seen_by_solver':read(attempt/'input/task.json'),
            'foundation_seen_by_solver':read(attempt/'input/foundation.json'),
            'native_dependency_manifest':receipt.get('dependency_manifest'),
            'current_candidate_sources':{name:bounded(attempt/'work',name).read_text() for name in hashes if name.startswith('candidate.')},
            'machine_evidence':{'final_receipt':receipt,'submission_gate':gate,'saved_work_hashes':hashes},
            'policy':policy,'evidence_scope':'Complete formal module includes technical seed, prior library and current task. Native names/types are navigation, not semantic certificates.'}
        if contract.get('existing_target_reference'):packet['existing_target_reference']=read(bounded(base,contract['existing_target_reference']['path']))
        name=f'r{slot["repetition"]:03}-{slot["task_id"]}-{slot["language"]}'
        prepared.append((name,packet,row));index['rows'].append(row)
    output.mkdir(parents=True,exist_ok=False)
    for name,packet,row in prepared:
        path=output/(name+'.packet.json');save(path,packet)
        review_path=output/(name+'.review.json');save(review_path,template(packet,sha(path)))
        row.update(packet=path.name,packet_sha256=sha(path),review=review_path.name)
    save(output/'index.json',index)
    (output/'judge-system.txt').write_bytes((HERE/'judge-system.txt').read_bytes())
    return index


def summarize(output):
    index=read(output/'index.json');rows=[];groups={}
    for item in index['rows']:
        row={k:v for k,v in item.items() if k not in ('packet','packet_sha256','review')}
        if item['kernel_status']=='pass':
            path=bounded(output,item['packet'])
            if sha(path)!=item['packet_sha256']:raise ValueError('Bound review packet changed')
            row.update(evaluate(read(path),read(bounded(output,item['review'])),item['packet_sha256']))
        else:row.update(translation_status='not_machine_verified',verified_faithful_translation=False if item['kernel_status']=='fail' else None)
        rows.append(row)
    for language in sorted({r['language'] for r in rows}):
        selected=[r for r in rows if r['language']==language];n=len(selected)
        passed=sum(r.get('verified_faithful_translation') is True for r in selected)
        unknown=sum(r.get('verified_faithful_translation') is None for r in selected)
        groups[language]={'registered_tasks':n,'kernel_passed':sum(r['kernel_status']=='pass' for r in selected),
            'faithful_translation_passed':passed,'unknown_translation_outcomes':unknown,
            'verified_faithful_translation_rate':passed/n if n and not unknown else None,
            'confirmed_translation_coverage':passed/n if n else None,'possible_rate_interval':[passed/n,(passed+unknown)/n] if n else None,
            'meaning':'Unknown/provisional reviews are not final accuracy. Machine scores and historical solver time/token records are unchanged.'}
    result={'model_calls':0,'groups':groups,'rows':rows,'policy':index['policy'],
        'registered_batch_slots':index.get('registered_batch_slots'),
        'slots_without_contract':index.get('slots_without_contract',[]),
        'scope':'Only task-language slots with a source contract; not a full-book accuracy estimate.'}
    save(output/'fidelity-summary.json',result);return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('validate-contracts')
    make=sub.add_parser('make');make.add_argument('--batch',type=Path,required=True);make.add_argument('--output',type=Path,required=True)
    summary=sub.add_parser('summarize');summary.add_argument('--reviews',type=Path,required=True)
    args=parser.parse_args()
    if args.command=='validate-contracts':
        paths=sorted((HERE/'contracts').glob('*.json'))
        for path in paths:validate_contract(read(path))
        print(json.dumps({'contracts':len(paths),'source_bindings_valid':True,'mathematical_interpretations':'draft; not independently certified','model_calls':0}))
    elif args.command=='make':
        result=make_packets(args.batch.resolve(),args.output.resolve())
        print(json.dumps({'packets':sum('packet' in r for r in result['rows']),'task_language_rows':len(result['rows']),'model_calls':0}))
    else:
        result=summarize(args.reviews.resolve());print(json.dumps({'groups':result['groups'],'model_calls':0},indent=2))


if __name__=='__main__':main()
