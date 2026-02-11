# R Analysis

## analysis_cogsci2026.Rmd

Main analysis file that produces all paper figures, tables, and statistics. Requires pre-computed data files at relative paths (`../../data/`, `../../stimuli/`).

**Outputs:**
- Figure 2: Study 1 model-human scatter plots with sample trial layouts
- Figure 3: Study 2 permutation test results (discriminability)
- Table 1: Study 2 model comparison (LOO cross-validation)
- Inline statistics exported as LaTeX macros

**Dependencies:** tidyverse, brms, loo, patchwork, ggridges, Hmisc

## utils.R

Shared plotting utilities: ggplot2 theme (Helvetica Neue), color palette, scatter plot helpers.
