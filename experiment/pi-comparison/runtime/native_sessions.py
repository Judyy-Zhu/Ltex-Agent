"""Persistent native verifiers with an external, replayable source journal."""
from __future__ import annotations
import hashlib
import json
import math
import os
from pathlib import Path
import queue
import select
import subprocess
import threading
import time
import uuid
from seed_support import starting_source,assemble_final
from recovery import save as durable_save


class SessionFault(RuntimeError):
    pass


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def save(path,value):
    durable_save(path,value)


class JsonProcess:
    def __init__(self,command,cwd):
        env = {k:v for k,v in os.environ.items() if not k.endswith('_API_KEY')}
        self.process = subprocess.Popen(command,cwd=cwd,env=env,stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1)
        self.responses = queue.Queue()
        os.set_blocking(self.process.stdin.fileno(),False)
        self.stderr = []
        self.bad_stdout = []
        threading.Thread(target=self._read_stdout,daemon=True).start()
        threading.Thread(target=self._read_stderr,daemon=True).start()

    def _read_stdout(self):
        decoder = json.JSONDecoder(); buffer = ''
        try:
            for line in self.process.stdout:
                buffer += line
                while buffer.strip():
                    buffer = buffer.lstrip()
                    try:
                        value,end = decoder.raw_decode(buffer)
                    except ValueError:
                        break
                    self.responses.put(value);buffer = buffer[end:]
        finally:
            if buffer.strip():
                self.bad_stdout.append(buffer)
            self.responses.put(None)

    def _read_stderr(self):
        for line in self.process.stderr:
            self.stderr.append(line)

    @property
    def alive(self):
        return self.process.poll() is None

    def exchange(self,request,deadline):
        if not self.alive:
            raise SessionFault('Native verifier exited; its context is unavailable')
        payload=request.encode();offset=0
        while offset<len(payload):
            remaining=deadline-time.monotonic()
            if remaining<=0:raise TimeoutError('Native verifier input timeout')
            if not select.select([],[self.process.stdin.fileno()],[],min(remaining,1))[1]:
                continue
            try:offset+=os.write(self.process.stdin.fileno(),payload[offset:offset+65536])
            except BlockingIOError:continue
            except (BrokenPipeError,OSError) as error:
                raise SessionFault('Native verifier pipe closed') from error
        remaining = deadline-time.monotonic()
        if remaining<=0:
            raise TimeoutError('Native verifier deadline exhausted')
        try:
            result = self.responses.get(timeout=None if math.isinf(remaining) else remaining)
        except queue.Empty as error:
            raise TimeoutError('Native verifier response timeout') from error
        if not isinstance(result,dict):
            raise SessionFault('Native verifier ended without a complete JSON object')
        return result

    def close(self):
        if self.alive:
            self.process.terminate()
            try:self.process.wait(timeout=.5)
            except subprocess.TimeoutExpired:
                self.process.kill();self.process.wait()
        for stream in (self.process.stdin,self.process.stdout,self.process.stderr):
            try:stream.close()
            except (OSError,ValueError):pass


def litex_frame(source):
    lines=[];mapping=[];comment=False
    for index,line in enumerate(source.splitlines(),1):
        stripped=line.strip()
        if stripped=='"""':comment=not comment;continue
        if comment or not stripped or stripped.startswith('#'):continue
        lines.append(line);mapping.append(index)
    if comment:raise ValueError('Unclosed Litex block comment; source was not submitted')
    return '\n'.join(lines)+'\n\n',mapping


def litex_repl_turns(frame):
    """Mirror pinned read_repl_block boundaries, without rewriting source.

    A first physical line not ending in ':' is executed immediately. Sending
    an invalid multiline function as one write can therefore enqueue several
    responses. Never write a later turn before accepting the current one.
    """
    turns=[];buffer=[];positions=[]
    for number,line in enumerate(frame.splitlines(),1):
        if not line.strip():
            if buffer:
                turns.append({'text':'\n'.join(buffer)+'\n\n','frame_lines':positions})
                buffer=[];positions=[]
            continue
        buffer.append(line);positions.append(number)
        if len(buffer)==1 and not line.strip().endswith(':'):
            turns.append({'text':line+'\n\n','frame_lines':positions})
            buffer=[];positions=[]
    if buffer:turns.append({'text':'\n'.join(buffer)+'\n\n','frame_lines':positions})
    return turns


class LitexSession:
    def __init__(self,job,root,deadline):
        seed=starting_source(job)
        self.io = JsonProcess([job['litex'],'-strict','-lang','en','-session'],root/'work')
        self.identity = uuid.uuid4().hex
        self.foundation_response=[]
        try:
            for block in litex_blocks(seed):
                passed,response=self.send(block['text'],deadline)
                self.foundation_response.append(response)
                if not passed:
                    raise SessionFault('Litex technical seed loading failed: '+json.dumps(response,ensure_ascii=False))
        except BaseException:
            self.io.close();raise

    @property
    def alive(self):return self.io.alive

    def send(self,source,deadline):
        # A standalone comment also produces an empty REPL response. Remove
        # full-line comments and blank lines so there is exactly one response
        # for this mathematical statement; retain original-to-frame line maps.
        framed,mapping=litex_frame(source)
        turns=litex_repl_turns(framed)
        if not turns:raise SessionFault('No Litex mathematical statement was supplied')
        # Submit only one native turn. In particular, an invalid "have fn ... ="
        # header must fail BEFORE its indented body reaches stdin. Otherwise
        # the body's second response is mistaken for the next candidate's.
        turn=turns[0]
        self.frame_source=turn['text']
        self.frame_line_map=[mapping[i-1] for i in turn['frame_lines']]
        response = self.io.exchange(self.frame_source,deadline)
        if response.get('kind')!='run' or response.get('target')!='repl':
            raise SessionFault('Expected one per-turn Litex repl response, not an exit summary')
        results = response.get('statement_results',[])
        if len(results)>1:
            raise SessionFault('One source block unexpectedly executed multiple statements; context discarded')
        passed = (response.get('run_result')=='success' and not response.get('errors')
                  and not response.get('session_terminated') and response.get('termination') is None
                  and bool(results) and all(r.get('statement_result')=='accepted' for r in results))
        if passed and len(turns)>1:
            self.io.close()
            raise SessionFault('One source block contains multiple native REPL turns; only its first turn was executed, '
                               'and that partial context was discarded. Put explicit function bodies on the same '
                               'physical line as =, and use documented colon blocks. First native response: '+
                               json.dumps(response,ensure_ascii=False))
        if response.get('session_terminated') or response.get('termination') is not None:
            self.io.close()
        return passed,response

    def close(self):self.io.close()


class LeanSession:
    def __init__(self,job,root,deadline):
        seed=starting_source(job)
        repl = Path(job['lean_repl'])
        if not repl.is_file():
            raise SessionFault('Pinned Lean REPL unavailable; whole-file fallback is disabled')
        self.io = JsonProcess([job['lake'],'env',str(repl)],job['lean_project'])
        self.identity = uuid.uuid4().hex
        self.environment = None
        try:
            response = self.io.exchange(json.dumps({'cmd':seed},ensure_ascii=False)+'\n\n',deadline)
            if not self._acceptable(response) or not isinstance(response.get('env'),int):
                raise SessionFault('Lean REPL foundation loading failed: '+json.dumps(response,ensure_ascii=False))
        except BaseException:
            self.io.close()
            raise
        self.environment = response['env']
        self.foundation_response=response
        self.baseline_declarations=set(self.inspect_declarations(deadline,axioms=False)) if job.get('auto_finalize') else set()

    def inspect_declarations(self,deadline,axioms=True):
        from native_index import lean_query,lean_metadata
        response=self.io.exchange(json.dumps({'cmd':lean_query(axioms),'env':self.environment})+'\n\n',deadline)
        if not self._acceptable(response):raise SessionFault('Trusted Lean metadata inspection failed: '+json.dumps(response))
        # Inspection does not adopt a different environment or journal a proof.
        return lean_metadata(response)

    @staticmethod
    def _acceptable(response):
        return (not response.get('error') and not response.get('sorries')
                and not any(m.get('severity')=='error' or 'declaration uses' in str(m.get('data',''))
                            for m in response.get('messages',[])))

    @property
    def alive(self):return self.io.alive

    def send(self,source,deadline):
        before = self.environment
        response = self.io.exchange(json.dumps({'cmd':source,'env':before},ensure_ascii=False)+'\n\n',deadline)
        passed = self._acceptable(response) and isinstance(response.get('env'),int)
        if passed:self.environment = response['env']
        # Never adopt the returned env on a failed command, even if it contains
        # declarations accepted before an error in that command.
        self.environment_transition={'before':before,'after':self.environment,'adopted_returned_env':passed}
        return passed,response

    def close(self):self.io.close()


def litex_blocks(source):
    """Frame indentation-based top-level source; native JSON checks the count.

    Each block is sent separately. Stop at the first rejection, so all earlier
    accepted blocks remain committed and later blocks are explicitly untested.
    """
    blocks = [];buffer = [];has_code = False;comment = False;continued = False;start = 1
    for number,line in enumerate(source.splitlines(keepends=True),1):
        stripped = line.strip()
        if stripped=='"""':
            comment = not comment;buffer.append(line);continue
        code = bool(stripped) and not comment and not stripped.startswith('#')
        top_level = code and not line[:1].isspace() and not continued
        if top_level and has_code:
            blocks.append({'text':''.join(buffer),'line':start})
            buffer=[];has_code=False;start=number
        buffer.append(line)
        has_code = has_code or code
        if code:
            continued = line.split('#',1)[0].rstrip().endswith('\\\\')
    if has_code:blocks.append({'text':''.join(buffer),'line':start})
    return blocks


class SessionLedger:
    def __init__(self,root,job):
        self.root = Path(root);self.job=job;self.native=None
        self.path = self.root/'session-journal.json'
        self.data = json.loads(self.path.read_text()) if self.path.exists() else {
            'language':job['language'],'entries':[],'starts':0,'restarts':0,'invalidations':[]}
        self.frames = [];self.replayed = 0;self.candidate_requests=0

    def close(self):
        if self.native:self.native.close()
        self.native=None

    def blocks(self,source):
        return litex_blocks(source) if self.job['language']=='litex' else [{'text':source,'line':1}]

    def _save(self):save(self.path,self.data)

    def _send(self,source,deadline,*,replay,path,index,line=1):
        start=time.monotonic()
        if not replay:self.candidate_requests+=1
        request_id=uuid.uuid4().hex
        def log(value):
            with (self.root/'session-events.jsonl').open('a') as stream:
                stream.write(json.dumps({'request_id':request_id,'session_id':self.native.identity,
                                         'controller_pid':os.getpid(),
                                         'monotonic':time.monotonic(),**value},ensure_ascii=False)+'\n')
                stream.flush();os.fsync(stream.fileno())
        log({'kind':'native_request','path':path,'block_index':index,'replay':replay,
             'source_sha256':sha(source),'source':source})
        try:passed,response=self.native.send(source,deadline)
        except BaseException as error:
            log({'kind':'native_error','error':str(error),'seconds':time.monotonic()-start,
                 'path':path,'block_index':index,'replay':replay})
            raise
        frame={'path':path,'block_index':index,'source_block_start_line':line,'replay':replay,'passed':passed,
               'seconds':time.monotonic()-start,'native':response}
        if isinstance(self.native,LeanSession):
            frame['environment_transition']=dict(self.native.environment_transition)
            if not passed:
                from diagnostic_context import lean_source_line
                context=lean_source_line(source,response)
                if context:frame['diagnostic_source']=context
        else:
            frame['submitted_source']=self.native.frame_source
            frame['frame_line_to_block_line']=self.native.frame_line_map
        self.frames.append(frame)
        log({'kind':'native_response',**frame})
        return passed,response

    def _ensure(self,deadline):
        if self.native and self.native.alive:return
        self.close()
        if self.data['starts']:self.data['restarts']+=1
        self.data['starts']+=1;self._save()
        cls=LitexSession if self.job['language']=='litex' else LeanSession
        start=time.monotonic()
        try:self.native=cls(self.job,self.root,deadline)
        except BaseException as error:
            with (self.root/'session-events.jsonl').open('a') as stream:
                stream.write(json.dumps({'kind':'session_start_error','seconds':time.monotonic()-start,'error':str(error)})+'\n')
            raise
        with (self.root/'session-events.jsonl').open('a') as stream:
            stream.write(json.dumps({'kind':'session_start','session_id':self.native.identity,
                                     'pid':self.native.io.process.pid,'seconds':time.monotonic()-start,
                                     'foundation_response':getattr(self.native,'foundation_response',None)},ensure_ascii=False)+'\n')
        for entry in self.data['entries']:
            passed,_=self._send(entry['text'],deadline,replay=True,path=entry['path'],index=entry['block_index'],line=entry.get('source_line',1))
            if not passed:
                self.close()
                raise SessionFault('Previously accepted source failed replay; no continuation permitted')
            self.replayed+=1

    def _changed(self):
        cache={}
        for index,entry in enumerate(self.data['entries']):
            path=entry['path']
            if path not in cache:
                file=self.root/'work'/path
                cache[path]=self.blocks(file.read_text()) if file.is_file() else []
            blocks=cache[path]
            if entry['block_index']>=len(blocks) or sha(blocks[entry['block_index']]['text'])!=entry['sha256']:
                return index,path
        return None

    def check(self,path,source,deadline):
        self.frames=[];self.replayed=0;self.candidate_requests=0;invalidated=[]
        starting_source(self.job)
        if self.job['language']=='litex':litex_frame(source)
        changed=self._changed()
        if changed:
            index,changed_path=changed
            invalidated=self.data['entries'][index:]
            self.data['entries']=self.data['entries'][:index]
            self.data['invalidations'].append({'changed_path':changed_path,
                                              'invalidated':[e['id'] for e in invalidated]})
            self._save();self.close()
            if changed_path!=path:
                return self._result(False,invalidated,error='Recheck changed prerequisite first: '+changed_path)
        self._ensure(deadline)
        blocks=self.blocks(source)
        known={(e['path'],e['block_index'],e['sha256']) for e in self.data['entries']}
        passed=True
        for index,block in enumerate(blocks):
            text=block['text'];fingerprint=sha(text)
            if (path,index,fingerprint) in known:continue
            passed,response=self._send(text,deadline,replay=False,path=path,index=index,line=block['line'])
            if not passed:break
            entry={'id':uuid.uuid4().hex,'path':path,'block_index':index,'source_line':block['line'],
                   'sha256':fingerprint,'text':text}
            if self.job.get('auto_finalize') and self.job['language']=='litex':entry['native']=response
            self.data['entries'].append(entry);self._save()
        return self._result(passed,invalidated)

    def _result(self,passed,invalidated,error=None):
        return {**self.snapshot(),'passed':passed,'frames':self.frames,'replayed_blocks':self.replayed,
                'invalidated_blocks':[{'path':e['path'],'block_index':e['block_index']} for e in invalidated],
                'controller_error':error}

    def snapshot(self):
        return {'session_id':self.native.identity if self.native else None,
                'session_pid':self.native.io.process.pid if self.native else None,
                'session_alive':bool(self.native and self.native.alive),
                'lean_environment':getattr(self.native,'environment',None),
                'accepted_blocks':len(self.data['entries']),'starts':self.data['starts'],
                'restarts':self.data['restarts']}

    def status(self,include_source=False):
        value={**self.snapshot(),'accepted_entries':[{k:e[k] for k in ('id','path','block_index','sha256')} for e in self.data['entries']]}
        if include_source:
            value['accepted_source']=assemble_final(self.job,'\n\n'.join(e['text'].rstrip() for e in self.data['entries'])+'\n')
        return value
