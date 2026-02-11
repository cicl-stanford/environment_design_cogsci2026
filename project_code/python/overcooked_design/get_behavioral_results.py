"""
Pull and preprocess behavioral data from OSF for overcooked_design study.

This script processes behavioral data for the overcooked_design pilot study, which includes:
- Practice cooking trials (3 per participant): Participants cook dishes to learn the environment
- Design trials (24 per participant): Participants place furniture to design efficient kitchens

Plugin documentation: https://unpkg.com/@anthropic/jspsych-overcooked/
"""

import os
import sys
import json
import pandas as pd
from pathlib import Path

# Add the project root to the Python path
try:
    project_root = Path(__file__).resolve().parents[3]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
except IndexError:
    raise RuntimeError("Could not find project root. Make sure the script is run from within the project structure.")

from project_code.python.utils.paths import DATA_DIR
from project_code.python.utils.osf_data_handler import OSFDataHandler

# OSF data loading configuration
# Pattern for overcooked_design: condition is 'overcooked_design' (underscore, not hyphen)
custom_pattern = (
    r'(?P<project>[^-]+)-'
    r'(?P<experiment>[^-]+)-'
    r'(?P<iteration_name>(?:[a-z]+-)*[a-z0-9]+)-'
    r'(?P<condition>[a-z_]+)-'
    r'(?P<gameID>[0-9]{4}-[a-f0-9\-]+)\.csv'
)

data_sources = [
    {
        'criteria': {
            'project': 'environment_design',
            'experiment': 'overcooked_design',
            'iteration_name': 'prolific-run-01132026',
        },
        'component': 'ywtf5'  # Pilot data component
    }
]

# Fetch raw data from all sources
print("Loading data from OSF...")
dfs = []
for source in data_sources:
    print(f"  Loading from component {source['component']}...")
    osf_handler = OSFDataHandler(source['component'], filename_pattern=custom_pattern)
    component_df = osf_handler.load_filtered_csvs(source['criteria'])
    dfs.append(component_df)
    print(f"  Found {len(component_df)} rows")

# Combine all raw data
df = pd.concat(dfs, ignore_index=True)
print(f"OSF data loading complete. Total rows: {len(df)}")


## Create session-level dataframe
# One row per participant session with game_id as primary key

session_rename_map = {
    'gameID': 'game_id',
    'prolificID': 'prolific_id',
    'condition': 'condition',
    'randomization': 'randomization',  # Randomization mode: blocked-by-dish, blocked-by-kitchen, fully-interleaved
    'iteration_name': 'iteration',
    'dev_mode': 'dev_mode',
    'project': 'project',
    'experiment': 'experiment',
    'startExperimentTS': 'start_experiment_ts',
    'endExperimentTS': 'end_experiment_ts',
    'comprehensionAttempts': 'comprehension_attempts',
    'width': 'browser_width',
    'height': 'browser_height',
    'browser': 'browser',
    'mobile': 'is_mobile_device',
    'design_trial_order': 'design_trial_order'  # Array of trial presentation order: [{uuid}_{dish}, ...]
}

session_order = [
    "game_id",
    "project", "experiment", "iteration", "dev_mode",
    "condition", "randomization", "prolific_id",
    "browser", "browser_width", "browser_height", "is_mobile_device",
    "start_experiment_ts", "end_experiment_ts", "experiment_duration_ms",
    "comprehension_attempts",
    "design_trial_order",
    "age", "gender", "race", "ethnicity",
    "judged_difficulty", "judged_effort", "input_device",
    "feedback", "technical_difficulties"
]

session_data = []
for game_id, group in df.groupby('gameID'):
    session_record = {}
    first_row = group.iloc[0]

    # Extract basic fields from first row
    basic_fields = ['gameID', 'condition', 'randomization', 'iteration_name', 'dev_mode', 'project', 'prolificID',
                   'experiment', 'comprehensionAttempts', 'width', 'height', 'browser', 'mobile', 'design_trial_order']
    for original_col, new_col in session_rename_map.items():
        if original_col in ['startExperimentTS', 'endExperimentTS']:
            continue  # Handle timestamps separately
        if original_col in basic_fields and original_col in group.columns:
            non_null_rows = group[~group[original_col].isna()]
            if len(non_null_rows) > 0:
                session_record[new_col] = non_null_rows.iloc[0][original_col]
            else:
                session_record[new_col] = first_row[original_col]

    # Extract demographics from survey response - expect exactly one survey per participant
    survey_rows = group[group.trial_type == 'survey']
    if len(survey_rows) != 1:
        raise ValueError(f"Expected exactly 1 survey trial for {game_id}, found {len(survey_rows)}")

    survey_response = survey_rows.iloc[0].response
    if pd.isna(survey_response):
        raise ValueError(f"Survey response is missing for {game_id}")

    try:
        demo_data = json.loads(survey_response)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse survey JSON for {game_id}: {e}")

    # Map demographics fields
    demo_mapping = {
        'participantYears': 'age',
        'participantGender': 'gender',
        'participantRace': 'race',
        'participantEthnicity': 'ethnicity',
        'participantComments': 'feedback',
        'TechnicalDifficultiesFreeResp': 'technical_difficulties',
        'participantEffort': 'judged_effort',
        'judgedDifficulty': 'judged_difficulty',
        'inputDevice': 'input_device'
    }
    for demo_field, session_field in demo_mapping.items():
        if demo_field in demo_data:
            session_record[session_field] = demo_data[demo_field]

    # Extract timestamps - expect exactly one of each per participant
    start_rows = group.dropna(subset=['startExperimentTS'])
    end_rows = group.dropna(subset=['endExperimentTS'])

    if len(start_rows) != 1:
        raise ValueError(f"Expected exactly 1 start timestamp for {game_id}, found {len(start_rows)}")
    if len(end_rows) != 1:
        raise ValueError(f"Expected exactly 1 end timestamp for {game_id}, found {len(end_rows)}")

    session_record['start_experiment_ts'] = start_rows.iloc[0]['startExperimentTS']
    session_record['end_experiment_ts'] = end_rows.iloc[0]['endExperimentTS']

    # Calculate experiment duration
    start_ts = session_record['start_experiment_ts']
    end_ts = session_record['end_experiment_ts']
    if pd.notna(start_ts) and pd.notna(end_ts):
        session_record['experiment_duration_ms'] = end_ts - start_ts

    # Convert design_trial_order to JSON string if it's an array/object
    if 'design_trial_order' in session_record:
        if pd.notna(session_record['design_trial_order']):
            if not isinstance(session_record['design_trial_order'], str):
                # Convert array/list to JSON string
                session_record['design_trial_order'] = json.dumps(session_record['design_trial_order'])
            # If it's already a string, leave it as is (might already be JSON)

    session_data.append(session_record)

# Create session dataframe with proper column ordering
session_df = pd.DataFrame(session_data)[session_order].reset_index(drop=True)

print(f"\nProcessed {len(session_df)} participants")


## Create cooking trial dataframe
# One row per cooking trial - practice trials where participants cook dishes to learn the environment

cooking_trials = df[df.trial_type == 'overcooked-cooking'].copy()

cooking_rename_map = {
    'trial_id': 'trial_id',
    'gameID': 'game_id',
    'trial_num': 'trial_num',
    'phase': 'phase',
    'kitchen': 'kitchen',
    'recipe': 'recipe',
    'timesteps': 'timesteps',
    'completed': 'completed',
    'undo_count': 'undo_count',
    'reset_index': 'reset_index',
    'rt': 'rt',
    'start_time_ms': 'start_time_ms',
    'end_time_ms': 'end_time_ms',
    'start_time_iso': 'start_time_iso',
    'end_time_iso': 'end_time_iso',
    'actions': 'actions',
    'final_snapshot': 'final_snapshot'
}

cooking_order = [
    "trial_id", "game_id", "trial_num", "phase", "dish", "kitchen",
    "timesteps", "completed", "undo_count", "reset_index", "rt",
    "start_time_ms", "end_time_ms", "start_time_iso", "end_time_iso",
    "actions", "final_snapshot"
]

cooking_data = []
for _, row in cooking_trials.iterrows():
    cooking_record = {}

    # Extract direct fields
    for original_col, new_col in cooking_rename_map.items():
        if original_col in row.index and pd.notna(row[original_col]):
            cooking_record[new_col] = row[original_col]

    # Map recipe to dish (TomatoSalad -> Salad, OnionSalad -> SaladOL)
    if 'recipe' in row.index and pd.notna(row['recipe']):
        recipe = row['recipe']
        if recipe == 'TomatoSalad':
            cooking_record['dish'] = 'Salad'
        elif recipe == 'OnionSalad':
            cooking_record['dish'] = 'SaladOL'
        else:
            cooking_record['dish'] = recipe  # Fallback to original

    # Convert JSON fields to strings
    for json_field in ['actions', 'final_snapshot']:
        if json_field in cooking_record and not isinstance(cooking_record[json_field], str):
            cooking_record[json_field] = json.dumps(cooking_record[json_field])

    cooking_data.append(cooking_record)

# Create cooking dataframe with proper column ordering
cooking_df = pd.DataFrame(cooking_data)
# Only keep columns that exist in the data
cooking_order_filtered = [col for col in cooking_order if col in cooking_df.columns]
cooking_df = cooking_df[cooking_order_filtered].reset_index(drop=True)

print(f"Processed {len(cooking_df)} cooking trials")


## Create design trial dataframe
# One row per design trial - main experimental data where participants design kitchens

design_trials = df[df.trial_type == 'overcooked-design'].copy()

design_rename_map = {
    'trial_id': 'trial_id',
    'gameID': 'game_id',
    'trial_num': 'trial_num',
    'block_num': 'block_num',
    'trial_num_in_block': 'trial_num_in_block',
    'config_filename': 'config_filename',
    'dish': 'dish',
    'floor_plan': 'floor_plan',
    'final_layout': 'final_layout',
    'furniture_placed': 'furniture_placed',
    'total_placed': 'total_placed',
    'placements': 'placements',
    'undo_count': 'undo_count',
    'redo_count': 'redo_count',
    'reset_count': 'reset_count',
    'rt': 'rt',
    'actions': 'actions',
    'design_space': 'design_space',
    'design_intent': 'design_intent'
}

design_order = [
    "trial_id", "game_id", "trial_num", "block_num", "trial_num_in_block",
    "config_filename", "dish", "floor_plan", "final_layout",
    "furniture_placed", "total_placed", "placements",
    "undo_count", "redo_count", "reset_count", "rt",
    "actions", "design_space", "design_intent"
]

design_data = []
for _, row in design_trials.iterrows():
    design_record = {}

    # Extract direct fields
    for original_col, new_col in design_rename_map.items():
        if original_col in row.index and pd.notna(row[original_col]):
            design_record[new_col] = row[original_col]

    # Convert JSON/object fields to strings
    for json_field in ['furniture_placed', 'placements', 'actions', 'design_space']:
        if json_field in design_record and not isinstance(design_record[json_field], str):
            design_record[json_field] = json.dumps(design_record[json_field])

    design_data.append(design_record)

# Create design dataframe with proper column ordering
design_df = pd.DataFrame(design_data)
# Only keep columns that exist in the data
design_order_filtered = [col for col in design_order if col in design_df.columns]
design_df = design_df[design_order_filtered].reset_index(drop=True)

print(f"Processed {len(design_df)} design trials")


## Validation and Summary Statistics

print(f"\n{'='*60}")
print(f"SUMMARY")
print(f"{'='*60}")
print(f"  Participants: {len(session_df)}")
print(f"  Cooking trials: {len(cooking_df)}")
print(f"  Design trials: {len(design_df)}")

# Verify trial counts per participant
cooking_counts = cooking_df.groupby('game_id').size()
design_counts = design_df.groupby('game_id').size()

print(f"\nCooking trials per participant:")
print(f"  Expected: 2")
print(f"  Mean: {cooking_counts.mean():.1f}")
print(f"  Min: {cooking_counts.min()}, Max: {cooking_counts.max()}")

print(f"\nDesign trials per participant:")
print(f"  Expected: 24")
print(f"  Mean: {design_counts.mean():.1f}")
print(f"  Min: {design_counts.min()}, Max: {design_counts.max()}")

# Check for anomalies
if not all(cooking_counts == 3):
    print("\n⚠️  WARNING: Some participants don't have exactly 3 cooking trials!")
    anomalies = cooking_counts[cooking_counts != 3]
    print(f"  Anomalous participants: {list(anomalies.index)}")

if not all(design_counts == 24):
    print("\n⚠️  WARNING: Some participants don't have exactly 24 design trials!")
    anomalies = design_counts[design_counts != 24]
    print(f"  Anomalous participants: {list(anomalies.index)}")


## Save outputs

output_dir = DATA_DIR / 'overcooked_design' / 'behavioral_results'
os.makedirs(output_dir, exist_ok=True)

session_file = output_dir / 'session_data.csv'
cooking_file = output_dir / 'cooking_data.csv'
design_file = output_dir / 'design_data.csv'

session_df.to_csv(session_file, index=False)
cooking_df.to_csv(cooking_file, index=False)
design_df.to_csv(design_file, index=False)

print(f"\n{'='*60}")
print(f"OUTPUT")
print(f"{'='*60}")
print(f"  Session data: {session_file}")
print(f"  Cooking data: {cooking_file}")
print(f"  Design data: {design_file}")
print(f"\n✓ Data processing complete!")
