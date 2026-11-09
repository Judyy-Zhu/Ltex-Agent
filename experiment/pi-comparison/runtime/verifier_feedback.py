"""Language-native solver feedback inside a common checker receipt envelope.

Litex formatting follows the audited legacy litex_llm_formatter.py:
preserve run_result, statement_results and errors in full. Control/process
fields are retained by the controller before any presentation cleanup.
"""
from __future__ import annotations
import json


def clean_litex(result):
    return {'run_result':result.get('run_result'),
            'statement_results':result.get('statement_results',[]),
            'errors':result.get('errors',[])}


def native_feedback(language,receipt):
    if receipt.get('scope') in ('persistent_incremental_session','independent_final_session'):
        frames=[]
        for frame in receipt.get('native_frames',[]):
            if frame.get('replay'):continue
            # Preserve each native response, including its own local indexes
            # and Session control fields. Never merge frames into a fake run.
            value={key:frame[key] for key in ('path','block_index','native','passed')}
            if 'source_block_start_line' in frame:value['source_block_start_line']=frame['source_block_start_line']
            if 'environment_transition' in frame:value['environment_transition']=frame['environment_transition']
            if 'diagnostic_source' in frame:value['diagnostic_source']=frame['diagnostic_source']
            if 'submitted_source' in frame:
                value['submitted_source']=frame['submitted_source']
                value['frame_line_to_block_line']=frame['frame_line_to_block_line']
            frames.append(value)
        value={'frames':frames,'session':receipt.get('session'),'verification_scope':receipt['scope'],
               'note':'Frames contain received native responses for new source blocks. Replay is recorded separately. Empty frames can mean cache/preparation failure OR a request interrupted before its response; inspect controller_error, item_tracking and the full receipt.'}
        return {'format':'litex-session-json' if language=='litex' else 'lean-repl-json',
                'data':value,'text':json.dumps(value,ensure_ascii=False,indent=2),'stderr':receipt.get('stderr','')}
    stdout = receipt.get('stdout') or ''
    stderr = receipt.get('stderr') or ''
    if language=='litex':
        try:
            parsed = json.loads(stdout)
            if not isinstance(parsed,dict):
                raise ValueError('Expected a Litex JSON object')
        except ValueError:
            return {'format':'litex-invalid-json','text':stdout,'stderr':stderr,
                    'presentation_error':'No valid native JSON response; inspect process_status and controller_error.'}
        data = clean_litex(parsed)
        return {'format':'litex-native-json','data':data,
                'text':json.dumps(data,ensure_ascii=False,indent=2),'stderr':stderr}
    return {'format':'lean-cli-text','stdout':stdout,'stderr':stderr,
            'text':'Lean stdout:\n'+stdout+'\nLean stderr:\n'+stderr}


def process_status(language,receipt):
    status = {'exit_code':receipt.get('exit_code'),'timed_out':receipt.get('error')=='checker_timeout'}
    if receipt.get('scope') in ('persistent_incremental_session','independent_final_session'):
        session=receipt.get('session') or {}
        status.update(process_alive=session.get('session_alive',False),
                      session_id=session.get('session_id'),
                      mode='independent_final' if receipt.get('scope')=='independent_final_session' else 'persistent')
    if language=='litex':
        try:
            raw = json.loads(receipt.get('stdout') or '')
        except ValueError:
            raw = {}
        if isinstance(raw,dict):
            status.update(session_terminated=raw.get('session_terminated'),termination=raw.get('termination'))
    return status
