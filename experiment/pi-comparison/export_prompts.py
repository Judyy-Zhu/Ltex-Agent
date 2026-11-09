#!/usr/bin/env python3
"""Export actual initial RPC prompts/tool definitions for a development pair."""
import argparse
import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent


def sha_bytes(value):
    return hashlib.sha256(value).hexdigest()


def initial_messages(path):
    system = user = None
    with path.open() as stream:
        for line in stream:
            event = json.loads(line)
            if event.get('type')!='message_end':
                continue
            message = event.get('message',{})
            if system is None and message.get('role')=='system':
                system = message
            if user is None and message.get('role')=='user':
                user = message
            if system is not None and user is not None:
                return system,user
    raise ValueError(f'Initial messages absent: {path}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('lean_run')
    parser.add_argument('litex_run')
    parser.add_argument('--output',type=Path,default=BASE/'prompt-snapshots/20261108-v2-I1')
    args = parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    recorded_tools = recorded_user = None
    manifest = {'scope':'Actual initial messages and registered tools, not a reconstructed proposed prompt',
                'rendering':'Pi getSystemMessageText: nonempty content and sections joined by two newlines',
                'later_context':'Tool responses and Pi-generated compaction summaries are in each run RPC log.',
                'languages':{}}
    for language,identifier in (('lean',args.lean_run),('litex',args.litex_run)):
        root = BASE/'runs'/identifier
        system,user = initial_messages(root/'rpc.jsonl')
        text = '\n\n'.join([part for part in [system.get('content',''),*system.get('sections',{}).values()] if part])
        user_text = ''.join(part['text'] for part in user['content'] if part['type']=='text')
        tools = system['toolsAdded']
        if recorded_tools is not None:
            assert recorded_tools==tools, 'Agent tool definitions differ'
            assert recorded_user==user_text, 'Initial task messages differ'
        recorded_tools,recorded_user = tools,user_text
        (args.output/f'{language}.system.txt').write_text(text)
        (args.output/f'{language}.system-message.json').write_text(json.dumps(system,ensure_ascii=False,indent=2)+'\n')
        job = json.loads((root/'job.json').read_text())
        (args.output/f'{language}.foundation.json').write_bytes((root/'input/foundation.json').read_bytes())
        docs = {}
        observed = json.loads((root/'manifest.json').read_text())
        for topic,path in job['docs'].items():
            data = Path(path).read_bytes()
            assert sha_bytes(data)==observed['guide_sha256'][topic], 'Guide changed since launch'
            suffix = Path(path).suffix
            destination = args.output/f'{language}.{topic}{suffix}'
            destination.write_bytes(data)
            docs[topic] = {'snapshot':destination.name,'sha256':sha_bytes(data)}
        manifest['languages'][language] = {'run_id':identifier,'system_sha256':sha_bytes(text.encode()),'docs':docs}
    (args.output/'shared.user.txt').write_text(recorded_user)
    (args.output/'tools.schema.json').write_text(json.dumps(recorded_tools,ensure_ascii=False,indent=2)+'\n')
    manifest.update(identical_tool_schemas=True,identical_initial_task_message=True,
                    tool_names=[tool['name'] for tool in recorded_tools])
    (args.output/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'directory':str(args.output),'identical_tools':True,'identical_user_prompt':True}))


if __name__=='__main__':
    main()
