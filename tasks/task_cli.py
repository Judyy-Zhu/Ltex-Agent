#!/usr/bin/env python3
"""Inspect tasks or prepare identical source inputs for Lean and Litex agents."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent


def load():
    return [json.loads(line) for line in (ROOT/'tasks.jsonl').read_text(encoding='utf-8').splitlines()]


def verify_source(manifest):
    pdf = ROOT/manifest['source']['local_cache']
    if not pdf.is_file():
        raise SystemExit(f'原文缓存缺失：{pdf}\n请从 catalog.json 的 source.url 恢复同一 PDF，并核对 SHA-256。')
    digest=hashlib.sha256(pdf.read_bytes()).hexdigest()
    if digest != manifest['source']['sha256']:
        raise SystemExit('原文 SHA-256 与冻结清单不符；拒绝混用不同版本。')
    return pdf


def pages_for(task):
    span=task['source_span']; start=span['start']; end=span['end_exclusive']
    last=end['pdf_page']-(1 if end['y_from_top_pt']==0 else 0)
    return start['pdf_page'],last


def prompt(task, language, pdf, rendered):
    first,last=pages_for(task)
    return '\n'.join([
        f'任务：{task["id"]} / {task["title_zh"]}',
        f'输出语言：{language}。只修改本任务工作区；不得修改验证器、冻结基础或任务规格。',
        task['instruction_zh'],
        f'原文PDF（含图形）：{pdf}',
        f'阅读PDF第{first}–{last}页，英文位于右栏。',
        f'精确范围：{json.dumps(task["source_span"],ensure_ascii=False)}',
        '以指定标题/编号的完整原文条目为目标；末页下一条标题及其后内容不属于当前范围。',
        '原文命题和原文证明可见；现有形式化答案、另一语言输出、历史checkpoint不可读。',
        '检查图形中点线关系及全部文字结论；文本抽取不能替代图形阅读。',
        '量、数、单位、面积、体积及角的类型须保留区分；未声明的额外前提不可补入目标。',
        '构造题给出合法见证并证明全部构造性质；部分结论不代表整项完成。',
        '需要辅助引理时实际证明；禁止sorry、admit、trust或新增未证明axiom作为兜底。',
        '只允许经实验统一批准的源公设与基础依赖；逐项记录实际使用的假设。',
        '提交源文件、依赖清单、原文到正式命题的对照、证明思路、最终独立验证命令和原始输出。',
        '若失败，保留原目标及诊断；不弱化目标、不把失败转为公理。',
        ('原文页面图像：'+', '.join(str(p) for p in rendered)) if rendered else '',
    ])+'\n'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    subs=p.add_subparsers(dest='command',required=True)
    listing=subs.add_parser('list'); listing.add_argument('--book',type=int,choices=range(1,14))
    listing.add_argument('--kind',choices=['proposition','definition','postulate','common_notion','lemma','corollary'])
    show=subs.add_parser('show'); show.add_argument('task_id')
    generate=subs.add_parser('prompt'); generate.add_argument('task_id')
    generate.add_argument('--language',choices=['lean','litex'],required=True)
    generate.add_argument('--render-dir',type=Path,help='Render complete source pages with pdftoppm for figure-aware agents')
    subs.add_parser('validate')
    args=p.parse_args(); tasks=load()
    manifest=json.loads((ROOT/'catalog.json').read_text(encoding='utf-8'))
    if args.command=='validate':
        from validate_catalog import validate
        validate(); return
    if args.command=='list':
        for t in tasks:
            if (args.book is None or t['book']==args.book) and (args.kind is None or t['kind']==args.kind):
                a,b=pages_for(t); print(f'{t["id"]}\t{t["title_zh"]}\tPDF {a}–{b}')
        return
    task=next((t for t in tasks if t['id']==args.task_id),None)
    if task is None: p.error('Unknown task ID: '+args.task_id)
    if args.command=='show':
        print(json.dumps(task,ensure_ascii=False,indent=2)); return
    pdf=verify_source(manifest); rendered=[]
    if args.render_dir:
        args.render_dir.mkdir(parents=True,exist_ok=True)
        first,last=pages_for(task)
        prefix=args.render_dir/task['id']
        existing=list(args.render_dir.glob(task['id']+'-*.png'))
        if existing: p.error('Render output already exists; choose a new directory.')
        subprocess.run(['pdftoppm','-f',str(first),'-l',str(last),'-scale-to','1500',
                        '-png',str(pdf),str(prefix)],check=True)
        rendered=sorted(args.render_dir.glob(task['id']+'-*.png'))
    print(prompt(task,args.language,pdf,rendered))


if __name__=='__main__': main()
