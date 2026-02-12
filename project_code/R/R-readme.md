# R Analysis

## analysis_cogsci2026.Rmd

Main analysis file that produces all paper figures, tables, and statistics. 

## utils.R

Shared plotting utilities: ggplot2 theme (Helvetica Neue), color palette, scatter plot helpers.

## overcooked_design/

Scripts for preprocessing behavioral data and fitting Bayesian regression models on the Stanford Sherlock HPC cluster.

### preprocess_for_brms.R
Preprocesses raw behavioral and model CSVs into analysis-ready RDS files for BRMS fitting. 

Usage:
```
Rscript preprocess_for_brms.R --data-dir /path/to/data --output-dir /path/to/output
```

### fit_brms_model.R
Fits a single BRMS Bayesian regression model. Designed for SLURM array execution where each array task fits one model. Uses the Poisson trick for multinomial choice modeling (`y ~ 0 + U + (1 | choice_occasion)`). Computes LOO-CV with lapse mixture after fitting.

Model IDs (9 total):
- `base_full`, `base_oracle`, `base_inference_ablation`, `base_efficiency_ablation`
- `comm_full`, `comm_oracle`, `comm_inference_ablation`, `comm_efficiency_ablation`
- `baseline` (uniform)

Usage:
```
Rscript fit_brms_model.R --model-id base_full --data-dir /path/to/data --output-dir /path/to/output
```

Output: `brms_fit_*.rds`, `loo_*.rds`

### loo_helpers.R
Helper functions for computing LOO-CV with lapse mixture for multinomial choice models. Converts Poisson-trick linear predictors to proper softmax log-likelihoods. Sourced by `fit_brms_model.R`.

### Cluster Reproduction

The BRMS fitting pipeline is orchestrated by `bash/overcooked_design/submit_brms.sh`:

```
preprocess_for_brms.R → df.long.rds
    → submit_brms.sh (submits SLURM array job for 10 models)
    → fit_brms_model.R (per model, 64 CPUs each) → brms_fit_*.rds + loo_*.rds
```
