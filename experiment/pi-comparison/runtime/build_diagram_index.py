#!/usr/bin/env python3
"""Offline, reproducible PDF graphic inventory; no OCR or model calls.

Recognize vector drawings in the English column, excluding thin page rules and
typeset fraction bars. Explicit links below handle figures placed before an
auxiliary heading. The index controls what images can enter an agent's input.
"""
import collections
import hashlib
import json
from pathlib import Path
import re
import pdfplumber
from task_inputs import catalog,source_pdf,BASE

OUTPUT=BASE/'contracts/source-diagrams.json'
REFERENCES={
    'EUCLID.X.COR003':('EUCLID.X.P006',[0],'Lettered A–F line arrangement from the parent proposition.'),
    'EUCLID.XI.LEM001':('EUCLID.XI.P023',[2],'Semicircle ABC for the auxiliary construction, not the preceding solid.'),
    'EUCLID.XII.LEM001':('EUCLID.XII.P002',[0],'Circles ABCD and EFGH used in the same construction.'),
    'EUCLID.XII.LEM002':('EUCLID.XII.P004',[0],'Explicitly refers to the same pyramid/prism figure.'),
    'EUCLID.XII.COR003':('EUCLID.XII.P017',[0],'Lettered sphere/polyhedron construction from the parent.'),
    'EUCLID.XIII.LEM001':('EUCLID.XIII.P002',[0],'Lettered AC, BC and DC configuration from the parent.'),
    'EUCLID.XIII.LEM002':('EUCLID.XIII.P013',[1],'Semicircle/square figure specifically used by the lemma.'),
    'EUCLID.XIII.LEM003':('EUCLID.XIII.P018',[1],'Pentagon ABCDE and center F, preceding the lemma heading.'),
}


def span_hash(record):
    return hashlib.sha256(json.dumps(record['source_span'],sort_keys=True).encode()).hexdigest()


def graphic_object(obj):
    kind=obj['object_type'];w=obj['width'];h=obj['height']
    return ((kind=='image' and min(w,h)>3) or
            (kind in ('line','curve') and obj.get('stroke') and max(w,h)>3) or
            (kind=='rect' and min(w,h)>3))


def figure_bbox(objects,page,words,top,bottom):
    x0=min(o['x0'] for o in objects);y0=min(o['top'] for o in objects)
    x1=max(o['x1'] for o in objects);y1=max(o['bottom'] for o in objects)
    # Preserve nearby point/number labels, without pulling prose lines into the
    # crop. This is layout extraction, not interpretation of diagram facts.
    labels=[]
    for word in words:
        if not re.fullmatch(r"(?:[A-Z][A-Z0-9′']{0,2}|[0-9]+)",word['text']):continue
        if not (x0-24<=word['x0']<=x1+24 and y0-24<=word['top']<=y1+24):continue
        if any(abs(other['top']-word['top'])<3 and re.search('[a-z]',other['text']) for other in words):continue
        labels.append(word)
    x0=min([x0]+[w['x0'] for w in labels]);y0=min([y0]+[w['top'] for w in labels])
    x1=max([x1]+[w['x1'] for w in labels]);y1=max([y1]+[w['bottom'] for w in labels])
    bbox=[round(max(page.width/2,x0-3),3),round(max(top,y0-3),3),
          round(min(page.width,x1+3),3),round(min(bottom,y1+3),3)]
    # A label can sit very close to the previous prose line. Cropping alone
    # leaves cut-off text at the edge. Mask only identified prose word boxes;
    # retain the original pixels of diagram labels, without recreating glyphs.
    prose=[]
    for word in words:
        if not (word['x1']>bbox[0] and word['x0']<bbox[2] and word['bottom']>bbox[1] and word['top']<bbox[3]):continue
        row=[w for w in words if abs(w['top']-word['top'])<3]
        lower=[w for w in row if re.search('[a-z]',w['text'])]
        if lower and (len(row)>=3 or any(len(w['text'])>8 for w in lower)):prose.append(word)
    boxes=lambda selected:[[round(w[k],3) for k in ('x0','top','x1','bottom')] for w in selected]
    return bbox,boxes(prose),boxes(labels)


def build():
    rows,_=catalog();pdf=source_pdf();by_page=collections.defaultdict(list)
    entries={r['id']:{'source_span_sha256':span_hash(r),'own_figures':[],
                       'referenced_figures':[],'review':'PDF graphics inventory; semantic necessity not inferred'} for r in rows}
    for record in rows:
        span=record['source_span']
        for number in range(span['start']['pdf_page'],span['end_exclusive']['pdf_page']+1):by_page[number].append(record)
    with pdfplumber.open(pdf) as document:
        for number in sorted(by_page):
            page=document.pages[number-1]
            graphics=[o for kind in ('line','curve','rect','image') for o in page.objects.get(kind,[])
                      if (o['x0']+o['x1'])/2>=page.width/2 and graphic_object(o)]
            words=[w for w in page.extract_words(x_tolerance=2,y_tolerance=2) if w['x0']>=page.width/2]
            for record in by_page[number]:
                span=record['source_span']
                top=max(0,span['start']['y_from_top_pt']-1) if number==span['start']['pdf_page'] else 0
                bottom=max(0,span['end_exclusive']['y_from_top_pt']-1) if number==span['end_exclusive']['pdf_page'] else page.height
                shapes=[o for o in graphics if top<=(o['top']+o['bottom'])/2<bottom]
                if not shapes:continue
                bbox,prose_boxes,label_boxes=figure_bbox(shapes,page,words,top,bottom)
                if bbox[2]<=bbox[0] or bbox[3]<=bbox[1]:raise ValueError('Invalid figure bounds')
                figures=entries[record['id']]['own_figures']
                figures.append({'figure_index':len(figures),'pdf_page':number,'bbox_pt':bbox,
                                'prose_masks_pt':prose_boxes,'preserved_labels_pt':label_boxes,
                                'object_count':len(shapes),'evidence_types':sorted({o['object_type'] for o in shapes})})
            page.close()
    for task_id,(owner,indices,reason) in REFERENCES.items():
        for index in indices:
            entries[owner]['own_figures'][index]  # validate reference, never silently omit
            entries[task_id]['referenced_figures'].append({'owner_task_id':owner,'figure_index':index,'reason':reason})
        entries[task_id]['review']='Auxiliary text checked for a lettered/shared figure reference; figure crops sampled visually'
    counts=collections.Counter('with_images' if entries[r['id']]['own_figures'] or entries[r['id']]['referenced_figures'] else 'text_only' for r in rows)
    data={'schema_version':1,'policy_id':'text-primary-figure-only-v1','source_sha256':hashlib.sha256(pdf.read_bytes()).hexdigest(),
          'method':'English-column PDF drawing objects; exclude thin raster page rules and thin typesetting bars; preserve nearby original label pixels; mask adjacent prose word boxes. Explicit auxiliary references are curated above.',
          'visual_review':'Sampled planar, arithmetic, irrational-magnitude and solid figures plus auxiliary shared-figure references; not an exhaustive semantic diagram audit.',
          'counts':dict(counts),'own_figure_count':sum(len(e['own_figures']) for e in entries.values()),'tasks':entries}
    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'output':str(OUTPUT),'counts':dict(counts),'own_figures':data['own_figure_count'],'model_calls':0}))


if __name__=='__main__':build()
