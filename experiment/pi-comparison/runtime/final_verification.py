"""Fresh, independent native verification with measured initialization boundaries.

The controller reads the unchanged saved final source. A NEW Session/REPL loads
its exact frozen prefix, then checks every candidate block. No earlier candidate
environment or acceptance cache is reused. Each original native JSON is retained.
"""
import hashlib
import json
import os
import time
from native_sessions import LeanSession,LitexSession,litex_blocks
from seed_support import starting_source,require_seed_prefix


MODE='split_native_session_v1'


def verify(job,root,source,deadline,receipt):
    require_seed_prefix(job,source)
    prefix=starting_source(job).rstrip()
    if not source.startswith(prefix):raise ValueError('Independent final prefix mismatch')
    candidate=source[len(prefix):].lstrip('\n')
    line_offset=source[:len(source)-len(candidate)].count('\n')
    if not candidate.strip():raise ValueError('Independent final candidate is empty')
    receipt.update(scope='independent_final_session',final_verification_mode=MODE,
                   verified_source_sha256=hashlib.sha256(source.encode()).hexdigest(),
                   final_initialization_seconds=0.0,final_verification_seconds=0.0,
                   native_frames=[],foundation_native=[],passed=False)
    def event(kind):
        with (root/'final-verification-events.jsonl').open('a') as stream:
            stream.write(json.dumps({'kind':kind,'receipt_id':receipt['receipt_id'],
                                     'monotonic':time.monotonic()})+'\n')
            stream.flush();os.fsync(stream.fileno())
    event('final_verification_started')
    native=None;start=time.monotonic()
    try:
        cls=LeanSession if job['language']=='lean' else LitexSession
        load_start=time.monotonic()
        try:native=cls({**job,'auto_finalize':False},root,deadline)
        finally:receipt['final_initialization_seconds']=time.monotonic()-load_start
        receipt.update(independent_session_id=native.identity,independent_pid=native.io.process.pid)
        foundation=native.foundation_response
        receipt['foundation_native']=foundation if isinstance(foundation,list) else [foundation]
        blocks=litex_blocks(candidate) if job['language']=='litex' else [{'text':candidate,'line':1}]
        if not blocks:raise ValueError('Independent final candidate has no statements')
        check_start=time.monotonic()
        try:
            passed=True
            for index,block in enumerate(blocks):
                accepted,response=native.send(block['text'],deadline)
                frame={'path':receipt['entry'],'block_index':index,'replay':False,
                       'source_block_start_line':line_offset+block.get('line',1),
                       'passed':accepted,'native':response}
                if job['language']=='litex':
                    frame.update(submitted_source=native.frame_source,
                                 frame_line_to_block_line=native.frame_line_map)
                elif hasattr(native,'environment_transition'):
                    frame['environment_transition']=native.environment_transition
                    if not accepted:
                        from diagnostic_context import lean_source_line
                        context=lean_source_line(candidate,response)
                        if context:frame['diagnostic_source']=context
                receipt['native_frames'].append(frame)
                if not accepted:passed=False;break
            receipt['passed']=passed
        finally:receipt['final_verification_seconds']=time.monotonic()-check_start
    finally:
        if native:
            receipt['stderr']=''.join(native.io.stderr)
            native.close()
            receipt['session']={'session_id':native.identity,'session_alive':False,
                                'mode':'independent_final','reuses_candidate_environment':False}
        receipt['native_process_seconds']=time.monotonic()-start
        event('final_verification_completed')
