# Python Scripts

Data processing, model orchestration, and simulation pipelines.

## Shared Utilities

### utils/osf_data_handler.py
Helper function to pull behavioral data from OSF (from jsPsych [DataPipe](https://pipe.jspsych.org/)).

### utils/paths.py
Centralized path definitions. Uses `.project_root` marker file to locate the project root.

## Study 1: s1_design_inference/

### find_start_locations.py
Computes optimal agent starting positions for all 36 trials. The idea is that agents can start at either the top-right or bottom-left corner of the kitchen, and the starting position we choose is the one that minimizes the completion time. For cooks trials, the first cook starts at the position that minimizes the completion time (so that judgments for how many cooks are needed are a result of collaboration and not due to the 2nd cook having a better starting position).

Output: `project_code/bash/s1_design_inference/start_locations.json`

### model_runs.py
Computes timesteps to complete the task for all kitchen layouts for each model and dish. Can be run locally or used with `--dry-run` to generate a task list for SLURM cluster execution (see `bash/s1_design_inference/gen_tasks.sh`).

### process_model_outputs.py
Converts simulation outputs from pickle files into structured CSV. Extracts performance metrics including timesteps to completion.

Output: `data/s1_design_inference/models/model_results.csv`

### get_behavioral_results.py
Downloads and processes participant data from OSF into trial-level and session-level CSV files.

Output: `data/s1_design_inference/behavioral_results/trial_data.csv`

## Study 2: overcooked_design/

### get_design_model_utilities.py
Computes model utilities:
1. **Full Model:** `L = C(g) + (1 - P_cook(g)) * C(¬g)` where `P_cook` uses softmax inference
2. **Oracle Model:** `L = C(g)` (cook knows intended dish)
3. **Inference Ablation:** `L = C(g) + 0.5 * C(¬g)` (cook guesses randomly)
4. **Efficiency Ablation:** `U = P_cook(g)` (only inference matters, constant costs)

### run_single_config_placement.py
Entry point for cluster (Sherlock) execution. Runs 100 simulation seeds for a single (config, placement, dish) combination and writes results to CSV. Called by `bash/overcooked_design/gen_tasks.sh`.

Output: per-combination CSV with columns: `config_id, placement_id, placement_x, placement_y, dish, seed, timesteps, full_kitchen_layout`

### get_placement_utilities.py
Converts raw simulation outputs (`planning_model_outputs.csv`) into model utilities for all four model variants. Aggregates timesteps across seeds (taking the minimum) and computes utility values.

Output: `data/overcooked_design/model_results/placement_utilities.csv`

### get_model_results.py
Runs simulations for all possible furniture placements across all kitchen layouts to get the timesteps to complete the task for each placement. 

Output: `data/overcooked_design/model_results/model_results.csv`

### get_behavioral_results.py
Downloads and processes participant data from OSF for the design study. Produces session, cooking trial, and design trial dataframes.

Output: `data/overcooked_design/behavioral_results/`

## Cluster (Sherlock) Reproduction

The simulation pipeline was run on the Stanford Sherlock HPC cluster. See `bash/` for SLURM submission scripts. The pipeline for each study is:

**Study 1:**
```
find_start_locations.py → start_locations.json
    → bash/s1_design_inference/gen_tasks.sh (generates task list using model_runs.py --dry-run)
    → bash/s1_design_inference/submit_all.sh (submits SLURM array jobs)
    → process_model_outputs.py → model_results.csv
```

**Study 2:**
```
bash/overcooked_design/gen_tasks.sh (generates task list)
    → bash/overcooked_design/submit_job.sh (submits SLURM array jobs calling run_single_config_placement.py)
    → bash/overcooked_design/aggregate_csvs.sh → planning_model_outputs.csv
    → get_placement_utilities.py → placement_utilities.csv
```
