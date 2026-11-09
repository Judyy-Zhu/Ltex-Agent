"""Freeze diagram-only crops; never mount whole-page screenshots for agents."""
import hashlib
import json
import math
from pathlib import Path
import subprocess
from PIL import Image,ImageDraw

INDEX=Path(__file__).resolve().parents[1]/'contracts/source-diagrams.json'


def policy():
    raw=INDEX.read_bytes();data=json.loads(raw)
    if data['schema_version']!=1:raise ValueError('Unsupported diagram policy')
    return data,hashlib.sha256(raw).hexdigest()


def entry(record):
    data,seal=policy();value=data['tasks'][record['id']]
    span=hashlib.sha256(json.dumps(record['source_span'],sort_keys=True).encode()).hexdigest()
    if value['source_span_sha256']!=span or data['source_sha256']!=record['source_span']['sha256']:
        raise ValueError('Diagram policy does not match the task source')
    return value,seal


def freeze_figures(record,folder,pack,pdf):
    selected,seal=entry(record)
    if pack.get('figure_policy_sha256')==seal:return pack
    # Only remove previously generated figure crops, never original source text.
    for figure in pack.get('figure_items',[]):
        name=figure['image']
        if Path(name).name!=name or '-figure-' not in name:raise ValueError('Invalid old figure path')
        (folder/name).unlink(missing_ok=True);pack['files'].pop(name,None)
    figures=[]
    for region in selected['own_figures']:
        name=f"{record['id']}-figure-{region['figure_index']:02}-{region['pdf_page']:03}.png"
        x0,y0,x1,y1=region['bbox_pt'];scale=1.5
        left=math.floor(x0*scale);top=math.floor(y0*scale)
        command=['pdftoppm','-f',str(region['pdf_page']),'-l',str(region['pdf_page']),'-r','108',
                 '-x',str(left),'-y',str(top),'-W',str(math.ceil(x1*scale)-left),
                 '-H',str(math.ceil(y1*scale)-top),'-singlefile','-png',str(pdf),str((folder/name).with_suffix(''))]
        subprocess.run(command,check=True,capture_output=True)
        if region['prose_masks_pt']:
            with Image.open(folder/name) as original:
                clean=original.convert('RGB');draw=ImageDraw.Draw(clean)
                def pixels(box):
                    a,b,c,d=box
                    return (max(0,math.floor((a-0.7)*scale)-left),max(0,math.floor((b-0.7)*scale)-top),
                            min(clean.width,math.ceil((c+0.7)*scale)-left),min(clean.height,math.ceil((d+0.7)*scale)-top))
                for box in region['prose_masks_pt']:
                    x0p,y0p,x1p,y1p=pixels(box)
                    if x1p>x0p and y1p>y0p:draw.rectangle((x0p,y0p,x1p-1,y1p-1),fill='white')
                clean.save(folder/name)
        pack['files'][name]=hashlib.sha256((folder/name).read_bytes()).hexdigest()
        figures.append({**region,'image':name,'owner_task_id':record['id'],'role':'auxiliary_diagram'})
    pack.update(figure_policy_sha256=seal,figure_items=figures)
    (folder/'pack.json').write_text(json.dumps(pack,ensure_ascii=False,indent=2)+'\n')
    return pack
