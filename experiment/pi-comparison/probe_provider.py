#!/usr/bin/env python3
"""Small Paratera protocol smoke; never runs the Euclid benchmark or Pi."""
from __future__ import annotations
import argparse
import base64
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import re
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT=Path(__file__).resolve().parent


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs): return None


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--direct',action='store_true',help='Ignore process proxy settings for this probe')
    args=ap.parse_args()
    cfg=json.loads((ROOT/'private/api_config.json').read_text())
    key=os.environ.get('PARATERA_API_KEY') or cfg['api_key']
    base=cfg['base_url'].rstrip('/')
    u=urllib.parse.urlsplit(base)
    if (u.scheme,u.hostname)!=('https','llmapi.paratera.com'):
        raise SystemExit('Refusing to send credential to a different service')
    handlers=[NoRedirect()]
    if args.direct: handlers.append(urllib.request.ProxyHandler({}))
    opener=urllib.request.build_opener(*handlers)
    report={'observed_at':datetime.now(timezone.utc).isoformat(),'provider':'paratera',
            'base_url':base,'requested_model':cfg['model'],'scope':'API-only compatibility smoke; no Pi or proof experiment',
            'checks':[]}

    def safe(s):
        return re.sub(r'sk-[A-Za-z0-9_.-]+','[REDACTED]',str(s).replace(key,'[REDACTED]'))[:1000]

    def request(name,path,body=None,stream=False):
        start=time.monotonic()
        entry={'name':name,'ok':False}
        req=urllib.request.Request(base+path, data=json.dumps(body).encode() if body is not None else None,
            headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
        try:
            with opener.open(req,timeout=45) as resp:
                entry['http_status']=resp.status
                if stream:
                    chunks=[]; texts=[]; usage=None
                    for raw in resp:
                        if not raw.startswith(b'data:'): continue
                        data=raw[5:].strip()
                        if data==b'[DONE]': break
                        event=json.loads(data);chunks.append(event)
                        if event.get('usage'): usage=event['usage']
                        for choice in event.get('choices',[]):
                            texts.append(choice.get('delta',{}).get('content') or '')
                    data={'text':''.join(texts),'chunks':len(chunks),'usage':usage}
                else: data=json.load(resp)
            entry['ok']=True
            if isinstance(data,dict):
                if data.get('model'): entry['response_model']=data['model']
                if data.get('usage'): entry['usage']=data['usage']
            return data,entry
        except urllib.error.HTTPError as e:
            entry.update(http_status=e.code,error=safe(e.read().decode(errors='replace')))
        except Exception as e:
            entry['error']=safe(type(e).__name__+': '+str(e))
        finally:
            entry['elapsed_seconds']=round(time.monotonic()-start,3)
            report['checks'].append(entry)
            print(json.dumps({k:v for k,v in entry.items() if k!='usage'},ensure_ascii=False),flush=True)
        return None,entry

    models,e=request('model_catalog','/models')
    if models:
        entries=models.get('data',[])
        e['requested_model_listed']=any(isinstance(x,dict) and x.get('id')==cfg['model'] for x in entries)
        e['model_count']=len(entries)

    def body(messages,**kwargs):
        return dict(model=cfg['model'],messages=messages,max_tokens=256,
                    thinking={'type':'disabled'},**kwargs)

    result,e=request('text','/chat/completions',body([{'role':'user','content':'Return exactly API_OK.'}]))
    if result:
        message=(result.get('choices') or [{}])[0].get('message',{})
        e['content']=safe(message.get('content'))
        e['content_matches']=str(message.get('content','')).strip()=='API_OK'
    if not e['ok']:
        # Do not issue more paid requests while basic authentication/protocol fails.
        report['stopped_after_text_failure']=True
    else:
        tool={'type':'function','function':{'name':'report_sum','description':'Add two integers.',
              'parameters':{'type':'object','properties':{'a':{'type':'integer'},'b':{'type':'integer'}},
                            'required':['a','b'],'additionalProperties':False}}}
        messages=[{'role':'user','content':'Call report_sum once with a=2 and b=3. After the tool result, return only that result.'}]
        result,e=request('function_call','/chat/completions',body(messages,tools=[tool],
                          tool_choice={'type':'function','function':{'name':'report_sum'}}))
        if result:
            msg=(result.get('choices') or [{}])[0].get('message',{})
            calls=msg.get('tool_calls') or []
            try:
                c=calls[0];params=json.loads(c['function']['arguments'])
                valid=len(calls)==1 and c['function']['name']=='report_sum' and params=={'a':2,'b':3}
            except (KeyError,IndexError,TypeError,ValueError): valid=False
            e['valid_requested_tool_call']=valid
            if valid:
                follow=messages+[msg,{'role':'tool','tool_call_id':c['id'],'content':'5'}]
                response,f=request('tool_result_round_trip','/chat/completions',body(follow,tools=[tool]))
                if response:
                    text=(response.get('choices') or [{}])[0].get('message',{}).get('content','')
                    f['content']=safe(text);f['content_matches']=str(text).strip()=='5'
        result,e=request('streaming_usage','/chat/completions',body([{'role':'user','content':'Return exactly STREAM_OK.'}],
                         stream=True,stream_options={'include_usage':True}),stream=True)
        if result:
            e.update(content_matches=result['text'].strip()=='STREAM_OK',chunks=result['chunks'],
                     usage_observed=result['usage'] is not None)
        try:
            from PIL import Image,ImageDraw
            image=Image.new('RGB',(96,96),'white');draw=ImageDraw.Draw(image)
            draw.rectangle((8,8,87,87),fill=(0,0,255))
            out=io.BytesIO();image.save(out,format='PNG')
            uri='data:image/png;base64,'+base64.b64encode(out.getvalue()).decode()
            content=[{'type':'text','text':'What color is the filled square? Reply with only its English color name.'},
                     {'type':'image_url','image_url':{'url':uri}}]
            result,e=request('image_input_smoke','/chat/completions',body([{'role':'user','content':content}]))
            if result:
                text=(result.get('choices') or [{}])[0].get('message',{}).get('content','')
                e['content']=safe(text);e['content_matches']=str(text).strip().lower().rstrip('.')=='blue'
                e['limitation']='Simple color recognition only; not a geometry-diagram fidelity test.'
        except ImportError:
            report['image_probe_skipped']='Pillow unavailable'
    target=ROOT/'provider-probe.json'
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('Saved redacted API-only probe receipt.',flush=True)


if __name__=='__main__': main()
