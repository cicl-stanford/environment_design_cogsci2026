# Stimuli

Relevant stimuli for behavioral experiments, organized by study.

## s1_design_inference/

### Kitchen Layouts

**txt/**: Text representations of 36 kitchen layouts (trial_01.txt through trial_36.txt) used as input for gym-cooking simulations. Each file encodes a 7x7 grid using ASCII characters representing different objects and surfaces.

Layout encoding:
- `-`: Counter space
- `/`: Cutting board
- `T`: Tomato dispenser
- `L`: Lettuce dispenser
- `O`: Onion dispenser
- `p`: Plate dispenser
- `*`: Delivery station
- Space: Open floor

Layouts are hand-crafted to embody specific design intentions, with systematic variation in the number of cutting boards (1-2) and interior counters (4, 6, or 9). Trials 01-18 are designed for cooks conditions, trials 19-36 for dish conditions.

**layouts/**: PNG images of kitchen layouts rendered for experimental display. Organized by number of agents (`agents=1/` with 36 images, `agents=2/` with 18 images).

**trials_metadata.csv**: Characteristics of each kitchen layout including trial ID, intention target (cooks or dish), number of cutting boards, and number of counters.

## overcooked_design/

**configs/**: 12 JSON design configuration files for the furniture placement task. Each config specifies a floor plan (ASCII kitchen layout), furniture piece (grid and name), and metadata. Configs are named by UUID matching the experiment trial files.
