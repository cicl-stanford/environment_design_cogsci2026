"""
Generate model predictions for overcooked_design study.

Runs gym-cooking simulations for all possible furniture placements across all
design configurations to determine optimal timesteps.
"""

import os
import sys
import json
import pandas as pd
import numpy as np
import subprocess
import tempfile
from pathlib import Path
from joblib import Parallel, delayed

# Add project root to path
try:
    project_root = Path(__file__).resolve().parents[3]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
except IndexError:
    raise RuntimeError("Could not find project root.")

from project_code.python.utils.paths import DATA_DIR, STIMULI_DIR


def load_design_configs():
    """Load all design configuration files from stimuli directory."""
    config_dir = STIMULI_DIR / 'overcooked_design' / 'configs'

    configs = []
    for config_file in sorted(config_dir.glob('*.json')):
        with open(config_file, 'r') as f:
            config_data = json.load(f)
            configs.append({
                'filename': config_file.name,
                'path': str(config_file),
                'data': config_data
            })

    print(f"Loaded {len(configs)} design configurations")
    return configs


def parse_design_space(floor_plan):
    """
    Parse floor_plan ASCII to identify design space boundaries.

    Design space is the interior region where furniture can be placed (floor tiles).
    """
    lines = floor_plan.strip().split('\n')
    grid = [list(line) for line in lines]

    # Find bounding box of all floor spaces (marked as ' ')
    min_row, max_row = None, None
    min_col, max_col = None, None

    for y, row in enumerate(grid):
        for x, cell in enumerate(row):
            if cell == ' ':
                if min_row is None or y < min_row:
                    min_row = y
                if max_row is None or y > max_row:
                    max_row = y
                if min_col is None or x < min_col:
                    min_col = x
                if max_col is None or x > max_col:
                    max_col = x

    return {
        'top': min_row,
        'bottom': max_row,
        'left': min_col,
        'right': max_col,
        'width': max_col - min_col + 1,
        'height': max_row - min_row + 1
    }


def enumerate_placements(floor_plan, furniture_spec, design_space_bounds):
    """
    Enumerate all valid furniture placements within design space.

    For pilot: 5×5 design space with 3×2 furniture = 12 placements
    """
    furniture_grid = furniture_spec['grid']
    furniture_name = furniture_spec['name']
    furniture_height = len(furniture_grid)
    furniture_width = len(furniture_grid[0])

    top = design_space_bounds['top']
    left = design_space_bounds['left']
    bottom = design_space_bounds['bottom']
    right = design_space_bounds['right']

    placements = []
    placement_id = 0

    # Enumerate all positions where furniture fits (row by row, left to right)
    for y in range(top, bottom - furniture_height + 2):
        for x in range(left, right - furniture_width + 2):
            placements.append({
                'placement_id': placement_id,
                'furniture_name': furniture_name,
                'furniture_grid': furniture_grid,
                'location_x': x,
                'location_y': y,
                'width': furniture_width,
                'height': furniture_height
            })
            placement_id += 1

    # Verify expected count
    expected_count = (design_space_bounds['height'] - furniture_height + 1) * \
                     (design_space_bounds['width'] - furniture_width + 1)

    if len(placements) != expected_count:
        raise ValueError(
            f"Expected {expected_count} placements but generated {len(placements)}"
        )

    return placements


def place_furniture_on_floor_plan(floor_plan, placement):
    """Overlay furniture onto floor_plan to create complete kitchen layout."""
    lines = floor_plan.strip().split('\n')
    grid = [list(line) for line in lines]

    furniture = placement['furniture_grid']
    x = placement['location_x']
    y = placement['location_y']

    for dy in range(len(furniture)):
        for dx in range(len(furniture[dy])):
            if y + dy < len(grid) and x + dx < len(grid[y + dy]):
                grid[y + dy][x + dx] = furniture[dy][dx]

    kitchen_ascii = '\n'.join([''.join(row) for row in grid])
    return kitchen_ascii

def extract_agent_start(kitchen_ascii):
    """
    Extract agent start location from kitchen string and remove '1' marker.

    Args:
        kitchen_str: Kitchen layout string with '1' marking agent start

    Returns:
        tuple: (cleaned_kitchen_str, agent_row, agent_col)
    """
    lines = kitchen_ascii.split('\n')
    agent_row, agent_col = None, None

    for row_idx, line in enumerate(lines):
        for col_idx, char in enumerate(line):
            if char == '1':
                agent_row, agent_col = row_idx, col_idx
                # Replace '1' with space
                lines[row_idx] = line[:col_idx] + ' ' + line[col_idx + 1:]
                break
        if agent_row is not None:
            break

    cleaned_kitchen = '\n'.join(lines)
    return cleaned_kitchen, agent_row, agent_col

def run_gym_cooking_simulation(kitchen_ascii, recipe, max_timesteps=100, seed=42):
    """
    Run gym-cooking simulation via subprocess.

    Returns timesteps taken to complete the task.
    """
    # # Map recipe names (Salad → TomatoSalad, SaladOL → OnionSalad)
    # recipe_map = {
    #     'Salad': 'TomatoSalad',
    #     'SaladOL': 'OnionSalad'
    # }
    # gym_recipe = recipe_map.get(recipe, recipe)
    cleaned_kitchen, agent_row, agent_col = extract_agent_start(kitchen_ascii)

    # Write kitchen layout to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(cleaned_kitchen)
        kitchen_file = f.name

    try:
        # Prepare command
        gym_cooking_dir = Path(__file__).resolve().parents[3] / 'gym-cooking'
        cmd = [
            sys.executable,
            str(gym_cooking_dir / 'gym_cooking' / 'run_simulation.py'),
            '--level', kitchen_file,
            '--recipe', recipe,
            '--num-agents', '1',
            '--model1', 'optimal-single',
            '--start-location-model1', f'{agent_col} {agent_row}',
            '--max-num-timesteps', str(max_timesteps),
            '--seed', str(seed),
            '--return-timesteps-only',
            '--output-dir', '/tmp',  # Required but not used
            '--output-prefix', 'dummy'  # Required but not used
        ]

        # Run simulation
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,  # Don't raise on non-zero exit
            cwd=str(gym_cooking_dir)
        )

        # Parse timesteps from output
        for line in result.stdout.split('\n'):
            if line.startswith('TIMESTEPS:'):
                timesteps = int(line.split(':')[1].strip())
                return timesteps

        # If no timesteps found, check for errors
        if result.returncode != 0:
            print(f"Simulation failed: {result.stderr}")
            return max_timesteps  # Mark as failure

        # Shouldn't reach here
        return max_timesteps

    finally:
        # Clean up temp file
        if os.path.exists(kitchen_file):
            os.unlink(kitchen_file)


def run_single_simulation(config_filename, floor_plan, placement, dish, seed=42):
    """
    Run a single simulation for one furniture placement with a specific seed.

    Returns dict with results matching model_results.csv schema.
    """
    # Generate complete kitchen with furniture
    kitchen_ascii = place_furniture_on_floor_plan(floor_plan, placement)

    # Run simulation
    timesteps = run_gym_cooking_simulation(
        kitchen_ascii=kitchen_ascii,
        recipe=dish,
        max_timesteps=100,
        seed=seed
    )

    was_successful = timesteps < 100

    return {
        'config_filename': config_filename,
        'floor_plan': floor_plan,
        'furniture_placement_id': placement['placement_id'],
        'furniture_name': placement['furniture_name'],
        'furniture': json.dumps(placement['furniture_grid']),
        'furniture_location_x': placement['location_x'],
        'furniture_location_y': placement['location_y'],
        'furniture_width': placement['width'],
        'furniture_height': placement['height'],
        'kitchen_ascii': kitchen_ascii,
        'dish': dish,
        'model_agents': 1,
        'model_algorithm': 'greedy',
        'model_seed': seed,
        'timesteps': timesteps,
        'was_successful': was_successful
    }


def run_multi_seed_simulation(config_filename, floor_plan, placement, dish, n_seeds=3, base_seed=42):
    """
    Run simulation with multiple seeds and return the minimum timesteps.

    Args:
        config_filename: Config filename
        floor_plan: Floor plan ASCII
        placement: Placement dict
        dish: Dish type
        n_seeds: Number of seeds to run
        base_seed: Starting seed value

    Returns:
        Dict with min timesteps across all seeds
    """
    # Run simulation with multiple seeds
    all_timesteps = []
    for i in range(n_seeds):
        seed = base_seed + i
        result = run_single_simulation(config_filename, floor_plan, placement, dish, seed)
        all_timesteps.append(result['timesteps'])

    # Take minimum timesteps
    min_timesteps = min(all_timesteps)
    was_successful = min_timesteps < 100

    return {
        'config_filename': config_filename,
        'floor_plan': floor_plan,
        'furniture_placement_id': placement['placement_id'],
        'furniture_name': placement['furniture_name'],
        'furniture': json.dumps(placement['furniture_grid']),
        'furniture_location_x': placement['location_x'],
        'furniture_location_y': placement['location_y'],
        'furniture_width': placement['width'],
        'furniture_height': placement['height'],
        'kitchen_ascii': place_furniture_on_floor_plan(floor_plan, placement),
        'dish': dish,
        'model_agents': 1,
        'model_algorithm': 'greedy',
        'n_seeds': n_seeds,
        'timesteps': min_timesteps,
        'was_successful': was_successful
    }


def main(n_seeds=15, overwrite=False):
    """
    Main execution: load configs, enumerate placements, run simulations, save results.

    Args:
        n_seeds: Number of seeds to run per placement (default 3). Min timesteps is reported.
        overwrite: If False (default), use existing model_results.csv if it exists and skip model execution.
                   Only regenerate visualizations.
    """
    print("="*60)
    print("OVERCOOKED DESIGN - MODEL RESULTS GENERATION")
    print("="*60)
    print(f"Running with n_seeds={n_seeds} (reporting min timesteps across seeds)")

    # Load all design configs
    configs = load_design_configs()

    # Set up output paths
    output_dir = DATA_DIR / 'overcooked_design' / 'model_results'
    os.makedirs(output_dir, exist_ok=True)
    output_file = output_dir / 'model_results.csv'

    # Check if model results exist and overwrite=False
    if not overwrite and output_file.exists():
        print(f"\n✓ Model results already exist at {output_file}")
        print("✓ Loading existing results (overwrite=False)...")
        print("✓ Skipping model execution, will only regenerate visualizations")
        model_df = pd.read_csv(output_file)

        # Print summary
        print(f"\n{'='*60}")
        print(f"LOADED MODEL RESULTS SUMMARY")
        print(f"{'='*60}")
        print(f"  Total simulations: {len(model_df)}")
        print(f"  Successful: {model_df['was_successful'].sum()}")
        print(f"  Failed: {(~model_df['was_successful']).sum()}")
        print(f"  Success rate: {model_df['was_successful'].mean():.1%}")

        # Per-config summary
        print(f"\nPer-config timestep statistics:")
        config_summary = model_df.groupby('config_filename')['timesteps'].agg(['mean', 'min', 'max', 'std']).round(2)
        print(config_summary)

        # Per-dish summary
        print(f"\nPer-dish timestep statistics:")
        dish_summary = model_df.groupby('dish')['timesteps'].agg(['mean', 'min', 'max', 'std']).round(2)
        print(dish_summary)
    else:
        # Run simulations
        if output_file.exists():
            print(f"\n⚠ Model results exist but overwrite=True, re-running simulations...")
        else:
            print(f"\n✓ No existing model results found, running simulations...")

        # Build task list for all simulations
        tasks = []

        for config in configs:
            floor_plan = config['data']['floor_plan']
            furniture_spec = config['data']['furniture']

            # Parse design space boundaries
            design_space_bounds = parse_design_space(floor_plan)
            print(f"\n{config['filename']}: Design space = {design_space_bounds}")

            # Enumerate all valid placements
            placements = enumerate_placements(floor_plan, furniture_spec, design_space_bounds)
            print(f"  Generated {len(placements)} placements")

            # Create simulation tasks for each placement × dish combination
            for placement in placements:
                for dish in ['Salad', 'SaladOL']:
                    tasks.append({
                        'config_filename': config['filename'],
                        'floor_plan': floor_plan,
                        'placement': placement,
                        'dish': dish,
                        'n_seeds': n_seeds,
                        'base_seed': 42
                    })

        print(f"\nTotal unique placements to evaluate: {len(tasks)}")
        print(f"Total simulation runs (with {n_seeds} seeds each): {len(tasks) * n_seeds}")
        print(f"Running in parallel with joblib...")

        # Run simulations in parallel
        results = Parallel(n_jobs=-1, verbose=10)(
            delayed(run_multi_seed_simulation)(**task) for task in tasks
        )

        # Convert to DataFrame
        model_df = pd.DataFrame(results)

        # Define column order (matching data schema)
        model_order = [
            'config_filename', 'floor_plan',
            'furniture_placement_id', 'furniture_name', 'furniture',
            'furniture_location_x', 'furniture_location_y',
            'furniture_width', 'furniture_height', 'kitchen_ascii',
            'dish', 'model_agents', 'model_algorithm', 'n_seeds',
            'timesteps', 'was_successful'
        ]

        model_df = model_df[model_order]

        # Save results
        model_df.to_csv(output_file, index=False)

        # Print summary
        print(f"\n{'='*60}")
        print(f"SUMMARY")
        print(f"{'='*60}")
        print(f"  Total simulations: {len(model_df)}")
        print(f"  Successful: {model_df['was_successful'].sum()}")
        print(f"  Failed: {(~model_df['was_successful']).sum()}")
        print(f"  Success rate: {model_df['was_successful'].mean():.1%}")

        # Per-config summary
        print(f"\nPer-config timestep statistics:")
        config_summary = model_df.groupby('config_filename')['timesteps'].agg(['mean', 'min', 'max', 'std']).round(2)
        print(config_summary)

        # Per-dish summary
        print(f"\nPer-dish timestep statistics:")
        dish_summary = model_df.groupby('dish')['timesteps'].agg(['mean', 'min', 'max', 'std']).round(2)
        print(dish_summary)

        print(f"\n✓ Model results saved to: {output_file}")


if __name__ == '__main__':
    main()
