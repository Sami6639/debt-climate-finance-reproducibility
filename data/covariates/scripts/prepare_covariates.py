#!/usr/bin/env python3
"""Build source-faithful recipient covariates and static PVCCI; no sample-dependent transforms.
Requires pandas, numpy, openpyxl. No imputation, interpolation, standardization or winsorization.
"""
import pathlib,json,hashlib,zipfile
import pandas as pd
import numpy as np
ROOT=pathlib.Path(__file__).resolve().parents[1]; RAW=ROOT/'raw'; OUT=ROOT/'processed';META=ROOT/'metadata'
MAP={
'DT.TDS.DPPF.XP.ZS':'debt_service_ppg_imf_pct_exports',
'DT.TDS.DPPG.XP.ZS':'debt_service_ppg_pct_exports',
'DT.TDS.DECT.EX.ZS':'debt_service_total_pct_exports',
'DT.TDS.DPPG.CD':'debt_service_ppg_current_usd',
'DT.TDS.DIMF.CD':'debt_service_imf_current_usd',
'DT.TDS.DECT.CD':'debt_service_total_current_usd',
'DT.DOD.DECT.GN.ZS':'debt_stock_total_pct_gni',
'DT.DOD.DECT.CD':'debt_stock_total_current_usd',
'DT.DOD.DPPG.CD':'debt_stock_ppg_current_usd',
'BX.GSR.TOTL.CD':'exports_goods_services_primary_income_current_usd',
'BX.GSR.GNFS.CD':'exports_goods_services_current_usd',
'NY.GDP.PCAP.KD':'gdp_pc_constant_usd',
'NY.GDP.PCAP.CD':'gdp_pc_current_usd',
'NY.GNP.PCAP.KD':'gni_pc_constant_usd',
'NY.GNP.PCAP.CD':'gni_pc_atlas_current_usd',
'SP.POP.TOTL':'population'}
cs=json.loads((RAW/'wb_countries.json').read_text())[1]
countries=pd.DataFrame([{'iso3':x['id'],'iso2':x['iso2Code'],'country_name':x['name'],'region':x['region']['value'],'region_code':x['region']['id'],'current_income_group':x['incomeLevel']['value'],'current_lending_type':x['lendingType']['value']} for x in cs if x['region']['id']!='NA'])
countries.to_csv(OUT/'wb_country_crosswalk.csv',index=False)
frames=[];meta=[];coverage=[]
for c,var in MAP.items():
 d=json.loads((RAW/f'wb_{c}_2010_2024.json').read_text()); assert d[0]['pages']==1 and len(d[1])==d[0]['total']
 f=pd.DataFrame([{'iso3':x['countryiso3code'],'year':int(x['date']),var:x['value']} for x in d[1]])
 f=f[f.iso3.isin(countries.iso3)]
 assert not f.duplicated(['iso3','year']).any()
 frames.append(f.set_index(['iso3','year']))
 md=json.loads((RAW/f'wb_metadata_{c}.json').read_text())[1][0]
 meta.append({'variable':var,'indicator_code':c,'official_name':md['name'],'source_note':md['sourceNote'],'source_organization':md['sourceOrganization'],'api_source':md['source'],'last_updated':d[0].get('lastupdated'),'period_requested':'2010:2024','ratio_unit':'percent, not proportion' if c.endswith('.ZS') else None,'metadata_url':f'https://api.worldbank.org/v2/indicator/{c}?source=2&format=json'})
 coverage += [{'variable':var,'year':int(y),'countries_nonmissing':int(s.notna().sum())} for y,s in f.groupby('year')[var]]
x=pd.concat(frames,axis=1).reset_index().merge(countries[['iso3','country_name']],on='iso3',validate='many_to_one').sort_values(['iso3','year'])
assert len(x)==217*15 and not x.duplicated(['iso3','year']).any()
x=x[['iso3','year','country_name']+list(MAP.values())]
x.to_csv(OUT/'recipient_covariates_2010_2024.csv',index=False,float_format='%.15g')
pd.DataFrame(coverage).to_csv(META/'covariate_coverage_by_year.csv',index=False)
(META/'wb_variable_dictionary.json').write_text(json.dumps(meta,indent=2,ensure_ascii=False))
# Retain original national ISO codes and retain Anguilla even though WDI lacks it.
pv=None
for sheet in ['PVCCI','PVCCI2','PVCCI3']:
 f=pd.read_excel(RAW/'pvcci_ferdi.xlsx',sheet_name=sheet)
 assert len(f)==191 and not f.ISO.duplicated().any() and f[sheet].notna().all()
 name=sheet.lower()
 f=f.rename(columns={'ISO':'iso3','Country':'country_name_ferdi',sheet:name,'Rank':name+'_rank'})
 cols=[c for c in f if c not in ['iso3','country_name_ferdi',name,name+'_rank']]
 components=['flooding','aridity','rainfall','temperature','storms']
 f=f.rename(columns=dict(zip(cols,[name+'_'+c for c in components])))
 # Published national composite is the quadratic mean of its five component scores.
 error=np.abs(np.sqrt((f[[name+'_'+c for c in components]]**2).mean(axis=1))-f[name])
 assert error.max()<1e-8, (sheet,error.max())
 pv=f if pv is None else pv.merge(f.drop(columns='country_name_ferdi'),on='iso3',validate='one_to_one')
pv['pvcci_edition']='October 2018';pv['climate_series_last_year']=2016;pv['storm_series_last_year']=2014
pv=pv.sort_values('iso3');pv.to_csv(OUT/'pvcci_static.csv',index=False,float_format='%.15g')
pv[['iso3','country_name_ferdi']].merge(countries[['iso3','iso2','country_name']],on='iso3',how='outer',indicator=True,validate='one_to_one').to_csv(META/'pvcci_wb_country_crosswalk_audit.csv',index=False)
# Auditable ratio identity. Keep reported ratios unchanged even for revision discrepancies.
a=x.dropna(subset=['debt_service_ppg_imf_pct_exports','debt_service_ppg_current_usd','debt_service_imf_current_usd','exports_goods_services_primary_income_current_usd']).copy()
a['reconstructed_ppg_imf_pct_primary_income']=100*(a.debt_service_ppg_current_usd+a.debt_service_imf_current_usd)/a.exports_goods_services_primary_income_current_usd
a['ratio_residual_pp']=a.debt_service_ppg_imf_pct_exports-a.reconstructed_ppg_imf_pct_primary_income
a['reconstructed_ppg_imf_pct_goods_services']=100*(a.debt_service_ppg_current_usd+a.debt_service_imf_current_usd)/a.exports_goods_services_current_usd
a['goods_services_only_residual_pp']=a.debt_service_ppg_imf_pct_exports-a.reconstructed_ppg_imf_pct_goods_services
a[['iso3','year','debt_service_ppg_imf_pct_exports','reconstructed_ppg_imf_pct_primary_income','ratio_residual_pp','reconstructed_ppg_imf_pct_goods_services','goods_services_only_residual_pp']].to_csv(META/'debt_ratio_denominator_validation.csv',index=False,float_format='%.15g')
valid=a['ratio_residual_pp'].abs()<1e-7
summary={'country_year_rows':len(x),'countries':x.iso3.nunique(),'years':[int(x.year.min()),int(x.year.max())],'pvcci_country_rows':len(pv),'pvcci_wb_matches':len(set(pv.iso3)&set(countries.iso3)),'ppg_imf_ratio_nonmissing':int(x.debt_service_ppg_imf_pct_exports.notna().sum()),'ppg_imf_countries':int(x.loc[x.debt_service_ppg_imf_pct_exports.notna(),'iso3'].nunique()),'ratio_identity_rows':len(a),'ratio_identity_abs_error_lt_1e_7':int(valid.sum()),'ratio_identity_exceptions':a.loc[~valid,['iso3','year','ratio_residual_pp']].to_dict('records'),'source_vintage':'WDI API source 2; lastupdated 2026-07-13','original_replication':False,'transforms_applied':'none; all reported ratios in percentage points; PVCCI unstandardized'}
(META/'validation_summary.json').write_text(json.dumps(summary,indent=2))
print(json.dumps({k:v for k,v in summary.items() if k!='ratio_identity_exceptions'},indent=2)); print('Ratio exceptions:',len(summary['ratio_identity_exceptions']));print(a.loc[~valid,['iso3','year','ratio_residual_pp']].to_string(index=False))
# Supplemental reproducible coverage and recipient lookup audits when OECD source files exist.
z=x.merge(pv[['iso3','pvcci']],on='iso3',how='left',validate='many_to_one')
z['joint_complete']=z[['debt_service_ppg_imf_pct_exports','gdp_pc_constant_usd','population','pvcci']].notna().all(axis=1)
z.groupby('year').agg(debt_service_nonmissing=('debt_service_ppg_imf_pct_exports',lambda s:s.notna().sum()),baseline_joint_complete=('joint_complete','sum')).reset_index().to_csv(META/'baseline_joint_covariate_coverage.csv',index=False)
oecd=ROOT.parent/'oecd'
if (oecd/'metadata/recipient.csv').exists():
 d=pd.read_csv(oecd/'metadata/recipient.csv')
 d=d[d.ISOcode.astype(str).str.fullmatch('[A-Z]{3}')][['Recipient code','Recipient name (EN)','ISOcode','Region']].rename(columns={'Recipient code':'oecd_recipient_code','Recipient name (EN)':'oecd_recipient_name','ISOcode':'iso3','Region':'oecd_region'})
 assert not d.iso3.duplicated().any()
 d.merge(countries[['iso3','country_name']],how='left',on='iso3',validate='one_to_one').merge(pv[['iso3','country_name_ferdi','pvcci']],how='left',on='iso3',validate='one_to_one').to_csv(OUT/'oecd_wb_pvcci_crosswalk.csv',index=False)
if (oecd/'processed/actual_recipient_codes.csv').exists():
 d=pd.read_csv(oecd/'processed/actual_recipient_codes.csv')
 d['is_named_country_or_territory']=d.de_recipientcode.astype(str).str.fullmatch('[A-Z]{3}')
 d['iso3']=d.de_recipientcode.where(d.is_named_country_or_territory).replace({'XKV':'XKX'})
 d['mapping_note']=np.where(d.de_recipientcode.eq('XKV'),'OECD recipient 57 Kosovo: official recipient codebook ISOcode XKX; source uses XKV',np.where(d.is_named_country_or_territory,'Direct source ISO3 match','Regional or unspecified allocation; do not assign country covariates'))
 a=d.merge(countries[['iso3','country_name']],on='iso3',how='left',validate='many_to_one').merge(pv[['iso3','country_name_ferdi','pvcci']],on='iso3',how='left',validate='many_to_one')
 debt_counts=x.groupby('iso3').agg(debt_service_available_years=('debt_service_ppg_imf_pct_exports',lambda s:s.notna().sum()),real_gdppc_available_years=('gdp_pc_constant_usd',lambda s:s.notna().sum())).reset_index()
 a=a.merge(debt_counts,on='iso3',how='left',validate='many_to_one')
 a.to_csv(OUT/'actual_oecd_recipient_covariate_crosswalk.csv',index=False)
 print('Actual named OECD source recipients:',a.is_named_country_or_territory.sum(),'of',len(a))
 print('Named source recipients absent WB or PVCCI:')
 print(a.loc[a.is_named_country_or_territory & (a.country_name.isna() | a.pvcci.isna()),['de_recipientcode','iso3','recipient_name','country_name','pvcci','debt_service_available_years']].to_string(index=False))
if (OUT/'actual_oecd_recipient_covariate_crosswalk.csv').exists():
 source_codes=pd.read_csv(OUT/'actual_oecd_recipient_covariate_crosswalk.csv').iso3.dropna()
 z[z.iso3.isin(source_codes)&z.year.between(2014,2023)].groupby('year').agg(joint_covariate_countries=('joint_complete','sum')).reset_index().to_csv(META/'actual_crs_recipient_covariate_coverage.csv',index=False)
# Record readable internal workbook edition evidence without treating site upload dates as index vintages.
r=pd.read_excel(RAW/'pvcci_ferdi.xlsx',sheet_name='Read me',header=None)
(META/'pvcci_workbook_readme.txt').write_text('\n'.join(f'Excel row {i+1}: {row[0]}' for i,row in r.iterrows() if row.notna().any()))
(META/'pvcci_workbook_core_properties.xml').write_bytes(zipfile.ZipFile(RAW/'pvcci_ferdi.xlsx').read('docProps/core.xml'))
files=sorted(f for f in ROOT.rglob('*') if f.is_file() and f.name!='SHA256SUMS' and '__pycache__' not in str(f) and f.suffix!='.log')
(META/'SHA256SUMS').write_text('\n'.join(hashlib.sha256(f.read_bytes()).hexdigest()+'  '+str(f.relative_to(ROOT)) for f in files)+'\n')
