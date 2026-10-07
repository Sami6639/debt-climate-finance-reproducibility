Validation scope and numerical results

Status: all 65 accepted empirical model outputs passed independent numerical verification. The two rejected initialization attempts are documented separately and are not evidence or substituted results.

Source and construction checks

An independent pass reconciled the full 6,245,831-row CRS source projection, eligibility selection, activity identifiers, observed cell aggregation, climate-marker definitions, overlap identities and zero handling. Full-row duplicate checks found no exact duplicates. Covariate identities, exact-calendar lags, country joins and the frozen country-level PVCCI reference were checked separately. The primary pre-estimation universe contains 68,945 cells, 109 recipients and 33 providers. Sensitivity cell universes and transformations were independently reconstructed, not merely compared with outputs from the same helper.

Synthetic checks

Six automated tests cover: PPML coefficients and unadjusted recipient covariance against a separate statsmodels Poisson GLM with a full-rank dummy basis; structural separation; PSD-failure handling; matched stacked coefficients; exact-calendar lags and unweighted unique-country standardization; and joint covariance contrast algebra. Under the final backend, coefficient agreement in the synthetic reference is within 1e-7 and covariance agreement within 1e-7 absolute tolerance. The measured reference discrepancies are recorded in analysis/synthetic_verification.json. These synthetic values are validation fixtures, not empirical findings.

Independent empirical checks

The model results were checked by an independent sparse weighted fixed-effect projection and cluster-sandwich construction. Verification covered fitted-mean coefficient recovery; recipient, provider and intersection covariance components; nonnested fixed-effect degrees of freedom and small-sample factors; p-values and intervals; conditional-debt variance cross-terms and exponential transformations; fixed-point matched support; formal contrasts and Holm families; annual restrictions; and every provider omission.

Across the 65 accepted outputs, the maximum coefficient discrepancy recovered from the fitted linear predictor was 2.64e-10. The maximum relative recipient covariance discrepancy was 1.30e-7. All 29 total-adaptation provider omissions were present, converged and independently checked against source exclusions, finite-identification pruning and the frozen covariates. These checks establish numerical consistency of this reconstruction, not causal identification.

Relocated package test

A fresh ZIP extraction into a different directory passed the delivered file manifest and locked-source hashes, all six automated tests, and exact DataFrame reconstruction of the 91,890-row historical-plus-baseline analytical panel. A primary adaptation fit was then rerun from the bundled clean panel. It retained the same 53,565 cell identifiers, with maximum absolute discrepancies of 2.32e-12 for coefficients, 2.90e-10 for recipient covariance and 1.58e-7 for fitted means. This used the existing pinned CPython 3.12.14 Linux environment. A new machine, another operating system, and a fresh Conda environment were not tested. Exact equality of derived file bytes across platforms is not promised.

Presentation and scope

The four Matplotlib figures were visually inspected for complete labels, readable intervals and faithful units. Manuscript table CSVs are generated from model outputs; descriptive macroeconomic variables use unique recipient-year observations, and PVCCI uses unique countries. Sample SDs in descriptive tables are explicitly distinct from the population SD used to standardize PVCCI. The review notebook’s pure-Python cells were executed sequentially using in-process IPython, with real outputs saved. Socket-based Jupyter kernel startup was blocked by the network-isolated runtime; that launch path was not validated. Its output images are the inspected Matplotlib figures; full HTML-page visual inspection was not performed. The notebook does not replace the full estimation scripts.

Unresolved scientific limits

The results remain observational, reporting-conditioned and potentially affected by unobserved recipient-year confounders, provider concentration, measurement and ex-post vulnerability classification. Raw non-PSD two-way covariance diagnostics are retained and their inference is suppressed. Loan support is particularly thin. The annual-equality and multiplicity-adjusted cutoff evidence does not establish temporal reorientation or a discrete policy break. No numerical test resolves these identification boundaries.
