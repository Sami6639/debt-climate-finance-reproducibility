"""Auditable reconstruction; estimation is delegated to pinned PyFixest.
No substantive fit is permitted until the source/design lock is finalized.
"""
from __future__ import annotations
import os
os.environ.setdefault('MPLCONFIGDIR','/tmp/debt_mpl')
os.environ.setdefault('XDG_CACHE_HOME','/tmp/debt_xdg')
os.environ.setdefault('OMP_NUM_THREADS','2')
from pathlib import Path
import argparse, hashlib, importlib.metadata as md, json, platform, sys, warnings
from dataclasses import dataclass
import numpy as np
import pandas as pd
import pyfixest as pf
import yaml
from scipy import stats
from statsmodels.stats.multitest import multipletests

ROOT=Path(__file__).resolve().parent
VARS=['debt10','interaction','lngdp','lnpop']
FE=['dyad','provider_year','sector']
SSC=dict(k_adj=True,k_fixef='nonnested',G_adj=True,G_df='conventional')


def serializable(value):
    if isinstance(value,dict): return {str(k):serializable(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)): return [serializable(x) for x in value]
    if isinstance(value,(np.ndarray,pd.Series,pd.Index)): return serializable(value.tolist())
    if isinstance(value,(np.integer,np.floating,np.bool_)): return value.item()
    if isinstance(value,Path): return str(value)
    return value


def save_json(path, value):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    Path(path).write_text(json.dumps(serializable(value),indent=2,allow_nan=False,default=str))


def file_sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()


def read_df(path):
    p=Path(path)
    return pd.read_parquet(p) if p.suffix=='.parquet' else pd.read_csv(p)


def load_lock(path):
    lock_path=Path(path).resolve()
    config=yaml.safe_load(lock_path.read_text())
    for item in config.get('inputs',{}).values():
        if not Path(item['path']).is_absolute():item['path']=str(lock_path.parent.parent/item['path'])
    if config.get('status')!='locked':
        raise RuntimeError('Substantive execution blocked: design/source lock is not finalized.')
    for name,item in config['inputs'].items():
        if file_sha(item['path'])!=item['sha256']:
            raise RuntimeError(f'Input hash differs from source lock: {name}')
    return config


def prepare(config,outdir):
    """Load already-filtered cells, merge exact calendar lags, standardize once."""
    outdir=Path(outdir);outdir.mkdir(parents=True,exist_ok=True)
    cells=read_df(config['inputs']['cells']['path']).rename(columns=config['column_maps'].get('cells',{}))
    cov=read_df(config['inputs']['covariates']['path']).rename(columns=config['column_maps'].get('covariates',{}))
    vuln=read_df(config['inputs']['vulnerability']['path']).rename(columns=config['column_maps'].get('vulnerability',{}))
    keys=['provider','recipient','year','sector']
    required=keys+list(config['outcomes'].values())
    assert set(required)<=set(cells),f'Missing cells columns: {set(required)-set(cells)}'
    assert not cells.duplicated(keys).any(),'Duplicated allocation cell'
    assert not cov.duplicated(['recipient','year']).any(),'Duplicated recipient-year covariate'
    assert not vuln.duplicated('recipient').any(),'Duplicated vulnerability recipient'
    assert not cells[keys].isna().any().any(),'Missing allocation key'
    if 'complete_markers' in cells: assert cells.complete_markers.all(),'Primary file contains incomplete marker cells'
    if 'primary_provider' in cells: assert cells.primary_provider.all(),'Primary file contains excluded providers'
    for prefix in ['adaptation','mitigation','nonclimate']:
        cols=[f'{prefix}_{suffix}' for suffix in ['total','grant','loan']]
        if set(cols)<=set(cells): assert np.allclose(cells[cols[0]],cells[cols[1]]+cells[cols[2]],rtol=1e-10,atol=1e-10),f'{prefix} instrument identity failed'
    for col in config['outcomes'].values():
        assert np.isfinite(cells[col]).all() and (cells[col]>=0).all(),f'Invalid nonnegative outcome: {col}'
    cov['year']=cov['year'].astype(int)+1  # Observed covariate at t-1 explicitly matched to allocation t.
    cov=cov.rename(columns={c:c+'_lag' for c in cov.columns if c not in ['recipient','year']})
    assert (vuln['pvcci'].dropna().groupby(vuln.recipient).nunique()<=1).all()
    panel=cells.merge(cov,on=['recipient','year'],how='left',validate='many_to_one')
    panel=panel.merge(vuln[[c for c in ['recipient','pvcci','pvcci2','pvcci3'] if c in vuln]],on='recipient',how='left',validate='many_to_one')
    audit=[]
    def note(stage,frame):
        audit.append({'stage':stage,'cells':len(frame),'recipients':frame.recipient.nunique(),'providers':frame.provider.nunique(),'years':','.join(map(str,sorted(frame.year.unique())))})
    note('classified_source_cells',panel)
    panel=panel[panel.year.between(config['start_year'],config['end_year'])].copy()
    note('analysis_period',panel)
    missing_counts=[]
    for v in ['debt_ratio_lag','gdppc_lag','population_lag','pvcci']:
        missing_counts.append({'variable':v,'missing_cells':int(panel[v].isna().sum()),'nonfinite_cells':int((~np.isfinite(panel[v])).sum()),'nonpositive_cells':int((panel[v]<=0).sum())})
    pd.DataFrame(missing_counts).to_csv(outdir/'covariate_missing_counts.csv',index=False)
    invalid=panel[['debt_ratio_lag','gdppc_lag','population_lag','pvcci']].isna().any(axis=1)
    invalid|=(panel.debt_ratio_lag<0)|(panel.gdppc_lag<=0)|(panel.population_lag<=0)
    invalid|=~np.isfinite(panel[['debt_ratio_lag','gdppc_lag','population_lag','pvcci']]).all(axis=1)
    panel.assign(invalid_covariate=invalid).loc[invalid,keys+['debt_ratio_lag','gdppc_lag','population_lag','pvcci','invalid_covariate']].to_csv(outdir/'excluded_covariate_cells.csv',index=False)
    panel=panel.loc[~invalid].copy()
    note('complete_lag_covariates',panel)
    # Standardize unique baseline eligible countries, not cells, years or separated samples.
    baseline=panel[panel.year.between(config['primary_start_year'],config['end_year'])]
    unique=baseline[['recipient','pvcci']].drop_duplicates()
    assert not unique.duplicated('recipient').any()
    mean=unique.pvcci.mean();sd=unique.pvcci.std(ddof=0)
    assert np.isfinite(sd) and sd>0
    unique['pvcci_z']=(unique.pvcci-mean)/sd
    unique.to_csv(outdir/'pvcci_standardization_countries.csv',index=False)
    save_json(outdir/'pvcci_standardization.json',{'mean':mean,'sd_population_ddof0':sd,'n_unique_recipients':len(unique),'baseline_start_year':config['primary_start_year'],'baseline_end_year':config['end_year'],'timing':'before all outcome-specific pruning'})
    panel['vuln_z']=(panel.pvcci-mean)/sd
    panel['debt10']=panel.debt_ratio_lag/10
    panel['interaction']=panel.debt10*panel.vuln_z
    panel['lngdp']=np.log(panel.gdppc_lag)
    panel['lnpop']=np.log(panel.population_lag)
    panel['dyad']=panel.provider.astype(str)+'|'+panel.recipient.astype(str)
    panel['provider_year']=panel.provider.astype(str)+'|'+panel.year.astype(str)
    panel=panel.sort_values(keys).reset_index(drop=True)
    panel['cell_id']=np.arange(len(panel))
    panel.to_parquet(outdir/'analysis_panel.parquet',index=False)
    pd.DataFrame(audit).to_csv(outdir/'sample_construction.csv',index=False)
    return panel


@dataclass
class Model:
    fit: object
    data: pd.DataFrame
    name: str
    formula: str
    pruning: list
    warnings: list


def fit_stable(df,y,name,rhs=None,fe=None,maxiter=300,tol=1e-10):
    """Repeated package fitting reaches stable finite-identification support.
    No local estimator or covariance algorithm is substituted.
    """
    rhs=rhs or VARS;fe=fe or FE
    formula=f"{y} ~ {' + '.join(rhs)} | {' + '.join(fe)}"
    assert df.cell_id.is_unique,'Each modeled row requires a unique cell_id.'
    current=df.copy();pruning=[];notes=[]
    # Exact structural preprocessing before the costly general separation check.
    # No coefficient or p-value is used. Zero-sum FE groups contain only zeros.
    while True:
        single=np.zeros(len(current),dtype=bool)
        for fename in fe: single|=current.groupby(fename,observed=True)[y].transform('size').to_numpy()==1
        if single.any():
            removed=current.loc[single];pruning.append({'stage':'structural_singleton','iteration':len(pruning)+1,'input_n':len(current),'retained_n':len(current)-len(removed),'removed_n':len(removed),'separation_removed_n':0,'singleton_removed_n':len(removed),'removed_cell_ids':removed.cell_id.tolist()});current=current.loc[~single].copy()
        zero=np.zeros(len(current),dtype=bool)
        for fename in fe: zero|=current.groupby(fename,observed=True)[y].transform('max').to_numpy()==0
        if zero.any():
            removed=current.loc[zero];pruning.append({'stage':'structural_allzero_fe','iteration':len(pruning)+1,'input_n':len(current),'retained_n':len(current)-len(removed),'removed_n':len(removed),'separation_removed_n':len(removed),'singleton_removed_n':0,'removed_cell_ids':removed.cell_id.tolist()});current=current.loc[~zero].copy()
        if not single.any() and not zero.any():break
    while True:
        if len(current)<len(rhs)+5 or current[y].sum()<=0:
            raise ValueError(f'{name}: no adequately identified positive outcome support.')
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')
            f=pf.fepois(formula,current.reset_index(drop=True),
                vcov={'CRV1':'recipient'},ssc=pf.ssc(**SSC),
                fixef_rm='singleton',separation_check=['fe','ir'],
                iwls_tol=tol,iwls_maxiter=maxiter,collin_tol=1e-10,
                demeaner=pf.LsmrDemeaner(backend='within',fixef_atol=1e-10,fixef_btol=1e-10,fixef_maxiter=10000),
                copy_data=True,store_data=True,lean=False)
        ws=[str(v.message) for v in w];notes+=ws
        if any('maximum number of iterations reached before convergence' in v for v in ws):
            raise RuntimeError(f'{name}: iterative separation check failed to converge. '+str(ws))
        if not getattr(f,'_convergence',False):
            raise RuntimeError(f'{name}: PPML convergence not established.')
        retained=f._data.copy()
        removed=current.loc[~current.cell_id.isin(retained.cell_id)]
        pruning.append({'iteration':len(pruning)+1,'input_n':len(current),'retained_n':len(retained),'removed_n':len(removed),'separation_removed_n':int(f.n_separation_na),'singleton_removed_n':int(len(removed)-f.n_separation_na),'removed_cell_ids':removed.cell_id.tolist()})
        assert len(retained)==f._N and len(removed)>=f.n_separation_na
        missing=set(rhs)-set(f.coef().index)
        if missing: raise RuntimeError(f'{name}: prespecified coefficients are collinear: {missing}')
        if len(removed)==0:
            return Model(f,retained,name,formula,pruning,notes)
        assert len(retained)<len(current)
        current=retained


def normal_contrast(beta,cov,vector,clusters):
    a=np.asarray(vector);estimate=float(a@beta);variance=float(a@cov@a)
    if variance<=0 or not np.isfinite(variance):
        return {'estimate':estimate,'variance':variance,'inference_valid':False}
    se=np.sqrt(variance);z=estimate/se;q=stats.norm.ppf(.975);qt=stats.t.ppf(.975,clusters-1)
    return {'estimate':estimate,'variance':variance,'se':se,'z':z,'p_normal':2*stats.norm.sf(abs(z)),'ci95_low':estimate-q*se,'ci95_high':estimate+q*se,'p_t_recipient':2*stats.t.sf(abs(z),clusters-1),'ci95_t_low':estimate-qt*se,'ci95_t_high':estimate+qt*se,'inference_valid':True}


def concentration(df,y,group):
    volume=df.groupby(group,observed=True)[y].sum();volume=volume[volume>0]
    share=volume/volume.sum();n=df.groupby(group,observed=True).size();ns=n/n.sum()
    return {'clusters_retained':df[group].nunique(),'positive_volume_clusters':len(volume),'effective_clusters_volume':float(1/(share**2).sum()),'largest_volume_share':float(share.max()),'effective_clusters_observations':float(1/(ns**2).sum())}


def export_model(model,outdir,y,conditional=True):
    """Export recipient-primary inference before changing covariance to diagnostic."""
    target=Path(outdir)/model.name;target.mkdir(parents=True,exist_ok=True)
    f=model.fit;d=model.data
    beta=f.coef();names=beta.index.tolist();cov=f._vcov.copy()
    pd.DataFrame(cov,index=names,columns=names).to_csv(target/'covariance_recipient.csv')
    rows=[]
    for j,name in enumerate(names):
        a=np.eye(len(names))[j]
        rows.append({'term':name,**normal_contrast(beta.values,cov,a,d.recipient.nunique())})
    pd.DataFrame(rows).to_csv(target/'coefficients.csv',index=False)
    # Retained source identifiers and fitted values permit independent checks.
    sample_cols=[c for c in ['cell_id','base_cell_id','purpose','provider','recipient','year','sector',y,'debt10','interaction','lngdp','lnpop','pvcci','vuln_z'] if c in d]
    retained=d[sample_cols].copy();retained['mu']=np.asarray(f._Y_hat_response)
    retained['response_residual']=np.asarray(f.resid()).flatten()
    retained.to_parquet(target/'retained_sample.parquet',index=False)
    residual=retained.response_residual.to_numpy();mu=retained.mu.to_numpy()
    # Source-space and FE score residuals, not only IWLS working residuals.
    raw_score={c:float(np.sum(d[c].to_numpy()*residual)) for c in names if c in d}
    fe_score={}
    for c in [x.strip() for x in model.formula.split('|')[1].split('+')]:
        g=pd.DataFrame({'fe':d[c].to_numpy(),'e':residual,'mu':mu}).groupby('fe',observed=True).sum()
        fe_score[c]=float((g.e.abs()/np.maximum(1,g.mu)).max())
    metadata={'model':model.name,'formula':model.formula,'outcome':y,'package':'pyfixest','demeaner':'LsmrDemeaner within, atol=btol=1e-10, maxiter=10000; numerical replacement after MAP failure, same model','version':md.version('pyfixest'),'n':len(d),'positive_n':int((d[y]>0).sum()),'zero_n':int((d[y]==0).sum()),'zero_share':float((d[y]==0).mean()),'total_outcome_usd_millions':float(d[y].sum()),'recipients':d.recipient.nunique(),'providers':d.provider.nunique(),'dyads':d[['recipient','provider']].drop_duplicates().shape[0],'years':sorted(d.year.unique().tolist()),'convergence':bool(f._convergence),'irls_iterations':'not exposed by pinned public result; convergence flag and score checks retained','recipient_years':d[['recipient','year']].drop_duplicates().shape[0],'deviance':float(f.deviance),'raw_slope_scores':raw_score,'fe_max_relative_scores':fe_score,'sum_response_residual':float(residual.sum()),'ssc_config':SSC,'primary_ssc_factors':f._ssc.copy(),'primary_df_k':f._df_k,'primary_reference':'standard normal','recipient_t_sensitivity_df':int(d.recipient.nunique()-1),'covariance_recipient_min_eigenvalue':float(np.linalg.eigvalsh(cov).min()),'pruning':model.pruning,'warnings':model.warnings,'provider_concentration':concentration(d,y,'provider'),'recipient_concentration':concentration(d,y,'recipient')}
    volume=d.groupby('provider',observed=True).agg(n=(y,'size'),positive_n=(y,lambda s:int((s>0).sum())),amount=(y,'sum')).reset_index()
    volume['volume_share']=volume.amount/volume.amount.sum()
    volume.sort_values('amount',ascending=False).to_csv(target/'provider_support.csv',index=False)
    if 'income_debt_interaction' in names:
        metadata['conditional_effect_reference']='Conditional debt slopes hold centered log real GDP per capita in 2014 at zero, the baseline-country mean of log income. They are not averaged over income.'
    if conditional and 'debt10' in names and 'interaction' in names:
        support=d[['recipient','vuln_z','pvcci']].drop_duplicates().sort_values('vuln_z')
        zvalues=np.unique(np.r_[np.linspace(support.vuln_z.min(),support.vuln_z.max(),151),support.vuln_z.quantile([0,.1,.25,.5,.75,.9,1]).values])
        effects=[]
        for z in zvalues:
            a=np.zeros(len(names));a[names.index('debt10')]=1;a[names.index('interaction')]=z
            r=normal_contrast(beta.values,cov,a,d.recipient.nunique())
            r.update(vuln_z=z,percent_change_10pp=100*np.expm1(r['estimate']),percent_ci95_low=100*np.expm1(r['ci95_low']),percent_ci95_high=100*np.expm1(r['ci95_high']))
            effects.append(r)
        pd.DataFrame(effects).to_csv(target/'conditional_debt_effect.csv',index=False)
        support.to_csv(target/'vulnerability_support.csv',index=False)
    # Package computes raw multiway inclusion-exclusion without spectral clipping.
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter('always');f.vcov({'CRV1':'recipient + provider'})
    cov2=f._vcov.copy();eig=np.linalg.eigvalsh(cov2)
    scale=max(float(np.linalg.norm(cov2,ord=2)),np.finfo(float).tiny)
    psd=bool(eig.min()>=-1e-10*scale)
    pd.DataFrame(cov2,index=names,columns=names).to_csv(target/'covariance_twoway_raw.csv')
    components=[];reconstructed=np.zeros_like(cov2)
    for j,c in enumerate(f._cluster_df.columns):
        codes=pd.factorize(f._cluster_df[c])[0]
        raw=f._vcov_crv1(clustid=np.unique(codes),cluster_col=codes)
        weighted=f._ssc[j]*raw;reconstructed+=weighted
        tag=['recipient','provider','intersection'][j]
        pd.DataFrame(raw,index=names,columns=names).to_csv(target/f'covariance_twoway_component_{tag}_unadjusted.csv')
        pd.DataFrame(weighted,index=names,columns=names).to_csv(target/f'covariance_twoway_component_{tag}_signed_adjusted.csv')
        components.append({'component':tag,'clusters':len(np.unique(codes)),'signed_ssc_factor':float(f._ssc[j])})
    assert np.allclose(reconstructed,cov2,rtol=1e-10,atol=1e-12)
    metadata['twoway']={'psd':psd,'eigenvalues':eig.tolist(),'components':components,'df_k':f._df_k,'warnings':[str(v.message) for v in w],'handling':'Raw matrix retained. Inference suppressed if non-PSD; no eigenvalue clipping.'}
    if psd:
        pd.DataFrame([{'term':name,**normal_contrast(beta.values,cov2,np.eye(len(names))[j],min(d.recipient.nunique(),d.provider.nunique()))} for j,name in enumerate(names)]).to_csv(target/'coefficients_twoway_diagnostic.csv',index=False)
    save_json(target/'diagnostics.json',metadata)
    # Restore primary covariance so downstream tests cannot silently use diagnostics.
    f.vcov({'CRV1':'recipient'})
    assert np.allclose(f._vcov,cov)
    return metadata


def common_support_contrast(panel,outcomes,left,right,name,outdir):
    """Intersect finite-identification samples to a fixed point, then stack.
    Purpose-specific controls and all nuisance FEs allow separate conditional means;
    recipient clustering captures within-cell and between-purpose correlation.
    """
    common=panel.copy();history=[]
    while True:
        fits={p:fit_stable(common,outcomes[p],f'{name}_{p}_support') for p in [left,right]}
        ids=set.intersection(*(set(m.data.cell_id) for m in fits.values()))
        history.append({'input_cells':len(common),'retained_common_cells':len(ids),'left_retained':len(fits[left].data),'right_retained':len(fits[right].data)})
        if len(ids)==len(common):break
        if not ids:raise RuntimeError(f'{name}: empty common finite-identification support')
        common=common[common.cell_id.isin(ids)].copy()
    pieces=[];rhs=[]
    for k,p in enumerate([left,right]):
        d=common.copy();d['purpose']=p;d['outcome']=d[outcomes[p]];d['base_cell_id']=d.cell_id
        for v in VARS:
            for kk in range(2): d[f'{v}_p{kk}']=d[v] if k==kk else 0.
        for fe in FE:d[f'{fe}_purpose']=d[fe].astype(str)+'|'+p
        pieces.append(d)
    stack=pd.concat(pieces,ignore_index=True);stack['cell_id']=np.arange(len(stack))
    rhs=[f'{v}_p{k}' for k in range(2) for v in VARS]
    m=fit_stable(stack,'outcome',name,rhs=rhs,fe=[f'{x}_purpose' for x in FE])
    if len(m.data)!=2*len(common):raise RuntimeError('Unexpected separation after fixed-point common support; investigate instead of reporting unmatched contrast.')
    meta=export_model(m,outdir,'outcome',conditional=False)
    names=m.fit.coef().index.tolist();a=np.zeros(len(names));a[names.index('interaction_p0')]=1;a[names.index('interaction_p1')]=-1
    result={'contrast':f'{left} minus {right}','common_cells':len(common),'stacked_rows':len(stack),'recipients':common.recipient.nunique(),'providers':common.provider.nunique(),**normal_contrast(m.fit.coef().values,m.fit._vcov,a,common.recipient.nunique())}
    # Check stacked slope estimates against the separate same-support models.
    deviations={}
    for k,p in enumerate([left,right]):
        for v in VARS:deviations[f'{p}:{v}']=float(m.fit.coef()[f'{v}_p{k}']-fits[p].fit.coef()[v])
    result['max_stacked_vs_separate_difference']=max(abs(v) for v in deviations.values())
    if result['max_stacked_vs_separate_difference']>1e-5:raise RuntimeError(f'Stacked slopes do not agree with separate common-support models: {deviations}')
    cov2=pd.read_csv(Path(outdir)/name/'covariance_twoway_raw.csv',index_col=0).to_numpy()
    if meta['twoway']['psd']:
        tw=normal_contrast(m.fit.coef().values,cov2,a,min(common.recipient.nunique(),common.provider.nunique()))
        result.update({'twoway_psd':True,**{f'twoway_{k}':v for k,v in tw.items() if k in ['se','p_normal','ci95_low','ci95_high']}})
    else: result['twoway_psd']=False
    save_json(Path(outdir)/name/'common_support.json',{'history':history,'contrast':result,'stacked_vs_separate_deviations':deviations})
    return result


def run_main(config,panel,outdir):
    outdir=Path(outdir);outdir.mkdir(parents=True,exist_ok=True)
    baseline=panel[panel.year.between(config['primary_start_year'],config['end_year'])].copy()
    summaries=[]
    for name in config['main_outcomes']:
        y=config['outcomes'][name]
        print(f'Fitting {name}, {len(baseline)} input cells',flush=True)
        try:
            model=fit_stable(baseline,y,name)
            meta=export_model(model,outdir,y)
            summaries.append({k:v for k,v in meta.items() if k in ['model','n','positive_n','zero_n','zero_share','total_outcome_usd_millions','recipients','providers','dyads','deviance']})
        except Exception as e:
            save_json(outdir/name/'failure.json',{'model':name,'error':str(e)})
            if name=='adaptation_total':raise
    pd.DataFrame(summaries).to_csv(outdir/'model_summary.csv',index=False)
    contrasts=[]
    for other in ['nonclimate_total','mitigation_total']:
        print(f'Common support adaptation_total vs {other}',flush=True)
        try:contrasts.append(common_support_contrast(baseline,config['outcomes'],'adaptation_total',other,f'contrast_adaptation_vs_{other}',outdir))
        except Exception as e:save_json(outdir/f'contrast_adaptation_vs_{other}'/'failure.json',{'error':str(e)})
    if contrasts:
        valid=[r for r in contrasts if r.get('inference_valid',False)]
        # Family contains both planned contrasts, including unestimable tests as p=1.
        p=[r['p_normal'] for r in valid]+[1.]*(2-len(valid))
        adj=multipletests(p,method='holm')[1]
        for r,a in zip(valid,adj):r['p_holm_planned_total_family']=a
        pd.DataFrame(contrasts).to_csv(outdir/'planned_total_contrasts.csv',index=False)


def run_secondary(config,panel,outdir):
    """Prespecified secondary definitions; never select the main model by results."""
    base=panel[panel.year.between(config['primary_start_year'],config['end_year'])].copy()
    y=config['outcomes']['adaptation_total'];tasks=[]
    tasks.append(('adaptation_post2018',base[base.year>=2019].copy(),y))
    for tag,key in [('exclusive','adaptation_exclusive'),('principal_significant','adaptation_principal_significant')]:
        if key in config['outcomes']:tasks.append((f'adaptation_{tag}',base.copy(),config['outcomes'][key]))
    for alt,col in [('ppg_only','debt_service_ppg_pct_exports_lag'),('debt_stock','debt_stock_total_pct_gni_lag')]:
        if col in base:
            d=base[np.isfinite(base[col])&(base[col]>=0)].copy();d['debt10']=d[col]/10;d['interaction']=d.debt10*d.vuln_z
            tasks.append((f'adaptation_{alt}',d,y))
    ref=pd.read_csv(Path(outdir).parent/'pvcci_standardization_countries.csv').recipient
    for v in ['pvcci2','pvcci3']:
        if v in base:
            reference=base[base.recipient.isin(ref)][['recipient',v]].drop_duplicates()
            assert len(reference)==len(ref) and not reference[v].isna().any()
            mean=reference[v].mean();sd=reference[v].std(ddof=0)
            save_json(Path(outdir).parent/f'{v}_standardization.json',{'mean':mean,'sd_population_ddof0':sd,'n_unique_recipients':len(reference)})
            d=base.copy();d['vuln_z']=(d[v]-mean)/sd;d['interaction']=d.debt10*d.vuln_z
            tasks.append((f'adaptation_{v}',d,y))
    summary=[]
    for name,d,yy in tasks:
        print(f'Secondary {name}',flush=True)
        try:
            m=fit_stable(d,yy,name);meta=export_model(m,outdir,yy)
            row=pd.read_csv(Path(outdir)/name/'coefficients.csv').set_index('term').loc['interaction'].to_dict()
            summary.append({'model':name,'n':meta['n'],'recipients':meta['recipients'],'providers':meta['providers'],**row})
        except Exception as e:save_json(Path(outdir)/name/'failure.json',{'error':str(e)})
    pd.DataFrame(summary).to_csv(Path(outdir)/'secondary_interactions.csv',index=False)
    # Instrument common-support difference remains descriptive when support is thin.
    if 'mitigation_loans' in config['outcomes']:
        try:common_support_contrast(base,config['outcomes'],'adaptation_loans','mitigation_loans','contrast_adaptation_vs_mitigation_loans',outdir)
        except Exception as e:save_json(Path(outdir)/'contrast_adaptation_vs_mitigation_loans'/'failure.json',{'error':str(e)})
    # Leave-one-provider-out diagnostics of adaptation loan association.
    loan_y=config['outcomes']['adaptation_loans']
    providers=base.loc[base[loan_y]>0,'provider'].unique();lopo=[]
    for provider in providers:
        name=f'adaptation_loans_without_provider_{provider}'
        print(f'Provider influence {provider}',flush=True)
        try:
            m=fit_stable(base[base.provider!=provider],loan_y,name);meta=export_model(m,outdir,loan_y)
            row=pd.read_csv(Path(outdir)/name/'coefficients.csv').set_index('term').loc['interaction'].to_dict()
            lopo.append({'excluded_provider':provider,'n':meta['n'],'recipients':meta['recipients'],'providers':meta['providers'],**row})
        except Exception as e:lopo.append({'excluded_provider':provider,'error':str(e)})
    pd.DataFrame(lopo).to_csv(Path(outdir)/'adaptation_loan_provider_influence.csv',index=False)


def run_temporal(config,panel,outdir):
    """Pooled annual slopes and fixed exploratory cutoffs, with correct lower terms."""
    y=config['outcomes']['adaptation_total'];d=panel.copy();years=sorted(d.year.unique())
    rhs=['lngdp','lnpop']
    for year in years:
        indicator=(d.year==year).astype(float)
        for col,source in [('debt_year','debt10'),('interaction_year','interaction')]:
            name=f'{col}_{year}';d[name]=indicator*d[source];rhs.append(name)
        if year!=years[0]:
            name=f'vulnerability_year_{year}';d[name]=indicator*d.vuln_z;rhs.append(name)
    try:
        m=fit_stable(d,y,'adaptation_annual_slopes',rhs=rhs)
        export_model(m,outdir,y,conditional=False)
        names=m.fit.coef().index.tolist();R=np.zeros((len(years)-1,len(names)))
        for j,year in enumerate(years[1:]):
            R[j,names.index(f'interaction_year_{year}')]=1;R[j,names.index(f'interaction_year_{years[0]}')]=-1
        eig=np.linalg.eigvalsh(R@m.fit._vcov@R.T)
        if eig.min()<=0:raise RuntimeError('Annual equality restriction covariance not positive definite.')
        test=m.fit.wald_test(R=R,distribution='chi2')
        save_json(Path(outdir)/'adaptation_annual_slopes'/'annual_slope_equality_test.json',{'null':'all annual debt-vulnerability interaction slopes equal','chi2':float(test['statistic']),'df':len(years)-1,'pvalue':float(test['pvalue']),'interpretation':'exploratory pooled temporal heterogeneity; no policy-break identification'})
    except Exception as e:save_json(Path(outdir)/'adaptation_annual_slopes'/'failure.json',{'error':str(e)})
    rows=[]
    for cutoff in [2012,2015,2018,2019,2020]:
        dd=panel.copy();post=(dd.year>=cutoff).astype(float)
        dd['debt_post']=dd.debt10*post;dd['vulnerability_post']=dd.vuln_z*post;dd['interaction_post']=dd.interaction*post
        name=f'adaptation_cutoff_{cutoff}'
        print(f'Exploratory cutoff {cutoff}',flush=True)
        try:
            m=fit_stable(dd,y,name,rhs=VARS+['debt_post','vulnerability_post','interaction_post'])
            meta=export_model(m,outdir,y,conditional=False)
            row=pd.read_csv(Path(outdir)/name/'coefficients.csv').set_index('term').loc['interaction_post'].to_dict()
            rows.append({'cutoff':cutoff,'n':meta['n'],**row})
        except Exception as e:save_json(Path(outdir)/name/'failure.json',{'error':str(e)})
    if rows:
        p=[r['p_normal'] for r in rows]+[1.]*(5-len(rows));adj=multipletests(p,method='holm')[1]
        for r,a in zip(rows,adj):r['p_holm_cutoff_family']=a
        pd.DataFrame(rows).to_csv(Path(outdir)/'exploratory_cutoffs.csv',index=False)


def main():
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare','main','secondary','temporal']);p.add_argument('--lock',default=str(ROOT/'design_lock.yaml'));p.add_argument('--output',default=str(ROOT/'outputs'));a=p.parse_args()
    cfg=load_lock(a.lock);out=Path(a.output)
    if a.stage=='prepare':prepare(cfg,out)
    elif a.stage=='main':run_main(cfg,pd.read_parquet(out/'analysis_panel.parquet'),out/'models')
    elif a.stage=='secondary':run_secondary(cfg,pd.read_parquet(out/'analysis_panel.parquet'),out/'models')
    else:run_temporal(cfg,pd.read_parquet(out/'analysis_panel.parquet'),out/'models')
    save_json(out/'run_inputs.json',{'design_lock_sha256':file_sha(a.lock),'script_sha256':file_sha(__file__),'inputs':cfg['inputs'],'runtime_python':sys.version,'runtime_platform':platform.platform(),'package_versions':{x:md.version(x) for x in ['pyfixest','numpy','pandas','scipy','statsmodels']}})

if __name__=='__main__':main()
