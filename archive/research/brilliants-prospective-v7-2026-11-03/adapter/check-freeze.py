"""Read-only checksum check for this fixed prospective study, not a release tool."""
import hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
freeze=json.loads((root/'FREEZE.json').read_text())
for name,item in freeze['files'].items():
    assert sha(root/name)==item['sha256'],name
adapter=json.loads((root/'ADAPTER-FREEZE.json').read_text())
for name,item in adapter['files'].items():
    assert sha(root/name)==item['sha256'],name
assert adapter['source_freeze_sha256']==sha(root/'FREEZE.json')
print(json.dumps({'source_files':len(freeze['files']),'adapter_files':len(adapter['files']),'source_freeze_sha256':sha(root/'FREEZE.json'),'status':'verified'}))
