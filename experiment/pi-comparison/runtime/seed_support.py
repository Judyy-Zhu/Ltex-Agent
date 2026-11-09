"""Frozen technical seed loading and final-file protection."""
import hashlib
from pathlib import Path


def seed_source(job):
    seed=job['foundation'].get('seed')
    if seed is None:
        # Preserve old development receipts/jobs without silently adding a new
        # mathematical starting point to their reconstruction.
        return '\n'.join('import '+name for name in job['foundation'].get('allowed_imports',[]))+'\n'
    data=Path(job['seed_path']).read_bytes()
    if hashlib.sha256(data).hexdigest()!=seed['sha256']:
        raise ValueError('Frozen technical seed changed; verification is blocked')
    return data.decode('utf-8')


def library_source(job):
    library=job.get('library')
    if not library:return ''
    root=Path(job['seed_path']).parent
    data=(root/library['input_path']).read_bytes()
    if hashlib.sha256(data).hexdigest()!=library['sha256']:
        raise ValueError('Frozen predecessor library changed')
    index=(root/library['index_path']).read_bytes()
    if hashlib.sha256(index).hexdigest()!=library['index_sha256']:
        raise ValueError('Frozen predecessor library index changed')
    return data.decode('utf-8')


def starting_source(job):
    return seed_source(job).rstrip()+'\n\n'+library_source(job).lstrip('\n')


def assemble_final(job,body):
    return starting_source(job).rstrip()+'\n\n'+body.lstrip('\n')


def require_seed_prefix(job,source):
    if job['foundation'].get('seed') is None:return
    prefix=starting_source(job).rstrip()
    if not source.startswith(prefix) or (len(source)>len(prefix) and source[len(prefix)]!='\n'):
        raise ValueError('Final module must start with the unchanged frozen seed and predecessor library; use write_source(base="accepted")')
