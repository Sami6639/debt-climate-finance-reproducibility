# Climate vulnerability and adaptation finance under debt-service pressure

Reproducibility materials for **Climate Vulnerability Conditions the Allocation of Adaptation Finance under Debt-Service Pressure**.

## Strengthened manuscript analyses — 9 October 2026

[Download the computational supplement](supplements/Climate_Vulnerability_Computational_Supplement.zip?raw=true) or [read its contents and reproduction instructions](supplements/README.md).

The supplement adds the two revision rounds, including all 108 recipient omissions, quadratic moderation, bilateral-sector fixed effects, and the outputs supporting Tables 5–6, Appendix A and Figure 5. The primary source data and estimates below are preserved. The additional checks are explicitly exploratory; their uncertainty and support losses are retained.

## Original reconstruction and primary analyses

Debt-service pressure and physical climate vulnerability
Reproducibility companion, public-data reconstruction dated 7 October 2026

What this is

This is a new reconstruction from documented official-source vintages. The original manuscript's estimation code and analytic dataset were not available, and its coefficients or observation counts were not treated as targets. The compact package includes source-faithful input cells and covariates, the clean analytical panel, original Python code, pinned environment, aggregate coefficients/covariances and diagnostics, four table data exports, up to four Matplotlib figures, tests and an executable review notebook.

The full 1.18 GB raw CRS source, virtual environment, caches, copyrighted articles, repeated fitted-row files and private working notes are excluded. Re-running the models regenerates fitted-row and exact structural-pruning audit files. Compact diagnostics preserve counts rather than bulky removed-cell ID arrays. Data attribution and source reuse terms are in SOURCE_AND_LICENSES.md.

Actual tested runtime

CPython 3.12.14 on Linux, installed into a virtual environment with uv; PyFixest 0.60.0. Exact packages are pinned in analysis/requirements.lock.txt. Statistical outputs were not generated with Conda. analysis/environment.yml is a recreation recipe, not a tested Conda execution or a guarantee of byte-for-byte cross-platform equality. Runtime details are in analysis/runtime_manifest.json.

Quick start from this package's root

python -m venv analysis/.venv
analysis/.venv/bin/python -m pip install -r analysis/requirements.lock.txt
analysis/.venv/bin/python analysis/verify_bundle.py
analysis/.venv/bin/python -m pytest analysis/test_pipeline.py -q
analysis/.venv/bin/python analysis/render_results.py

Use Python 3.12.14 for the closest match to the tested runtime. Windows users need the corresponding Scripts/python executable paths. These platforms and Conda have not been tested. The shipped aggregate outputs and analytical data can be inspected without rerunning estimation.

Recompute the models

Set OMP_NUM_THREADS=2, OPENBLAS_NUM_THREADS=2 and RAYON_NUM_THREADS=2 to bound CPU parallelism. Set MPLCONFIGDIR and XDG_CACHE_HOME to writable directories if required by the host.

analysis/.venv/bin/python analysis/ppml_pipeline.py prepare
analysis/.venv/bin/python analysis/ppml_pipeline.py main
analysis/.venv/bin/python analysis/ppml_pipeline.py secondary
analysis/.venv/bin/python analysis/run_universe_sensitivities.py
analysis/.venv/bin/python analysis/ppml_pipeline.py temporal
analysis/.venv/bin/python analysis/run_postbaseline_diagnostics.py
analysis/.venv/bin/python analysis/render_results.py

Run verify_bundle.py on the untouched extracted package before tests or analyses; those commands legitimately regenerate outputs and can change their file hashes through harmless floating-point differences. All source input hashes are checked against analysis/design_lock.yaml. Paths are relative to the package root. The main baseline is 2015–2024; the historical extension is 2011–2024. PPML models use provider–recipient, provider–year and three-digit sector fixed effects. Logged lagged real GDP per capita and population are controls. Debt is lagged PPG-plus-IMF debt service as a percentage of exports of goods, services and primary income, divided by ten. PVCCI uses a frozen unweighted unique-country reference with population SD. The static vulnerability level is absorbed.

The primary recipient-cluster CRV1 covariance and normal-reference confidence intervals were selected before substantive fitting. The t reference is a labeled sensitivity. Two-way covariance is diagnostic: raw non-PSD matrices are preserved without eigenvalue clipping, and their inference is suppressed. Common-support tests stack both outcomes with purpose-specific slopes and fixed effects and use joint covariance; Holm adjustment covers the two planned total-purpose comparisons.

The initial MAP demeaning attempt failed and was rejected. The successful implementation uses PyFixest's sparse LSMR backend, exact structural singleton/all-zero-FE pruning, and then full package FE and iterated-rectifier separation checks. No result is accepted merely because an unconverged solver returns numbers. Numerical tolerances are documented in analysis/NUMERICAL_NOTES.md. The package does not expose the final IRLS iteration count; convergence flags, score checks and independent covariance verification are reported instead.

Post-baseline diagnostics

The fixed 2014 income moderator and all 29 retained-provider total-adaptation omissions were added after baseline results at 08:51 UTC on 7 October 2026. A single common-slope model adding vulnerability-by-year terms was added at 09:00 UTC. They address income-related slope differences, provider concentration and changing vulnerability-related allocation gradients. Their timing is explicit, every result is retained, and no alternative definitions were selected by significance. They do not replace the locked baseline.

Rebuild public-source inputs

The delivered processed source files preserve the exact hashed vintage, so rerunning analysis does not require live API calls. Acquisition scripts are provided under data/oecd/code and data/covariates/scripts. The full CRS download URL is mutable; acquire_full.py refuses bytes that differ from the locked v20260803 hash. A future public update may make that vintage unavailable from the live URL. Do not label a new vintage as an exact reproduction.

For a full rebuild, use an isolated copy of this package and preserve the bundled originals: acquire_full.py, prepare_metadata.py and build_panel.py rebuild CRS cells from the raw snapshot and included codebooks; download_covariates.py and prepare_covariates.py rebuild macroeconomic and vulnerability files. World Bank live series can be revised; matching hashes are required for the locked analysis. The source manifests record official URLs, retrieval dates and hashes. Download scripts make read-only public-source requests and do not send messages or publish anything.

Review notebook

analysis/reconstruction_review.ipynb reads saved outputs. Its cells were executed top-to-bottom with in-process IPython because the network-isolated runtime could not start a socket-based Jupyter kernel. Real cell outputs are saved. A normal Jupyter kernel launch on a separate machine has not been tested; select the pinned environment when rerunning. It is a review companion; the .py scripts above perform the full estimations. Exact manuscript map: Table 1 uses table4_sample_flow.csv plus the descriptive recipient-year and country CSVs; Table 2 uses table1_main_models.csv; Table 3 uses table2_planned_common_support_contrasts.csv; Table 4 uses table3_prespecified_sensitivities.csv. Figure 1 is figure2_reporting_coverage; Figure 2 is figure1_conditional_debt_association; Figure 3 is figure3_loan_provider_concentration; Figure 4 is figure4_annual_interactions. All figure files are under analysis/outputs/paper in PNG and PDF formats.

Validation and scope

The synthetic tests cover coefficient and unadjusted recipient-covariance agreement against a separate statsmodels Poisson fit with a full-rank dummy basis, known separation, exact calendar lags, fixed country standardization, joint covariance contrasts, stacked-model equivalence and non-PSD handling. Source keys, aggregation and empirical cluster sandwiches were also independently recomputed. Floating-point differences within numerical tolerances can occur across machines; bitwise equality is not promised. See VALIDATION.md for measured discrepancies and the final checked scope.

These estimates describe conditional associations within a reporting-conditioned observed allocation universe. They do not identify causal compensation, donor intent, a policy break, concessionality, disbursements or realized resilience outcomes. Principal markers can overlap, and positive interactions alone do not establish uniformly negative debt slopes. The full uncertainty and support limits remain part of the result.

Source acquisition manifests describe the original download snapshots. Delivery metadata removes transient HTTP cookies and machine-specific paths; the source data bytes and their locked SHA-256 values are unchanged. bundle_manifest.sha256.json describes the files actually delivered.

Git checkout byte preservation

The package-root .gitattributes contains exactly * -text followed by a newline. This disables Git text conversion so future GitHub Desktop checkouts preserve stored file bytes used by the manifest. It does not promise identical numerical results across operating systems or software environments.
