"""Durable combined save/check operation. Replaying a tool result never buys a new round."""
import hashlib
import json
import uuid
from recovery import save
from agent_language import require_english


def pending(root):
    return [p for p in (root/'candidate-transactions').glob('*.json')
            if json.loads(p.read_text()).get('status')=='pending']


def submit(host,code,operation_id=None):
    require_english(code,'Candidate source')
    if not isinstance(code,str) or not code.strip():raise ValueError('Submit a nonempty complete candidate')
    if len(code.encode())>16_000_000:raise ValueError('Source exceeds 16 MB limit')
    identity=str(operation_id) if operation_id is not None else uuid.uuid4().hex
    path=host.root/'candidate-transactions'/(hashlib.sha256(identity.encode()).hexdigest()+'.json')
    fingerprint=hashlib.sha256(code.encode()).hexdigest()
    name='candidate.'+('lean' if host.job['language']=='lean' else 'lit')
    if path.exists():
        transaction=json.loads(path.read_text())
        if transaction['source_sha256']!=fingerprint:raise ValueError('Candidate operation ID was reused with different code')
        if transaction['status']=='done':return transaction['result']
    else:
        if host.rounds.summary()['remaining']==0:raise ValueError('Whole-task round limit exhausted')
        transaction={'status':'pending','operation_id':identity,'source_sha256':fingerprint,'code':code,
                     'path':name,'prior_total_rounds':host.rounds.summary()['total_used']}
        save(path,transaction)
    # A receipt may have been committed before the broker/result cache was interrupted.
    reserved=next((r for r in host.rounds.read()['rounds'][transaction['prior_total_rounds']:]
                   if r.get('kind')=='candidate' and r.get('path')==name and r.get('source_sha256')==fingerprint),None)
    if reserved:
        source=host.root/'work'/name
        if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest()!=fingerprint:
            raise ValueError('Interrupted atomic candidate changed; no result may be restored')
        receipt_path=host.root/'receipts'/(reserved['receipt_id']+'.json')
        if not receipt_path.exists():
            result=host.check({'path':name,'mode':'incremental'},recovery_round=reserved['round'])
        else:
            result=host.check_response(json.loads(receipt_path.read_text()))
        result={**result,'operation_restored':True}
    else:
        host.dispatch('write_source',{'path':name,'content':code,'base':'none'})
        result=host.check({'path':name,'mode':'incremental'})
    transaction.update(status='done',result=result)
    save(path,transaction)
    return result


def recover(host):
    for path in pending(host.root):
        value=json.loads(path.read_text())
        submit(host,value['code'],value['operation_id'])
