#!/usr/bin/env python3
"""
Process model simulation outputs from s1_design_inference study.

Converts pickle files from gym-cooking model runs into a structured CSV
and creates GIFs from PNG frame sequences for visualization.
"""

import os
import sys
import glob
import dill as pickle
import subprocess
import shutil
import pandas as pd
from tqdm import tqdm
from joblib import Parallel, delayed
import multiprocessing
from pathlib import Path

# Add the project root to the Python path
try:
    project_root = Path(__file__).resolve().parents[3]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
except IndexError:
    raise RuntimeError("Could not find project root. Make sure the script is run from within the project structure.")

from project_code.python.utils.paths import DATA_DIR, STIMULI_DIR, GYM_COOKING_DIR


def create_single_gif(seed_dir, gif_path):
    """Create a single GIF from PNG frames in seed_dir."""
    # Check for PNG frames
    frames = glob.glob(os.path.join(seed_dir, 't=*.png'))
    if not frames:
        return False

    # Create output directory if needed
    os.makedirs(os.path.dirname(gif_path), exist_ok=True)

    # Create GIF with ffmpeg
    cmd = [
        'ffmpeg', '-y', '-v', 'error', '-framerate', '2',
        '-pattern_type', 'glob', '-i', os.path.join(seed_dir, 't=*.png'),
        '-vf', 'fps=2,split[s0][s1];[s0]palettegen=stats_mode=diff[p];[s1][p]paletteuse=dither=sierra2_4a',
        '-loop', '0', gif_path
    ]

    return subprocess.run(cmd, capture_output=True).returncode == 0


from project_code.python.utils.paths import DATA_DIR, STIMULI_DIR, GYM_COOKING_DIR

def main():
    # Directory setup
    model_dir = DATA_DIR / 's1_design_inference' / 'models'
    pickle_dir = model_dir / 'pickles'
    records_dir = model_dir / 'records'
    gifs_dir = model_dir / 'gifs'
    stimuli_dir = STIMULI_DIR / 's1_design_inference'

    # Add gym-cooking to path for imports
    sys.path.append(str(GYM_COOKING_DIR / 'gym_cooking'))
    import recipe_planner

    print("Loading trial metadata...")
    trial_metadata = pd.read_csv(os.path.join(stimuli_dir, 'trials_metadata.csv')).set_index('trial_id')

    # Process model data
    print("Processing model output files...")
    model_df = []
    model_paths = glob.glob(os.path.join(pickle_dir, '*.pkl'))

    if not model_paths:
        print(f"No pickle files found in {pickle_dir}")
        return

    for path in tqdm(model_paths, desc="Processing pickles"):
        try:
            with open(path, 'rb') as f:
                data = pickle.load(f)

            # Extract trial and parameters from filename
            agents = list(data['actions'].keys())
            trial = os.path.splitext(os.path.basename(data['level']))[0]
            filename_parts = os.path.splitext(os.path.basename(path))[0].split('-')[1:]

            # Parse parameters
            params = {f'model_{p.split("=")[0]}': p.split("=")[1] for p in filename_parts}
            params['model_agents'] = int(params['model_agents'])
            params['model_seed'] = int(params['model_seed'])
            params['model_settings'] = '-'.join(filename_parts[:-1])

            # Calculate metrics
            model_df.append({
                'trial': trial,
                **trial_metadata.loc[trial].to_dict(),
                **params,
                'timesteps': len(data['actions']['agent-1']),
                'agent_pauses': sum(a == (0, 0) for agent in agents for a in data['actions'][agent]),
                'agent_collisions': len(data['collisions']),
                'was_successful': data['was_successful']
            })

        except Exception as e:
            print(f"Error processing {path}: {e}")
            continue

    # Save CSV
    if model_df:
        model_df = pd.DataFrame(model_df).sort_values(['trial', 'model_model', 'model_recipe', 'model_seed'])
        os.makedirs(model_dir, exist_ok=True)
        csv_path = os.path.join(model_dir, 'model_results.csv')
        model_df.to_csv(csv_path, index=False)
        print(f"Saved {len(model_df)} records to {csv_path}")

    # Create GIFs in parallel
    if os.path.exists(records_dir) and shutil.which('ffmpeg'):
        print("Creating GIFs from PNG sequences...")

        # Collect all GIF tasks
        gif_tasks = []
        skipped = 0

        for trial_dir in glob.glob(os.path.join(records_dir, 'trial_*')):
            trial_name = os.path.basename(trial_dir)
            parts = trial_name.split('-', 1)
            if len(parts) != 2:
                continue

            trial_prefix, config_part = parts
            output_dir = os.path.join(gifs_dir, trial_prefix, config_part)

            for seed_dir in glob.glob(os.path.join(trial_dir, 'seed=*')):
                seed_name = os.path.basename(seed_dir)
                gif_path = os.path.join(output_dir, f'{seed_name}.gif')

                if os.path.exists(gif_path):
                    skipped += 1
                    continue

                gif_tasks.append((seed_dir, gif_path))

        if gif_tasks:
            # Use 80% of available cores
            n_jobs = max(1, int(multiprocessing.cpu_count() * 0.8))
            print(f"Processing {len(gif_tasks)} GIFs using {n_jobs} cores...")

            results = Parallel(n_jobs=n_jobs)(
                delayed(create_single_gif)(seed_dir, gif_path)
                for seed_dir, gif_path in tqdm(gif_tasks, desc="Creating GIFs")
            )

            created = sum(results)
            print(f"GIFs: {created} created, {skipped} skipped")
        else:
            print("No new GIFs to create")

    elif not os.path.exists(records_dir):
        print("No records directory found - skipping GIF creation")
    elif not shutil.which('ffmpeg'):
        print("ffmpeg not found - skipping GIF creation")

    print("Processing complete!")


if __name__ == '__main__':
    main()