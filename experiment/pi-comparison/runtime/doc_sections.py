"""Stable section retrieval; full original references remain available verbatim."""
import re


def sections(text):
    result=[];lines=text.splitlines(keepends=True);start=0;title='Overview';fence=None
    for index,line in enumerate(lines):
        stripped=line.lstrip()
        marker=re.match(r'(`{3,}|~{3,})',stripped)
        if marker:
            token=marker[1][0]
            if fence is None:fence=token
            elif fence==token:fence=None
            continue
        heading=re.match(r'^#{1,4}\s+(.+?)\s*#*\s*$',line.rstrip()) if fence is None else None
        if heading:
            if index>start:result.append((title,''.join(lines[start:index])))
            start=index;title=heading[1]
    if start<len(lines):result.append((title,''.join(lines[start:])))
    if not result:result=[('Overview',text)]
    return [{'id':'s'+str(i).zfill(2),'title':title,'text':content,'characters':len(content)}
            for i,(title,content) in enumerate(result)]


def retrieve(text,topic,section=None,selected_sections=None,query=None):
    values=sections(text)
    if sum(v is not None for v in (section,selected_sections,query))>1:raise ValueError('Use section, sections or query, not more than one')
    if selected_sections is not None:
        if not selected_sections or len(selected_sections)>20:raise ValueError('Request 1..20 section IDs, or section=all')
        selected=[next((s for s in values if s['id']==key),None) for key in dict.fromkeys(selected_sections)]
        if any(v is None for v in selected):raise ValueError('Unknown section; list read_docs(topic) first')
        return {'topic':topic,'sections':selected,'complete_sections':True}
    if query is not None:
        terms=set(re.findall(r'[a-z0-9_]+',query.lower()))-{'the','a','an','is','of','to','and','in','how','for'}
        ranked=sorted(values,key=lambda s:sum(5*(word in s['title'].lower())+min(3,s['text'].lower().count(word)) for word in terms),reverse=True)
        selected=[s for s in ranked if any(word in s['text'].lower() for word in terms)][:3]
        return {'topic':topic,'query':query,'sections':selected,'complete_sections':True,
                'note':'Local lexical retrieval; section=all returns the intact reference if broader context is needed.'}
    if section=='all':return {'topic':topic,'section':'all','text':text,'complete_reference':True}
    if section is None or section=='index':
        return {'topic':topic,'sections':[{k:v for k,v in s.items() if k!='text'} for s in values],
                'usage':'Use section for one ID, sections for several IDs, or query for a specific question. Use one selector. section=all returns the complete reference.'}
    found=next((s for s in values if s['id']==section),None)
    if found is None:raise ValueError('Unknown section; list read_docs(topic) first')
    return {'topic':topic,'section':found['id'],'title':found['title'],'text':found['text'],'complete_section':True}
