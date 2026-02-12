"""
Compute model utilities for overcooked design study.

Implements 4 computational models from writeup/overcooked_design_formal_model.pdf:

1. Full Model: L(ℓ,g,k) = C(ℓ,k,g) + (1 - P_cook(g|ℓ,k)) * C(ℓ,k,¬g)
   - P_cook(g|ℓ,k) = exp{-λ C(ℓ,k,g)} / Σ_d exp{-λ C(ℓ,k,d)}

2. Oracle Model: L(ℓ,g,k) = C(ℓ,k,g)
   - Assumes cook knows intended dish

3. InferenceAblation: L(ℓ,g,k) = C(ℓ,k,g) + 0.5 * C(ℓ,k,¬g)
   - Assumes cook guesses randomly (50/50)

4. EfficiencyAblation: L(ℓ,g,k) = -1 + (1 - P_cook(g|ℓ,k)) * 1
   - Uses constant costs, only inference matters

All models convert losses to utilities via U = -L.
"""

import os
import sys
import json
import numpy as np
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from joblib import Parallel, delayed

# Add project root to path
try:
    project_root = Path(__file__).resolve().parents[3]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
except IndexError:
    raise RuntimeError("Could not find project root.")

# Constants
C_MAX = 10**6  # Infeasibility marker (when timesteps >= max_timesteps)
MAX_TIMESTEPS_DEFAULT = 100  # Default threshold for infeasibility

# Dish name mapping: Model names ↔ Gym-cooking recipe names
DISH_MAPPING = {
    'TomatoSalad': 'Salad',      # Tomato + Lettuce
    'OnionSalad': 'SaladOL'      # Onion + Lettuce
}


# ============================================================================
# Helper Functions (Copied from get_model_results.py logic)
# ============================================================================

def parse_design_space(floor_plan: str) -> Dict:
    """
    Parse floor_plan ASCII to identify design space boundaries.

    Design space is the interior region where furniture can be placed (floor tiles).

    Returns:
        dict: {top, bottom, left, right, width, height}
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


def enumerate_placements(floor_plan: str, furniture_spec: dict,
                        design_space_bounds: dict) -> List[Dict]:
    """
    Enumerate all valid furniture placements within design space.

    For pilot: 5×5 design space with 2×3 furniture = 12 placements
    Enumeration order: row-by-row, left-to-right

    Returns:
        List of placement dicts with keys:
        - placement_id, furniture_name, furniture_grid
        - location_x, location_y, width, height
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


def place_furniture_on_floor_plan(floor_plan: str, placement: dict) -> str:
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


def extract_agent_start(kitchen_ascii: str) -> Tuple[str, int, int]:
    """
    Extract agent start location from kitchen string and remove '1' marker.

    Args:
        kitchen_ascii: Kitchen layout string with '1' marking agent start

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


def validate_furniture(furniture_spec: dict):
    """
    Validate that furniture is 2×3 (width × height).

    Raises NotImplementedError for other furniture sizes.
    """
    grid = furniture_spec['grid']
    height, width = len(grid), len(grid[0]) if grid else 0
    if height != 3 or width != 2:
        raise NotImplementedError(
            f"Only 2×3 furniture supported (width=2, height=3), got width={width}, height={height}"
        )


# ============================================================================
# Simulation Execution Functions
# ============================================================================

def _run_single_simulation(cleaned_kitchen: str, agent_row: int, agent_col: int,
                          dish: str, seed: int, max_timesteps: int) -> int:
    """
    Run a single simulation via subprocess.

    Returns:
        Timesteps taken, or max_timesteps if failed
    """
    gym_cooking_dir = Path(__file__).resolve().parents[3] / 'gym-cooking'

    # Prepare command with --model1 greedy
    cmd = [
        sys.executable,
        str(gym_cooking_dir / 'gym_cooking' / 'run_simulation.py'),
        '--level', cleaned_kitchen,  # ASCII string directly
        '--recipe', dish,
        '--num-agents', '1',
        '--model1', 'greedy',  # Use greedy model
        '--start-location-model1', f'{agent_col} {agent_row}',
        '--max-num-timesteps', str(max_timesteps),
        '--seed', str(seed),
        '--return-timesteps-only',
        '--output-dir', '/tmp',
        '--output-prefix', 'dummy'
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
        cwd=str(gym_cooking_dir)
    )

    # Parse timesteps from output
    for line in result.stdout.split('\n'):
        if line.startswith('TIMESTEPS:'):
            return int(line.split(':')[1].strip())

    # If no timesteps found, treat as failure
    return max_timesteps


def run_simulation_for_cost(kitchen_ascii: str, dish: str,
                           n_seeds: int = 10, max_timesteps: int = MAX_TIMESTEPS_DEFAULT) -> float:
    """
    Run simulation and return minimum timesteps across n_seeds.

    Args:
        kitchen_ascii: Complete kitchen layout with furniture and '1' for agent start
        dish: Dish name in gym-cooking format (Salad or SaladOL)
        n_seeds: Number of seeds to run (default 10)
        max_timesteps: Threshold for infeasibility

    Returns:
        Minimum timesteps across seeds, or C_MAX if infeasible
    """
    # Extract agent start location
    cleaned_kitchen, agent_row, agent_col = extract_agent_start(kitchen_ascii)

    # Run simulations with multiple seeds
    all_timesteps = []
    for i in range(n_seeds):
        seed = 42 + i
        timesteps = _run_single_simulation(
            cleaned_kitchen, agent_row, agent_col, dish, seed, max_timesteps
        )
        all_timesteps.append(timesteps)

    # Take minimum across seeds
    min_timesteps = min(all_timesteps)

    # Mark as infeasible if >= max_timesteps
    return C_MAX if min_timesteps >= max_timesteps else float(min_timesteps)


def _compute_single_cost(placement_id: int, kitchen: str,
                        dish: str, n_seeds: int, max_timesteps: int) -> Tuple[int, str, float]:
    """Helper for parallel cost computation."""
    cost = run_simulation_for_cost(kitchen, dish, n_seeds, max_timesteps)
    return (placement_id, dish, cost)


def compute_costs_for_all_placements(
    floor_plan: str,
    furniture_spec: dict,
    n_seeds: int = 10,
    max_timesteps: int = MAX_TIMESTEPS_DEFAULT,
    parallelize: bool = False
) -> Tuple[Dict[int, float], Dict[int, float]]:
    """
    Compute costs C(ℓ,k,d) for all placements and both dishes.

    Returns:
        (costs_salad, costs_salad_ol) where each is {placement_id: cost}
    """
    design_space_bounds = parse_design_space(floor_plan)
    placements = enumerate_placements(floor_plan, furniture_spec, design_space_bounds)

    if parallelize:
        # Build task list
        tasks = []
        for p in placements:
            kitchen = place_furniture_on_floor_plan(floor_plan, p)
            for dish in ['Salad', 'SaladOL']:
                tasks.append((p['placement_id'], kitchen, dish, n_seeds, max_timesteps))

        # Run in parallel
        results = Parallel(n_jobs=-1, verbose=0)(
            delayed(_compute_single_cost)(pid, k, d, n_seeds, max_timesteps)
            for pid, k, d, n_seeds, max_timesteps in tasks
        )

        # Organize results
        costs_salad = {}
        costs_salad_ol = {}
        for placement_id, dish, cost in results:
            if dish == 'Salad':
                costs_salad[placement_id] = cost
            else:
                costs_salad_ol[placement_id] = cost

    else:
        # Sequential execution
        costs_salad = {}
        costs_salad_ol = {}

        for p in placements:
            kitchen = place_furniture_on_floor_plan(floor_plan, p)
            pid = p['placement_id']

            print(f"Computing costs for placement {pid}...")
            costs_salad[pid] = run_simulation_for_cost(kitchen, 'Salad', n_seeds, max_timesteps)
            costs_salad_ol[pid] = run_simulation_for_cost(kitchen, 'SaladOL', n_seeds, max_timesteps)

    return costs_salad, costs_salad_ol


# ============================================================================
# Inference Probability Computation
# ============================================================================

def compute_cook_inference_probability(
    cost_g: float,
    cost_not_g: float,
    lambda_param: float
) -> float:
    """
    Compute P_cook(g | ℓ,k) using softmax over negative costs (Eq. 9).

    P_cook(g | ℓ,k) = exp{-λ C(ℓ,k,g)} / [exp{-λ C(ℓ,k,g)} + exp{-λ C(ℓ,k,¬g)}]

    Edge cases (from formal model pages 3-4):
    - If cost_g < C_MAX and cost_not_g = C_MAX: return 1.0
    - If both = C_MAX: return 0.0 (undefined, handled by caller with infinite loss)

    Args:
        cost_g: Cost for intended dish
        cost_not_g: Cost for alternative dish
        lambda_param: Inference sensitivity parameter (default 0.294)

    Returns:
        Probability that cook will attempt dish g
    """
    # Edge cases ensure that vanishing probabilities snap to 0 or 1.
    # Edge case 1: Only intended dish is feasible (page 3-4)
    if cost_g < C_MAX and cost_not_g >= C_MAX:
        return 1.0

    # Edge case 2: Both infeasible (handled by caller with infinite loss)
    if cost_g >= C_MAX and cost_not_g >= C_MAX:
        return 0.0

    # Standard case: softmax
    exp_g = np.exp(-lambda_param * cost_g)
    exp_not_g = np.exp(-lambda_param * cost_not_g)

    return exp_g / (exp_g + exp_not_g)


# ============================================================================
# Model-Specific Utility Functions
# ============================================================================

def compute_full_model_utilities(
    costs_g: Dict[int, float],
    costs_not_g: Dict[int, float],
    lambda_param: float
) -> np.ndarray:
    """
    Compute Full model utilities: U = -L where
    L(ℓ,g,k) = C(ℓ,k,g) + (1 - P_cook(g|ℓ,k)) * C(ℓ,k,¬g)

    Returns:
        utilities as 1D array indexed by placement_id
    """
    n_placements = len(costs_g)
    losses = np.zeros(n_placements)

    for k in range(n_placements):
        cost_g = costs_g[k]
        cost_not_g = costs_not_g[k]

        # Compute P_cook(g | ℓ,k)
        p_cook_g = compute_cook_inference_probability(cost_g, cost_not_g, lambda_param)

        # Clamp to C_MAX to avoid double counting infeasible placement losses.
        losses[k] = min(cost_g + (1 - p_cook_g) * cost_not_g, C_MAX)

    # Convert to utilities (negate losses)
    utilities = -losses
    return utilities


def compute_oracle_model_utilities(
    costs_g: Dict[int, float]
) -> np.ndarray:
    """
    Compute Oracle model utilities: U = -L where
    L(ℓ,g,k) = C(ℓ,k,g)

    Assumes cook knows intended dish with certainty (Eq. 10).

    Returns:
        utilities as 1D array indexed by placement_id
    """
    n_placements = len(costs_g)
    utilities = np.zeros(n_placements)

    for k in range(n_placements):
        utilities[k] = -costs_g[k]

    return utilities


def compute_inference_ablation_utilities(
    costs_g: Dict[int, float],
    costs_not_g: Dict[int, float]
) -> np.ndarray:
    """
    Compute InferenceAblation model utilities: U = -L where
    L(ℓ,g,k) = C(ℓ,k,g) + 0.5 * C(ℓ,k,¬g)

    Assumes cook guesses randomly (50/50) without inference (Eq. 11).

    Returns:
        utilities as 1D array indexed by placement_id
    """
    n_placements = len(costs_g)
    utilities = np.zeros(n_placements)

    for k in range(n_placements):
        loss = costs_g[k] + 0.5 * costs_not_g[k]
        # Clamp to C_MAX to standardize infeasible placement losses.
        loss = loss if loss <= C_MAX / 2 else C_MAX
        utilities[k] = -loss

    return utilities


def compute_efficiency_ablation_utilities(
    costs_g: Dict[int, float],
    costs_not_g: Dict[int, float],
    lambda_param: float
) -> np.ndarray:
    """
    Compute EfficiencyAblation model utilities: U = -L where
    L(ℓ,g,k) = C_tilde(g) + (1 - P_cook(g|ℓ,k)) * C_tilde(¬g)
    where C_tilde(g) = -1, C_tilde(¬g) = +1

    Note: P_cook still uses actual costs C(ℓ,k,d), not substituted costs.

    Simplifies to (Eq. 12-13):
    L(ℓ,g,k) = -1 + (1 - P_cook(g|ℓ,k)) * 1 = -P_cook(g|ℓ,k)
    So: U(ℓ,g,k) = P_cook(g|ℓ,k)

    Returns:
        utilities as 1D array indexed by placement_id
    """
    n_placements = len(costs_g)
    utilities = np.zeros(n_placements)

    for k in range(n_placements):
        cost_g = costs_g[k]
        cost_not_g = costs_not_g[k]

        # Compute P_cook using actual costs (not substituted)
        p_cook_g = compute_cook_inference_probability(cost_g, cost_not_g, lambda_param)
        
        # U = P_cook (derived from L = -P_cook)
        utilities[k] = p_cook_g

    return utilities


# ============================================================================
# Main Function
# ============================================================================

def compute_model_utilities(
    model: str,
    design_problem: dict,
    lambda_param: float = 0.294,
    n_seeds: int = 10,
    max_timesteps: int = MAX_TIMESTEPS_DEFAULT,
    parallelize: bool = False
) -> dict:
    """
    Compute model utilities for all placements and both dishes.

    Args:
        model: One of "full", "oracle", "inference-ablation", "efficiency-ablation"
        design_problem: Dict with keys:
            - "floor_plan": ASCII string of kitchen layout
            - "furniture": Dict with "grid", "id", "name"
        lambda_param: Inference parameter (default 0.294 from inference study)
        n_seeds: Number of simulation seeds (default 10)
        max_timesteps: Threshold for infeasibility (default 100)
        parallelize: Whether to use parallel execution (default False)

    Returns:
        Dict mapping dish names to utility grids:
        {
            "TomatoSalad": np.ndarray of shape (3, 4),  # 3 rows × 4 cols = 12 placements
            "OnionSalad": np.ndarray of shape (3, 4)
        }

        Grid indexing: utilities[row, col] = utility for furniture placement
        with top-left corner at (row, col) in the design space.

        Placement enumeration order: row-major (row 0 left-to-right, then row 1, etc.)

    Example:
        >>> with open('design_config_01.json') as f:
        ...     problem = json.load(f)
        >>> utils = compute_model_utilities('full', problem)
        >>> utils['TomatoSalad'].shape
        (3, 4)  # For 5×5 space with 2×3 furniture
    """
    # Validate model name
    valid_models = {"full", "oracle", "inference-ablation", "efficiency-ablation"}
    if model not in valid_models:
        raise ValueError(f"Model must be one of {valid_models}, got '{model}'")

    # Extract design problem components
    floor_plan = design_problem['floor_plan']
    furniture_spec = design_problem['furniture']

    # Validate furniture is 2×3
    validate_furniture(furniture_spec)

    # Compute costs for all placements
    print(f"Computing costs for all placements (n_seeds={n_seeds})...")
    costs_salad, costs_salad_ol = compute_costs_for_all_placements(
        floor_plan, furniture_spec, n_seeds, max_timesteps, parallelize
    )

    # Get design space dimensions for reshaping
    design_space_bounds = parse_design_space(floor_plan)
    furniture_height = len(furniture_spec['grid'])
    furniture_width = len(furniture_spec['grid'][0])
    n_rows = design_space_bounds['height'] - furniture_height + 1
    n_cols = design_space_bounds['width'] - furniture_width + 1

    # Compute utilities for each dish
    results = {}

    for dish_model_name, dish_gym_name in DISH_MAPPING.items():
        print(f"Computing {model} utilities for {dish_model_name}...")

        # Determine which costs are for g vs ¬g
        if dish_gym_name == 'Salad':
            costs_g = costs_salad
            costs_not_g = costs_salad_ol
        else:  # SaladOL
            costs_g = costs_salad_ol
            costs_not_g = costs_salad

        # Compute utilities based on model type
        if model == "full":
            utilities_1d = compute_full_model_utilities(
                costs_g, costs_not_g, lambda_param
            )
        elif model == "oracle":
            utilities_1d = compute_oracle_model_utilities(costs_g)
        elif model == "inference-ablation":
            utilities_1d = compute_inference_ablation_utilities(
                costs_g, costs_not_g
            )
        elif model == "efficiency-ablation":
            utilities_1d = compute_efficiency_ablation_utilities(
                costs_g, costs_not_g, lambda_param
            )

        # Reshape to 2D grid (row-major order)
        # placement_id = row * n_cols + col
        utilities_2d = utilities_1d.reshape(n_rows, n_cols)

        results[dish_model_name] = utilities_2d

    return results


# ============================================================================
# Convenience Functions
# ============================================================================

def get_placement_probabilities(
    utilities: np.ndarray,
    beta: float = 1.0
) -> np.ndarray:
    """
    Convert utilities to softmax probabilities (Eq. 6).

    q(k | ℓ, g, β) ∝ exp{β U(ℓ, g, k)}

    Args:
        utilities: 2D array of utilities
        beta: Softmax temperature/sensitivity parameter

    Returns:
        2D array of probabilities (sums to 1)
    """
    # Flatten
    u_flat = utilities.flatten()

    # Softmax with numerical stability
    exp_u = np.exp(beta * (u_flat - np.max(u_flat)))
    probs = exp_u / exp_u.sum()

    # Reshape back to 2D
    return probs.reshape(utilities.shape)


def compute_all_models_utilities(
    design_problem: dict,
    lambda_param: float = 0.294,
    n_seeds: int = 10,
    max_timesteps: int = MAX_TIMESTEPS_DEFAULT,
    parallelize: bool = True
) -> dict:
    """
    Compute utilities for all 4 models at once (more efficient than calling compute_model_utilities 4 times).

    This is more efficient because step costs are computed only once and shared across all models.

    Args:
        design_problem: Dict with keys:
            - "floor_plan": ASCII string of kitchen layout
            - "furniture": Dict with "grid", "id", "name"
        lambda_param: Inference parameter (default 0.294 from inference study)
        n_seeds: Number of simulation seeds (default 10)
        max_timesteps: Threshold for infeasibility (default 100)
        parallelize: Whether to use parallel execution (default True)

    Returns:
        Dict mapping model names to dish utilities:
        {
            "full": {"TomatoSalad": np.ndarray, "OnionSalad": np.ndarray},
            "oracle": {"TomatoSalad": np.ndarray, "OnionSalad": np.ndarray},
            "inference-ablation": {"TomatoSalad": np.ndarray, "OnionSalad": np.ndarray},
            "efficiency-ablation": {"TomatoSalad": np.ndarray, "OnionSalad": np.ndarray}
        }
    """
    # Extract design problem components
    floor_plan = design_problem['floor_plan']
    furniture_spec = design_problem['furniture']

    # Validate furniture is 2×3
    validate_furniture(furniture_spec)

    # Compute costs ONCE for all placements and both dishes
    print(f"Computing costs for all placements (n_seeds={n_seeds}, parallelize={parallelize})...")
    costs_salad, costs_salad_ol = compute_costs_for_all_placements(
        floor_plan, furniture_spec, n_seeds, max_timesteps, parallelize
    )

    # Get design space dimensions for reshaping
    design_space_bounds = parse_design_space(floor_plan)
    furniture_height = len(furniture_spec['grid'])
    furniture_width = len(furniture_spec['grid'][0])
    n_rows = design_space_bounds['height'] - furniture_height + 1
    n_cols = design_space_bounds['width'] - furniture_width + 1

    # Compute utilities for all models
    all_results = {}

    for model in ["full", "oracle", "inference-ablation", "efficiency-ablation"]:
        print(f"Computing {model} model utilities...")
        model_results = {}

        for dish_model_name, dish_gym_name in DISH_MAPPING.items():
            # Determine which costs are for g vs ¬g
            if dish_gym_name == 'Salad':
                costs_g = costs_salad
                costs_not_g = costs_salad_ol
            else:  # SaladOL
                costs_g = costs_salad_ol
                costs_not_g = costs_salad

            # Compute utilities based on model type
            if model == "full":
                utilities_1d = compute_full_model_utilities(
                    costs_g, costs_not_g, lambda_param
                )
            elif model == "oracle":
                utilities_1d = compute_oracle_model_utilities(costs_g)
            elif model == "inference-ablation":
                utilities_1d = compute_inference_ablation_utilities(
                    costs_g, costs_not_g
                )
            elif model == "efficiency-ablation":
                utilities_1d = compute_efficiency_ablation_utilities(
                    costs_g, costs_not_g, lambda_param
                )

            # Reshape to 2D grid
            utilities_2d = utilities_1d.reshape(n_rows, n_cols)
            model_results[dish_model_name] = utilities_2d

        all_results[model] = model_results

    return all_results


if __name__ == '__main__':
    # Example usage
    import json

    # Load design problem
    config_path = Path(__file__).parent.parent.parent.parent / 'stimuli' / 'overcooked_design' / 'pilot_configs' / 'design_config_01.json'
    with open(config_path) as f:
        problem = json.load(f)

    # Compute utilities for all models
    for model_name in ['full', 'oracle', 'inference-ablation', 'efficiency-ablation']:
        print(f"\n{'='*60}")
        print(f"Model: {model_name}")
        print(f"{'='*60}")

        utils = compute_model_utilities(
            model=model_name,
            design_problem=problem,
            lambda_param=0.294 * 0.7, # note -- the default parameter is the best-fit parameter but seems to be too big
            n_seeds=3,  # Small for testing
            max_timesteps=100,
            parallelize=True
        )

        print(f"\nUtilities for TomatoSalad:")
        print(utils['TomatoSalad'])
        print(f"\nUtilities for OnionSalad:")
        print(utils['OnionSalad'])

        # Get probabilities
        probs = get_placement_probabilities(utils['TomatoSalad'], beta=1.0)
        print(f"\nProbabilities for TomatoSalad (sum={probs.sum():.6f}):")
        print(probs)
