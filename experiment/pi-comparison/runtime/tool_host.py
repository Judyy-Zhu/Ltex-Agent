#!/usr/bin/env python3
"""Restricted persistent tool host with native incremental verifiers.

This enforces data/tool boundaries, not an OS sandbox for hostile compiler code.
The conservative source guard is intentionally narrower than either language.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
from verifier_feedback import native_feedback,process_status
from native_sessions import SessionLedger,SessionFault
from seed_support import require_seed_prefix,assemble_final,starting_source
from item_tracking import ItemTracker,summary as retry_summary,validate_unit,read_events
from agent_language import require_english
from budgets import remaining,until,timeout_seconds
from task_rounds import TaskRounds
from recovery import save as durable_save,append_event


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path):
    return json.loads(path.read_text())


def save_json(path, value):
    durable_save(path,value)


def bounded(root, name):
    if not isinstance(name, str) or not name or Path(name).is_absolute():
        raise ValueError('Only nonempty relative paths are allowed')
    result = (root/name).resolve()
    if not result.is_relative_to(root.resolve()) or result == root.resolve():
        raise ValueError('Path escapes approved area')
    return result


def lean_code_for_import_check(text):
    """Mask comments/strings without shifting lines; imports remain visible."""
    output=[];index=0;depth=0;quoted=False
    while index<len(text):
        pair=text[index:index+2];char=text[index]
        if depth:
            if pair=='/-':depth+=1;output.extend('  ');index+=2;continue
            if pair=='-/':depth-=1;output.extend('  ');index+=2;continue
            output.append('\n' if char=='\n' else ' ');index+=1;continue
        if quoted:
            if char=='\\' and index+1<len(text):
                output.extend('  ');index+=2;continue
            if char=='"':quoted=False
            output.append('\n' if char=='\n' else ' ');index+=1;continue
        if pair=='--':
            end=text.find('\n',index)
            if end<0:end=len(text)
            output.extend(' '*(end-index));index=end;continue
        if pair=='/-':depth=1;output.extend('  ');index+=2;continue
        if char=='"':quoted=True;output.append(' ');index+=1;continue
        output.append(char);index+=1
    return ''.join(output)


def source_guard(text, language, allowed_imports):
    # Reject suspicious text even inside comments: safe false positives can be edited.
    if language == 'lean':
        banned = r'\b(sorry|admit|axiom|unsafe|run_cmd|run_tac|by_elab|elab|macro|syntax|initialize|builtin_initialize|native_decide|implemented_by|extern|set_option|IO|EIO|BaseIO|System)\b|#(eval|reduce|check|print)|\battribute\b'
        if re.search(banned, text):
            raise ValueError('Unapproved placeholder, metaprogramming, command, or trust feature')
        code=lean_code_for_import_check(text)
        import_lines=re.findall(r'(?m)^\s*(?:(?:public|private|meta)\s+)*import\b([^\n]*)',code)
        if len(import_lines)!=len(re.findall(r'\bimport\b',code)):
            raise ValueError('Unsupported import placement; use approved standalone import lines')
        for imported in import_lines:
            modules=imported.split('--',1)[0].split()
            if not modules:raise ValueError('Empty import command')
            for module in modules:
                if module not in allowed_imports:
                    raise ValueError(f'Import not approved: {module}')
    else:
        permitted=re.sub(r'(?m)^(\s*)release(?=\s+thm\s+tuple_equal_from_coordinates\s*\()',r'\1',text)
        if re.search(r'\b(axiom|trust|trust_have|abstract_prop|release|import)\b',permitted):
            raise ValueError('Unapproved trust, abstract predicate, foundation release, or import')
    if language=='litex' and re.search(r'(?m)^\s*(?:exit|quit|:quit)\s*(?:#.*)?$',text):
        raise ValueError('Session lifecycle commands are controlled by the adapter, not source fragments')


class Host:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.job = read_json(self.root/'job.json')
        self.state = read_json(self.root/'state.json')
        self.ledger = SessionLedger(self.root,self.job)
        self.items = ItemTracker(self.root,self.job)
        self.rounds = TaskRounds(self.root,self.job)

    def close(self):
        self.ledger.close()

    def hashes(self):
        return {str(p.relative_to(self.root/'work')): digest(p)
                for p in sorted((self.root/'work').rglob('*')) if p.is_file()}

    def remaining(self):
        deadline=self.state.get('deadline_monotonic');checks=self.job.get('max_check_calls')
        return {'deadline_remaining_seconds':None if deadline is None else remaining(deadline),
                'check_calls_remaining':None if checks is None else max(0,checks-self.state['checks']-self.state.get('submission_gate_checks',0)),
                'task_rounds':self.rounds.summary()}

    def time_available(self):
        return remaining(self.state.get('deadline_monotonic'))>0

    def checks_available(self):
        value=self.remaining()['check_calls_remaining']
        return value is None or value>0

    def dispatch(self, name, args):
        completed=self.root/'auto-finalization.json'
        if self.job.get('auto_finalize') and completed.exists() and read_json(completed).get('status')=='complete' and name in ('write_source','check','submit','submit_candidate'):
            return {'completed':True,'task_completed':True,'note':'Task already independently verified and saved; no further mutation is permitted.'}
        if not self.time_available():
            raise ValueError('Task deadline exhausted')
        if name == 'remaining_budget':
            return self.remaining()
        if name == 'read_input':
            path = bounded(self.root/'input', args['path'])
            if not path.is_file() and (self.root/'work'/args['path']).is_file():
                raise ValueError('This is a work file, not an input. Use read_library(["file:'+args['path']+'"]).')
            if path.suffix.lower() not in ('.txt','.json','.lean','.lit','.md'):
                raise ValueError('Text-only experiment: image and binary inputs are forbidden; use the primary TXT input')
            text=path.read_text();require_english(text,'Input text')
            return {'text':text, 'sha256':digest(path)}
        if name == 'read_docs':
            paths = self.job['docs']
            if args['topic'] not in paths:
                return {'available_topics':sorted(paths)}
            path = Path(paths[args['topic']])
            text=path.read_text();require_english(text,'Guide text')
            if self.job.get('compact_protocol') or args.get('section') is not None:
                from doc_sections import retrieve
                selected=args.get('sections');origin=None
                if self.job.get('direct_protocol') and all(args.get(k) is None for k in ('section','sections','query')):
                    repair=self.root/'last-direct-repair.json'
                    if repair.exists():
                        selected=[r['section'] for r in read_json(repair).get('reference_sections',[])
                                  if r.get('topic')==args['topic'] and r.get('reference_sha256')==digest(path)] or None
                        if selected:origin='latest_native_error'
                result=retrieve(text,args['topic'],args.get('section'),selected,args.get('query'))
                return {**result,'reference_sha256':digest(path),
                        **({'selection_origin':origin} if origin else {}),
                        **({'sha256':hashlib.sha256(result['text'].encode()).hexdigest()} if 'text' in result else {})}
            return {'text':text, 'sha256':digest(path)}
        if name == 'read_library':
            requested = args['symbols']
            if requested==['retry_stats']:return retry_summary(self.root)
            if requested==['submission_gate']:
                path=self.root/'submission-gate.json'
                return read_json(path) if path.exists() else {'status':'not_checked'}
            if len(requested)==1 and requested[0].startswith('receipt:'):
                receipt = read_json(bounded(self.root/'receipts',requested[0][8:]+'.json'))
                return receipt
            index=self.job.get('library',{}).get('index',{'entries':[]})
            selected={};selected_interfaces={};symbol_matches={};unresolved=[];offset=max(0,len(index['entries'])-10);limit=10
            seed_interface=read_json(self.root/'input/seed-interface.json')
            seed_matches={e['name']:e for e in seed_interface.get('exports',[]) if e['name'] in requested}
            for requested_name in requested:
                if requested_name.startswith('index:'):
                    parts=requested_name.split(':')
                    if len(parts)!=3:raise ValueError('Use index:offset:limit')
                    offset=int(parts[1]);limit=int(parts[2])
                    if offset<0 or not 1<=limit<=50:raise ValueError('Index page limit must be 1..50')
                matches=[entry for entry in index['entries'] if
                         (requested_name.startswith('entry:') and entry['task_id']==requested_name[6:]) or
                         requested_name in entry.get('symbols',[])]
                for entry in matches:
                    task_id=entry['task_id']
                    if requested_name in entry.get('symbols',[]):
                        declarations=(entry.get('interfaces') or {}).get('declarations',{})
                        if isinstance(declarations,list):declarations={v['name']:v for v in declarations if isinstance(v,dict) and 'name' in v}
                        symbol_matches[requested_name]={'task_id':task_id,'source_reference':'entry:'+task_id,
                            'native_metadata':declarations.get(requested_name)}
                    if task_id not in selected:
                            path=bounded(self.root/'input/library-parts',entry['file'])
                            if digest(path)!=entry['sha256']:raise ValueError('Frozen library increment changed')
                            selected[task_id]=path.read_text()
                            selected_interfaces[task_id]=entry.get('interfaces')
                if not matches and requested_name not in seed_matches and not requested_name.startswith(('index:','file:')) and requested_name!='accepted_prefix':unresolved.append(requested_name)
            page=[{k:v for k,v in e.items() if k!='interfaces'} for e in index['entries'][offset:offset+limit]]
            return {'approved_foundation':self.job['foundation'],
                    'success_criterion':'machine_verification','semantic_review_required':False,
                    'published_library_usable':True,
                    'library_index':{'total_entries':len(index['entries']),'offset':offset,'entries':page},
                    'selected_entries':selected,'selected_interfaces':selected_interfaces,
                    'symbol_matches':symbol_matches,'unresolved_symbols':unresolved,
                    'seed_symbol_matches':seed_matches,'seed_source':Path(self.job['seed_path']).read_text() if seed_matches else None,
                    'accepted_geometry_symbols':sorted({n for e in index['entries'] for n in e.get('symbols',[])}) if self.job.get('auto_finalize') else [],
                    'library_is_loaded_in_verifier':True,
                    'session':self.ledger.status(include_source='accepted_prefix' in requested),
                    'requested_symbols':args['symbols'], 'current_source_files':self.hashes(),
                    'current_source':{name:bounded(self.root/'work',name[5:]).read_text()
                                      for name in requested if name.startswith('file:')}}
        if name == 'write_source':
            require_english(args['content'],'Source and interface content')
            path = bounded(self.root/'work', args['path'])
            suffix = '.lean' if self.job['language']=='lean' else '.lit'
            if self.job.get('auto_finalize') and (args['path']!='candidate'+suffix or args.get('base','none')!='none'):
                raise ValueError('Automatic completion mode: write only the complete candidate'+suffix+' with base=none; the controller owns final files and metadata')
            if path.suffix not in (suffix, '.json'):
                raise ValueError(f'Only {suffix} and interface .json files can be written')
            if len(args['content'].encode()) > 16_000_000:
                raise ValueError('Source exceeds 16 MB limit')
            content=args['content'];base=args.get('base','none')
            if self.job.get('auto_finalize'):
                args={k:v for k,v in args.items() if k not in ('item_id','item_kind')}
            if base not in ('none','library','accepted'):raise ValueError('Unknown source base')
            relative=str(path.relative_to(self.root/'work'))
            if path.suffix==suffix and base=='none':
                item_id=args.get('item_id') or self.items.lookup(relative)
                if self.job.get('candidate_protocol')=='whole_task':
                    item_id=item_id or self.job['primary_item_id']
                    if item_id!=self.job['primary_item_id']:raise ValueError('Use one complete task candidate, not separate helper submissions')
                    args={**args,'item_kind':self.job['primary_item_kind']}
                if item_id or self.job.get('item_tracking_required'):
                    kind=args.get('item_kind') or self.items.data['items'].get(item_id,{}).get('item_kind')
                    self.items.register(relative,item_id,kind)
            elif args.get('item_id') or args.get('item_kind'):
                raise ValueError('Item metadata belongs only to incremental language fragments (base=none)')
            if base!='none' and self.items.lookup(relative):raise ValueError('Use a separate path for assembled final source')
            if base!='none':
                if path.suffix!=suffix:raise ValueError('Source base is only valid for language source files')
                content=(assemble_final(self.job,content) if base=='library' else
                         self.ledger.status(include_source=True)['accepted_source'].rstrip()+'\n\n'+content)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('w') as stream:
                stream.write(content);stream.flush();os.fsync(stream.fileno())
            self.state['last_final_receipt'] = None
            return {'path':args['path'], 'sha256':digest(path),'item_id':self.items.lookup(relative)}
        if name == 'check':
            return self.check(args)
        if name == 'submit_candidate':
            if not self.job.get('compact_protocol'):raise ValueError('Combined candidate tool is not enabled for this historical job')
            from atomic_candidate import submit
            return submit(self,args['code'],getattr(self,'operation_id',None))
        if name == 'submit':
            return self.submit(args['submission'])
        raise ValueError('Unknown tool')

    def check(self, args, recovery_round=None):
        if args['mode'] not in ('incremental','final'):
            raise ValueError('Invalid check mode')
        if not self.checks_available():
            raise ValueError('Checker call budget exhausted')
        path = bounded(self.root/'work', args['path'])
        language = self.job['language']
        expected = '.lean' if language=='lean' else '.lit'
        if path.suffix != expected:
            raise ValueError('Wrong language source')
        args={**args,'path':str(path.relative_to(self.root/'work'))}
        prior_requests=0
        if recovery_round is not None:
            record=self.rounds.read()['rounds'][recovery_round-1]
            receipt_id=record['receipt_id']
            events,_=read_events(self.root)
            started=next((e for e in events if e.get('kind')=='check_started' and e['receipt_id']==receipt_id),None)
            if not started or started['path']!=args['path'] or digest(path)!=started['source_sha256']:
                raise ValueError('Interrupted candidate changed; cannot restore its original round')
            native=self.root/'session-events.jsonl'
            if native.exists():
                for line in native.read_text().splitlines():
                    try:e=json.loads(line)
                    except ValueError:continue
                    prior_requests+=bool(e.get('kind')=='native_request' and not e.get('replay') and
                        e.get('path')==args['path'] and e.get('controller_pid')==started.get('controller_pid') and
                        e.get('monotonic',0)>=started.get('monotonic',float('inf')))
            round_number=recovery_round
            self.state['checks']=max(self.state['checks'],int(receipt_id.split('-')[1]))
        else:
            round_number=self.rounds.begin(f"check-{self.state['checks']+1:04}",source={
                'path':args['path'],'source_sha256':digest(path) if path.is_file() else None}) if args['mode']=='incremental' else None
            self.state['checks'] += 1
            receipt_id = f"check-{self.state['checks']:04}"
        # Persist before starting a potentially interrupted compiler process.
        save_json(self.root/'state.json',self.state)
        receipt = {'receipt_id':receipt_id,'mode':args['mode'],'source_hashes':self.hashes(),
                   'dependency_manifest':self.job['foundation'],'entry':args['path'],
                   'scope':'persistent_incremental_session' if args['mode']=='incremental' else 'fresh_final_file',
                   'passed':False}
        if args['mode']=='final':receipt['native_process_seconds']=None
        start = time.monotonic()
        item_id=None;begun=False;controller_rejection=False;phase='candidate_validation'
        self.ledger.candidate_requests=0
        try:
            source=path.read_text()
            if args['mode']=='incremental':
                item_id=self.items.lookup(args['path']) if recovery_round is not None else self.items.begin(args['path'],receipt_id,source)
                begun=True
                if self.job.get('item_tracking_required') and not item_id:
                    raise ValueError('Incremental fragments require write_source item_id and item_kind; read_docs(items)')
                if item_id:
                    item=self.items.data['items'][item_id]
                    if item['current_path']!=args['path']:raise ValueError('Recheck the current path registered for this item_id')
                    if self.job.get('candidate_protocol')=='whole_task':
                        if item_id!=self.job['primary_item_id']:
                            raise ValueError('Submit the complete task candidate under primary_item_id; auxiliary files do not receive separate rounds')
                    else:validate_unit(source,language,item['item_kind'],lean_code_for_import_check)
            if args['mode']=='final':
                require_seed_prefix(self.job,source)
                if self.job.get('item_tracking_required'):
                    if self.ledger._changed() or source.strip()!=self.ledger.status(include_source=True)['accepted_source'].strip():
                        raise ValueError('Final must exactly assemble unchanged accepted fragments; check each item incrementally first')
                    main=self.items.data['items'].get(self.job['primary_item_id'])
                    if not main or not any(e['path']==main['current_path'] for e in self.ledger.data['entries']):
                        raise ValueError('Primary task item has not been accepted incrementally')
                    if self.job.get('candidate_protocol')=='whole_task' and not any(
                            i['is_primary'] and i['status']=='accepted' for i in retry_summary(self.root)['items']):
                        raise ValueError('The complete task candidate must pass before final assembly; partial prefixes are not complete')
            imports=self.job['foundation'].get('allowed_imports',[]) if args['mode']=='final' else []
            source_guard(source,language,imports)
            if args['mode']=='incremental':
                phase='session_preparation'
                deadline=until(self.state,self.job,start)
                session=self.ledger.check(args['path'],source,deadline)
                receipt['native_frames']=session.pop('frames')
                receipt['session']=session
                if session.get('controller_error'):
                    receipt['error']=session['controller_error']
                current=[frame for frame in receipt['native_frames'] if not frame['replay']]
                if current:
                    receipt['stdout']=json.dumps(current[-1]['native'],ensure_ascii=False)
                receipt['passed']=bool(session['passed'] and self.time_available())
            elif language=='lean':
                command = [self.job['lake'],'env','lean',str(path)]
                cwd = self.job['lean_project']
            else:
                command = [self.job['litex'],'-strict','-lang','en','-f',str(path)]
                cwd = str(self.root/'work')
            if args['mode']=='final':
                if self.job.get('split_final_timing'):
                    from final_verification import verify
                    verify(self.job,self.root,source,until(self.state,self.job,start),receipt)
                    receipt['passed']=bool(receipt['passed'] and self.time_available())
                else:
                    timeout = timeout_seconds(until(self.state,self.job,start))
                    env={key:value for key,value in os.environ.items() if not key.endswith('_API_KEY')}
                    native_start=time.monotonic()
                    try:result = subprocess.run(command,cwd=cwd,env=env,capture_output=True,text=True,timeout=timeout)
                    finally:receipt['native_process_seconds']=time.monotonic()-native_start
                    receipt.update(exit_code=result.returncode,stdout=result.stdout,stderr=result.stderr)
                    passed = result.returncode==0
                    if language=='litex':
                        output = json.loads(result.stdout)
                        passed = (passed and output.get('kind')=='run' and output.get('run_result')=='success'
                                  and not output.get('errors') and not output.get('session_terminated')
                                  and output.get('termination') is None)
                    if language=='lean' and re.search(r'sorry|sorryAx|declaration uses',result.stdout+result.stderr):
                        passed = False
                    receipt['passed'] = bool(passed and self.time_available())
        except subprocess.TimeoutExpired as error:
            receipt.update(error='checker_timeout',stdout=(error.stdout or b'').decode() if isinstance(error.stdout,bytes) else error.stdout,
                           stderr=(error.stderr or b'').decode() if isinstance(error.stderr,bytes) else error.stderr)
        except (TimeoutError,SessionFault) as error:
            receipt.update(error='checker_timeout' if isinstance(error,TimeoutError) else str(error))
            receipt.setdefault('native_frames',self.ledger.frames)
            self.ledger.close()
        except (ValueError, OSError) as error:
            receipt['error'] = str(error)
            controller_rejection=isinstance(error,ValueError) and phase=='candidate_validation'
        receipt.setdefault('session',self.ledger.snapshot())
        if args['mode']=='incremental':receipt.setdefault('native_frames',[])
        receipt['seconds'] = time.monotonic()-start
        self.rounds.finish(round_number,receipt['passed'],receipt.get('error'))
        receipt['task_rounds']=self.rounds.summary()
        if args['mode']=='incremental' and begun:
            stats=self.items.finish(receipt,candidate_requests=self.ledger.candidate_requests+prior_requests,
                                    controller_rejection=controller_rejection)
            receipt['item_tracking']=next((i for i in stats['items'] if i['item_id']==item_id),None)
        save_json(self.root/'receipts'/f'{receipt_id}.json',receipt)
        if args['mode']=='final' and receipt['passed']:
            self.state['last_final_receipt'] = receipt_id
        automatic=None
        if self.job.get('auto_finalize') and args['mode']=='incremental' and receipt['passed']:
            from auto_finalize import complete
            automatic=complete(self,receipt,round_number)
        return self.check_response(receipt,automatic)

    def check_response(self,receipt,automatic=None):
        language=self.job['language'];receipt_id=receipt['receipt_id']
        if automatic is None and receipt['mode']=='incremental' and receipt['passed'] and self.job.get('auto_finalize'):
            path=self.root/'auto-finalization.json'
            status=read_json(path) if path.exists() else {}
            if status.get('candidate_receipt_id')==receipt['receipt_id']:
                automatic={'completed':status['status']=='complete','controller_error':status.get('error'),
                           'final_receipt_id':status.get('final_receipt_id')}
                if status['status']=='failed':
                    gate=self.root/'submission-gate.json'
                    if gate.exists():automatic['gate']=read_json(gate)
                    if status.get('final_receipt_id'):
                        automatic['final_check']=self.check_response(read_json(self.root/'receipts'/(status['final_receipt_id']+'.json')))
        from direct_context import repair_hints
        repair=repair_hints(self.job,receipt)
        if repair is not None:save_json(self.root/'last-direct-repair.json',repair)
        return {key:receipt[key] for key in ('receipt_id','mode','source_hashes','entry','scope','passed','seconds')} | {
            **({'repair':repair} if repair is not None else {}),
            'auto_finalization':automatic,'task_completed':bool(automatic and automatic['completed']),
            'language':language,'feedback':native_feedback(language,receipt),
            'process_status':process_status(language,receipt),'controller_error':receipt.get('error'),
            'session':receipt.get('session'),
            'item_tracking':receipt.get('item_tracking'),
            'task_rounds':self.rounds.summary(),
            'feedback_truncated':False,'full_receipt':f'receipt:{receipt_id}',
            'exit_code':receipt.get('exit_code')}

    def recover_pending_check(self):
        if not self.job.get('checkpoint_resume'):return
        for record in self.rounds.read()['rounds']:
            rid=record.get('receipt_id')
            if not rid or (self.root/'receipts'/(rid+'.json')).exists():continue
            events,_=read_events(self.root)
            started=next((e for e in events if e.get('kind')=='check_started' and e['receipt_id']==rid),None)
            if started is None and record.get('path') and record.get('source_sha256'):
                file=bounded(self.root/'work',record['path'])
                if digest(file)!=record['source_sha256']:raise ValueError('Interrupted reserved candidate changed')
                self.items.begin(record['path'],rid,file.read_text())
                started={'path':record['path']}
            if started:
                result=self.check({'path':started['path'],'mode':'incremental'},recovery_round=record['round'])
                append_event(self.root,'interrupted_check_recovered',receipt_id=rid,round=record['round'],passed=result['passed'])

        if self.job.get('auto_finalize'):
            from auto_finalize import recover
            recover(self)
        if self.job.get('compact_protocol'):
            from atomic_candidate import recover
            recover(self)

    def submit(self, submission):
        require_english(submission,'Submission metadata')
        if submission['task_id']!=self.job['task_id'] or submission['language']!=self.job['language']:
            raise ValueError('Submission task/language mismatch')
        for name in submission['source_files']:
            if not bounded(self.root/'work',name).is_file():
                raise ValueError('Submitted source missing')
        if submission['interfaces_file'] is not None:
            read_json(bounded(self.root/'work',submission['interfaces_file']))
        if submission['agent_claim']=='complete':
            rid = submission['final_receipt_id']
            if not rid or rid!=self.state.get('last_final_receipt'):
                raise ValueError('Complete requires the current successful final receipt')
            receipt = read_json(bounded(self.root/'receipts',rid+'.json'))
            if receipt['source_hashes']!=self.hashes() or not receipt['passed']:
                raise ValueError('Final receipt stale or failed')
            if submission['unfinished']:
                raise ValueError('Complete cannot contain unfinished clauses')
            mapped = {c['clause_id'] for c in submission['clause_mapping'] if c['declarations']}
            if not set(self.job['required_clause_ids']).issubset(mapped):
                raise ValueError('Required clause mapping missing')
            if receipt['entry'] not in submission['source_files'] or not submission['interfaces_file']:
                raise ValueError('Complete requires checked entry and interface metadata')
            if self.job.get('require_submission_gate'):
                from submission_gate import validate
                if not self.checks_available():raise ValueError('No check budget remains for submission gate')
                self.state['submission_gate_checks']=self.state.get('submission_gate_checks',0)+1
                save_json(self.root/'state.json',self.state)
                symbols=sorted({n for c in submission['clause_mapping'] for n in c['declarations']})
                start=time.monotonic()
                try:gate=validate(self.job,bounded(self.root/'work',receipt['entry']).read_text(),symbols,until(self.state,self.job))
                except (ValueError,OSError,subprocess.TimeoutExpired) as error:gate={'passed':False,'error':str(error)}
                gate['seconds']=time.monotonic()-start
                gate.update(source_hashes=self.hashes(),final_receipt_id=rid)
                save_json(self.root/'submission-gate.json',gate)
                with (self.root/'submission-gates.jsonl').open('a') as stream:
                    stream.write(json.dumps(gate,ensure_ascii=False)+'\n')
                if not gate['passed']:raise ValueError('Declaration/axiom gate failed; see submission-gate receipt')
        save_json(self.root/'submission.json',submission)
        self.state['submitted'] = True
        return {'received':True,'semantic_status':'pending','assumption_audit':'pending',
                'machine_passed':submission['agent_claim']=='complete','semantic_review_required':False,
                'note':'Complete submissions pass the automatic machine gate. Optional semantic annotations do not block completion, publication or the primary score.'}


def execute(host,name,args,operation_id=None):
    start = time.monotonic()
    cache=None
    if operation_id and host.job.get('checkpoint_resume') and name in ('write_source','check','submit','submit_candidate'):
        key=hashlib.sha256(str(operation_id).encode()).hexdigest()
        cache=host.root/'tool-results'/(key+'.json')
        arguments_hash=hashlib.sha256(json.dumps({'tool':name,'arguments':args},sort_keys=True).encode()).hexdigest()
        if cache.exists():
            stored=read_json(cache)
            if stored['arguments_sha256']!=arguments_hash:
                return {'isError':True,'content':[{'type':'text','text':'Tool operation ID was reused with different arguments; no mutation performed'}],
                        'details':{'error':'operation_id_conflict'}}
            append_event(host.root,'tool_result_restored',tool=name,operation_id=str(operation_id))
            return stored['result']
    try:
        host.operation_id=operation_id
        value = host.dispatch(name,args)
        if name in ('check','submit_candidate') and 'feedback' in value:
            # Separate blocks keep Litex's pretty JSON and Lean's multiline
            # diagnostics readable instead of double-encoding them in JSON.
            metadata = {key:value for key,value in value.items() if key!='feedback'}
            feedback = value['feedback']
            metadata['feedback_format'] = feedback['format']
            content = [{'type':'text','text':json.dumps(metadata,ensure_ascii=False)},
                       {'type':'text','text':feedback['text']}]
            if feedback['format'].startswith('litex') and feedback.get('stderr'):
                content.append({'type':'text','text':'Litex stderr:\n'+feedback['stderr']})
        else:
            content = [{'type':'text','text':json.dumps(value,ensure_ascii=False)}]
        result = {'content':content,'details':value}
    except (KeyError, ValueError, OSError, subprocess.TimeoutExpired) as error:
        result = {'isError':True,'content':[{'type':'text','text':str(error)}], 'details':{'error':str(error)}}
    save_json(host.root/'state.json',host.state)
    if host.job.get('auto_finalize') and name in ('read_input','read_docs','read_library'):
        memory_path=host.root/'context-memory.json'
        memory=read_json(memory_path) if memory_path.exists() else {'read_inputs':[],'read_docs':[],'library_queries':[],'recent_errors':[]}
        if not result.get('isError'):
            field,key=('read_inputs',args.get('path')) if name=='read_input' else ('read_docs',args.get('topic')+(':'+json.dumps({k:args[k] for k in ('section','sections','query') if k in args},sort_keys=True) if any(k in args for k in ('section','sections','query')) else '')) if name=='read_docs' else ('library_queries',args.get('symbols'))
            if key not in memory[field]:memory[field].append(key)
            if name=='read_library':
                value=result.get('details',{})
                remembered=memory.setdefault('symbol_metadata',{})
                remembered.update(value.get('symbol_matches',{}))
                memory['symbol_metadata']=dict(list(remembered.items())[-20:])
                sources=value.get('selected_entries',{})
                if sources:
                    task_id,source=list(sources.items())[-1]
                    memory['last_retrieved_library_source']={'task_id':task_id,'source':source} if len(source)<=8000 else {'task_id':task_id,'reference':'entry:'+task_id,'inline':False}
        elif result.get('details',{}).get('error'):
            memory['recent_errors']=(memory['recent_errors']+[{'tool':name,'arguments':args,'error':result['details']['error']}])[-5:]
        save_json(memory_path,memory)
    if cache is not None:save_json(cache,{'arguments_sha256':arguments_hash,'result':result})
    with (host.root/'tools.jsonl').open('a') as stream:
        stream.write(json.dumps({'tool':name,'seconds':time.monotonic()-start,
                                 'error':result.get('isError',False)},ensure_ascii=False)+'\n')
    return result


def main():
    host=Host(sys.argv[1])
    def terminate(_number,_frame):raise SystemExit(0)
    signal.signal(signal.SIGTERM,terminate)
    try:
        if sys.argv[2]=='--server':
            for line in sys.stdin:
                request=json.loads(line)
                result=execute(host,request['tool'],request['arguments'],request.get('operation_id'))
                print(json.dumps({'id':request['id'],'result':result},ensure_ascii=False),flush=True)
        else:
            print(json.dumps(execute(host,sys.argv[2],json.load(sys.stdin)),ensure_ascii=False))
    finally:host.close()


if __name__=='__main__':
    main()
