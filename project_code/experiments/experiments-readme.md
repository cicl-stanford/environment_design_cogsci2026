# Experiments

Online behavioral experiments built with jsPsych, served via GitHub Pages.

## s1_design_inference/

Participants view kitchen layouts and make judgments about design intent or task difficulty using slider scales. Four between-subjects conditions implemented via URL parameters:

- Condition 0 (cooks): Slider judging how many cooks the kitchen was designed for
- Condition 1 (dish): Slider judging which dish the kitchen was designed for
- Condition 2 (cooks_effort): Two sliders estimating time for one vs two cooks
- Condition 3 (dish_effort): Two sliders estimating time for tomato vs onion salad

```bash
cd project_code/experiments/s1_design_inference
python3 -m http.server 8000
# http://localhost:8000?condition=0&dev_mode=true
```

## overcooked_design/

Participants place furniture in kitchen layouts to facilitate efficient dish preparation. Includes cooking familiarization trials followed by design trials.

See [overcooked_design/README.md](overcooked_design/README.md) for detailed documentation.

```bash
cd project_code/experiments/overcooked_design
python3 -m http.server 8000
# http://localhost:8000/index.html
```

## Deployment

Experiments are deployed via GitHub Pages using the workflow in `.github/workflows/static.yml`. The workflow serves the `project_code/experiments/` directory.
