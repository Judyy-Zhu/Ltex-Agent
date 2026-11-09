#!/usr/bin/env python3
"""Validate inventory, partitions, source positions and frozen-source identity."""
import collections
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
EXPECTED=[48,14,37,16,25,33,39,27,36,115,39,18,18]


def read(name):
    return [json.loads(x) for x in (ROOT/name).read_text(encoding='utf-8').splitlines()]


def validate():
    manifest=json.loads((ROOT/'catalog.json').read_text(encoding='utf-8'))
    all_tasks=read('tasks.jsonl'); propositions=read('propositions.jsonl')
    foundation=read('foundations.jsonl'); supplements=read('supplements.jsonl')
    ids=[t['id'] for t in all_tasks]
    assert len(ids)==len(set(ids))==manifest['total_tasks']
    assert len(propositions)==465
    assert set(ids)=={t['id'] for t in propositions+foundation+supplements}
    assert len(all_tasks)==len(propositions)+len(foundation)+len(supplements)
    for b,count in enumerate(EXPECTED,1):
        assert [t['number'] for t in propositions if t['book']==b]==list(range(1,count+1)), b
    for filename in ['propositions.jsonl','foundations.jsonl','supplements.jsonl']:
        for t in read(filename):
            assert t==next(x for x in all_tasks if x['id']==t['id']), t['id']
    for i,t in enumerate(all_tasks,1):
        assert t['source_order']==i
        assert t['benchmark_status']=={'lean':'not_started','litex':'not_started'}
        assert t['languages']==['lean','litex']
        assert t['source_span']['sha256']==manifest['source']['sha256']
        a=t['source_span']['start']; b=t['source_span']['end_exclusive']
        assert 1<=a['pdf_page']<=b['pdf_page']<=manifest['source']['pdf_pages']
        assert (a['pdf_page'],a['y_from_top_pt'])<(b['pdf_page'],b['y_from_top_pt']), t['id']
        if i>1:
            prev=all_tasks[i-2]['source_span']['start']
            assert (prev['pdf_page'],prev['y_from_top_pt'])<(a['pdf_page'],a['y_from_top_pt'])
    counts=collections.Counter(t['kind'] for t in all_tasks)
    assert dict(counts)==manifest['counts']
    for kind in ['definition','postulate','common_notion']:
        for book in range(1,14):
            seq=[t['number'] for t in foundation if t['book']==book and t['kind']==kind]
            assert seq==list(range(1,len(seq)+1)), (book,kind,seq)
    assert counts['postulate']==5 and counts['common_notion']==5
    assert counts['definition']==130
    pdf=ROOT/manifest['source']['local_cache']
    assert pdf.is_file(), 'Frozen source PDF cache missing'
    assert pdf.stat().st_size==manifest['source']['bytes']
    assert hashlib.sha256(pdf.read_bytes()).hexdigest()==manifest['source']['sha256']
    print(json.dumps({'validation':'passed','total_tasks':len(all_tasks),'counts':dict(counts),
                      'proofs_checked':0},ensure_ascii=False))


if __name__=='__main__': validate()
