from pathlib import Path
import pandas as pd,numpy as np,pyarrow.parquet as pq,json
P=Path(__file__).resolve().parents[1];d=pd.read_parquet(P/'processed/eligible_activities.parquet')
keys=['year','provider','agency_code','crs_id','recipient_code','purpose_code'];r=d.loc[d.duplicated(keys,keep=False)]
ids=set(r.source_row);selected=[];offset=0
for batch in pq.ParquetFile(P/'raw/CRS_v20260803.parquet').iter_batches(batch_size=50000):
 idx=np.arange(offset,offset+len(batch));offset+=len(batch);mask=np.isin(idx,list(ids))
 if mask.any():
  t=batch.filter(mask).to_pandas();t['source_row']=idx[mask];selected.append(t)
f=pd.concat(selected,ignore_index=True);cols=[c for c in f if c!='source_row'];f.to_parquet(P/'processed/repeated_full_source_rows.parquet',index=False)
exact=f.duplicated(cols,keep=False);print('full exact duplicated rows',exact.sum(),'beyond first',f.duplicated(cols).sum());print(f.loc[exact,['year','donor_code','crs_id','project_number','usd_commitment','purpose_code','source_row']].to_string(index=False))
# Describe fields differentiating source records sharing the same activity-sector key.
rows=[]
for k,g in f.groupby(['year','donor_code','agency_code','crs_id','recipient_code','purpose_code'],dropna=False):
 varying=[c for c in cols if g[c].nunique(dropna=False)>1]
 rows.append({'key':list(k),'rows':len(g),'varying_fields':varying,'source_rows':g.source_row.tolist()})
(P/'metadata/repeated_row_audit.json').write_text(json.dumps({'exact_duplicate_rows':int(exact.sum()),'exact_duplicate_excess':int(f.duplicated(cols).sum()),'groups':rows},indent=2,default=str))
