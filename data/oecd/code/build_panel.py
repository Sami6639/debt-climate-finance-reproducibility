"""Reconstruct observed OECD CRS cells without filling unreported universes.
Source lock candidate v20260803. Amounts: constant 2024 USD millions.
Primary provider scope: country/territory governments in official DAC/non-DAC lists;
EU Institutions kept only for sensitivity. Marker-complete cells are primary.
Run with ../analysis/.venv/bin/python after acquire_full.py and prepare_metadata.py.
"""
from pathlib import Path
from collections import defaultdict
import json,hashlib
import pandas as pd
import numpy as np
import pyarrow.parquet as pq
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'processed';META=ROOT/'metadata'
SOURCE=ROOT/'raw'/'CRS_v20260803.parquet'
providers=pd.read_csv(META/'donor_classification.csv'); official=set(providers.loc[providers.donor_type.isin(['DAC','non-DAC']),'donor_code'])
assert 918 in official
f=pq.ParquetFile(SOURCE)
cols=['year','donor_code','de_donorcode','donor_name','agency_code','crs_id','project_number','initial_report','recipient_code','de_recipientcode','recipient_name','flow_code','flow_name','bi_multi','category','finance_t','aid_t','usd_commitment','usd_commitment_defl','purpose_code','sector_code','sector_name','climate_mitigation','climate_adaptation','commitment_date','ps_iflag']
audits=[]; kept=[]; donor_seen=[];offset=0
for batchno,b in enumerate(f.iter_batches(batch_size=150000,columns=cols)):
 d=b.to_pandas();d['source_row']=np.arange(offset,offset+len(d),dtype=np.int64);offset+=len(d)
 d=d.loc[d.year.between(2010,2024)].copy()
 if not len(d):continue
 donor_seen.append(d[['donor_code','donor_name','de_donorcode']].drop_duplicates())
 masks=[('01_source_years',lambda x:np.ones(len(x),dtype=bool)),('02_official_DAC_nonDAC_including_EU',lambda x:x.donor_code.isin(official)),('03_ODA_category10',lambda x:x.category.eq(10)),('04_bilateral_1_3_7_8',lambda x:x.bi_multi.isin([1,3,7,8])),('05_projecttype_C01',lambda x:x.aid_t.eq('C01')),('06_sector100_499',lambda x:x.sector_code.between(100,499)),('07_standard_grant_loan110_421',lambda x:x.finance_t.isin([110,421])),('08_exclude_estimated_nature8',lambda x:~x.initial_report.eq(8)),('09_positive_reported_commitment',lambda x:np.isfinite(x.usd_commitment)&x.usd_commitment.gt(0)),('10_positive_constant_commitment',lambda x:np.isfinite(x.usd_commitment_defl)&x.usd_commitment_defl.gt(0))]
 for stage,fn in masks:
  d=d.loc[fn(d)].copy()
  if len(d):
   a=d.groupby('year').agg(rows=('source_row','size'),current_usd_millions=('usd_commitment','sum'),constant_2024_usd_millions=('usd_commitment_defl','sum')).reset_index();a['stage']=stage;audits.append(a)
 kept.append(d)
 print('batch',batchno,'retained',len(d),flush=True)
d=pd.concat(kept,ignore_index=True)
d['provider']=d.donor_code.astype(int);d['sector']=d.sector_code.astype(int);d['iso3']=d.de_recipientcode.replace({'XKV':'XKX'})
d['named_recipient']=d.iso3.str.fullmatch('[A-Z]{3}',na=False)
d['primary_provider']=d.provider.ne(918)
d['valid_adaptation']=d.climate_adaptation.isin([0,1,2]);d['valid_mitigation']=d.climate_mitigation.isin([0,1,2]);d['both_markers_valid']=d.valid_adaptation & d.valid_mitigation
d['estimated_nature']=d.initial_report.eq(8);d['provisional_nature']=d.initial_report.eq(5);d['reported_nature123']=d.initial_report.isin([1,2,3])
d.to_parquet(OUT/'eligible_activities_including_regional_EU.parquet',index=False)
all_donors=pd.concat(donor_seen).drop_duplicates();all_donors.merge(providers[['donor_code','donor_type']],on='donor_code',how='left').to_csv(OUT/'all_source_provider_classification.csv',index=False)
# Separate regional allocations; never map regional financial flows to named countries.
d.loc[~d.named_recipient].groupby(['year','provider','donor_name','de_recipientcode','recipient_name'],dropna=False).agg(rows=('source_row','size'),constant_2024_usd_millions=('usd_commitment_defl','sum')).to_csv(OUT/'excluded_regional_allocations.csv')
d=d.loc[d.named_recipient].copy()
d.to_parquet(OUT/'eligible_activities.parquet',index=False)
for stage,sub in [('11_named_recipient',d),('12_country_government_provider',d.loc[d.primary_provider])]:
 a=sub.groupby('year').agg(rows=('source_row','size'),current_usd_millions=('usd_commitment','sum'),constant_2024_usd_millions=('usd_commitment_defl','sum')).reset_index();a['stage']=stage;audits.append(a)
audit=pd.concat(audits).groupby(['stage','year'],as_index=False)[['rows','current_usd_millions','constant_2024_usd_millions']].sum();audit.to_csv(OUT/'filter_audit.csv',index=False)
# Complete-cell eligibility is determined before any marker-based record deletion.
keys=['provider','iso3','year','sector']
g=d.groupby(keys,observed=True)
cells=g.agg(n_activities=('source_row','size'),n_classified=('both_markers_valid','sum'),eligible_commitment=('usd_commitment_defl','sum'),n_reported_nature123=('reported_nature123','sum')).reset_index()
cells['complete_markers']=cells.n_activities.eq(cells.n_classified);cells['primary_provider']=cells.provider.ne(918)
cells['complete_reported_nature123']=cells.n_activities.eq(cells.n_reported_nature123)
valid=d.loc[d.both_markers_valid].copy();v=valid
purpose_masks={'adaptation':v.climate_adaptation.eq(2),'mitigation':v.climate_mitigation.eq(2),'nonclimate':v.climate_adaptation.eq(0)&v.climate_mitigation.eq(0),'climate_union':v.climate_adaptation.eq(2)|v.climate_mitigation.eq(2),'exclusive_adaptation':v.climate_adaptation.eq(2)&~v.climate_mitigation.eq(2),'adaptation_broad':v.climate_adaptation.isin([1,2]),'mitigation_broad':v.climate_mitigation.isin([1,2]),'dual_principal':v.climate_adaptation.eq(2)&v.climate_mitigation.eq(2),'screened':np.ones(len(v),dtype=bool)}
amountcols=[]
for purpose,pm in purpose_masks.items():
 for instrument,im in [('total',np.ones(len(v),dtype=bool)),('grant',v.finance_t.eq(110)),('loan',v.finance_t.eq(421))]:
  c=purpose+'_'+instrument;v[c]=v.usd_commitment_defl.where(pm & im,0.0);amountcols.append(c)
agg=v.groupby(keys,observed=True)[amountcols].sum().reset_index()
cells=cells.merge(agg,on=keys,how='left',validate='1:1')
# Unclassifiable cells receive NA, never artificial zeros. Within observed classified cells,
# a missing purpose has zero by summing its indicator over eligible observed activities.
assert cells.loc[cells.complete_markers,amountcols].notna().all().all()
lookup=d[['provider','donor_name','de_donorcode']].drop_duplicates();assert not lookup.provider.duplicated().any()
cells=cells.merge(lookup,on='provider',how='left',validate='m:1')
recipient_lookup=d[['iso3','recipient_code','recipient_name','de_recipientcode']].drop_duplicates();assert not recipient_lookup.iso3.duplicated().any()
cells=cells.merge(recipient_lookup,on='iso3',how='left',validate='m:1')
cells.to_parquet(OUT/'all_observed_cells_with_coverage.parquet',index=False)
strict=cells.loc[cells.complete_markers & cells.primary_provider].copy()
strict.to_parquet(OUT/'cell_outcomes.parquet',index=False)
strict.to_csv(OUT/'cell_outcomes.csv',index=False)
cells.loc[cells.complete_markers].to_parquet(OUT/'cell_outcomes_including_EU.parquet',index=False)
cells.loc[cells.primary_provider & cells.n_classified.gt(0)].to_parquet(OUT/'cell_outcomes_valid_records_sensitivity.parquet',index=False)
# Coverage by provider/year before any marker filtering.
d['classified_commitment']=d.usd_commitment_defl.where(d.both_markers_valid,0.0)
coverage=d.groupby(['provider','donor_name','year']).agg(n_activities=('source_row','size'),n_both_valid=('both_markers_valid','sum'),eligible_commitment=('usd_commitment_defl','sum'),classified_commitment=('classified_commitment','sum')).reset_index()
cc=cells.groupby(['provider','year']).agg(n_observed_cells=('iso3','size'),n_complete_cells=('complete_markers','sum')).reset_index()
coverage=coverage.merge(cc,on=['provider','year'],validate='1:1');coverage['row_coverage']=coverage.n_both_valid/coverage.n_activities;coverage['amount_coverage']=coverage.classified_commitment/coverage.eligible_commitment
coverage.to_csv(OUT/'provider_year_marker_coverage.csv',index=False)
d.groupby(['year','climate_adaptation','climate_mitigation'],dropna=False).agg(n_activities=('source_row','size'),constant_2024_usd_millions=('usd_commitment_defl','sum')).to_csv(OUT/'marker_pair_audit.csv')
d.groupby(['year','initial_report'],dropna=False).agg(n_activities=('source_row','size'),constant_2024_usd_millions=('usd_commitment_defl','sum')).to_csv(OUT/'nature_audit.csv')
strict.groupby(['provider','donor_name','de_donorcode']).agg(n_cells=('year','size'),first_year=('year','min'),last_year=('year','max'),adaptation_total=('adaptation_total','sum'),mitigation_total=('mitigation_total','sum'),nonclimate_total=('nonclimate_total','sum')).reset_index().merge(providers[['donor_code','donor_type']],left_on='provider',right_on='donor_code',how='left',validate='1:1').to_csv(OUT/'included_providers.csv',index=False)
# Audit repeated CRS IDs; retain distinct source records (split-sector/year rows are legitimate).
idkeys=['year','provider','agency_code','crs_id','recipient_code','purpose_code']
repeated=d.duplicated(idkeys,keep=False)
d.loc[repeated,idkeys+['source_row','finance_t','usd_commitment','usd_commitment_defl','climate_adaptation','climate_mitigation']].to_parquet(OUT/'repeated_activity_keys.parquet',index=False)
semkeys=[x for x in cols if x not in ['donor_name','recipient_name','sector_name','flow_name']]
exact_duplicates=int(d.duplicated(semkeys).sum())
summary={'source_rows':f.metadata.num_rows,'eligible_named_activities_including_EU':len(d),'strict_cells_all2010_2024':len(strict),'primary_cells2015_2024':int(strict.year.ge(2015).sum()),'extension_cells2011_2024':int(strict.year.ge(2011).sum()),'quality_cells2010':int(strict.year.eq(2010).sum()),'primary_providers2015_2024':int(strict.loc[strict.year.ge(2015),'provider'].nunique()),'primary_recipients2015_2024':int(strict.loc[strict.year.ge(2015),'iso3'].nunique()),'incomplete_cells_excluding_EU':int((~cells.complete_markers & cells.primary_provider).sum()),'incomplete_cell_amount_excluding_EU':float(cells.loc[~cells.complete_markers & cells.primary_provider,'eligible_commitment'].sum()),'row_semantic_duplicates_retained':exact_duplicates,'repeated_activity_key_rows':int(repeated.sum()),'sector_purpose_code_mismatches':int((d.purpose_code.floordiv(100)!=d.sector).sum()),'amount_units':'millions of constant 2024 USD','source_snapshot':'v20260803','status':'source candidate; awaiting methods and join validation before model fit'}
(META/'panel_summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2),flush=True)
strict.groupby('year').agg(cells=('iso3','size'),providers=('provider','nunique'),recipients=('iso3','nunique'),adaptation=('adaptation_total','sum'),mitigation=('mitigation_total','sum'),nonclimate=('nonclimate_total','sum')).to_csv(OUT/'strict_panel_year_summary.csv')
assert not strict.duplicated(keys).any()
assert (strict[amountcols]>=0).all().all()
for purpose in purpose_masks:
 assert np.allclose(strict[purpose+'_total'],strict[purpose+'_grant']+strict[purpose+'_loan'])
