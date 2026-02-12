#!/usr/bin/env Rscript
# fit_brms_model.R
#
# Fits a single BRMS model based on command-line arguments.
# Designed for Sherlock cluster execution with optimized parallelization.
#
# Model IDs:
#   Main models (8): base_full, base_oracle, base_inference_ablation, base_efficiency_ablation,
#                    comm_full, comm_oracle, comm_inference_ablation, comm_efficiency_ablation
#   Baseline (1):    baseline
#   H4 model (1):    h4
#
# Usage:
#   Rscript fit_brms_model.R \
#     --model-id base_full \
#     --data-dir /path/to/model_cache \
#     --output-dir /path/to/output \
#     --chains 16 \
#     --iter 4000 \
#     --threads-per-chain 2

suppressPackageStartupMessages({
  library(dplyr)
  library(brms)
  library(loo)
  library(argparse)
})

# Source LOO helpers (get script directory robustly for Rscript execution)
get_script_dir <- function() {
  args <- commandArgs(trailingOnly = FALSE)
  file_arg <- grep("^--file=", args, value = TRUE)
  if (length(file_arg) > 0) {
    return(dirname(normalizePath(sub("^--file=", "", file_arg))))
  }
  return(getwd())
}
script_dir <- get_script_dir()
source(file.path(script_dir, "loo_helpers.R"))

# =============================================================================
# ARGUMENT PARSING
# =============================================================================
parser <- ArgumentParser(description = "Fit a single BRMS model for Overcooked Design analysis")
parser$add_argument("--model-id", type = "character", required = TRUE,
                    help = "Model ID (e.g., base_full, comm_oracle, baseline, h4)")
parser$add_argument("--data-dir", type = "character", required = TRUE,
                    help = "Directory containing preprocessed RDS files")
parser$add_argument("--output-dir", type = "character", required = TRUE,
                    help = "Directory for output model files")
parser$add_argument("--chains", type = "integer", default = 16,
                    help = "Number of MCMC chains (default: 16)")
parser$add_argument("--iter", type = "integer", default = 4000,
                    help = "Total iterations per chain (default: 4000)")
parser$add_argument("--warmup", type = "integer", default = NULL,
                    help = "Warmup iterations (default: iter/2)")
parser$add_argument("--threads-per-chain", type = "integer", default = 2,
                    help = "Threads per chain for within-chain parallelism (default: 2)")
parser$add_argument("--seed", type = "integer", default = 42,
                    help = "Random seed (default: 42)")
args <- parser$parse_args()

MODEL_ID <- args$model_id
DATA_DIR <- args$data_dir
OUTPUT_DIR <- args$output_dir
N_CHAINS <- args$chains
N_ITER <- args$iter
N_WARMUP <- if (is.null(args$warmup)) N_ITER / 2 else args$warmup
THREADS_PER_CHAIN <- args$threads_per_chain
SEED <- args$seed

# Create output directory if needed
if (!dir.exists(OUTPUT_DIR)) {
  dir.create(OUTPUT_DIR, recursive = TRUE)
}

cat("\n")
cat(paste(rep("=", 80), collapse = ""), "\n")
cat(sprintf("FITTING MODEL: %s\n", MODEL_ID))
cat(paste(rep("=", 80), collapse = ""), "\n\n")

cat(sprintf("Configuration:\n"))
cat(sprintf("  Chains: %d\n", N_CHAINS))
cat(sprintf("  Iterations: %d (warmup: %d)\n", N_ITER, N_WARMUP))
cat(sprintf("  Threads per chain: %d\n", THREADS_PER_CHAIN))
cat(sprintf("  Total cores: %d\n", N_CHAINS * THREADS_PER_CHAIN))
cat(sprintf("  Seed: %d\n", SEED))
cat(sprintf("  Data dir: %s\n", DATA_DIR))
cat(sprintf("  Output dir: %s\n", OUTPUT_DIR))
cat("\n")

# Set BRMS backend options
options(mc.cores = N_CHAINS)
options(brms.backend = "cmdstanr")

# =============================================================================
# PARSE MODEL ID
# =============================================================================
# Model ID formats:
#   base_{model}  -> condition = "base", model = {model}
#   comm_{model}  -> condition = "communicative", model = {model}
#   baseline      -> uniform baseline (base condition only)
#   h4            -> H4 placement_id model

if (MODEL_ID == "baseline") {
  model_type <- "baseline"
  condition <- "base"
  model_name <- NULL
} else if (MODEL_ID == "h4") {
  model_type <- "h4"
  condition <- NULL
  model_name <- NULL
} else if (grepl("^base_", MODEL_ID)) {
  model_type <- "main"
  condition <- "base"
  model_name <- sub("^base_", "", MODEL_ID)
} else if (grepl("^comm_", MODEL_ID)) {
  model_type <- "main"
  condition <- "communicative"
  model_name <- sub("^comm_", "", MODEL_ID)
} else {
  stop(sprintf("Unknown model ID: %s", MODEL_ID))
}

cat(sprintf("Model type: %s\n", model_type))
if (!is.null(condition)) cat(sprintf("Condition: %s\n", condition))
if (!is.null(model_name)) cat(sprintf("Model name: %s\n", model_name))
cat("\n")

# =============================================================================
# LOAD DATA
# =============================================================================
cat("Loading data...\n")

if (model_type %in% c("main", "baseline")) {
  df.long <- readRDS(file.path(DATA_DIR, "df.long.rds"))
  cat(sprintf("  Loaded df.long.rds: %d rows\n", nrow(df.long)))
} else if (model_type == "h4") {
  df.h4 <- readRDS(file.path(DATA_DIR, "df.h4.rds"))
  cat(sprintf("  Loaded df.h4.rds: %d rows\n", nrow(df.h4)))
}

# =============================================================================
# FIT MODEL
# =============================================================================
cat("\nFitting model...\n")
start_time <- Sys.time()

if (model_type == "main") {
  # Main Poisson-trick models: y ~ 0 + U + (1 | choice_occasion)
  data_subset <- df.long %>%
    filter(condition == !!condition) %>%
    mutate(U = !!sym(paste0("U_", model_name)))

  cat(sprintf("  Formula: y ~ 0 + U + (1 | choice_occasion)\n"))
  cat(sprintf("  Data: %d rows (%d choice occasions x 12 placements)\n",
              nrow(data_subset), nrow(data_subset) / 12))

  fit <- brm(
    y ~ 0 + U + (1 | choice_occasion),
    family = poisson(),
    prior = prior(normal(1, 1), class = "b", coef = "U"),
    data = data_subset,
    chains = N_CHAINS,
    iter = N_ITER,
    warmup = N_WARMUP,
    cores = N_CHAINS,
    threads = threading(THREADS_PER_CHAIN),
    seed = SEED,
    refresh = 100,
    backend = "cmdstanr"
  )

  fit_file <- sprintf("brms_fit_%s_%s.rds", condition, model_name)

} else if (model_type == "baseline") {
  # Uniform baseline: y ~ 0 + (1 | choice_occasion)
  data_subset <- df.long %>% filter(condition == "base")

  cat(sprintf("  Formula: y ~ 0 + (1 | choice_occasion)\n"))
  cat(sprintf("  Data: %d rows (%d choice occasions x 12 placements)\n",
              nrow(data_subset), nrow(data_subset) / 12))

  fit <- brm(
    y ~ 0 + (1 | choice_occasion),
    family = poisson(),
    data = data_subset,
    chains = N_CHAINS,
    iter = N_ITER,
    warmup = N_WARMUP,
    cores = N_CHAINS,
    threads = threading(THREADS_PER_CHAIN),
    seed = SEED,
    refresh = 100,
    backend = "cmdstanr"
  )

  fit_file <- "brms_fit_baseline.rds"

} else if (model_type == "h4") {
  # H4 placement_id model: placement_id ~ dish_model + condition + (1|participant_id) + (1|kitchen_layout)
  # Convert placement_id to factor for categorical family
  data_subset <- df.h4 %>%
    mutate(placement_id = factor(placement_id, levels = 0:11))
  
  formula_str <- "placement_id ~ dish_model + condition + (1 | participant_id) + (1 | kitchen_layout)"

  cat(sprintf("  Formula: %s\n", formula_str))
  cat(sprintf("  Data: %d rows\n", nrow(data_subset)))

  fit <- brm(
    formula = as.formula(formula_str),
    data = data_subset,
    family = categorical(),
    chains = N_CHAINS,
    iter = N_ITER,
    warmup = N_WARMUP,
    cores = N_CHAINS,
    threads = threading(THREADS_PER_CHAIN),
    seed = SEED,
    refresh = 100,
    backend = "cmdstanr"
  )

  fit_file <- "brms_fit_h4.rds"
}

end_time <- Sys.time()
fit_duration <- difftime(end_time, start_time, units = "mins")
cat(sprintf("\nModel fitting completed in %.1f minutes\n", as.numeric(fit_duration)))

# =============================================================================
# SAVE FIT
# =============================================================================
fit_path <- file.path(OUTPUT_DIR, fit_file)
saveRDS(fit, fit_path)
cat(sprintf("Saved fit: %s\n", fit_file))

# =============================================================================
# COMPUTE LOO (for Poisson models only)
# =============================================================================
if (model_type %in% c("main", "baseline")) {
  cat("\nComputing LOO with lapse mixture...\n")
  loo_start <- Sys.time()

  log_lik_lapse <- compute_loglik_with_lapse(
    fit,
    data_subset,
    epsilon = 0.01,
    K = 12
  )

  loo_result <- loo(log_lik_lapse)

  loo_end <- Sys.time()
  loo_duration <- difftime(loo_end, loo_start, units = "mins")
  cat(sprintf("LOO computation completed in %.1f minutes\n", as.numeric(loo_duration)))

  # Check Pareto k diagnostics
  n_bad_k <- sum(loo_result$diagnostics$pareto_k > 0.7)
  if (n_bad_k > 0) {
    cat(sprintf("WARNING: %d observations with Pareto k > 0.7\n", n_bad_k))
  }

  cat(sprintf("ELPD: %.2f (SE: %.2f)\n",
              loo_result$estimates["elpd_loo", "Estimate"],
              loo_result$estimates["elpd_loo", "SE"]))

  # Save LOO
  if (model_type == "main") {
    loo_file <- sprintf("loo_%s_%s.rds", condition, model_name)
  } else {
    loo_file <- "loo_baseline.rds"
  }
  loo_path <- file.path(OUTPUT_DIR, loo_file)
  saveRDS(loo_result, loo_path)
  cat(sprintf("Saved LOO: %s\n", loo_file))

  # Clean up
  rm(log_lik_lapse)
  gc()
}

# =============================================================================
# SUMMARY
# =============================================================================
cat("\n")
cat(paste(rep("=", 80), collapse = ""), "\n")
cat("COMPLETE\n")
cat(paste(rep("=", 80), collapse = ""), "\n")
cat(sprintf("Model: %s\n", MODEL_ID))
cat(sprintf("Fit saved to: %s\n", fit_path))
if (model_type %in% c("main", "baseline")) {
  cat(sprintf("LOO saved to: %s\n", loo_path))
}

# Print beta estimate for main models
if (model_type == "main") {
  beta_est <- fixef(fit)["U", "Estimate"]
  cat(sprintf("\nBeta estimate (U): %.4f\n", beta_est))
}

# Print convergence summary
cat("\nConvergence summary:\n")
summary_fit <- summary(fit)
if ("fixed" %in% names(summary_fit)) {
  rhat_vals <- summary_fit$fixed$Rhat
  if (!is.null(rhat_vals)) {
    cat(sprintf("  Max Rhat (fixed effects): %.4f\n", max(rhat_vals, na.rm = TRUE)))
    if (any(rhat_vals > 1.01, na.rm = TRUE)) {
      cat("  WARNING: Some Rhat > 1.01 - consider more iterations\n")
    } else {
      cat("  All Rhat < 1.01 (good convergence)\n")
    }
  }
}

cat("\nDone.\n")
