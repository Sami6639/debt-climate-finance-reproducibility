"""At most four manuscript table exports and four static Matplotlib figures."""
import os
os.environ.setdefault('MPLCONFIGDIR','/tmp/debt_mpl')
from pathlib import Path
import json
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'outputs';MODELS=OUT/'models';PAPER=OUT/'paper';PAPER.mkdir(exist_ok=True)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.titleweight':'bold','savefig.dpi':220,'axes.labelsize':10,'figure.facecolor':'white'})
BLUE='#176895';RED='#9b3c40';GRAY='#68747d'
labels={'adaptation_total':'Adaptation: total','mitigation_total':'Mitigation: total','nonclimate_total':'Non-climate: total','adaptation_grants':'Adaptation: grants','adaptation_loans':'Adaptation: loans','mitigation_grants':'Mitigation: grants','mitigation_loans':'Mitigation: loans'}
rows=[]
for name,label in labels.items():
    folder=MODELS/name
    if not (folder/'coefficients.csv').exists():continue
    c=pd.read_csv(folder/'coefficients.csv').set_index('term');m=json.loads((folder/'diagnostics.json').read_text())
    r={'outcome':label,'beta_debt10':c.loc['debt10','estimate'],'se_debt10':c.loc['debt10','se'],'p_debt10':c.loc['debt10','p_normal'],'beta_interaction':c.loc['interaction','estimate'],'se_interaction':c.loc['interaction','se'],'p_interaction':c.loc['interaction','p_normal'],'n':m['n'],'recipients':m['recipients'],'providers':m['providers'],'zero_share':m['zero_share'],'usd2024_billion':m['total_outcome_usd_millions']/1000,'provider_effective_volume_n':m['provider_concentration']['effective_clusters_volume'],'two_way_psd':m['twoway']['psd']}
    rows.append(r)
main=pd.DataFrame(rows);main.to_csv(PAPER/'table1_main_models.csv',index=False)
for source,dest in [('planned_total_contrasts.csv','table2_planned_common_support_contrasts.csv'),('secondary_interactions.csv','table3_prespecified_sensitivities.csv')]:
    if (MODELS/source).exists():
        frame=pd.read_csv(MODELS/source)
        if source=='secondary_interactions.csv' and (MODELS/'universe_sensitivities.csv').exists():frame=pd.concat([frame,pd.read_csv(MODELS/'universe_sensitivities.csv')],ignore_index=True)
        frame.to_csv(PAPER/dest,index=False)
panel=pd.read_parquet(OUT/'analysis_panel.parquet');base=panel[panel.year>=2015]
flow=pd.read_csv(OUT/'sample_construction.csv')
flow=pd.concat([flow,pd.DataFrame([{'stage':'primary_2015_2024_before_separation','cells':len(base),'recipients':base.recipient.nunique(),'providers':base.provider.nunique(),'years':'2015–2024'}])],ignore_index=True)
flow.to_csv(PAPER/'table4_sample_flow.csv',index=False)
# Figure1: conditional log-mean and exact multiplicative slopes, observed support.
f=MODELS/'adaptation_total'
if (f/'conditional_debt_effect.csv').exists():
    e=pd.read_csv(f/'conditional_debt_effect.csv');support=pd.read_csv(f/'vulnerability_support.csv')
    fig,axes=plt.subplots(1,2,figsize=(10.8,4.2),layout='constrained')
    for ax,est,lo,hi,title,ylab in [(axes[0],'estimate','ci95_low','ci95_high','Log-mean slope','Log-mean change per 10 percentage points'),(axes[1],'percent_change_10pp','percent_ci95_low','percent_ci95_high','Proportional association','Conditional mean change (%)')]:
        ax.fill_between(e.vuln_z,e[lo],e[hi],color=BLUE,alpha=.16,label='95% pointwise recipient-cluster CI')
        ax.plot(e.vuln_z,e[est],color=BLUE,lw=2)
        ax.axhline(0,color=GRAY,lw=.8,ls='--');ax.set(xlabel='Physical vulnerability (baseline country SD)',ylabel=ylab,title=title)
        ax.plot(support.vuln_z,np.full(len(support),.025),marker='|',ls='',color=GRAY,alpha=.35,transform=ax.get_xaxis_transform())
    fig.suptitle('Conditional debt-service associations',fontsize=11)
    axes[0].legend(frameon=False,fontsize=8,loc='best');fig.savefig(PAPER/'figure1_conditional_debt_association.png');fig.savefig(PAPER/'figure1_conditional_debt_association.pdf');plt.close(fig)
# Figure2: reporting coverage before covariate matching and PPML separation.
coverage=pd.read_csv(ROOT.parent/'data/oecd/processed/provider_year_marker_coverage.csv')
coverage=coverage[coverage.provider!=918]
annual=coverage.groupby('year')[['eligible_commitment','classified_commitment','n_observed_cells','n_complete_cells']].sum()
strict=pd.read_parquet(ROOT.parent/'data/oecd/processed/cell_outcomes.parquet').groupby('year').eligible_commitment.sum()
annual['strict_complete_cell_commitment']=strict
annual['joint_valid_record_amount_share']=annual.classified_commitment/annual.eligible_commitment
annual['strict_complete_cell_amount_share']=annual.strict_complete_cell_commitment/annual.eligible_commitment
annual['strict_complete_cell_count_share']=annual.n_complete_cells/annual.n_observed_cells
annual.to_csv(OUT/'reporting_coverage_annual.csv')
fig,ax=plt.subplots(figsize=(9,4.6),layout='constrained')
ax.plot(annual.index,100*annual.joint_valid_record_amount_share,'o-',c=BLUE,label='Joint-marker-valid activities')
ax.plot(annual.index,100*annual.strict_complete_cell_amount_share,'s--',c=RED,label='Strict-complete allocation cells')
ax.set_ylim(0,103);ax.set_xticks(annual.index);ax.tick_params(axis='x',rotation=45)
ax.axvspan(2009.6,2010.4,color=GRAY,alpha=.12);ax.set_xlim(2009.6,2024.4)
ax.axvline(2014.5,c=GRAY,ls=':',lw=1)
ax.set(xlabel='Commitment year (2010 excluded; 2011–2014 historical extension)',ylabel='Share of otherwise-eligible commitment volume (%)',title='Reporting coverage')
ax.legend(frameon=False,loc='lower right');fig.savefig(PAPER/'figure2_reporting_coverage.png');fig.savefig(PAPER/'figure2_reporting_coverage.pdf');plt.close(fig)
# Figure3: adaptation-loan provider concentration, with original OECD country labels.
p=MODELS/'adaptation_loans'/'provider_support.csv'
if p.exists():
    vol=pd.read_csv(p);vol=vol[vol.amount>0].sort_values('amount')
    names=base[['provider','donor_name']].drop_duplicates().set_index('provider').donor_name
    fig,ax=plt.subplots(figsize=(8.8,4.6),layout='constrained');ax.barh(vol.provider.map(names).fillna(vol.provider.astype(str)),100*vol.volume_share,color=BLUE)
    ax.set(xlabel='Share of retained adaptation-loan commitments (%)',title='Provider concentration')
    for i,v in enumerate(vol.volume_share):ax.text(100*v+.3,i,f'{100*v:.1f}%',va='center',fontsize=9)
    ax.set_xlim(0,max(100*vol.volume_share)*1.15)
    fig.savefig(PAPER/'figure3_loan_provider_concentration.png');fig.savefig(PAPER/'figure3_loan_provider_concentration.pdf');plt.close(fig)
# Figure4 only if the optional pooled temporal model converged.
p=MODELS/'adaptation_annual_slopes'/'coefficients.csv'
if p.exists() and not (p.parent/'failure.json').exists():
    a=pd.read_csv(p);a=a[a.term.str.startswith('interaction_year_')].copy();a['year']=a.term.str.rsplit('_',n=1).str[-1].astype(int);a=a.sort_values('year')
    fig,ax=plt.subplots(figsize=(9,4.6),layout='constrained');ax.errorbar(a.year,a.estimate,yerr=1.95996398454*a.se,fmt='o-',color=BLUE,capsize=3)
    ax.axhline(0,c=GRAY,lw=.8,ls='--');ax.set_xticks(a.year);ax.tick_params(axis='x',rotation=45);ax.set(xlabel='Commitment year',ylabel='Annual debt-service × vulnerability slope',title='Annual interaction estimates')
    fig.savefig(PAPER/'figure4_annual_interactions.png');fig.savefig(PAPER/'figure4_annual_interactions.pdf');plt.close(fig)
print('Wrote',sorted(p.name for p in PAPER.iterdir()))
