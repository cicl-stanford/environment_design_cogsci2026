#!/usr/bin/env python3
"""
Find optimal start locations for all s1_design_inference trials.

For "cooks" trials: Run 1-agent greedy tests at both candidate locations to determine
which location should be assigned to agent1 (better performance) vs agent2.

For "dish" trials: Get the single start location from gym-cooking's auto-placement.

Outputs a complete start_locations.json file for all 36 trials with metadata.
"""

import os
import sys
import json
import csv
import subprocess
import argparse
import shutil
from pathlib import Path

print(f"Running with Python {sys.version}")

def read_trials_metadata(metadata_path):
    """Read trials metadata and return list of trial info."""
    trials = []
    with open(metadata_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            trials.append({
                'trial_id': row['trial_id'].strip(),
                'trial_type': row['trial_type'].strip(),
                'level_file': None  # Will be set below
            })
    return trials


def get_single_start_location(level_file, model_type="greedy", seed=1):
    """
    Get a single start location using the same level-specific logic as cooks trials.
    Returns the agent1 location (top-right interior scan) for the specific level.
    """
    # Use the same candidate location detection as cooks trials
    loc1, loc2 = get_candidate_locations(level_file)
    if loc1 is None:
        print(f"Error: Could not determine start location for {level_file}")
        return None

    # For dish trials, we just need agent1's location (the better of the two candidates)
    # Since there's no competition, we can just use the standard agent1 position
    return loc1


import sys
from pathlib import Path

# Add the project root to the Python path
try:
    project_root = Path(__file__).resolve().parents[3]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
except IndexError:
    raise RuntimeError("Could not find project root. Make sure the script is run from within the project structure.")

from project_code.python.utils.paths import GYM_COOKING_DIR

def run_single_agent_test(level_file, start_location, model_type="greedy", seed=1):
    """
    Run a single 1-agent test with the specified start location.
    Returns the number of timesteps taken to complete the task.
    """
    output_prefix = f"temp_optimization_{seed}"
    output_dir = GYM_COOKING_DIR / "temp_output"
    sim_script = GYM_COOKING_DIR / "gym_cooking" / "run_simulation.py"


    # Check if conda is available
    has_conda = shutil.which("conda") is not None

    base_cmd = [
        "python3", str(sim_script),
        "--level", level_file,
        "--recipe", "Salad", # since cooks trials are all Salad
        "--num-agents", "1",
        "--seed", str(seed),
        "--model1", model_type,
        "--start-location-model1", start_location,
        "--output-dir", str(output_dir),
        "--output-prefix", output_prefix,
        "--return-timesteps-only"
    ]

    if has_conda:
        cmd = ["conda", "run", "-n", "design-overcooked"] + base_cmd
        env = None
    else:
        cmd = base_cmd
        env = os.environ.copy()
        env["OMP_NUM_THREADS"] = "1"
        env["MKL_NUM_THREADS"] = "1"
        env["OPENBLAS_NUM_THREADS"] = "1"
        env["NUMEXPR_NUM_THREADS"] = "1"

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root, env=env)

        if result.returncode != 0:
            print(f"Error running test for {level_file} at {start_location}: {result.stderr}")
            return None

        # Parse the output to extract timesteps
        for line in result.stdout.split('\n'):
            if line.startswith('TIMESTEPS:'):
                timesteps = int(line.split(':')[1])
                return timesteps

        print(f"No timesteps found in output for {level_file} at {start_location}")
        return None

    except Exception as e:
        print(f"Exception running test for {level_file} at {start_location}: {e}")
        return None


def get_candidate_locations(level_file):
    """
    Get the two candidate start locations by parsing the level file and using the same
    scanning logic as gym-cooking's auto_place_agents to find real open spaces.
    """
    try:
        # Parse the level file to get world dimensions and objects
        with open(level_file, 'r') as f:
            lines = f.readlines()

        # Find the end of phase 1 (kitchen map)
        phase = 1
        max_x = 0
        max_y = 0
        world_objects = {}

        # Parse the level file to extract objects (similar to load_level in overcooked_environment.py)
        y = 0
        for line in lines:
            line = line.strip()
            if line == '':
                phase += 1
                if phase > 1:
                    break
                continue

            if phase == 1:
                max_x = max(max_x, len(line))
                max_y += 1

                # Parse objects in this line (similar to load_level logic)
                for x, rep in enumerate(line):
                    # Object, i.e. Tomato, Lettuce, Onion, or Plate.
                    if rep in 'tlop':
                        world_objects[(x, y)] = rep
                    # Food dispenser: make food dispenser object and food on top as a hack
                    elif rep in 'TLOP':
                        world_objects[(x, y)] = rep
                    # GridSquare, i.e. Floor, Counter, Cutboard, Delivery.
                    elif rep in '-*/':
                        world_objects[(x, y)] = rep
                    # Empty spaces are walkable
                    else:
                        world_objects[(x, y)] = ' '
                y += 1

        # Calculate world dimensions
        w, h = max_x, max_y

        # Use the same logic as gym-cooking's auto_place_agents to find candidate locations
        # Start from the same initial positions as the environment
        top_right_interior = (max(1, w - 2), 1)
        bottom_left_interior = (1, max(1, h - 2))

        # Use the scanning logic to find actual open spaces
        a1 = scan_open(world_objects, w, h, top_right_interior, dir_primary=(-1, 0), dir_secondary=(0, 1))
        a2 = scan_open(world_objects, w, h, bottom_left_interior, dir_primary=(0, -1), dir_secondary=(1, 0))
        if a2 == a1:
            a2 = scan_open(world_objects, w, h, (a2[0], a2[1]-1), dir_primary=(0, -1), dir_secondary=(1, 0))

        return f"{a1[0]} {a1[1]}", f"{a2[0]} {a2[1]}"

    except Exception as e:
        print(f"Error getting candidate locations for {level_file}: {e}")
        return None, None


def is_open_start_tile(world_objects, width, height, xy):
    """Open if it's inside the grid, not collidable, and not a supply/cut/delivery/counter."""
    x, y = xy
    if x < 0 or y < 0 or x >= width or y >= height:
        return False

    # Check if there's an object at this location
    if (x, y) in world_objects:
        obj = world_objects[(x, y)]
        # Objects that are collidable/not walkable
        if obj in '-*/':  # walls, counters, etc.
            return False
        # Objects that are walkable but not good start locations
        if obj in 'tlopTLOP':  # food items and dispensers
            return False

    # For empty spaces, they should be walkable
    return True


def scan_open(world_objects, width, height, start_xy, dir_primary, dir_secondary):
    """
    Scan within the interior bounding box (exclude outer walls) in the pattern:
    - Agent 1: move left along the row; when exhausted, move down a row, reset x to right interior.
    - Agent 2: move up along the column; when exhausted, move right a column, reset y to bottom interior.
    """
    # interior bounds (exclude border walls)
    xmin, xmax = 1, max(1, width - 2)
    ymin, ymax = 1, max(1, height - 2)

    # clamp start into interior
    x, y = start_xy
    x = min(max(x, xmin), xmax)
    y = min(max(y, ymin), ymax)

    visited = set()
    for _ in range(max(1, (xmax - xmin + 1) * (ymax - ymin + 1))):
        if (x, y) not in visited and is_open_start_tile(world_objects, width, height, (x, y)):
            return (x, y)
        visited.add((x, y))

        # step primary
        x += dir_primary[0]
        y += dir_primary[1]

        # if moved out of interior, wrap & step secondary
        if not (xmin <= x <= xmax and ymin <= y <= ymax):
            # undo last step
            x -= dir_primary[0]
            y -= dir_primary[1]
            # step secondary
            x += dir_secondary[0]
            y += dir_secondary[1]
            # reset along primary axis to appropriate interior edge
            if dir_primary[0] != 0:  # horizontal primary (agent 1)
                x = xmax if dir_primary[0] < 0 else xmin
            if dir_primary[1] != 0:  # vertical primary (agent 2)
                y = ymax if dir_primary[1] < 0 else ymin
            # clamp
            x = min(max(x, xmin), xmax)
            y = min(max(y, ymin), ymax)
    # As a last resort, return top-left interior
    return (xmin, ymin)


def optimize_cooks_trial(trial_info, num_seeds=3):
    """
    Optimize start locations for a "cooks" trial by testing both candidate locations.
    Returns dict with agent1_location, agent2_location, and optimization data.
    """
    level_file = trial_info['layout_abspath']

    # Get candidate locations
    loc1, loc2 = get_candidate_locations(level_file)

    print(f"Optimizing {trial_info['trial_id']} with candidate locations: {loc1}, {loc2}")

    # Test each location with multiple seeds
    loc1_times = []
    loc2_times = []
    loc1_seed_data = []
    loc2_seed_data = []

    for seed in range(1, num_seeds + 1):
        print(f"  Testing seed {seed}...")

        # Test location 1
        time1 = run_single_agent_test(level_file, loc1, "greedy", seed)
        if time1 is not None:
            loc1_times.append(time1)
            loc1_seed_data.append({"seed": seed, "timesteps": time1})

        # Test location 2
        time2 = run_single_agent_test(level_file, loc2, "greedy", seed)
        if time2 is not None:
            loc2_times.append(time2)
            loc2_seed_data.append({"seed": seed, "timesteps": time2})

    if not loc1_times or not loc2_times:
        print(f"Failed to get valid results for {trial_info['trial_id']}")
        return None

    # Calculate average times
    avg_time1 = sum(loc1_times) / len(loc1_times)
    avg_time2 = sum(loc2_times) / len(loc2_times)

    print(f"  Average times: {loc1}={avg_time1:.1f}, {loc2}={avg_time2:.1f}")

    # Assign better location to agent1, worse to agent2
    if avg_time1 <= avg_time2:
        agent1_loc, agent2_loc = loc1, loc2
        agent1_data, agent2_data = loc1_seed_data, loc2_seed_data
    else:
        agent1_loc, agent2_loc = loc2, loc1
        agent1_data, agent2_data = loc2_seed_data, loc1_seed_data

    return {
        'agent1_location': agent1_loc,
        'agent2_location': agent2_loc,
        'optimization_data': {
            'agent1_seed_data': agent1_data,
            'agent2_seed_data': agent2_data,
            'avg_time_agent1': sum(time['timesteps'] for time in agent1_data) / len(agent1_data),
            'avg_time_agent2': sum(time['timesteps'] for time in agent2_data) / len(agent2_data)
        }
    }


def process_dish_trial(trial_info):
    """
    Process a "dish" trial by getting the single start location.
    Returns dict with agent1_location only.
    """
    level_file = trial_info['layout_abspath']

    print(f"Getting start location for {trial_info['trial_id']} (dish trial)")

    # Get single start location from gym-cooking
    start_loc = get_single_start_location(level_file)

    if start_loc is None:
        print(f"Failed to get start location for {trial_info['trial_id']}")
        return None

    return {
        'agent1_location': start_loc,
        'agent2_location': None
    }


def main():
    parser = argparse.ArgumentParser(description="Find optimal start locations for all s1_design_inference trials")
    parser.add_argument("--metadata", type=Path,
                       default=Path(__file__).resolve().parents[3] / "stimuli/s1_design_inference/trials_metadata.csv",
                       help="Path to trials metadata CSV")
    parser.add_argument("--txt-dir", type=Path,
                       default=Path(__file__).resolve().parents[3] / "stimuli/s1_design_inference/txt",
                       help="Directory containing trial level files")
    parser.add_argument("--output", type=Path,
                       default=Path(__file__).resolve().parents[3] / "data/s1_design_inference/start_locations.json",
                       help="Output JSON file path")
    parser.add_argument("--seeds", type=int, default=3,
                       help="Number of seeds for optimization testing")
    parser.add_argument("--dry-run", action="store_true",
                       help="Print what would be done without running tests")

    args = parser.parse_args()

    # Read trials metadata
    trials = read_trials_metadata(args.metadata)

    # Set level file paths and verify they exist
    for trial in trials:
        layout_file = args.txt_dir / f"{trial['trial_id']}.txt"
        if not layout_file.exists():
            print(f"Error: Level file not found: {layout_file}")
            return 1
        trial['layout_abspath'] = str(layout_file)

    # Process all trials
    results = []

    for trial in trials:
        print(f"\nProcessing {trial['trial_id']} ({trial['trial_type']})...")

        if args.dry_run:
            print(f"  [DRY RUN] Would process {trial['trial_id']}")
            continue

        # Base result structure (use relative path for portability)
        result = {
            'trial_id': trial['trial_id'],
            'trial_type': trial['trial_type'],
            'layout_path': f"stimuli/s1_design_inference/txt/{trial['trial_id']}.txt"
        }

        if trial['trial_type'] == 'cooks':
            # Optimize start locations for cooks trials
            opt_result = optimize_cooks_trial(trial, args.seeds)
            if opt_result is None:
                print(f"Failed to optimize {trial['trial_id']}, skipping...")
                continue
            result.update(opt_result)

        elif trial['trial_type'] == 'dish':
            # Get single start location for dish trials
            dish_result = process_dish_trial(trial)
            if dish_result is None:
                print(f"Failed to process {trial['trial_id']}, skipping...")
                continue
            result.update(dish_result)

        else:
            print(f"Unknown trial type '{trial['trial_type']}' for {trial['trial_id']}")
            continue

        results.append(result)
        print(f"  Completed {trial['trial_id']}")

    if args.dry_run:
        print(f"\n[DRY RUN] Would write {len(results)} results to {args.output}")
        return 0

    # Write results to JSON
    args.output.parent.mkdir(parents=True, exist_ok=True)

    with open(args.output, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\nCompleted! Processed {len(results)} trials.")
    print(f"Results saved to: {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())