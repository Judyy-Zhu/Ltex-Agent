"""Controller-only named credentials. Keys never enter plans or model inputs."""
import json
from pathlib import Path
import secrets
from paths import BASE

FILES={'primary':'api_config.json','secondary':'api_config.secondary.json'}


def read_credential(alias,private_root=None):
    if alias not in FILES:raise ValueError('Unknown credential alias')
    root=Path(private_root) if private_root else BASE/'private'
    path=root/FILES[alias]
    if path.stat().st_mode & 0o077:raise ValueError('Credential file must be private (chmod 600): '+FILES[alias])
    value=json.loads(path.read_text())
    if not isinstance(value.get('api_key'),str) or not value['api_key'].strip():raise ValueError('API key missing for '+alias)
    return value


def validate_pair(bindings,private_root=None):
    if set(bindings)!= {'lean','litex'} or set(bindings.values())!={'primary','secondary'}:
        raise ValueError('Parallel languages require distinct primary/secondary credential aliases')
    left=read_credential(bindings['lean'],private_root)['api_key']
    right=read_credential(bindings['litex'],private_root)['api_key']
    if secrets.compare_digest(left,right):raise ValueError('Parallel keys must be distinct')
    return {'lean':bindings['lean'],'litex':bindings['litex'],'distinct_keys_configured':True,
            'provider_quota_independence':'not_assumed'}
