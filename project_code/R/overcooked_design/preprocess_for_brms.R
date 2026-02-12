#!/usr/bin/env Rscript
# preprocess_for_brms.R
#
# Preprocesses raw CSVs into analysis-ready RDS files for BRMS fitting.
# Creates:
#   - df.long.rds: Long format data (12 rows per choice occasion)
#   - df.analysis.rds: Wide format analysis data
#
# Usage:
#   Rscript preprocess_for_brms.R --data-dir /path/to/data --output-dir /path/to/output

suppressPackageStartupMessages({
  library(dplyr)
  library(tidyr)
  library(readr)
  library(purrr)
  library(tibble)
  library(stringr)
  library(jsonlite)
  library(argparse)
})

# =============================================================================
# ARGUMENT PARSING
# =============================================================================
parser <- ArgumentParser(description = "Preprocess data for BRMS model fitting")
parser$add_argument("--data-dir", type = "character", required = TRUE,
                    help = "Directory containing behavioral_results/ and model_results/")
parser$add_argument("--output-dir", type = "character", required = TRUE,
                    help = "Directory for output RDS files")
args <- parser$parse_args()

DATA_DIR <- args$data_dir
OUTPUT_DIR <- args$output_dir

# Create output directory if needed
if (!dir.exists(OUTPUT_DIR)) {
  dir.create(OUTPUT_DIR, recursive = TRUE)
  cat("Created output directory:", OUTPUT_DIR, "\n")
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================
compute_placement_id <- function(x, y, config_filename) {
  # Map (x, y) coordinates to placement_id (0-11).
  # Row-major enumeration in 3x4 grid (5x5 space with 2x3 furniture).
  design_space_left <- 1
  design_space_top <- 1
  n_cols <- 4
  row <- y - design_space_top
  col <- x - design_space_left
  placement_id <- row * n_cols + col
  return(placement_id)
}

create_poisson_format <- function(data, utilities_df) {
  # Convert to long format: one row per (trial, placement_alternative).
  # Each choice occasion (participant x config x dish) -> 12 rows with y in {0,1}
  data_long <- data %>%
    crossing(placement_alternative = 0:11) %>%
    left_join(
      utilities_df %>%
        select(config_id, dish, placement_id,
               U_full, U_oracle, U_inference_ablation, U_efficiency_ablation),
      by = c("config_id" = "config_id",
             "dish_model" = "dish",
             "placement_alternative" = "placement_id")
    ) %>%
    mutate(
      y = as.integer(placement_alternative == placement_id),
      baseline = 1/12,
      choice_occasion = paste(game_id, design_problem, sep = "_")
    ) %>%
    arrange(choice_occasion, placement_alternative)

  return(data_long)
}

# =============================================================================
# LOAD DATA
# =============================================================================
cat("\n=== Loading Data ===\n\n")

df.design <- read_csv(
  file.path(DATA_DIR, "behavioral_results", "design_data.csv"),
  show_col_types = FALSE
)
df.session <- read_csv(
  file.path(DATA_DIR, "behavioral_results", "session_data.csv"),
  show_col_types = FALSE
)
df.model <- read_csv(
  file.path(DATA_DIR, "model_results", "placement_utilities.csv"),
  show_col_types = FALSE
)

cat(sprintf("  Design trials: %d\n", nrow(df.design)))
cat(sprintf("  Participants: %d\n", n_distinct(df.design$game_id)))
cat(sprintf("  Placement utilities: %d (configs x dishes x placements)\n", nrow(df.model)))

# =============================================================================
# PREPROCESS
# =============================================================================
cat("\n=== Preprocessing ===\n\n")

# Extract placement coordinates from JSON and map to placement_id
df.design <- df.design %>%
  mutate(
    placements_parsed = map(placements, fromJSON),
    placement_x = map_dbl(placements_parsed, ~.x$location$x[1]),
    placement_y = map_dbl(placements_parsed, ~.x$location$y[1]),
    placement_id = compute_placement_id(placement_x, placement_y, config_filename)
  )

# Join condition
df.design <- df.design %>%
  left_join(df.session %>% select(game_id, condition), by = "game_id")

# Create analysis dataframe
df.analysis <- df.design %>%
  select(game_id, condition, trial_id, config_filename, dish, placement_id, placement_x, placement_y) %>%
  mutate(
    config_id = str_remove(config_filename, "\\.json$"),
    dish_model = recode(dish, "Salad" = "TomatoSalad", "SaladOL" = "OnionSalad"),
    design_problem = interaction(config_id, dish_model, sep = "_")
  )

cat(sprintf("  Placements mapped to IDs (range: %d-%d)\n",
            min(df.analysis$placement_id), max(df.analysis$placement_id)))
cat(sprintf("  Conditions: %s\n", paste(unique(df.analysis$condition), collapse = ", ")))
cat(sprintf("  Design problems: %d unique\n", n_distinct(df.analysis$design_problem)))

# =============================================================================
# CREATE LONG FORMAT
# =============================================================================
cat("\n=== Creating Long Format ===\n\n")

df.long <- create_poisson_format(df.analysis, df.model)

cat(sprintf("Long-format data created:\n"))
cat(sprintf("  Total rows: %d (= %d choice occasions x 12 placements)\n",
            nrow(df.long), nrow(df.analysis)))
cat(sprintf("  Choice occasions: %d\n", n_distinct(df.long$choice_occasion)))

# =============================================================================
# CREATE H4 DATA
# =============================================================================
cat("\n=== Creating H4 Data ===\n\n")

df.h4 <- df.analysis %>%
  mutate(participant_id = game_id, kitchen_layout = config_id)

cat(sprintf("H4 data created: %d rows\n", nrow(df.h4)))

# =============================================================================
# SAVE
# =============================================================================
cat("\n=== Saving Outputs ===\n\n")

saveRDS(df.long, file.path(OUTPUT_DIR, "df.long.rds"))
cat(sprintf("  Saved: df.long.rds (%d rows)\n", nrow(df.long)))

saveRDS(df.analysis, file.path(OUTPUT_DIR, "df.analysis.rds"))
cat(sprintf("  Saved: df.analysis.rds (%d rows)\n", nrow(df.analysis)))

saveRDS(df.h4, file.path(OUTPUT_DIR, "df.h4.rds"))
cat(sprintf("  Saved: df.h4.rds (%d rows)\n", nrow(df.h4)))

cat("\n=== Preprocessing Complete ===\n")
