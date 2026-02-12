"""
Compute placement utilities from simulation outputs for overcooked design study.

This script converts Sherlock simulation outputs (planning_model_outputs.csv) into
model utilities that can be used in R for statistical analysis.

The script is designed to be extensible: adding new models requires only:
1. Implementing the utility function in get_design_model_utilities.py
2. Adding an entry to MODEL_REGISTRY below
3. Re-running this script
"""

import argparse
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List

# Import utility computation functions
from get_design_model_utilities import (
    compute_full_model_utilities,
    compute_oracle_model_utilities,
    compute_inference_ablation_utilities,
    compute_efficiency_ablation_utilities,
    compute_cook_inference_probability
)

# Model registry - add new models here
MODEL_REGISTRY = {
    'full': {
        'compute_fn': compute_full_model_utilities,
        'requires': ['costs_g', 'costs_not_g', 'lambda_param']
    },
    'oracle': {
        'compute_fn': compute_oracle_model_utilities,
        'requires': ['costs_g']
    },
    'inference_ablation': {
        'compute_fn': compute_inference_ablation_utilities,
        'requires': ['costs_g', 'costs_not_g']
    },
    'efficiency_ablation': {
        'compute_fn': compute_efficiency_ablation_utilities,
        'requires': ['costs_g', 'costs_not_g', 'lambda_param']
    }
}


def load_simulation_costs(csv_path: str, max_timesteps: int = 200) -> Dict:
    """
    Load planning_model_outputs.csv and aggregate to min costs per placement.

    Input CSV columns: config_id, placement_id, placement_x, placement_y, dish, seed, timesteps

    Args:
        csv_path: Path to planning_model_outputs.csv
        max_timesteps: Maximum timesteps to clamp costs to (default: 200)

    Returns: {
        config_id: {
            dish: {
                placement_id: {
                    'cost': min_timesteps,  # Minimum across seeds, clamped to max_timesteps
                    'x': placement_x,
                    'y': placement_y,
                    'n_seeds': count
                }
            }
        }
    }
    """
    print(f"Loading simulation outputs from {csv_path}...")
    df = pd.read_csv(csv_path)

    print(f"Loaded {len(df)} rows")
    print(f"Configs: {df['config_id'].nunique()}")
    print(f"Placements per config: {df.groupby('config_id')['placement_id'].nunique().unique()}")
    print(f"Dishes: {df['dish'].unique()}")
    print(f"Seeds per placement: {df.groupby(['config_id', 'placement_id', 'dish']).size().unique()}")

    # Aggregate timesteps over seeds (min), clamping to max_timesteps
    costs = {}
    for (config, dish, placement), group in df.groupby(['config_id', 'dish', 'placement_id']):
        if config not in costs:
            costs[config] = {}
        if dish not in costs[config]:
            costs[config][dish] = {}

        min_cost = group['timesteps'].min()
        clamped_cost = min(min_cost, max_timesteps)
        
        costs[config][dish][placement] = {
            'cost': clamped_cost,
            'x': group['placement_x'].iloc[0],
            'y': group['placement_y'].iloc[0],
            'n_seeds': len(group)
        }

    print(f"\nAggregated to {len(costs)} configs with min costs per placement (clamped to max_timesteps={max_timesteps})")
    return costs


def compute_utilities_for_model(model_name: str, costs_dict: Dict, lambda_param: float = 1.0, max_timesteps: int = 200) -> pd.DataFrame:
    """
    Compute utilities for a single model across all config/dish/placements.

    Args:
        model_name: Key from MODEL_REGISTRY
        costs_dict: Output from load_simulation_costs()
        lambda_param: Inference temperature (default: 1.0)
        max_timesteps: Maximum timesteps used for clamping (default: 200)

    Returns:
        DataFrame with columns:
        - config_id, dish, placement_id, placement_x, placement_y
        - cost_g, cost_not_g, p_cook (inference probability)
        - lambda_param, max_timesteps
        - U_{model_name}
    """
    model_info = MODEL_REGISTRY[model_name]
    compute_fn = model_info['compute_fn']

    results = []

    for config_id, dishes in costs_dict.items():
        for dish, placements in dishes.items():
            # Extract costs for intended and alternative dish
            dish_other = 'OnionSalad' if dish == 'TomatoSalad' else 'TomatoSalad'

            # Build costs arrays (sorted by placement_id)
            placement_ids = sorted(placements.keys())
            costs_g = {p: placements[p]['cost'] for p in placement_ids}

            # Get costs for other dish
            if dish_other not in dishes:
                raise ValueError(
                    f"Missing data for {dish_other} in config {config_id}. "
                    f"Expected both TomatoSalad and OnionSalad data for all configs."
                )
            costs_not_g = {p: dishes[dish_other][p]['cost'] for p in placement_ids}

            # Compute utilities based on model requirements
            if model_name == 'full':
                utilities = compute_fn(costs_g, costs_not_g, lambda_param)
            elif model_name == 'oracle':
                utilities = compute_fn(costs_g)
            elif model_name == 'inference_ablation':
                utilities = compute_fn(costs_g, costs_not_g)
            elif model_name == 'efficiency_ablation':
                utilities = compute_fn(costs_g, costs_not_g, lambda_param)
            else:
                raise ValueError(f"Unknown model: {model_name}")

            # Store results with intermediate values
            for i, p_id in enumerate(placement_ids):
                # Compute inference probability for all models (for transparency)
                p_cook = compute_cook_inference_probability(
                    costs_g[p_id],
                    costs_not_g[p_id],
                    lambda_param
                )

                results.append({
                    'config_id': config_id,
                    'dish': dish,
                    'placement_id': p_id,
                    'placement_x': placements[p_id]['x'],
                    'placement_y': placements[p_id]['y'],
                    'cost_g': costs_g[p_id],
                    'cost_not_g': costs_not_g[p_id],
                    'p_cook': p_cook,
                    'lambda_param': lambda_param,
                    'max_timesteps': max_timesteps,
                    f'U_{model_name}': utilities[i]
                })

    return pd.DataFrame(results)


def compute_all_utilities(models: List[str] = None, lambda_param: float = 1.0, max_timesteps: int = 200, input_csv: str = None) -> pd.DataFrame:
    """
    Compute utilities for multiple models and merge into single DataFrame.

    Args:
        models: List of model names (default: all models in registry)
        lambda_param: Inference temperature (default: 1.0 from preregistration)
        max_timesteps: Maximum timesteps to clamp costs to (default: 200)
        input_csv: Path to simulation outputs (default: data/.../planning_model_outputs.csv)

    Returns:
        Wide-format DataFrame with columns:
        - config_id, dish, placement_id, placement_x, placement_y
        - cost_g, cost_not_g, p_cook, lambda_param, max_timesteps
        - U_full, U_oracle, U_inference_ablation, U_efficiency_ablation
        - (and any future models added to registry)
    """
    if models is None:
        models = list(MODEL_REGISTRY.keys())

    if input_csv is None:
        # Default path relative to project root
        script_dir = Path(__file__).parent
        input_csv = script_dir / '../../../data/overcooked_design/model_results/planning_model_outputs.csv'

    # Load costs
    costs = load_simulation_costs(str(input_csv), max_timesteps=max_timesteps)

    # Compute utilities for first model (includes cost_g, cost_not_g, p_cook, lambda_param, max_timesteps)
    print(f"\nComputing utilities for model: {models[0]}")
    df = compute_utilities_for_model(models[0], costs, lambda_param, max_timesteps=max_timesteps)

    # Join utilities from other models (only add U_{model_name} columns)
    for model_name in models[1:]:
        print(f"Computing utilities for model: {model_name}")
        df_model = compute_utilities_for_model(model_name, costs, lambda_param, max_timesteps=max_timesteps)
        # Only merge the utility column (cost_g, cost_not_g, p_cook, lambda_param, max_timesteps should be identical)
        df = df.merge(
            df_model[['config_id', 'dish', 'placement_id', f'U_{model_name}']],
            on=['config_id', 'dish', 'placement_id'],
            how='outer',
            validate='one_to_one'
        )

    return df


def main():
    """
    CLI entry point.

    Usage:
        python get_placement_utilities.py --lambda-param 1.0 --models full oracle --output utilities.csv
    """
    parser = argparse.ArgumentParser(
        description='Compute placement utilities from Sherlock simulation outputs'
    )
    parser.add_argument('--lambda-param', type=float, default=1.0,
                        help='Inference temperature (default: 1.0 from preregistration)')
    parser.add_argument('--max-timesteps', type=int, default=200,
                        help='Maximum timesteps to clamp costs to (default: 200)')
    parser.add_argument('--models', nargs='+', default=None,
                        help='Models to compute (default: all models in registry)')
    parser.add_argument('--input', type=str, default=None,
                        help='Path to planning_model_outputs.csv')
    parser.add_argument('--output', type=str, default=None,
                        help='Output path for placement_utilities.csv')

    args = parser.parse_args()

    # Default output path
    if args.output is None:
        script_dir = Path(__file__).parent
        args.output = script_dir / '../../../data/overcooked_design/model_results/placement_utilities.csv'

    # Compute utilities
    print(f"\n{'='*60}")
    print("Computing placement utilities")
    print(f"{'='*60}")
    print(f"Lambda: {args.lambda_param}")
    print(f"Max timesteps: {args.max_timesteps}")
    print(f"Models: {args.models if args.models else 'all'}")
    print()

    df = compute_all_utilities(
        models=args.models,
        lambda_param=args.lambda_param,
        max_timesteps=args.max_timesteps,
        input_csv=args.input
    )

    # Save
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)

    print(f"\n{'='*60}")
    print("Summary")
    print(f"{'='*60}")
    print(f"Total placements: {len(df)}")
    print(f"Configs: {df['config_id'].nunique()}")
    print(f"Dishes: {df['dish'].nunique()}")
    print(f"Placements per config: {len(df) // (df['config_id'].nunique() * df['dish'].nunique())}")
    print(f"\nUtility columns: {[c for c in df.columns if c.startswith('U_')]}")
    print(f"\nSaved to: {output_path}")

    # Show sample
    print(f"\nSample rows:")
    print(df.head(3))


if __name__ == '__main__':
    main()
