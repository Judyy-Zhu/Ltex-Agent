"""Durable, language-neutral counts for logical definition/proof candidates.

An item is not a checker call: replay, cached acceptance, final and submission
gates are separate. Unfinished check events retain unknown counts on recovery.
"""
from __future__ import annotations
import hashlib
import json
import re
import os
import time
from pathlib import Path
from recovery import save as durable_save


def read_events(root):
    path=Path(root)/'item-events.jsonl'
    events=[];issues=[]
    if path.exists():
        for number,line in enumerate(path.read_text().splitlines(),1):
            try:events.append(json.loads(line))
            except ValueError:issues.append({'line':number,'error':'incomplete item event'})
    return events,issues


class ItemTracker:
    def __init__(self,root,job):
        self.root=Path(root);self.job=job;self.path=self.root/'items.json'
        self.data=json.loads(self.path.read_text()) if self.path.exists() else {'items':{},'paths':{}}

    def save(self):
        durable_save(self.path,self.data)

    def register(self,path,item_id,kind):
        if not isinstance(item_id,str) or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,160}',item_id):
            raise ValueError('Use a stable item_id (letters, digits, _, ., :, -; at most 160 characters)')
        if kind not in ('definition','proof','scope'):raise ValueError('item_kind must be definition, proof or scope')
        main=self.job.get('primary_item_id',self.job['task_id']+':main')
        if item_id==main and kind!=self.job.get('primary_item_kind',kind):
            raise ValueError('Primary item_kind differs from the assigned task kind')
        bound=self.data['paths'].get(path)
        if bound and bound!=item_id:raise ValueError('A source path cannot change item_id; repair under its original ID')
        item=self.data['items'].get(item_id)
        if item and item['item_kind']!=kind:raise ValueError('item_kind cannot change for an existing item_id')
        if item:
            # A failed candidate can move paths without losing its retry history.
            # Accepted declarations cannot be duplicated under a second path.
            journal=self.root/'session-journal.json'
            entries=json.loads(journal.read_text()).get('entries',[]) if journal.exists() else []
            if path not in item['paths'] and any(e['path'] in item['paths'] for e in entries):
                raise ValueError('Accepted item must be edited at its existing path')
        else:
            item={'item_id':item_id,'item_kind':kind,'is_primary':item_id==main,'paths':[]}
            self.data['items'][item_id]=item
        if path not in item['paths']:item['paths'].append(path)
        item['current_path']=path
        self.data['paths'][path]=item_id;self.save()
        return item

    def lookup(self,path):
        return self.data['paths'].get(path)

    def event(self,**value):
        with (self.root/'item-events.jsonl').open('a') as stream:
            stream.write(json.dumps(value,ensure_ascii=False)+'\n');stream.flush();os.fsync(stream.fileno())

    def begin(self,path,receipt_id,source):
        item_id=self.lookup(path)
        self.event(kind='check_started',receipt_id=receipt_id,item_id=item_id,path=path,
                   source_sha256=hashlib.sha256(source.encode()).hexdigest(),
                   monotonic=time.monotonic(),controller_pid=os.getpid())
        return item_id

    def finish(self,receipt,*,candidate_requests,controller_rejection=False):
        item_id=self.lookup(receipt['entry'])
        if candidate_requests or controller_rejection:classification='candidate'
        elif receipt['passed']:classification='cached'
        else:classification='preparation_failure'
        self.event(kind='check_finished',receipt_id=receipt['receipt_id'],item_id=item_id,
                   classification=classification,passed=receipt['passed'],seconds=receipt['seconds'],
                   native_candidate_requests=candidate_requests,error=receipt.get('error'))
        return summary(self.root)


def summary(root):
    root=Path(root);registry=root/'items.json'
    if not registry.exists():return {'available':False,'items':[],'reason':'No tracked item writes'}
    data=json.loads(registry.read_text());events,issues=read_events(root)
    starts={e['receipt_id']:e for e in events if e.get('kind')=='check_started'}
    finishes={e['receipt_id']:e for e in events if e.get('kind')=='check_finished'}
    journal=root/'session-journal.json'
    entries=json.loads(journal.read_text()).get('entries',[]) if journal.exists() else []
    items=[]
    for item_id,item in data['items'].items():
        checks=[e for e in finishes.values() if e.get('item_id')==item_id]
        candidates=[e for e in checks if e['classification']=='candidate']
        pending=sum(e.get('item_id')==item_id and rid not in finishes for rid,e in starts.items())
        known=len(candidates);complete=not pending and not issues
        # Cached checks and process recovery must not manufacture proof retries.
        file=root/'work'/item['current_path']
        accepted_entries=[e for e in entries if e['path']==item['current_path']]
        accepted=False
        if file.is_file() and accepted_entries:
            language=json.loads((root/'job.json').read_text())['language']
            if language=='litex':
                from native_sessions import litex_blocks
                blocks=litex_blocks(file.read_text())
            else:blocks=[{'text':file.read_text()}]
            accepted=bool(blocks) and len(blocks)==len(accepted_entries) and all(
                any(e['block_index']==index and e['sha256']==hashlib.sha256(block['text'].encode()).hexdigest()
                    for e in accepted_entries) for index,block in enumerate(blocks))
        items.append({**item,'attempt_count':known if complete else None,
                      'retry_count':max(0,known-1) if complete else None,
                      'known_attempt_count':known,'known_retry_count':max(0,known-1),
                      'pending_checks':pending,'counts_complete':complete,
                      'failed_candidate_count':sum(not e['passed'] for e in candidates),
                      'cached_checks':sum(e['classification']=='cached' for e in checks),
                      'preparation_failures':sum(e['classification']=='preparation_failure' for e in checks),
                      'check_seconds':sum(e['seconds'] for e in checks),
                      'source_versions':len({e['source_sha256'] for e in starts.values() if e.get('item_id')==item_id}),
                      'status':'accepted' if accepted else ('pending' if pending else 'not_accepted')})
    formal=[i for i in items if i['item_kind']!='scope']
    complete=not issues and all(i['counts_complete'] for i in formal)
    main=next((i for i in formal if i['is_primary']),None)
    return {'available':True,'counts_complete':complete,'items':items,'log_issues':issues,
            'main_attempt_count':main['attempt_count'] if main else None,
            'main_retry_count':main['retry_count'] if main else None,
            'attempt_count':sum(i['known_attempt_count'] for i in formal) if complete else None,
            'retry_count':sum(i['known_retry_count'] for i in formal) if complete else None,
            'known_retry_count':sum(i['known_retry_count'] for i in formal),
            'definition_retry_count':sum(i['known_retry_count'] for i in formal if i['item_kind']=='definition') if complete else None,
            'proof_retry_count':sum(i['known_retry_count'] for i in formal if i['item_kind']=='proof') if complete else None,
            'pending_checks':sum(i['pending_checks'] for i in items),
            'definition':'One candidate incremental check per stable logical item; retries=max(0, attempts-1). Scope, cached checks, replay, final and submission gates are excluded. Unknown interrupted counts remain null.'}


def validate_unit(source,language,kind,mask_lean):
    """Conservative fragment protocol, not a replacement for either parser."""
    if language=='litex':
        from native_sessions import litex_blocks,litex_frame
        litex_frame(source)
        if len(litex_blocks(source))!=1:raise ValueError('One tracked Litex item must contain exactly one complete top-level block')
        if kind=='scope':raise ValueError('Litex does not use Lean scope fragments')
        return
    code=mask_lean(source)
    declarations=re.findall(r'(?m)^\s*(?:(?:private|protected|noncomputable|partial)\s+)*(?:def|abbrev|theorem|lemma|example|structure|inductive|class|instance|opaque)\b',code)
    if kind=='scope':
        if declarations:raise ValueError('Scope fragments cannot contain declarations')
        for line in code.splitlines():
            if line.strip() and not re.match(r'^\s*(namespace|section|end|open|universe|universes|variable|variables)\b',line):
                raise ValueError('Scope fragments permit only namespace/section/end/open/universe/variable commands')
    elif len(declarations)!=1:
        raise ValueError('One tracked Lean item must contain exactly one complete declaration (with its entire proof/body)')
