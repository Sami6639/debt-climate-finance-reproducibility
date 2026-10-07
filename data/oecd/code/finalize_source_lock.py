from pathlib import Path
import pandas as pd,json,hashlib,base64
from datetime import datetime,timezone
P=Path(__file__).resolve().parents[1];O=P/'processed';M=P/'metadata'
s=pd.read_parquet(O/'cell_outcomes.parquet');d=pd.read_csv(M/'donor_classification.csv')
b=s.loc[s.year.ge(2015)].groupby(['provider','donor_name','de_donorcode']).agg(n_cells=('year','size'),first_year=('year','min'),last_year=('year','max'),adaptation_total=('adaptation_total','sum'),mitigation_total=('mitigation_total','sum'),nonclimate_total=('nonclimate_total','sum')).reset_index().merge(d[['donor_code','donor_type']],left_on='provider',right_on='donor_code',how='left',validate='1:1');b.to_csv(O/'included_providers_primary2015_2024.csv',index=False)
s.loc[s.year.ge(2015),['iso3','recipient_code','recipient_name','de_recipientcode']].drop_duplicates().to_csv(O/'included_recipients_primary2015_2024.csv',index=False)
summary=json.loads((M/'panel_summary.json').read_text());summary['status']='source locked after independent methods validation, 2026-10-07; covariate joins and PPML samples are separate';summary['exact_full_source_duplicate_rows']=0;(M/'panel_summary.json').write_text(json.dumps(summary,indent=2))
files=[]
for directory in ['code','processed','metadata']:
 for p in sorted((P/directory).glob('*')):
  if p.is_file() and p.name not in ['source_lock_manifest.json']:
   h=hashlib.sha256()
   with open(p,'rb') as f:
    while x:=f.read(1024*1024):h.update(x)
   files.append({'file':str(p.relative_to(P)),'bytes':p.stat().st_size,'sha256':h.hexdigest()})
lock={'snapshot':'OECD_CRS_v20260803','locked_at_utc':datetime.now(timezone.utc).isoformat(),'raw_source_manifest':'metadata/full_source_manifest.json','scientific_scope':'2015–2024 primary;2011–2024 extension;2010 quality only. Government providers, EU excluded from primary. Observed fully marker-classified cells only.','methods_validation':'Independent audit checked cell identities, outcome construction, zeros, source-filter code, provider scope and duplicate handling; signoff2026-10-07.','files':files,'future_changes':'Preserve this source lock; use a new version and new manifest for any data, eligibility, or code change.'}
(M/'source_lock_manifest.json').write_text(json.dumps(lock,indent=2))
print('Locked',len(files),'files. Primary panel SHA:',next(x['sha256'] for x in files if x['file']=='processed/cell_outcomes.parquet'))
