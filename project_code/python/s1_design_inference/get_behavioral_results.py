"""
Pull and preprocess behavioral data from OSF for s1_design_inference study.
Handles both inference conditions (cooks, dish) and effort conditions (cooks_effort, dish_effort).
"""

import os
import sys
import json
import uuid
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
# Pattern breakdown:
# - iteration_name: either single word (dev) OR multi-part like (prolific-run-8jnza)
# - condition: can contain underscores (dish_effort, cooks_effort) but no hyphens
# - gameID: starts with 4 digits, then hyphenated UUID
# Key: condition cannot contain hyphens, so we use [^-] to stop iteration_name from being too greedy
custom_pattern = r'(?P<project>[^-]+)-(?P<experiment>[^-]+)-(?P<iteration_name>(?:[a-z]+-)*[a-z0-9]+)-(?P<condition>[a-z_]+)-(?P<gameID>[0-9]{4}-[a-f0-9\-]+)\.csv'

data_sources = [
    # inference conditions
    {
        'criteria': {
            'project': 'environment_design',
            'experiment': 's1_design_inference',
            'iteration_name': 'prolific-run-8jnza',
        },
        'component': 'ykeqp'
    },
    # effort conditions
    {
        'criteria': {
            'project': 'environment_design',
            'experiment': 's1_design_inference',
            'iteration_name': 'prolific-run-2mjyu'
        },
        'component': '8fjh9'
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
    print(f"Found {len(component_df)} rows")

# Combine all raw data
df = pd.concat(dfs, ignore_index=True)
print(f"OSF data loading complete. Total rows: {len(df)}")


## Create session-level dataframe
# One row per participant session with game_id as primary key

session_rename_map = {
    'gameID': 'game_id',
    'prolificID': 'prolific_id',
    'condition': 'condition',
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
    'mobile': 'is_mobile_device'
}

session_order = [
    "game_id",
    "project", "experiment", "iteration", "dev_mode", "condition", "prolific_id",
    "browser", "browser_width", "browser_height", "is_mobile_device",
    "start_experiment_ts", "end_experiment_ts", "experiment_duration_ms",
    "comprehension_attempts",
    "age", "gender", "race", "ethnicity",
    "judged_difficulty", "judged_effort", "input_device",
    "feedback", "technical_difficulties"
]

session_data = []
for game_id, group in df.groupby('gameID'):
    session_record = {}
    first_row = group.iloc[0]

    # Extract basic fields from first row
    basic_fields = ['gameID', 'condition', 'iteration_name', 'dev_mode', 'project', 'prolificID',
                   'experiment', 'comprehensionAttempts', 'width', 'height', 'browser', 'mobile']
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

    session_data.append(session_record)

# Create session dataframe with proper column ordering
session_df = pd.DataFrame(session_data)[session_order].reset_index(drop=True)

# Print condition counts
condition_counts = session_df.condition.value_counts()
print(f"Participants by condition: {dict(condition_counts)}")


## Create trial-level dataframe
# One row per slider response (inference conditions: 1 per trial, effort conditions: 2 per trial)

def process_trial_responses(row, condition):
    """
    Process trial responses into individual rows.
    For inference conditions: 1 row per trial
    For effort conditions: 2 rows per trial
    
    Returns list of response dictionaries.
    """
    try:
        response_data = json.loads(row.response)
        questions = json.loads(row.questions)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse slider JSON for {row.gameID}: {e}")
    
    responses = []
    # Generate trial_id once per trial (shared across multiple responses for effort conditions)
    trial_id = str(uuid.uuid4())
    
    if condition == 'cooks':
        question = questions[0]
        responses.append({
            'trial_id': trial_id,
            'response_id': str(uuid.uuid4()),
            'game_id': row.gameID,
            'kitchen_layout_id': row.trial_id,
            'trial_order': int(row.trial_num) if pd.notna(row.trial_num) else None,
            'condition': condition,
            'question_type': 'intent_agents',
            'prompt': question.get('prompt'),
            'slider_min_value': 'one cook',
            'slider_max_value': 'two cooks',
            'slider_response': response_data.get(question.get('name')),
            'rt': row.rt if pd.notna(row.rt) else None
        })
    elif condition == 'dish':
        question = questions[0]
        responses.append({
            'trial_id': trial_id,
            'response_id': str(uuid.uuid4()),
            'game_id': row.gameID,
            'kitchen_layout_id': row.trial_id,
            'trial_order': int(row.trial_num) if pd.notna(row.trial_num) else None,
            'condition': condition,
            'question_type': 'intent_recipe',
            'prompt': question.get('prompt'),
            'slider_min_value': 'tomato',
            'slider_max_value': 'onion',
            'slider_response': response_data.get(question.get('name')),
            'rt': row.rt if pd.notna(row.rt) else None
        })
    elif condition == 'cooks_effort':
        # Two questions per trial - same trial_id for both
        for i, question in enumerate(questions):
            question_name = question.get('name')
            responses.append({
                'trial_id': trial_id,
                'response_id': str(uuid.uuid4()),
                'game_id': row.gameID,
                'kitchen_layout_id': row.trial_id,
                'trial_order': int(row.trial_num) if pd.notna(row.trial_num) else None,
                'condition': condition,
                'question_type': question_name,  # 'effort_one_cook' or 'effort_two_cooks'
                'prompt': question.get('prompt'),
                'slider_min_value': 'not much time',
                'slider_max_value': 'a lot of time',
                'slider_response': response_data.get(question_name),
                'rt': row.rt if pd.notna(row.rt) else None
            })
    elif condition == 'dish_effort':
        # Two questions per trial - same trial_id for both
        for i, question in enumerate(questions):
            question_name = question.get('name')
            responses.append({
                'trial_id': trial_id,
                'response_id': str(uuid.uuid4()),
                'game_id': row.gameID,
                'kitchen_layout_id': row.trial_id,
                'trial_order': int(row.trial_num) if pd.notna(row.trial_num) else None,
                'condition': condition,
                'question_type': question_name,  # 'effort_tomato' or 'effort_onion'
                'prompt': question.get('prompt'),
                'slider_min_value': 'not much time',
                'slider_max_value': 'a lot of time',
                'slider_response': response_data.get(question_name),
                'rt': row.rt if pd.notna(row.rt) else None
            })
    else:
        raise ValueError(f"Unknown condition: {condition}")
    
    return responses


slider_trials = df[df.trial_type == 'survey-slider'].copy()

trial_data = []
for _, row in slider_trials.iterrows():
    # Get condition from session data using game_id as key
    participant_condition = session_df[session_df.game_id == row.gameID]['condition'].iloc[0]
    
    # Process trial into response rows
    responses = process_trial_responses(row, participant_condition)
    trial_data.extend(responses)

trial_df = pd.DataFrame(trial_data)


## Save data
output_dir = DATA_DIR / 's1_design_inference' / 'behavioral_results'
os.makedirs(output_dir, exist_ok=True)

session_file = os.path.join(output_dir, 'session_data.csv')
trial_file = os.path.join(output_dir, 'trial_data.csv')

session_df.to_csv(session_file, index=False)
trial_df.to_csv(trial_file, index=False)

print(f"\nFinished processing {len(session_df)} participants and {len(trial_df.trial_id.unique())} trials!")
print("\nResponses by condition:")
response_counts = trial_df.groupby('condition').size()
print(response_counts)
print("\nSample session data:")
print(session_df.sample(1).iloc[0])
print("\nSample trial data:")
print(trial_df.sample(1).iloc[0])
print(f"\nData saved to {output_dir}")
