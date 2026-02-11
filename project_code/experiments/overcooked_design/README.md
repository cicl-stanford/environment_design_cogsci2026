# Overcooked Design Experiment

**Study**: `overcooked_design`
**Project**: `environment_design`

## Overview

This experiment investigates how people design physical environments to support specific goals. Participants arrange furniture in kitchen layouts to facilitate efficient dish preparation.

## Quick Start

### Running Locally

1. Start a local server in this directory:
   ```bash
   python -m http.server 8000
   ```

2. Open in browser:
   ```
   http://localhost:8000/index.html
   ```

3. For development, the experiment runs in `dev_mode` by default (set in `config.mjs`)

### URL Parameters

- `PROLIFIC_PID`: Prolific participant ID
- `STUDY_ID`: Prolific study ID
- `SESSION_ID`: Prolific session ID

## File Structure

```
overcooked_design/
├── index.html                    # Entry point
├── config.mjs                    # Study configuration
├── README.md                     # This file
│
├── assets/
│   ├── experiment_assets.json   # Assets to preload
│   ├── instructions/            # Instruction images/gifs
│   └── trials/
│       ├── cooking_trials/      # Kitchen layouts for cooking practice
│       └── design_trials/       # Floor plans for design task
│
└── js/
    ├── setup.js                 # Main experiment logic
    ├── jspsych-singleton.mjs    # jsPsych instance
    ├── loading-sequence.mjs     # Landing, consent, preload
    ├── instructions.mjs         # All instruction sequences
    ├── cooking-trials.mjs       # Cooking trial generation
    ├── design-trials.mjs        # Design trial generation
    └── exit-sequence.mjs        # Survey and data upload
```

## Trial Flow

1. **Loading Sequence**: Landing, consent, browser check, preload
2. **Instructions Part 1**: Overcooked environment dynamics
3. **Cooking Trials** (2): Familiarization with making both dishes
4. **Instructions Part 2**: Design task explanation
5. **Design Trials** (N): Main experimental trials
6. **Exit Sequence**: Survey and data upload

## Plugins

- **overcooked-cooking**: Interactive cooking task
- **overcooked-design**: Furniture placement task
- Loaded via unpkg (no build required)

## Data & Links

- **OSF Project**: https://osf.io/xqvs5
- **OSF Data Component**: https://osf.io/ywtf5
