# Python Scripts

Data processing, model orchestration, and utility scripts.

## Shared Infrastructure

### utils/osf_data_handler.py
Client for retrieving behavioral data from OSF storage. Handles filename pattern matching, metadata extraction, and local caching to minimize redundant API calls.

### utils/paths.py
Centralized path definitions. Uses `.project_root` marker file to locate the project root.

## Study 1: s1_design_inference/

**find_start_locations.py**
Computes optimal agent starting positions for all 36 trials. Tests candidate locations for cooks trials and selects configurations that minimize completion time.

**model_runs.py**
Orchestrates parallel simulation execution for all trial configurations. Generates task lists for each combination of trial, agents, model algorithm, recipe type, and random seed.

**process_model_outputs.py**
Converts simulation outputs from pickle files into structured CSV. Extracts performance metrics including timesteps to completion.

Output: `data/s1_design_inference/models/model_results.csv`

**get_behavioral_results.py**
Downloads and processes participant data from OSF into session and trial-level CSV files. Handles inference and effort conditions from separate OSF components.

Output: `data/s1_design_inference/behavioral_results/trial_data.csv`

## Study 2: overcooked_design/

**get_model_results.py**
Runs gym-cooking simulations for all possible furniture placements across all design configurations. Enumerates placement positions, runs simulations in parallel, and saves timestep results.

Output: `data/overcooked_design/model_results/model_results.csv`

**get_behavioral_results.py**
Downloads and processes participant data from OSF for the design study. Produces session, cooking trial, and design trial dataframes.

Output: `data/overcooked_design/behavioral_results/`

## Pipeline

1. Run simulations locally or on cluster (`model_runs.py` / `get_model_results.py`)
2. Process model outputs (`process_model_outputs.py`)
3. Download behavioral data from OSF (`get_behavioral_results.py`)
4. Analyze in R (`project_code/R/analysis_cogsci2026.Rmd`)
