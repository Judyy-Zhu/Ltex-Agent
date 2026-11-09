#!/usr/bin/env python3
"""Build source-addressed, language-neutral tasks from the frozen source PDF.

This inventories source items, not verified mathematical statements. The
translation is read from the PDF at task time rather than copied into JSONL.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
SOURCE_URL = 'https://farside.ph.utexas.edu/Books/Euclid/Elements.pdf'
ROMAN = ['', 'I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI', 'XII', 'XIII']
COUNTS = [0, 48, 14, 37, 16, 25, 33, 39, 27, 36, 115, 39, 18, 18]
STARTS = [0, 5, 49, 69, 109, 129, 155, 193, 227, 253, 281, 423, 471, 505, 539]
SUBJECTS = ['', '平面几何基础', '几何代数', '圆与切线', '内接与外切构造', '量与比例',
            '比例与相似', '整数、整除与最大公约数', '连比例整数', '数论与数列',
            '可通约量与无理量分类', '立体几何基础', '面积、体积与穷竭法', '正多面体']


def dump(path: Path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def read_lines(pdf: Path):
    with tempfile.TemporaryDirectory(prefix='euclid-bbox-') as tmp:
        xml = Path(tmp) / 'source.xml'
        subprocess.run(['pdftotext', '-bbox-layout', '-enc', 'UTF-8', str(pdf), str(xml)], check=True)
        # Legacy TeX glyph encodings can emit XML-1.0-forbidden controls in
        # the Greek column. They do not carry English heading/number data.
        cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', xml.read_text(encoding='utf-8'))
        tree = ET.ElementTree(ET.fromstring(cleaned))
    ns = {'h': 'http://www.w3.org/1999/xhtml'}
    pages = tree.findall('.//h:page', ns)
    lines = []
    for page_no, page in enumerate(pages, 1):
        width, height = float(page.attrib['width']), float(page.attrib['height'])
        for line in page.findall('.//h:line', ns):
            words = line.findall('h:word', ns)
            right = [w for w in words if float(w.attrib['xMin']) >= width * .5]
            if not right:
                continue
            text = ' '.join(''.join(w.itertext()) for w in right)
            lines.append({'page': page_no, 'y': float(line.attrib['yMin']),
                          'y_end': float(line.attrib['yMax']), 'text': text,
                          'page_width': width, 'page_height': height})
    return sorted(lines, key=lambda x: (x['page'], x['y'])), len(pages)


def position(line):
    return {'pdf_page': line['page'], 'y_from_top_pt': round(line['y'], 3)}


def book_of(page):
    return next((b for b in range(1, 14) if STARTS[b] <= page < STARTS[b+1]), None)


def inventory(lines):
    events, section = [], None
    parent = None
    previous_book = None
    suffixes = collections.Counter()
    for line in lines:
        b = book_of(line['page'])
        if b is None:
            continue
        if b != previous_book:
            section, parent, previous_book = None, None, b
        text = line['text'].strip()
        prop = re.fullmatch(r'Proposition\s+(\d+)\s*[†‡*]?', text)
        if prop:
            n = int(prop[1]); parent = n; section = None
            events.append(dict(line, book=b, kind='proposition', number=n,
                               id=f'EUCLID.{ROMAN[b]}.P{n:03}'))
            continue
        if re.fullmatch(r'Definitions(?:\s+[IVX]+)?', text):
            section = 'definition'; continue
        if text == 'Postulates':
            section = 'postulate'; continue
        if text == 'Common Notions':
            section = 'common_notion'; continue
        supplement = re.fullmatch(r'(Corollary|Lemma)(?:\s+(\d+|[IVX]+))?\s*[†‡*]?', text)
        if supplement:
            kind = supplement[1].lower()
            suffixes[(b, kind)] += 1
            n = suffixes[(b, kind)]
            # Adjacency is source location, not an inferred logical parent.
            # In particular a lemma after P13 can support P14.
            events.append(dict(line, book=b, kind=kind, number=n, preceding_proposition=parent,
                               id=f'EUCLID.{ROMAN[b]}.{"COR" if kind == "corollary" else "LEM"}{n:03}'))
            section = None
            continue
        number = re.match(r'^(\d+)\.\s', text)
        if section and number:
            n = int(number[1])
            code = {'definition':'D', 'postulate':'POST', 'common_notion':'CN'}[section]
            events.append(dict(line, book=b, kind=section, number=n,
                               id=f'EUCLID.{ROMAN[b]}.{code}{n:03}'))
    return events


def make_task(event, end, digest, sequence):
    b, kind, n = event['book'], event['kind'], event['number']
    label = {'proposition':'命题', 'definition':'定义', 'postulate':'公设',
             'common_notion':'公理', 'corollary':'推论', 'lemma':'引理'}[kind]
    preceding = event.get('preceding_proposition')
    prefix = f'第{ROMAN[b]}卷'
    if kind == 'definition':
        action = '在统一模型中建立与原文等价的定义或明确的解释映射，证明必要的语义桥接及适用性条件。'
    elif kind in {'postulate','common_notion'}:
        action = '准确形式化原文基础项；明确它在选定模型中是待证明性质还是经批准的源公设，并记录假设边界。'
    else:
        action = '完整形式化并证明该原文条目；保留量词、适用域、非退化条件、全部分支、结论与构造正确性。'
    return {
        'id': event['id'], 'source_order': sequence, 'book': b, 'book_roman': ROMAN[b],
        'kind': kind, 'number': n, 'preceding_proposition': preceding,
        'title_zh': f'{prefix}{label}{n}' + (f'（位于命题{preceding}之后）' if preceding else ''), 'subject_zh': SUBJECTS[b],
        'instruction_zh': action + '以source_span定位的原文为规格，不以标题或历史完成标签替代原文。',
        'languages': ['lean','litex'],
        'source_span': {'source_id':'fitzpatrick-2008', 'sha256':digest,
                        'start':position(event), 'end_exclusive':end,
                        'column':'english_right', 'coordinate_system':'PDF points from top; pages are one-based'},
        'acceptance': ['原文全部数学内容经过语义审核', '保存文件在固定版本的新进程中完整验证通过',
                       '无超出统一批准基础的直接或传递未证明依赖', '只完成部分结论不计整项成功'],
        'dependencies': {'reviewed_task_ids':[], 'status':'not_yet_reviewed',
                         'policy':'源文顺序用于导航，不宣称相邻编号是逻辑依赖；不得无证假设缺失的前置结论。'},
        'benchmark_status': {'lean':'not_started','litex':'not_started'},
        'statement_review': 'source_located_formal_target_not_yet_frozen',
    }


def build(pdf: Path):
    digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
    lines, page_count = read_lines(pdf)
    events = inventory(lines)
    ids = [e['id'] for e in events]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate source items: ' + str([x for x,c in collections.Counter(ids).items() if c>1]))
    for b in range(1,14):
        actual = [e['number'] for e in events if e['book']==b and e['kind']=='proposition']
        if actual != list(range(1,COUNTS[b]+1)):
            raise ValueError(f'Book {b} proposition inventory mismatch: {actual}')
    tasks = []
    for i, event in enumerate(events):
        following = next((x for x in events[i+1:] if x['book']==event['book']), None)
        end = position(following) if following else {'pdf_page':STARTS[event['book']+1], 'y_from_top_pt':0}
        tasks.append(make_task(event,end,digest,i+1))
    # Source-declared consequences that lack their own heading stay in the
    # parent task's source span and must be included in its semantic review.
    for filename, subset in [('tasks.jsonl',tasks),
                             ('propositions.jsonl',[t for t in tasks if t['kind']=='proposition']),
                             ('foundations.jsonl',[t for t in tasks if t['kind'] in {'definition','postulate','common_notion'}]),
                             ('supplements.jsonl',[t for t in tasks if t['kind'] in {'lemma','corollary'}])]:
        (ROOT/filename).write_text(''.join(json.dumps(t,ensure_ascii=False)+'\n' for t in subset),encoding='utf-8')
    books = []
    for b in range(1,14):
        kinds = collections.Counter(t['kind'] for t in tasks if t['book']==b)
        books.append({'book':b,'roman':ROMAN[b],'subject_zh':SUBJECTS[b],
                      'pdf_start_page':STARTS[b],'pdf_end_page':STARTS[b+1]-1,
                      'counts':dict(kinds)})
    manifest = {
        'schema_version':1,'created_date':'2026-11-08','scope':'Euclid Elements Books I–XIII',
        'scope_supersedes_for_new_runs':'translation_records/geometry-only-scope-and-audit.json',
        'historical_proofs_reclassified':False,
        'source':{'id':'fitzpatrick-2008','url':SOURCE_URL,'edition':'Richard Fitzpatrick, revised 2008; Heiberg Greek text',
                  'sha256':digest,'bytes':pdf.stat().st_size,'pdf_pages':page_count,
                  'local_cache':'sources/elements-2008.pdf',
                  'text_policy':'Source text and diagrams are read from the cached PDF; modern translation is not reproduced in JSONL.'},
        'counts':dict(collections.Counter(t['kind'] for t in tasks)), 'total_tasks':len(tasks),
        'primary_accuracy_denominator':465,'legacy_148_proposition_delta':317,
        'books':books,
        'completeness':{'numbered_propositions':'complete_contiguous_source_inventory',
                        'foundations':'individually_located_in_source',
                        'supplements':'explicit_lemma_and_corollary_headings_plus_unheaded_consequences_in_parent_span',
                        'source_supplement_semantic_split_review':'pending; a heading inventory alone is not an exhaustive clause audit',
                        'formal_statement_pairs':'not_yet_authored_or_reviewed',
                        'new_proofs':'none'},
        'run_policy':{'source_proof_visibility':'original_source_statement_and_proof_visible_to_both_languages',
                      'historical_solutions_visible_to_agent':False,
                      'model':'freeze_before_run','skills':'freeze_before_run',
                      'strict_no_new_unproved_debt':True,
                      'definitions_and_supplements_reported_separately':True,
                      'do_not_treat_tasks_as_independent_trials':True},
    }
    dump(ROOT/'catalog.json',manifest)
    print(json.dumps({'tasks':len(tasks),'counts':manifest['counts'],'source_sha256':digest},ensure_ascii=False))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pdf',type=Path)
    args=parser.parse_args()
    build(args.pdf.resolve())
