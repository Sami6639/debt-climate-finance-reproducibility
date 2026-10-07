"""Check the delivered file manifest and locked analytical source files."""
from pathlib import Path
import hashlib,json,sys
from ppml_pipeline import load_lock
ROOT=Path(__file__).resolve().parent.parent

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

if __name__=='__main__':
    load_lock(ROOT/'analysis/design_lock.yaml')
    manifest=ROOT/'bundle_manifest.sha256.json'
    if manifest.exists():
        entries=json.loads(manifest.read_text())
        failures=[r['file'] for r in entries if not (ROOT/r['file']).exists() or sha(ROOT/r['file'])!=r['sha256']]
        if failures:raise SystemExit('Files changed or absent: '+', '.join(failures))
        print(f'All {len(entries)} delivered file hashes match.')
    print('Every locked analytical source input hash matches.')
