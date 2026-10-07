"""Source/zero-universe sensitivity; keep the primary PVCCI reference frozen."""
from pathlib import Path
import pandas as pd,numpy as np
from ppml_pipeline import load_lock,save_json,fit_stable,export_model
ROOT=Path(__file__).resolve().parent

def merge_variant(config,key):
    d=pd.read_parquet(config['inputs'][key]['path']).rename(columns={'iso3':'recipient'})
    cov=pd.read_csv(config['inputs']['covariates']['path']).rename(columns=config['column_maps']['covariates'])
    cov['year']=cov.year+1
    cov=cov[['recipient','year','debt_ratio','gdppc','population']].rename(columns={'debt_ratio':'debt_ratio_lag','gdppc':'gdppc_lag','population':'population_lag'})
    v=pd.read_csv(config['inputs']['vulnerability']['path']).rename(columns={'iso3':'recipient'})
    d=d.merge(cov,on=['recipient','year'],how='left',validate='many_to_one').merge(v[['recipient','pvcci']],on='recipient',how='left',validate='many_to_one')
    d=d[d.year.between(2015,2024)].copy()
    required=['debt_ratio_lag','gdppc_lag','population_lag','pvcci']
    valid=np.isfinite(d[required]).all(axis=1)&(d.debt_ratio_lag>=0)&(d.gdppc_lag>0)&(d.population_lag>0)
    d=d[valid].copy()
    import json
    ref=json.loads((ROOT/'outputs/pvcci_standardization.json').read_text())
    d['vuln_z']=(d.pvcci-ref['mean'])/ref['sd_population_ddof0'];d['debt10']=d.debt_ratio_lag/10
    d['interaction']=d.debt10*d.vuln_z;d['lngdp']=np.log(d.gdppc_lag);d['lnpop']=np.log(d.population_lag)
    d['dyad']=d.provider.astype(str)+'|'+d.recipient.astype(str);d['provider_year']=d.provider.astype(str)+'|'+d.year.astype(str)
    d=d.sort_values(['provider','recipient','year','sector']).reset_index(drop=True);d['cell_id']=np.arange(len(d))
    assert not d.duplicated(['provider','recipient','year','sector']).any()
    return d

def main():
    c=load_lock(ROOT/'design_lock.yaml');out=ROOT/'outputs/models';rows=[]
    for key,name in [('cells_valid_records','adaptation_valid_records'),('cells_including_EU','adaptation_including_EU')]:
        print(name,flush=True)
        try:
            d=merge_variant(c,key);folder=out/name;folder.mkdir(exist_ok=True,parents=True);d.to_parquet(folder/'preestimation_variant_panel.parquet',index=False)
            m=fit_stable(d,'adaptation_total',name);meta=export_model(m,out,'adaptation_total')
            row=pd.read_csv(folder/'coefficients.csv').set_index('term').loc['interaction'].to_dict();rows.append({'model':name,'n':meta['n'],'recipients':meta['recipients'],'providers':meta['providers'],**row})
        except Exception as e:save_json(out/name/'failure.json',{'error':str(e)})
    pd.DataFrame(rows).to_csv(out/'universe_sensitivities.csv',index=False)
if __name__=='__main__':main()
