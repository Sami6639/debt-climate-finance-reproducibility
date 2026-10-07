Analysis protocol and dated amendments

Scope and source lock

The reconstruction uses official OECD CRS full snapshot v20260803, World Bank WDI/IDS indicators and FERDI's October 2018 national PVCCI workbook. The design and sources were locked on 7 October 2026 before the first empirical fit at 08:37 UTC. This is not a coefficient-matching replication of the earlier manuscript.

Primary eligible activities are official-government bilateral ODA (category 10; collaboration codes 1, 3, 7, 8), project interventions C01, standard grants 110 or loans 421, three-digit sectors 100–499, positive reported commitments and finite positive constant-price amounts. Estimated nature code 8 is excluded. Named country/territory recipients are mapped with verified identifiers; regional/unallocated records are excluded. EU Institutions and multilateral/private providers are excluded from the primary scope. Repeated activity keys are not blindly deduplicated; a full-row check found no exact duplicates.

Construct observed provider–recipient–year–sector cells before climate-marker filtering. Retain a primary cell only if every eligible activity has both markers in {0,1,2}. Adaptation and mitigation use their respective principal marker=2, allowing overlap; non-climate requires both markers=0. Significant-only cells remain in the observed universe. Unreported cells are never manufactured as zeros, and loan models are not restricted to positive-loan cells at entry.

Main aid period: 2015–2024. Historical extension: 2011–2024. Debt and macroeconomic controls are lagged by exact calendar year. The primary debt series DT.TDS.DPPF.XP.ZS measures PPG-plus-IMF debt service relative to exports of goods, services and primary income, scaled by 10 percentage points. Controls are log real GDP per capita (NY.GDP.PCAP.KD, constant 2015 US$) and log population. No imputation, interpolation or winsorization is used. PVCCI is standardized across the 109 unique complete-case baseline recipients before outcome separation, using mean 53.46656348693887 and population SD 6.454156228861506. The same scale is reused in every comparison.

Model and inference

PPML includes debt, debt×standardized-PVCCI, both logged controls, provider–recipient fixed effects, provider–year fixed effects and three-digit sector fixed effects. The PVCCI level is absorbed. Primary covariance is recipient CRV1, with k_adj=True, k_fixef='nonnested', G_adj=True and G_df='conventional', and normal-reference intervals. Recipient t inference is sensitivity. Raw two-way recipient/provider covariance and components are diagnostic; non-PSD inference is suppressed, never spectrally repaired or selected because its standard error is smaller.

The two planned total-purpose tests compare adaptation with non-climate and mitigation on iteratively matched finite-identification cell support. Stacking allows purpose-specific slopes and all nuisance fixed effects, retaining original recipient/provider cluster IDs. Holm adjustment covers the two-test family. Conditional debt-service slopes include the debt/interact covariance cross-term and are evaluated over observed recipient vulnerability support.

Prespecified secondary checks include grant/loan decomposition and support/concentration; exclusive principal adaptation; principal-or-significant adaptation; PPG-only service; debt stock/GNI as a distinct financial concept; PVCCI2/PVCCI3 using the same reference countries; 2019–2024 allocation years; valid-record reporting; EU inclusion; a common-support adaptation–mitigation loan contrast; and loan-provider omissions. The pooled historical profile includes annual debt slopes, annual debt×PVCCI slopes and vulnerability×year terms, with a reference vulnerability×year omitted. Fixed cutoffs are 2012, 2015, 2018, 2019 and 2020 with all lower-order estimable terms and Holm correction across five tests. Temporal results are exploratory and identify no policy treatment.

Numerical amendments

The initial MAP demeaning fit failed and was rejected. The algebraically equivalent sparse LSMR backend was then used. An initial iterated-rectifier check failed its iteration limit on the unpruned sample; this result was also rejected. Exact iterative singleton/all-zero-FE preprocessing was added, followed by mandatory full FE and iterated-rectifier checks. No coefficient-dependent trimming or source change was made. The final implementation passed synthetic and empirical independent numerical checks. Details and limitations are in analysis/NUMERICAL_NOTES.md.

Post-baseline diagnostics

At 08:51 UTC, after observing the baseline, a single debt×centered log GDP-per-capita-in-2014 moderator and all 29 retained-provider total-adaptation omissions were added to assess income-related moderation and provider concentration. All 109 reference recipients had 2014 income data. At 09:00 UTC, one final model added vulnerability×year terms with common debt/debt×vulnerability slopes and 2015 as reference, to assess changing vulnerability-related allocation gradients. Every result and failed fit is retained. No alternative moderator years or definitions were searched, and no further specifications were added.

Interpretation boundary

The study estimates conditional associations within a reported, eligible allocation universe. It does not identify donor intent, causal debt compensation, optimal allocation, a Paris effect, concessionality or realized adaptation outcomes. Static PVCCI incorporates information collected after some early aid years; the later-period sensitivity addresses a different sample, not a causal correction.
