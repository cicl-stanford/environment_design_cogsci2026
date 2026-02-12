# Bash & SLURM Scripts

Shell scripts for orchestrating simulation and model-fitting pipelines on the Stanford Sherlock HPC cluster.

## Study 1: s1_design_inference/

### gen_tasks.sh
Generates a task list (`tasks.txt`) for SLURM array submission. Calls `model_runs.py --dry-run` to enumerate all simulation configurations, then injects agent start locations from `start_locations.json` and redirects output to `$SCRATCH`.

### submit_all.sh
Master orchestrator. Checks for `start_locations.json` (submits `run_optimization.slurm` if missing), generates the task list if needed, identifies incomplete tasks by checking for existing pickle files, and submits SLURM array jobs for only the missing tasks.

### run_optimization.slurm
SLURM job for computing optimal agent start locations via `find_start_locations.py`.

### run_overcooked_array.slurm
SLURM array job that executes one simulation task per array element. Each task runs `gym-cooking/run_simulation.py` with the parameters specified in `tasks.txt`.

### Pipeline
```
submit_all.sh
    → run_optimization.slurm (if start_locations.json missing)
    → gen_tasks.sh → tasks.txt
    → run_overcooked_array.slurm (SLURM array, one task per line)
```

## Study 2: overcooked_design/

### gen_tasks.sh
Generates a task list (`final_config_tasks.txt`) enumerating all (config, placement, dish) combinations. For each of the 12 configs x 12 placements x 2 dishes = 288 tasks, creates a command calling `run_single_config_placement.py`.

### submit_job.sh
Master orchestrator. Generates the task list if needed, checks for existing/complete CSVs, and submits SLURM array jobs for only the missing or incomplete tasks.

### run_array.slurm
SLURM array job that executes one simulation task per array element. Each task runs `run_single_config_placement.py` for 100 seeds.

### aggregate_csvs.sh
Concatenates all per-combination CSV files from the simulation runs into a single `planning_model_outputs.csv`.

### submit_brms.sh
Orchestrates the BRMS model fitting pipeline. Runs `preprocess_for_brms.R` to prepare data, then submits `run_brms.slurm` as a SLURM array job.

### run_brms.slurm
SLURM array job that fits one BRMS model per array element (9 models total: 4 models x 2 conditions + baseline). Each job uses 64 CPUs (16 chains x 4 threads).

### Pipeline
```
Simulations:
    submit_job.sh
        → gen_tasks.sh → final_config_tasks.txt
        → run_array.slurm (SLURM array, 288 tasks)
        → aggregate_csvs.sh → planning_model_outputs.csv

BRMS fitting:
    submit_brms.sh
        → preprocess_for_brms.R → df.long.rds
        → run_brms.slurm (SLURM array, 10 models)
        → fit_brms_model.R → brms_fit_*.rds + loo_*.rds
```
