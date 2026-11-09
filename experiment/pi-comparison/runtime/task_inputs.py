"""Language-neutral full-catalog inputs. No model or historical proof access."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import shutil
import pdfplumber
from agent_language import english_record,require_english,SUCCESS_POLICY

BASE=Path(__file__).resolve().parents[1]
TASKS=BASE.parents[1]/'tasks'


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def catalog():
    rows=[json.loads(line) for line in (TASKS/'tasks.jsonl').read_text().splitlines()]
    meta=json.loads((TASKS/'catalog.json').read_text())
    if len(rows)!=meta['total_tasks'] or len({r['id'] for r in rows})!=len(rows):
        raise ValueError('Invalid task catalog')
    if sum(r['kind']=='proposition' for r in rows)!=meta['primary_accuracy_denominator']:
        raise ValueError('Invalid proposition denominator')
    return rows,meta


def source_pdf():
    _,meta=catalog();path=TASKS/meta['source']['local_cache']
    if digest(path)!=meta['source']['sha256']:raise ValueError('Source PDF hash mismatch')
    return path


def specification(record):
    if record['id']=='EUCLID.I.P001':
        task=json.loads((BASE/'agent-kit/examples/I1/task.json').read_text())
        task['status']='source_to_library_automatic_machine_acceptance'
        task['instruction_language']='en'
        task['success_policy']=dict(SUCCESS_POLICY)
        require_english(task,'Task specification')
        return task
    record=english_record(record)
    return {'task_id':record['id'],'status':'source_specification_automatic_machine_acceptance',
            'instruction_language':'en','title':record['title'],
            'success_policy':dict(SUCCESS_POLICY),
            'book':record['book'],'kind':record['kind'],'source_order':record['source_order'],
            'source':record['source_span'],'instruction':record['instruction'],
            'acceptance':record['acceptance'],
            'required_clauses':[
                {'clause_id':'source_content','requirement':('Provide the definitions in the source and any explicitly asserted mathematical claims. Do not invent additional semantic-bridge theorems.' if record['kind']=='definition' else 'Cover ALL mathematical statements, branches, witnesses and unheaded consequences in the bounded source.')},
                {'clause_id':'encoding','requirement':'State domains, quantifiers, nondegeneracy and the meaning of every new representation; check well-definedness and explain the source correspondence.'}],
            'foundation_policy':'Modern analytic model. Source postulates/common notions are modeled and proved, not introduced as new unchecked axioms. Build missing domains, including 3D, as checked definitions. Do not assume failed predecessors.',
            'dependencies':record['dependencies'],
            'primary_denominator':record['kind']=='proposition',
            'semantic_audit':'Optional post-run annotation, never a prerequisite for automatic task success or publication. Clause labels are a coverage checklist, not a pre-reviewed formal target.'}


def required_clauses(task):
    if task.get('task_id')=='EUCLID.I.P001':return ['C1','C2','C3','C4','C5']
    return [c['clause_id'] for c in task['required_clauses']]


def render_record(record,output,document):
    output.mkdir(parents=True,exist_ok=True)
    span=record['source_span'];pieces=[];items=[]
    for number in range(span['start']['pdf_page'],span['end_exclusive']['pdf_page']+1):
        page=document.pages[number-1]
        top=max(0,span['start']['y_from_top_pt']-1) if number==span['start']['pdf_page'] else 0
        bottom=max(0,span['end_exclusive']['y_from_top_pt']-1) if number==span['end_exclusive']['pdf_page'] else page.height
        if bottom<=top:continue
        main=page.within_bbox((page.width/2,top,page.width,bottom)).filter(
            lambda obj:obj.get('object_type')!='char' or obj.get('size',10)>8.1)
        notes=page.within_bbox((0,top,page.width,bottom)).filter(
            lambda obj:obj.get('object_type')=='char' and obj.get('size',10)<=8.1)
        pieces.append((main.extract_text(x_tolerance=1) or '')+'\n'+(notes.extract_text(x_tolerance=1) or ''))
        items.append({'task_id':record['id'],'pdf_page':number,
                      'y_start_pt':top,'y_end_exclusive_pt':bottom})
    text='\n'.join(pieces).strip()+'\n'
    if not items or not text.strip():raise ValueError('Empty source pack: '+record['id'])
    (output/(record['id']+'.txt')).write_text(text)
    seal={'format':'text-only-v1','task_id':record['id'],'source_sha256':span['sha256'],'items':items,
          'files':{p.name:digest(p) for p in sorted(output.iterdir()) if p.is_file()}}
    (output/'pack.json').write_text(json.dumps(seal,ensure_ascii=False,indent=2)+'\n')
    return seal


def verify_pack(folder,record,*,allow_legacy=False):
    seal=json.loads((folder/'pack.json').read_text())
    if seal['task_id']!=record['id'] or seal['source_sha256']!=record['source_span']['sha256']:
        raise ValueError('Source pack identity mismatch')
    for name,value in seal['files'].items():
        if Path(name).name!=name or digest(folder/name)!=value:raise ValueError('Source pack changed: '+name)
    if not allow_legacy:
        if seal.get('format')!='text-only-v1' or set(seal['files'])!={record['id']+'.txt'}:
            raise ValueError('Source pack is not text-only; prepare a new text-only batch')
        if any(p.is_file() and p.name not in {record['id']+'.txt','pack.json'} for p in folder.iterdir()):
            raise ValueError('Unexpected file in text-only source pack')
        if any('image' in item for item in seal['items']):raise ValueError('Image metadata in text-only source pack')
    return seal


def copy_text_pack(origin,target,record):
    """Convert a verified old cache without ever copying an image to the new one."""
    original=verify_pack(Path(origin),record,allow_legacy=True)
    target.mkdir(parents=True,exist_ok=False)
    name=record['id']+'.txt'
    shutil.copyfile(Path(origin)/name,target/name)
    seal={'format':'text-only-v1','task_id':record['id'],'source_sha256':original['source_sha256'],
          'items':[{k:v for k,v in item.items() if k in ('task_id','pdf_page','y_start_pt','y_end_exclusive_pt')}
                   for item in original['items']],
          'files':{name:original['files'][name]}}
    (target/'pack.json').write_text(json.dumps(seal,ensure_ascii=False,indent=2)+'\n')


def freeze_sources(cache,records):
    """Prepare each distinct source span once, reused byte-for-byte by both sides."""
    pdf=source_pdf();cache=Path(cache);cache.mkdir(parents=True,exist_ok=True)
    with pdfplumber.open(pdf) as document:
        for index,record in enumerate(records,1):
            folder=cache/record['id']
            if (folder/'pack.json').exists():seal=verify_pack(folder,record)
            else:
                if folder.exists():shutil.rmtree(folder)
                seal=render_record(record,folder,document)
            if index%25==0:print(json.dumps({'source_packs_prepared':index,'total':len(records)}),flush=True)


def package_task(output,task_id,cache=None):
    rows,_=catalog();record=next(r for r in rows if r['id']==task_id)
    # Prior foundations of this book are context, never free formal results.
    context=[r for r in rows if r['book']==record['book'] and r['source_order']<record['source_order']
             and r['kind'] in ('definition','postulate','common_notion')]
    selected=context+[record]
    output.mkdir(parents=True,exist_ok=True)
    if any(output.iterdir()):raise ValueError('Source input directory must be empty; do not reuse material from another task')
    items=[];files={}
    if cache is None:
        import tempfile
        with tempfile.TemporaryDirectory(prefix='euclid-source-') as temporary:
            freeze_sources(Path(temporary),selected)
            return package_task(output,task_id,Path(temporary))
    for item in selected:
        folder=Path(cache)/item['id'];seal=verify_pack(folder,item)
        name=item['id']+'.txt'
        shutil.copyfile(folder/name,output/name);files[name]=seal['files'][name]
        items.extend(seal['items'])
    manifest={'source_sha256':record['source_span']['sha256'],'current_task':task_id,
              'context_task_ids':[r['id'] for r in context],'items':items,'files':files,
              'context_policy':'Source context only; no predecessor is automatically proved.',
              'input_modality':'text_only','images_available':False,
              'reading_policy':{
                  'version':'text-only-v1',
                  'primary_specification':'task.json',
                  'primary_text_files':[record['id']+'.txt'],
                  'context_text_files':[r['id']+'.txt' for r in context],
                  'optional_image_files':[],
                  'image_role':'No images are provided or readable, including initial figures, proof diagrams and screenshots.',
                  'text_authority':'Use task.json and the extracted .txt. Report missing/garbled/ambiguous initial conditions; do not invent conditions or seek image fallback.'},
              'source_text_review':'Text completeness and semantic target review remain pending; no automatic image fallback.'}
    (output/'source-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    (output/'task.json').write_text(json.dumps(specification(record),ensure_ascii=False,indent=2)+'\n')
    return manifest
