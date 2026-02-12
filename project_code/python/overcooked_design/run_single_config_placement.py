#!/usr/bin/env python3
"""
Run simulations for a single (config, placement, dish) combination.

Generates 100 simulation runs (one per seed) and outputs results as CSV rows.
Each row contains: config_id, placement_id, placement_x, placement_y, dish, seed, timesteps, full_kitchen_layout

Usage:
    python3 run_single_config_placement.py \
        --config-path stimuli/overcooked_design/final_configs/6be479f8-4a3f-4d97-8f06-0f301b0acd64.json \
        --placement-id 0 \
        --dish TomatoSalad \
        --n-seeds 100 \
        --seed-start 42 \
        --output-csv /tmp/output.csv
"""

import argparse
import json
import csv
import sys
from pathlib import Path

# Add project root to path
try:
    project_root = Path(__file__).resolve().parents[3]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
except IndexError:
    raise RuntimeError("Could not find project root.")

# Import from get_design_model_utilities
from project_code.python.overcooked_design.get_design_model_utilities import (
    parse_design_space,
    enumerate_placements,
    place_furniture_on_floor_plan,
    extract_agent_start,
    _run_single_simulation,
    DISH_MAPPING
)


# extract_agent_start is imported from get_design_model_utilities


def main():
    parser = argparse.ArgumentParser(description='Run simulations for one config/placement/dish')
    parser.add_argument('--config-path', type=Path, required=True,
                       help='Path to JSON config file')
    parser.add_argument('--placement-id', type=int, required=True,
                       help='Placement index (0-11)')
    parser.add_argument('--dish', type=str, required=True,
                       choices=['TomatoSalad', 'OnionSalad'],
                       help='Dish name')
    parser.add_argument('--n-seeds', type=int, default=100,
                       help='Number of seeds to run')
    parser.add_argument('--seed-start', type=int, default=42,
                       help='Starting seed value')
    parser.add_argument('--output-csv', type=Path, required=True,
                       help='Output CSV file path')
    parser.add_argument('--max-timesteps', type=int, default=200,
                       help='Maximum timesteps (feasibility threshold)')

    args = parser.parse_args()

    # Load config
    print(f"Loading config from {args.config_path}")
    with open(args.config_path, 'r') as f:
        config = json.load(f)

    config_id = config['id']
    floor_plan = config['floor_plan']
    furniture_spec = config['furniture']

    print(f"Config ID: {config_id}")
    print(f"Placement: {args.placement_id}")
    print(f"Dish: {args.dish}")
    print(f"Seeds: {args.n_seeds} (starting at {args.seed_start})")

    # Parse design space bounds
    design_space_bounds = parse_design_space(floor_plan)

    # Enumerate placements
    placements = enumerate_placements(floor_plan, furniture_spec, design_space_bounds)

    if args.placement_id < 0 or args.placement_id >= len(placements):
        raise ValueError(f"Invalid placement_id {args.placement_id}. Must be 0-{len(placements)-1}")

    placement = placements[args.placement_id]
    placement_x = placement['location_x']
    placement_y = placement['location_y']

    print(f"Placement coordinates: ({placement_x}, {placement_y})")

    # Build complete kitchen with furniture placed
    kitchen_ascii = place_furniture_on_floor_plan(floor_plan, placement)

    # Extract agent start location (returns cleaned_kitchen, agent_row, agent_col)
    try:
        cleaned_kitchen, agent_row, agent_col = extract_agent_start(kitchen_ascii)
        print(f"Agent start: ({agent_col}, {agent_row})")
    except ValueError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    # Convert dish name to gym-cooking format
    gym_dish = DISH_MAPPING[args.dish]  # 'TomatoSalad' -> 'Salad'
    print(f"Gym-cooking dish: {gym_dish}")

    # Create output directory if needed
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)

    # Check for existing CSV and determine starting seed
    start_idx = 0
    file_exists = args.output_csv.exists()
    has_valid_header = False
    
    if file_exists:
        # Check if file is empty
        if args.output_csv.stat().st_size == 0:
            print(f"Existing CSV is empty, starting fresh")
            file_exists = False
        else:
            # Read existing CSV to find completed seeds and verify header
            print(f"Checking existing CSV: {args.output_csv}")
            completed_seeds = set()
            try:
                with open(args.output_csv, 'r', newline='') as f:
                    reader = csv.DictReader(f)
                    # Check if header is valid (has expected columns)
                    expected_columns = {'config_id', 'placement_id', 'placement_x', 'placement_y', 
                                      'dish', 'seed', 'timesteps', 'full_kitchen_layout'}
                    if reader.fieldnames and set(reader.fieldnames) == expected_columns:
                        has_valid_header = True
                        for row in reader:
                            completed_seeds.add(int(row['seed']))
                    else:
                        print(f"Warning: CSV has invalid header, starting fresh")
                        file_exists = False
                        has_valid_header = False
                
                if has_valid_header:
                    # Find first missing seed
                    for i in range(args.n_seeds):
                        seed = args.seed_start + i
                        if seed not in completed_seeds:
                            start_idx = i
                            break
                    else:
                        # All seeds completed
                        print(f"All {args.n_seeds} seeds already completed in {args.output_csv}")
                        return
                    
                    print(f"Resuming from seed {args.seed_start + start_idx} (completed {len(completed_seeds)}/{args.n_seeds})")
            except Exception as e:
                print(f"Warning: Could not read existing CSV ({e}), starting fresh")
                file_exists = False
                has_valid_header = False

    # Open file in append mode if resuming with valid header, write mode otherwise
    file_mode = 'a' if (file_exists and has_valid_header) else 'w'
    
    # Run seeds and write CSV with checkpointing
    print(f"\nRunning {args.n_seeds} simulations...")
    with open(args.output_csv, file_mode, newline='') as f:
        writer = csv.writer(f)

        # Write header only if starting fresh (new file or invalid header)
        if not (file_exists and has_valid_header):
            writer.writerow([
                'config_id',
                'placement_id',
                'placement_x',
                'placement_y',
                'dish',
                'seed',
                'timesteps',
                'full_kitchen_layout'
            ])
            f.flush()  # Ensure header is written immediately

        # Escape kitchen layout for CSV (replace newlines with literal \n)
        escaped_layout = kitchen_ascii.replace('\n', '\\n')

        # Run simulations for each seed
        for i in range(start_idx, args.n_seeds):
            seed = args.seed_start + i

            # Run single simulation
            timesteps = _run_single_simulation(
                cleaned_kitchen,
                agent_row,
                agent_col,
                gym_dish,
                seed,
                args.max_timesteps
            )

            # Write row immediately
            writer.writerow([
                config_id,
                args.placement_id,
                placement_x,
                placement_y,
                args.dish,
                seed,
                timesteps,
                escaped_layout
            ])

            # Checkpoint every 10 seeds (flush to disk)
            if (i + 1) % 10 == 0:
                f.flush()  # Force write to disk
                print(f"  Checkpoint: Completed {i + 1}/{args.n_seeds} seeds (saved to CSV)")

        # Final flush
        f.flush()
        print(f"  Completed {args.n_seeds}/{args.n_seeds} seeds")

    print(f"\nResults written to {args.output_csv}")
    print(f"Total rows: {args.n_seeds}")


if __name__ == '__main__':
    main()
