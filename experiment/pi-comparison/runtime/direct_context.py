"""Local prompt preparation and error routing; no model calls or source mutation."""
import hashlib
import json
from pathlib import Path
import re
from seed_support import library_source
from diagnostic_context import locate,syntax_issue,code_only


def code_without_comments(text,language):
    """Compact a DISPLAY COPY only. Preserve quoted strings and code newlines."""
    out=[];i=0;depth=0;quoted=False;block=False
    while i<len(text):
        pair=text[i:i+2];char=text[i]
        if language=='litex' and not quoted and text.startswith('"""',i):
            block=not block;i+=3;continue
        if block:
            if char=='\n':out.append('\n')
            i+=1;continue
        if depth:
            if pair=='/-':depth+=1;i+=2;continue
            if pair=='-/':depth-=1;i+=2;out.append(' ');continue
            if char=='\n':out.append('\n')
            i+=1;continue
        if quoted:
            out.append(char)
            if char=='\\' and i+1<len(text):out.append(text[i+1]);i+=2;continue
            if char=='"':quoted=False
            i+=1;continue
        if char=='"':quoted=True;out.append(char);i+=1;continue
        if language=='lean' and pair=='/-':depth=1;i+=2;out.append(' ');continue
        if (language=='lean' and pair=='--') or (language=='litex' and char=='#'):
            end=text.find('\n',i);i=len(text) if end<0 else end;continue
        out.append(char);i+=1
    if depth or quoted or block:raise ValueError('Unclosed comment/string in predecessor display copy')
    return '\n'.join(line.rstrip() for line in ''.join(out).splitlines() if line.strip())+'\n'


def prepare_context(root,job,limit=18000):
    source=library_source(job)
    removed=True
    try:code=code_without_comments(source,job['language']) if source else ''
    except ValueError:code=source;removed=False
    manifest=root/'input/source-manifest.json'
    files=json.loads(manifest.read_text())['reading_policy'].get('context_text_files',[]) if manifest.exists() else []
    context={name:(root/'input'/name).read_text() for name in files}
    inline=len(code)<=limit
    if not inline:code=''
    source_context_inline=sum(len(t) for t in context.values())<=12000
    data={'version':'direct-context-v1','library_complete':inline,'library_source_sha256':hashlib.sha256(source.encode()).hexdigest(),
          'display_only_comments_removed':removed,'library_code':code,'original_context_complete':source_context_inline,
          'original_context':context if source_context_inline else {},'source_context_files':files,
          'note':'The verifier receives the unchanged original library. This is a prompt display copy; no theorem proof is supplied beyond already published predecessors.'}
    (root/'input/direct-context.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    job['direct_candidate_ready']=inline and source_context_inline


def procedures(job):
    return json.loads(Path(job['docs']['procedures']).read_text())['patterns']


def first_diagnostic(language,receipt):
    """Select the first new native error, without searching source identifiers."""
    for index,frame in enumerate(receipt.get('native_frames',[])):
        if frame.get('replay'):continue
        native=frame.get('native',{})
        errors=list(native.get('errors',[]))
        if language=='lean':
            errors.extend(m for m in native.get('messages',[]) if m.get('severity')=='error')
        if not errors and native.get('error'):errors=[{'message':native['error']}]
        if errors:
            error=errors[0]
            if not isinstance(error,dict):error={'message':str(error)}
            message=error.get('message',error.get('data',''))
            if not isinstance(message,str):message=json.dumps(message,ensure_ascii=False)
            return {'frame_index':index,'block_index':frame.get('block_index'),
                    'phase':error.get('phase'),'message':message,
                    'source_location':error.get('source_location',error.get('pos')),
                    'source_context':locate(error,frame,language)},error
    return None,{}


def repair_hints(job,receipt):
    if not job.get('direct_protocol') or receipt.get('passed'):return None
    language=job['language'];diagnostic,error=first_diagnostic(language,receipt)
    message=(diagnostic['message'] if diagnostic else '').lower()
    statement=code_only(str(error.get('statement',error.get('failed_statement',''))),language).lower()
    context=(diagnostic or {}).get('source_context',{'code':''})
    issue=syntax_issue(language,context,message,(diagnostic or {}).get('phase'))
    chosen=[];actions=[];rule='native_obligation'
    # Error messages take precedence. A source identifier containing "witness"
    # or the domain GeoPoint is not evidence for an existential/equality repair.
    undefined=any(token in message for token in ('undefined name','unknown identifier','unknown constant'))
    if undefined and re.search(r"[`'\"]prop[`'\"]",message):
        rule='predicate_definition';chosen=['predicate_definition']
        actions.append('Define a predicate with prop name(parameters): and its fact body; do not declare a function returning Prop. Apply it as $name(arguments).'
                       if language=='litex' else 'Define a predicate as def name (parameters) : Prop := body; use its actual argument list.')
    elif issue=='proof_goal_layout':
        rule=issue
        actions.append('A simple ? goal line has no trailing colon. In by cases, state the common conclusion as ? G, then use case H: for each branch. The common goal and the case condition have different roles. Preserve the original conclusion and prove it in every branch; commas in an outer parameter list are unrelated to this error.')
    elif issue=='contradiction_layout':
        rule=issue
        actions.append('impossible is syntax inside a by contra proof block, not a function or library declaration to look up. Use the checked block shape with ? target and its required impossible clause. Justify an actual contradiction using available premises and the counter-assumption introduced by by contra; do not assert an unproved target or false fact.')
    elif issue in ('set_comprehension','set_membership'):
        rule=issue;chosen=['sets_membership']
        actions.append('Use {x T: condition} for a set comprehension; a vertical bar is not the binder separator. Keep the binder domain and predicate unchanged.'
                       if issue=='set_comprehension' else 'For a membership fact use x $in S, not x in S. Check the located source line; retain its quantifiers and hypotheses.')
    elif issue=='logical_composition':
        rule=issue;chosen=['logical_composition']
        actions.append('The parser is treating parentheses as an object expression. Name the logical subcondition with a predicate and compose its application; preserve conjunction/disjunction and their scopes.')
    elif issue=='existential_spelling':
        rule=issue;chosen=['exist_elimination']
        actions.append('Write the existential keyword as exist, with st { ... }. Preserve its variables, domains and complete body.')
    elif issue=='predicate_constraints':
        rule='parameter_constraints';chosen=['parameter_constraints','quantifier_composition']
        actions.append('Do not copy constrained function-parameter syntax into a prop parameter list. Express the intended conditional with explicit predicates/universal hypotheses using supported syntax; preserve its original domain and logical meaning.')
    elif issue=='quantifier_composition':
        rule=issue;chosen=['quantifier_composition']
    elif language=='lean' and 'unexpected token' in message and '/--' in message:
        rule='declaration_layout'
        actions.append('Put a /-- ... -/ documentation comment before the complete declaration, including modifiers such as noncomputable or private. Do not put it between a modifier and def/theorem, or between a declaration keyword and its name. Ordinary -- comments may be used between declarations.')
    elif 'nested `forall`' in message:
        rule='quantifier_composition';chosen=['quantifier_composition']
    elif undefined:
        rule='undefined_symbol'
        if language=='litex' and re.search(r"[`'\"]or[`'\"]",message):
            actions.append('Write a disjunction as one fact line: P or Q. An indented line beginning with or does not continue the preceding fact.')
        else:
            actions.append('Check the exact missing name against the seed and published predecessor declarations. Retain every helper needed by this COMPLETE replacement candidate, declared before its use. A helper from an earlier rejected version is not a published predecessor. Do not invent a replacement builtin or assume a failed predecessor is available.')
    elif language=='lean' and 'membership' in message and ('synthesize' in message or 'instance' in message):
        rule='set_membership';chosen=['sets_membership']
        actions.append('Check the element type and set type at the native location. Use S : Set T and x : T for x ∈ S; a membership proof and a set-valued function have different types.')
    elif (error.get('category')=='well_defined' or (diagnostic or {}).get('phase')=='predicate_signature'
          or 'well-defined' in message or language=='lean' and any(s in message for s in ('type mismatch','application type mismatch','function expected'))):
        rule='parameter_constraints';chosen=['parameter_constraints']
        actions.append('Check declared domains and the actual argument list at the failing use. Establish every precondition of a restricted operation before applying it. Use power_set(T) in Litex or Set T in Lean when a parameter must be a set of T-elements. In Lean include explicit proof arguments where required. Do not delete source conditions, add axioms or change the target to obtain well-definedness.')
    elif language=='litex' and ((diagnostic or {}).get('phase')=='parse' or any(token in message for token in
            ('unexpected indent','expected comparison operator','trailing tokens in fact','expected object','expected `','expected {'))):
        rule='syntax_layout'
        if 'trailing tokens in fact' in message:
            if context['code'].rstrip().endswith(',') or re.search(r'trailing tokens in fact:\s*`,`\s*$',message):
                rule='trailing_fact_comma'
                actions.append('Remove the extra trailing comma from this fact line. Keep commas that separate parameter names in declaration headers.')
            else:
                rule='trailing_fact_token'
                actions.append('Repair the exact extra token reported on the located fact line. Do not infer a comma error from commas elsewhere in the declaration, or move quantifiers merely because the declaration contains forall.')
        elif re.search(r'\bnot\s+exist\b',statement):
            chosen=['not_exist']
        elif re.search(r'\bforall\b',statement) or len(re.findall(r'\bexist\b',statement))>1:
            rule='quantifier_composition';chosen=['quantifier_composition']
        elif re.search(r'\bexist\b',statement):chosen=['exist_elimination']
        elif re.search(r'\bhave\s+fn\b',statement):chosen=['function_layout']
    else:
        # These fields describe the actual failed obligation, not arbitrary
        # source code or a serialized whole native response.
        obligation=message+' '+str(error.get('obligation','')).lower()
        if re.search(r'\bnot\s+exist\b|\bnegated existential\b',obligation):chosen=['not_exist']
        elif re.search(r'\bexistential\b|\bexist\b|\bwitness\b',obligation):chosen=['exist_elimination']
        elif 'coordinate equality' in obligation or 'tuple_equal_from_coordinates' in obligation:chosen=['coordinate_equality']
    if 'quantifier_composition' in chosen:
        actions.append('Name inner quantified conditions as separate predicates and compose their applications. Keep every free parameter explicit and preserve quantifier order, scope and witness dependencies; never exchange forall/exists merely to satisfy the parser.')
    if language=='litex' and any(key in chosen for key in ('not_exist','exist_elimination')):
        actions.append('An existential is a complete fact: exist ... st {...}, never exists ... :. Use obtain only to extract a witness from an established existential. Do not write P and exist ... as one atomic expression.')
    if not actions:
        actions.append('Repair the first actual native error before changing later statements. Use established premises and definition expansions; preserve every source condition and conclusion. A failed proof search does not show the target is false.')
    selected=[p for p in procedures(job) if p['id'] in set(chosen)][:2]
    if diagnostic:
        diagnostic={**diagnostic,'message':diagnostic['message'][:512],
                    'message_truncated':len(diagnostic['message'])>512}
        source=diagnostic['source_context']
        diagnostic['source_context']={k:v for k,v in source.items() if k!='code'}
        diagnostic['source_context']['text']=source.get('text','')[:512]
        diagnostic['source_context']['text_truncated']=len(source.get('text',''))>512
    references=[]
    chapter={'set_comprehension':'s06','set_membership':'s06','sets_membership':'s06',
             'parameter_constraints':'s04','logical_composition':'s08','quantifier_composition':'s07',
             'predicate_definition':'s05','undefined_symbol':'s03','function_layout':'s04',
             'declaration_layout':'s03',
             'proof_goal_layout':'s12','contradiction_layout':'s12',
             'exist_elimination':'s11','existential_spelling':'s11','not_exist':'s11','coordinate_equality':'s13'}
    key=chapter.get(rule) or next((chapter[p['id']] for p in selected if p['id'] in chapter),None)
    core=job.get('docs',{}).get('core')
    if key and core:
        from doc_sections import sections
        text=Path(core).read_text();section=next((s for s in sections(text) if s['id']==key),None)
        if section:references=[{'topic':'core','section':key,'title':section['title'],'text':section['text'],
                                'reference_sha256':hashlib.sha256(text.encode()).hexdigest()}]
    return {'origin':'deterministic_local_error_routing','version':'source-location-v4-proof-layout','model_calls':0,
            'matched_rule':rule,'diagnostic':diagnostic,'actions':actions,'reference_patterns':selected,
            'reference_sections':references,
            'note':'These are checked generic reference patterns, not proofs of the current target. The original native feedback below is unchanged.'}
