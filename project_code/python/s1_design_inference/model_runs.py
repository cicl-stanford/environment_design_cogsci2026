#!/usr/bin/env python3
import argparse, csv, os, subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Optional, List
import sys

# Add the project root to the Python path
try:
    project_root = Path(__file__).resolve().parents[3]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
except IndexError:
    raise RuntimeError("Could not find project root. Make sure the script is run from within the project structure.")

from project_code.python.utils.paths import STIMULI_DIR, DATA_DIR, GYM_COOKING_DIR

# Project roots
EXPERIMENT = "s1_design_inference"
LEVEL_DIR = STIMULI_DIR / EXPERIMENT
TXT_DIR = LEVEL_DIR / "txt"
METADATA_CSV = LEVEL_DIR / "trials_metadata.csv"

DATA_ROOT = DATA_DIR / "models" / EXPERIMENT

PYTHON = "python3"
SIM_SCRIPT = GYM_COOKING_DIR / "gym_cooking" / "run_simulation.py"

def read_metadata(csv_path: Path):
    rows = []
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append({
                "trial_id": str(r["trial_id"]).strip(),
                "trial_type": str(r["trial_type"]).strip().lower(),
            })
    return rows

def ensure_dirs(*paths: Path):
    for p in paths:
        p.mkdir(parents=True, exist_ok=True)

def build_cmd(level: Path, num_agents: int, seed: int, outdir: Path, prefix: str,
              models: List[str], recipe: str):
    env = os.environ.copy()
    # single-thread heavy libs for CPU parallel
    env["OMP_NUM_THREADS"] = "1"
    env["MKL_NUM_THREADS"] = "1"
    env["OPENBLAS_NUM_THREADS"] = "1"
    env["NUMEXPR_NUM_THREADS"] = "1"

    cmd = [
        PYTHON, str(SIM_SCRIPT),
        "--level", str(level),
        "--recipe", recipe,
        "--num-agents", str(num_agents),
        "--seed", str(seed),
        "--record",
        "--output-dir", str(outdir),
        "--output-prefix", prefix,
    ]
    for i, m in enumerate(models[:num_agents], start=1):
        try:
            cmd += [f"--model{i}", m]
        except:
            print(f"Warning: Model {i} is None for {level}")

    return cmd, env

def log_header(level: Path, seed: int, num_agents: int, models: List[str], recipe: str):
    ts = datetime.now().strftime("%H:%M:%S")
    model_str = ",".join([m for m in models[:num_agents] if m])
    print(f"[ {ts} | lvl={level.stem} seed={seed} ] Agents={num_agents} models={model_str} recipe={recipe}")

def main():
    ap = argparse.ArgumentParser(description="S1 Design Inference model runs (CPU-parallel)")
    ap.add_argument("--metadata", type=Path, default=METADATA_CSV)
    ap.add_argument("--seeds", type=int, default=20, help="Run seeds 1..N")
    ap.add_argument("--jobs", type=int, default=os.cpu_count() * 0.8, help="Parallel processes")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    seeds = list(range(1, args.seeds + 1))
    rows = read_metadata(args.metadata)

    tasks = []  # (level, na, seed, outdir, prefix, models, recipe)

    for r in rows:
        trial_id = r["trial_id"]
        trial_type = r["trial_type"]
        level_path = TXT_DIR / f"{trial_id}.txt"
        if not level_path.exists():
            raise FileNotFoundError(f"Missing level file: {level_path}")

        data_dir = DATA_ROOT

        if trial_type == "cooks":
            run_specs = [
                dict(na=1, models=["greedy", None, None, None], recipe="Salad",
                     label="agents=1-model=greedy-recipe=Salad"),
                dict(na=2, models=["bd", "bd", None, None],     recipe="Salad",
                     label="agents=2-model=bd_bd-recipe=Salad"),
                dict(na=2, models=["centralized", "centralized", None, None],     recipe="Salad",
                     label="agents=2-model=centralized_centralized-recipe=Salad"),
                dict(na=2, models=["greedy", "greedy", None, None], recipe="Salad",
                     label="agents=2-model=greedy_greedy-recipe=Salad"),
            ]
            for spec in run_specs:
                for seed in seeds:
                    prefix = f"{trial_id}-{spec['label']}"
                    tasks.append((level_path, spec["na"], seed, data_dir, prefix,
                                  spec["models"], spec["recipe"]))

        elif trial_type == "dish":
            # single-agent greedy with two recipes
            for recipe in ("Salad", "SaladOL"):
                label = f"agents=1-model=greedy-recipe={recipe}"
                for seed in seeds:
                    prefix = f"{trial_id}-{label}"
                    tasks.append((level_path, 1, seed, data_dir, prefix,
                                  ["greedy", None, None, None], recipe))
        else:
            raise ValueError(f"Unknown trial_type '{trial_type}' for trial_id={trial_id}")

    # Ensure dirs
    for _, _, seed, outdir, prefix, _, _ in tasks:
        record_dir = Path(os.path.join(outdir, 'records', prefix, f'seed={seed}'))
        ensure_dirs(outdir, record_dir)

    futures, rcodes = [], []
    with ThreadPoolExecutor(max_workers=args.jobs) as ex:
        for t in tasks:
            level, na, seed, outdir, prefix, models, recipe = t
            log_header(level, seed, na, models, recipe)
            cmd, env = build_cmd(level, na, seed, outdir, prefix, models, recipe)
            if args.dry_run:
                print("DRY-RUN:", " ".join(cmd))
                rcodes.append(0)
            else:
                futures.append(ex.submit(subprocess.call, cmd, env=env))

        for fu in as_completed(futures):
            rcodes.append(fu.result())

    failed = sum(1 for r in rcodes if r != 0)
    if failed:
        print(f"{failed} task(s) failed.")
        raise SystemExit(1)

if __name__ == "__main__":
    main()
