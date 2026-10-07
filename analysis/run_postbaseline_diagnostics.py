"""Approved post-baseline diagnostics, distinguished from pre-fit specifications."""
from pathlib import Path
import numpy as np,pandas as pd
from ppml_pipeline import load_lock,fit_stable,export_model,save_json,VARS
ROOT=Path(__file__).resolve().parent

def main():
    config=load_lock(ROOT/'design_lock.yaml');out=ROOT/'outputs/models'
    base=pd.read_parquet(ROOT/'outputs/analysis_panel.parquet');base=base[base.year>=2015].copy()
    cov=pd.read_csv(config['inputs']['covariates']['path']);g=cov[cov.year==2014][['iso3','gdp_pc_constant_usd']].rename(columns={'iso3':'recipient','gdp_pc_constant_usd':'gdppc2014'})
    countries=base[['recipient','vuln_z']].drop_duplicates().merge(g,on='recipient',how='left',validate='one_to_one')
    countries['lngdp2014']=np.log(countries.gdppc2014);valid=countries.lngdp2014.notna()&np.isfinite(countries.lngdp2014)
    center=countries.loc[valid,'lngdp2014'].mean();countries['income2014_centered']=countries.lngdp2014-center
    countries.to_csv(ROOT/'outputs/postbaseline_income_reference.csv',index=False)
    d=base.merge(countries[['recipient','income2014_centered']],on='recipient',how='left',validate='many_to_one').dropna(subset='income2014_centered')
    d['income_debt_interaction']=d.debt10*d.income2014_centered
    save_json(ROOT/'outputs/postbaseline_diagnostics_design.json',{'approval_time_utc':'2026-10-07T08:51:00Z','status':'approved after observing baseline results; not prespecified before baseline','reason':'income-related debt-slope heterogeneity and provider concentration','income_reference_year':2014,'income_definition':'log real GDP per capita, centered at unweighted unique baseline recipient mean','income_mean_log':center,'reference_recipients':len(countries),'missing_income_recipients':int((~valid).sum()),'country_correlation_Z_log_income':float(countries[['vuln_z','lngdp2014']].corr().iloc[0,1]),'matched_input_cells':len(d),'no_income_definition_search':True})
    name='adaptation_income_moderator_postbaseline'
    try:
        print(name,flush=True);m=fit_stable(d,'adaptation_total',name,rhs=VARS+['income_debt_interaction']);export_model(m,out,'adaptation_total')
        if len(d)!=len(base):
            m=fit_stable(d,'adaptation_total','adaptation_income_matched_baseline');export_model(m,out,'adaptation_total')
    except Exception as e:save_json(out/name/'failure.json',{'error':str(e)})
    # Last additional diagnostic, approved after baseline at 09:00 UTC.
    name='adaptation_vulnerability_year_postbaseline';dd=base.copy();extra=[]
    for year in range(2016,2025):
        term=f'vulnerability_year_{year}';dd[term]=dd.vuln_z*(dd.year==year);extra.append(term)
    save_json(ROOT/'outputs/postbaseline_vulnerability_year_design.json',{'approval_time_utc':'2026-10-07T09:00:00Z','status':'approved after baseline results; last added diagnostic','reason':'test changing vulnerability-related allocation gradients not absorbed by provider-year effects','reference_year':2015,'terms':extra,'common_debt_and_debt_vulnerability_slopes':True,'same_source_controls_FE_and_frozen_Z':True,'no_additional_specification_search':True})
    try:
        print(name,flush=True);m=fit_stable(dd,'adaptation_total',name,rhs=VARS+extra);export_model(m,out,'adaptation_total')
    except Exception as e:save_json(out/name/'failure.json',{'error':str(e)})
    retained=pd.read_parquet(out/'adaptation_total'/'retained_sample.parquet');providers=sorted(retained.provider.unique());volume=retained.groupby('provider').adaptation_total.sum();rows=[]
    names=base[['provider','donor_name']].drop_duplicates().set_index('provider').donor_name
    for provider in providers:
        name=f'adaptation_total_without_provider_{provider}'
        print(name,flush=True)
        try:
            dd=base[base.provider!=provider].copy();m=fit_stable(dd,'adaptation_total',name);meta=export_model(m,out,'adaptation_total')
            r=pd.read_csv(out/name/'coefficients.csv').set_index('term').loc['interaction'].to_dict()
            rows.append({'excluded_provider':provider,'provider_name':names[provider],'baseline_volume_share':volume[provider]/volume.sum(),'input_n':len(dd),'retained_n':meta['n'],'recipients':meta['recipients'],'providers':meta['providers'],'status':'converged',**r})
        except Exception as e:
            save_json(out/name/'failure.json',{'error':str(e)});rows.append({'excluded_provider':provider,'provider_name':names[provider],'baseline_volume_share':volume[provider]/volume.sum(),'status':'failed','error':str(e)})
        pd.DataFrame(rows).to_csv(out/'adaptation_total_provider_influence_postbaseline.csv',index=False)
    print('Completed every retained-provider omission.',flush=True)
if __name__=='__main__':main()
