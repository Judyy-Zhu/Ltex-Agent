"""Verify transferred source bytes against a credential-free manifest."""
import hashlib
import json
from pathlib import Path
import sys

root=Path(sys.argv[1]).resolve()
manifest=json.loads(Path(sys.argv[2]).read_text())
errors=[]
for name,expected in manifest['files'].items():
    path=(root/name).resolve()
    if not path.is_relative_to(root) or not path.is_file():errors.append(name+': missing');continue
    if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:errors.append(name+': changed')
result={'passed':not errors,'checked_files':len(manifest['files']),'errors':errors,'model_calls':0}
print(json.dumps(result,ensure_ascii=False,indent=2))
if errors:raise SystemExit(1)
