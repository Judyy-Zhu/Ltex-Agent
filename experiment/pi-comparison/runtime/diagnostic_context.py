"""Source-location helpers for native errors; never rewrite verifier input."""
import re


def code_only(source,language):
    """Mask literals/comments while preserving every offset and newline."""
    out=list(source);i=0;depth=0;triple=False;quoted=False
    while i<len(source):
        pair=source[i:i+2];char=source[i]
        if depth:
            if pair=='/-':depth+=1;out[i:i+2]=[' ',' '];i+=2;continue
            if pair=='-/':depth-=1;out[i:i+2]=[' ',' '];i+=2;continue
            if char!='\n':out[i]=' '
            i+=1;continue
        if triple:
            if source.startswith('"""',i):out[i:i+3]=[' ']*3;triple=False;i+=3;continue
            if char!='\n':out[i]=' '
            i+=1;continue
        if quoted:
            if char!='\n':out[i]=' '
            if char=='\\' and i+1<len(source):
                if source[i+1]!='\n':out[i+1]=' '
                i+=2;continue
            if char=='"':quoted=False
            i+=1;continue
        if language=='litex' and source.startswith('"""',i):out[i:i+3]=[' ']*3;triple=True;i+=3;continue
        if language=='lean' and pair=='/-':out[i:i+2]=[' ',' '];depth=1;i+=2;continue
        if char=='"':out[i]=' ';quoted=True;i+=1;continue
        if (language=='litex' and char=='#') or (language=='lean' and pair=='--'):
            end=source.find('\n',i);end=len(source) if end<0 else end
            out[i:end]=[' ']*(end-i);i=end;continue
        i+=1
    return ''.join(out)


def lean_source_line(source,response):
    for error in response.get('messages',[]):
        if error.get('severity')!='error':continue
        pos=error.get('pos') or {};line=pos.get('line');lines=source.splitlines()
        if isinstance(line,int) and 1<=line<=len(lines):
            return {'line':line,'column':pos.get('column'),'text':lines[line-1],
                    'code':code_only(source,'lean').splitlines()[line-1]}
        break
    return None


def locate(error,frame,language):
    """Native positions take precedence over normalized statement text."""
    if language=='lean' and frame.get('diagnostic_source'):
        value=dict(frame['diagnostic_source'])
        value.update(source_line=frame.get('source_block_start_line',1)+value['line']-1,
                     path=frame.get('path'),confidence='native_location')
        return value
    position=error.get('source_location',error.get('pos')) or {}
    source=frame.get('submitted_source') or str(error.get('statement',error.get('failed_statement','')))
    line=position.get('line');lines=source.splitlines()
    if isinstance(line,int) and 1<=line<=len(lines):
        mapping=frame.get('frame_line_to_block_line',[])
        relative=mapping[line-1] if line<=len(mapping) else line
        return {'line':line,'column':position.get('column'),'text':lines[line-1],
                'code':code_only(source,language).splitlines()[line-1],
                'source_line':frame.get('source_block_start_line',1)+relative-1,
                'path':frame.get('path'),'confidence':'native_location'}
    # A one-line statement has no ambiguity. Multiline unlocated statements
    # are kept out of precise lexical rules; generic phase guidance may apply.
    if len(lines)==1:return {'line':None,'column':None,'text':source,'code':code_only(source,language),
                             'source_line':None,'path':frame.get('path'),'confidence':'single_statement'}
    return {'line':None,'column':None,'text':'','code':'','source_line':None,
            'path':frame.get('path'),'confidence':'unlocated'}


def syntax_issue(language,context,message,phase):
    if language!='litex' or not (phase=='parse' or any(s in message for s in ('expected','undefined name','invalid parameter'))):return None
    code=context['code']
    if 'trailing tokens in fact' in message and re.match(r'^\s*\?\s+(?!forall\b).+:\s*$',code):return 'proof_goal_layout'
    if ('expected `impossible`' in message or
        re.search(r"undefined name [`'\"]impossible[`'\"]",message) and re.match(r'^\s*impossible\b',code)):
        return 'contradiction_layout'
    if re.search(r'\{\s*[^\s{}|]+\s+[^{}|\n]+\|',code):return 'set_comprehension'
    if re.search(r'(?<=[\w)\]])\s+in\s+(?=[\w({])',code):return 'set_membership'
    if 'expected `)`' in message and re.search(r'\b(?:or|and)\b',code):return 'logical_composition'
    if re.search(r'\b(?:and|or)\s+(?:exist|forall)\b',code):return 'quantifier_composition'
    if re.search(r'\bexists\b',code) and 'undefined name' in message:return 'existential_spelling'
    if re.search(r"undefined name [`'\"](?:forall|exist)[`'\"]",message) and re.search(r'\b(?:forall|exist)\b',code):return 'quantifier_composition'
    if 'invalid parameter' in message and re.search(r'^\s*prop\b.*:',code):return 'predicate_constraints'
    return None
