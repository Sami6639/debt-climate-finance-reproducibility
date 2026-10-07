"""Synthetic numerical and workflow verification, never empirical manuscript evidence."""
import os
os.environ.setdefault('MPLCONFIGDIR','/tmp/debt_mpl')
import json
from pathlib import Path
import numpy as np,pandas as pd,pyfixest as pf,statsmodels.api as sm
from scipy.linalg import qr
from ppml_pipeline import fit_stable,export_model,common_support_contrast,normal_contrast,prepare,load_lock
ROOT=Path(__file__).resolve().parent

def synthetic():
    d=pd.read_csv(ROOT/'synthetic_probe.csv')
    d['pvcci']=50+10*d.vuln_z
    rng=np.random.default_rng(28395)
    d['y2']=rng.poisson(np.exp(1.1-.05*d.debt10+.02*d.interaction+.1*d.lngdp+.07*d.lnpop))
    return d

def test_pyfixest_vs_statsmodels():
    d=synthetic();m=fit_stable(d,'y','synthetic_test');f=m.fit;d=m.data
    dummy=pd.get_dummies(d[['dyad','provider_year','sector']].astype(str),dtype=float).to_numpy()
    q,r,pivot=qr(dummy,mode='economic',pivoting=True)
    rank=int((np.abs(np.diag(r))>1e-9).sum())
    x=np.column_stack([d[f.coef().index].to_numpy(),dummy[:,pivot[:rank]]])
    assert np.linalg.matrix_rank(x)==x.shape[1]
    ref=sm.GLM(d.y.to_numpy(),x,family=sm.families.Poisson()).fit(maxiter=300,tol=1e-11,cov_type='cluster',cov_kwds={'groups':d.recipient,'use_correction':False})
    coefgap=max(abs(f.coef().to_numpy()-ref.params[:4]))
    f._ssc_dict=pf.ssc(k_adj=False,k_fixef='none',G_adj=False,G_df='conventional');f.vcov({'CRV1':'recipient'})
    covgap=float(np.max(np.abs(f._vcov-ref.cov_params()[:4,:4])))
    assert coefgap<1e-7
    assert covgap<1e-7
    assert len(d)==465 and m.pruning[0]['separation_removed_n']==15
    (ROOT/'synthetic_verification.json').write_text(json.dumps({'synthetic_only':True,'statsmodels_version':'0.15.0','max_absolute_coefficient_difference':coefgap,'max_absolute_unadjusted_recipient_covariance_difference':covgap,'input_n':480,'retained_n':465,'known_all_zero_dyad_removed_n':15},indent=2))

def test_export_and_nonpsd():
    d=synthetic();m=fit_stable(d,'y','synthetic_export')
    meta=export_model(m,ROOT/'test_outputs','y')
    assert meta['n']==465
    assert meta['twoway']['psd'] is False
    assert not (ROOT/'test_outputs'/'synthetic_export'/'coefficients_twoway_diagnostic.csv').exists()
    r=pd.read_csv(ROOT/'test_outputs'/'synthetic_export'/'conditional_debt_effect.csv')
    assert np.isfinite(r.se).all()
    assert (r.ci95_low<r.ci95_high).all()

def test_stacked_common_support():
    d=synthetic()
    result=common_support_contrast(d,{'a':'y','b':'y2'},'a','b','synthetic_contrast',ROOT/'test_outputs')
    assert result['common_cells']==465
    assert result['stacked_rows']==930
    assert result['max_stacked_vs_separate_difference']<1e-6

def test_joint_covariance_contrast():
    b=np.array([.1,.2]);v=np.array([[.01,-.002],[-.002,.003]])
    r=normal_contrast(b,v,[1,2],20)
    assert np.isclose(r['estimate'],.5)
    assert np.isclose(r['variance'],.01+4*.003-4*.002)

def test_unlocked_source_gate(tmp_path):
    import pytest
    pending=tmp_path/'pending.yaml';pending.write_text('status: pending\n')
    with pytest.raises(RuntimeError):load_lock(pending)


def test_exact_calendar_lag_and_frozen_country_scaling(tmp_path):
    cells=pd.DataFrame({'provider':[1]*5,'recipient':['AAA','AAA','BBB','BBB','AAA'],'year':[2014,2014,2014,2014,2015],'sector':[111,112,111,112,111],'adaptation_total':[0.,1.,2.,0.,4.]})
    cov=pd.DataFrame({'recipient':['AAA','AAA','BBB'],'year':[2013,2015,2013],'debt_ratio':[10.,30.,20.],'gdppc':[100.,110.,200.],'population':[10.,11.,20.]})
    pv=pd.DataFrame({'recipient':['AAA','BBB'],'pvcci':[40.,60.]})
    for name,d in [('cells',cells),('covariates',cov),('vulnerability',pv)]:d.to_csv(tmp_path/f'{name}.csv',index=False)
    config={'inputs':{name:{'path':str(tmp_path/f'{name}.csv')} for name in ['cells','covariates','vulnerability']},'column_maps':{},'outcomes':{'adaptation_total':'adaptation_total'},'start_year':2014,'primary_start_year':2014,'end_year':2015}
    result=prepare(config,tmp_path/'out')
    assert len(result)==4
    assert result[result.recipient=='AAA'].debt10.eq(1).all()
    assert set(result.vuln_z)=={-1.,1.}
    assert (result.adaptation_total==0).sum()==2
