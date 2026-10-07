"""Download official public OECD CRS snapshot; retain raw bytes and provenance."""
import urllib.request, hashlib, json, os
from pathlib import Path
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parents[1]
u='https://webfs-dcd.oecd.org/files/dotStat/DSD_CRS/CRS-reduced.parquet'
p=ROOT/'raw'/'CRS-reduced_v20260803.parquet'
if p.exists():
 print('Immutable file already present',p,flush=True)
else:
 req=urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0'})
 with urllib.request.urlopen(req,timeout=120) as r:
  hdr={k:v for k,v in r.headers.items() if k.lower() not in ['set-cookie']}
  if hdr.get('Content-MD5') != '4l08APF+higOYcZ5DmjfDQ==': raise RuntimeError('Official mutable URL no longer matches locked snapshot; do not relabel a new vintage.')
  h=hashlib.sha256(); size=0
  with open(str(p)+'.part','wb') as f:
   while b:=r.read(1024*1024):
    f.write(b);h.update(b);size+=len(b)
    if size%(25*1024*1024)==0:print(size,flush=True)
  if hdr.get('Content-Length') and size!=int(hdr['Content-Length']): raise ValueError('Truncated download')
 if h.hexdigest() != '3f795d9b6ef3354ecfd1072a6b088baca7adc63952d84d6254f96abf5e3ee3ba': raise RuntimeError('SHA-256 differs from locked v20260803 snapshot')
 os.rename(str(p)+'.part',p);p.chmod(0o444)
 meta={'url':u,'snapshot_label':'CRS-reduced-parquet-v20260803','retrieved_at_utc':datetime.now(timezone.utc).isoformat(),'bytes':size,'sha256':h.hexdigest(),'http_headers':hdr,'source_catalog':'https://sdmx.oecd.org/dcd-public/rest/dataflow/OECD.DCD.FSD/DSD_CRS@DF_CRS/1.6?references=all','source_file':str(p),'data_scope':'Official all-years reduced activity-level CRS, downloaded unchanged. Analysis will filter 2010–2024.'}
 (ROOT/'metadata'/'source_manifest.json').write_text(json.dumps(meta,indent=2));print(meta,flush=True)
