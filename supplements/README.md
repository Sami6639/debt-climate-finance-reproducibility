# Computational supplement for the strengthened manuscript

Manuscript: **Climate Vulnerability Conditions the Allocation of Adaptation Finance under Debt-Service Pressure**.

[Download the complete computational supplement](Climate_Vulnerability_Computational_Supplement.zip?raw=true) · [SHA-256 checksum](Climate_Vulnerability_Computational_Supplement.zip.sha256)

The archive contains the additional analysis scripts, pinned environment, coefficients, covariance matrices, convergence records, literature comparison, and Figure 5. Its internal `ARCHIVE_SHA256.json` verifies individual file bytes. Original primary models, source data and estimation code remain in the repository root, `analysis/` and `data/`.

## Reproduce the additional analyses

Use the tested Python 3.12.14 environment described in the root README. From the repository root, extract the archive so that `revision_analysis/` sits beside `analysis/`:

```bash
python -m zipfile -e supplements/Climate_Vulnerability_Computational_Supplement.zip .
python revision_analysis/run_revision.py
python revision_analysis/descriptive_checks.py
python revision_analysis/independent_covariance_check.py
python revision_analysis/run_round2.py omissions --workers 8
python revision_analysis/run_round2.py models
python revision_analysis/run_round2.py scale
python revision_analysis/plot_round2.py
```

The extracted `revision_analysis/README.md` provides the complete manuscript-to-output map and execution notes. Cached recipient-omission results are reused; deleting selected per-country checkpoints deliberately forces those fits to rerun. Large fitted-row files are regenerated rather than bundled.

## Coverage and interpretation

The first revision adds additive recipient-plus-provider inference, external-resource controls, sector–year effects, common-period support and sample-selection diagnostics. The second adds all 108 recipient omissions, one quadratic moderation term, provider–recipient–sector fixed effects, and an observed annual debt-change scale. Table 5, Table 6, Appendix A and Figure 5 are mapped to the archived outputs.

The main positive interaction survives the targeted checks, including all recipient omissions. Quadratic moderation is positive near mean vulnerability but its upper-support shape remains uncertain. The finer fixed effects substantially reduce retained support. These are exploratory checks of conditional allocation associations; they do not identify causality or delivered adaptation outcomes.

The public repository contains reproducibility materials. The manuscript Word file is not included. Source acknowledgments and data reuse terms remain in `SOURCE_AND_LICENSES.md` and the archive.
