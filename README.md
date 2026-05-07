# From chopped to cooked: Design and inference in physical environments

<!-- **Justin Yang, Lionel Wong, Judith E. Fan, Tobias Gerstenberg** -->

<!-- Presented at the 48th Annual Meeting of the Cognitive Science Society (2026). -->

[Link to paper](https://github.com/cicl-stanford/environment_design_cogsci2026/blob/main/fromchopped_0202.pdf) · [Project website](https://cicl-stanford.github.io/environment_design_cogsci2026/)

```
@inproceedings{yang2026environmentdesign,
  title = {From chopped to cooked: Design and inference in physical environments},
  booktitle = {Proceedings of the 48th {Annual} {Conference} of the {Cognitive} {Science} {Society}},
  author = {Yang, Justin and Wong, Lionel and Fan, Judith E. and Gerstenberg, Tobias},
  year = {2026},
}
```

**Contents:**

* [Overview](#overview)
* [Repository structure](#repository-structure)
* [Set up](#set-up)
* [Experiments](#experiments)
* [Empirical analyses](#empirical-analyses)
* [External resources](#external-resources)
* [CRediT author statement](#credit-author-statement)

## Overview

<p align="center" style="font-size: smaller">
  <img width="85%" src="https://github.com/cicl-stanford/environment_design_cogsci2026/blob/main/figures/%E2%80%8Eoverview_fig.png"></img><br/>
</p>

Physical spaces are often designed to support specific uses. But how do people create such environments, and how do users infer their intended function? We propose that design and inference about design are complementary processes, grounded in a capacity to mentally simulate goal-directed actions. We tested this using "Overcooked"-style kitchens where participants either judged what a kitchen was designed for (Study 1) or designed kitchens for cooks with varying goals and beliefs (Study 2). In Study 1, participants inferred that kitchens were designed for tasks the layout made easier to complete, consistent with the prediction of a simulation-based computational model. In Study 2, participants made designs that helped cooks efficiently complete their task, adjusting their choices when cooks faced uncertainty about which task to perform. Together, these findings point towards a study of design as a cognitive activity grounded in the same mechanisms that support planning and social reasoning.

## Repository structure

```
├── project_code/
│   ├── R/                          # Statistical analysis
│   ├── python/                     # Data processing and model pipelines
│   ├── bash/                       # bash and slurm scripts
│   └── experiments/                # jsPsych web experiments
├── data/                           # Behavioral and model data
├── stimuli/                        # Experimental stimuli
├── figures/                        # Generated figures
├── gym-cooking/                    # Simulation framework (submodule)
└── environment.yml                 # Conda environment
```

See the individual READMEs for more details:
- [`data/data-readme.md`](data/data-readme.md) — description of behavioral and model data files
- [`stimuli/stimuli-readme.md`](stimuli/stimuli-readme.md) — description of experimental stimuli
- [`project_code/python/python-readme.md`](project_code/python/python-readme.md) — data preprocessing and simulation pipelines
- [`project_code/R/R-readme.md`](project_code/R/R-readme.md) — statistical analyses and figure generation
- [`project_code/bash/bash-readme.md`](project_code/bash/bash-readme.md) — bash and slurm scripts

## Set up

The project uses Python 3 and R. We recommend using conda to set up the analysis environment:

```bash
conda env create -f environment.yml
conda activate design-inference
```

## Experiments

Pre-registrations for each study can be found on the Open Science Framework:
- [Inference Study — effort conditions](https://osf.io/2mjyu/overview?view_only=d18a9fef257646149190cafe061d6a4a)
- [Inference Study — inference conditions](https://osf.io/ek67j/overview?view_only=14c0a367853e43879d1b5115c2c541b0)
- [Design Study](https://osf.io/h6fqe/overview?view_only=f1eba5b80c254ab78515f765988d23a6)

### Inference Study

In Study 1, participants viewed "Overcooked"-style kitchen layouts and judged what the kitchen was designed for (e.g., which dish, or how many cooks).

<p align="center" style="font-size: smaller">
  <img width="75%" src="https://github.com/cicl-stanford/environment_design_cogsci2026/blob/main/figures/inference_study_screenshot.png"></img><br/>
  Example inference trial.
</p>

Demos for each condition:
- [Cooks inference](https://cicl-stanford.github.io/environment_design_cogsci2026/s1_design_inference/?condition=0)
- [Dish inference](https://cicl-stanford.github.io/environment_design_cogsci2026/s1_design_inference/?condition=1)
- [Cooks effort](https://cicl-stanford.github.io/environment_design_cogsci2026/s1_design_inference/?condition=2)
- [Dish effort](https://cicl-stanford.github.io/environment_design_cogsci2026/s1_design_inference/?condition=3)

Code for this experiment can be found in `project_code/experiments/s1_design_inference`.

### Design Study

In Study 2, participants designed kitchens for cooks with varying goals and beliefs by placing furniture in the environment.

<p align="center" style="font-size: smaller">
  <img width="75%" src="https://github.com/cicl-stanford/environment_design_cogsci2026/blob/main/figures/design_study_cooks.gif"></img><br/>
  Example cooking trial (task familiarization).
</p>

<p align="center" style="font-size: smaller">
  <img width="75%" src="https://github.com/cicl-stanford/environment_design_cogsci2026/blob/main/figures/design_study_design.gif"></img><br/>
  Example design trial.
</p>

Demos for each condition:
- [Cook knows which dish to make](https://cicl-stanford.github.io/environment_design_cogsci2026/overcooked_design/index.html?condition=0)
- [Cook does not know which dish to make](https://cicl-stanford.github.io/environment_design_cogsci2026/overcooked_design/index.html?condition=1)

Code for this experiment can be found in `project_code/experiments/overcooked_design`.

## Empirical analyses

All paper figures, tables, and statistics are generated by a single R Markdown file. Pre-computed data files are included so you can knit without running simulations.

**Step 1:** Download the [brms model cache](https://osf.io/download/5vcyk/) (~4.5 GB) from OSF and unzip it into `data/overcooked_design/model_cache/`. If you skip this step, the Rmd will attempt to refit the models from scratch, which takes several hours.

**Step 2:** Knit the analysis notebook:

```bash
cd project_code/R
Rscript -e "rmarkdown::render('analysis_cogsci2026.Rmd')"
```

For information about reproducing behavioral data preprocessing and simulation model runs, see [`project_code/python/python-readme.md`](project_code/python/python-readme.md).

For details on the statistical analyses, see [`project_code/R/R-readme.md`](project_code/R/R-readme.md).

## External resources

- **OSF project:** https://osf.io/xqvs5/overview
- **gym-cooking framework:** https://github.com/cicl-stanford/gym-cooking

## CRediT author statement

*What is a [CRediT author statement](https://www.elsevier.com/authors/policies-and-guidelines/credit-author-statement)?*


| Term                       | Definition                                                                                                                                                                                                    | Justin Yang | Lio Wong | Judith Fan | Tobias Gerstenberg |
|----------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------|----------|------------|--------------------|
| Conceptualization          | Ideas; formulation or evolution of overarching research goals and aims                                                                                                                                        | x           | x        | x          | x                  |
| Methodology                | Development or design of methodology; creation of models                                                                                                                                                      | x           | x        | x          | x                  |
| Software                   | Programming, software development; designing computer programs; implementation of the computer code and supporting algorithms; testing of existing code components                                            | x           |          |            |                    |
| Validation                 | Verification, whether as a part of the activity or separate, of the overall replication/ reproducibility of results/experiments and other research outputs                                                    | x           |          |            |                    |
| Formal analysis            | Application of statistical, mathematical, computational, or other formal techniques to analyze or synthesize study data                                                                                       | x           |          |            |                    |
| Investigation              | Conducting a research and investigation process, specifically performing the experiments, or data/evidence collection                                                                                         | x           |          |            |                    |
| Resources                  | Provision of study materials, reagents, materials, patients, laboratory samples, animals, instrumentation, computing resources, or other analysis tools                                                       |             |          |            | x                  |
| Data Curation              | Management activities to annotate (produce metadata), scrub data and maintain research data (including software code, where it is necessary for interpreting the data itself) for initial use and later reuse | x           |          |            |                    |
| Writing - Original Draft   | Preparation, creation and/or presentation of the published work, specifically writing the initial draft (including substantive translation)                                                                   | x           |          |            |                    |
| Writing - Review & Editing | Preparation, creation and/or presentation of the published work by those from the original research group, specifically critical review, commentary or revision – including pre-or postpublication stages     | x           | x        | x          | x                  |
| Visualization              | Preparation, creation and/or presentation of the published work, specifically visualization/ data presentation                                                                                                | x           |          |            |                    |
| Supervision                | Oversight and leadership responsibility for the research activity planning and execution, including mentorship external to the core team                                                                      |             | x        | x          | x                  |
| Project administration     | Management and coordination responsibility for the research activity planning and execution                                                                                                                   | x           |          | x          | x                  |
| Funding acquisition        | Acquisition of the financial support for the project leading to this publication                                                                                                                              |             |          |            | x                  |
