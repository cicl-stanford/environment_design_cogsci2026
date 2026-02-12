# Python Scripts

Data processing, model orchestration, and utility scripts.

## Shared Infrastructure

### utils/osf_data_handler.py
Client for retrieving behavioral data from OSF storage. Handles filename pattern matching, metadata extraction, and local caching to minimize redundant API calls.

### utils/paths.py
Centralized path definitions. Uses `.project_root` marker file to locate the project root.

## Study 1: s1_design_inference/

**find_start_locations.py**
Computes optimal agent starting positions for all 36 trials. Tests candidate locations for cooks trials and selects configurations that minimize completion time. The idea is that agents can start at either the top-right or bottom-left corner of the kitchen, and the starting position we choose is the one that minimizes the completion time. For cooks trials, the first cook starts at the position that minimizes the completion time (so that judgments for how many cooks are needed are a result of collaboration and not due to a better starting position).

**model_runs.py**
Computes timesteps to complete the task for all kitchen layouts for each model and dish.

**process_model_outputs.py**
Converts simulation outputs from pickle files into structured CSV. Extracts performance metrics including timesteps to completion.

Output: `data/s1_design_inference/models/model_results.csv`

**get_behavioral_results.py**
Downloads and processes participant data from OSF into session and trial-level and session-level CSV files. 

Output: `data/s1_design_inference/behavioral_results/trial_data.csv`

## Study 2: overcooked_design/

**get_model_results.py**
Runs simulations for all possible furniture placements across all kitchen layouts to get the timesteps to complete the task for each placement. 

Output: `data/overcooked_design/model_results/model_results.csv`

**get_behavioral_results.py**
Downloads and processes participant data from OSF for the design study. Produces session, cooking trial, and design trial dataframes.

Output: `data/overcooked_design/behavioral_results/`