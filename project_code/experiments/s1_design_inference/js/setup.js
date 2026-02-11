import { loadingSequence } from "./loading-sequence.mjs";
import { instructionSequence } from "./instructions.mjs";
import { exitSurveySequence } from "./exit-sequence.mjs";
import { getJsPsych } from "./jspsych-singleton.mjs";
import { settings, getIntentionTarget } from "../config.mjs";
import { QUESTION_CONFIGS } from "./question-config.js";

// Load trials metadata and experiment assets
let trialsMetadataJson = [];
let experimentAssetsJson = [];

async function loadTrialsMetadata() {
  const response = await fetch('assets/trials_metadata.json');
  trialsMetadataJson = await response.json();
}

async function loadExperimentAssets() {
  const response = await fetch('assets/experiment_assets.json');
  experimentAssetsJson = await response.json();
}

export async function setupGame() {
  const jsPsych = getJsPsych();

  // Load metadata and assets
  await Promise.all([
    loadTrialsMetadata(),
    loadExperimentAssets()
  ]);

  // Combine static assets with trial stimuli
  const experiment_assets = [
    ...experimentAssetsJson,
    ...trialsMetadataJson.map(trial => `assets/stims/${trial.trial_id}.png`)
  ];

  // Select trials based on intention target using JSON metadata
  const condition = settings.study_metadata.condition;
  const intentionTarget = getIntentionTarget(condition);
  const relevantTrials = trialsMetadataJson.filter(trial => trial.trial_type === intentionTarget);
  const selected_stims = relevantTrials.map(trial => `assets/stims/${trial.trial_id}.png`);
  // const selected_stims = [ -- use this to get revised screenshots
  //   'assets/scratch/instructions_base_cook.png',
  //   'assets/scratch/instructions_base_dish.png'
  // ]
  
  // Get questions for current condition
  const questions = QUESTION_CONFIGS[condition];

  const slider_trials = _.map(_.shuffle(selected_stims), (stim, i) => {
    // Extract trial_id from stim path (e.g., "assets/stims/trial_01.png" -> "trial_01")
    const trial_id = stim.match(/assets\/stims\/(.+)\.png$/)[1];
    // const trial_id = null; -- need this for revised screenshots
    
    return {
      type: jsPsychSurveySlider,
      preamble: `<img src="${stim}" style="height: 450px;">`,
      questions: questions,
      require_movement: true,
      slider_width: 800,
      post_trial_gap: 500,
      data: {
        trial_id: trial_id,
        trial_num: i
      },
      on_start: () => {
        jsPsych.progressBar.message = `Kitchen ${i + 1} of ${selected_stims.length}`;
        jsPsych.progressBar.update();
      },
      on_finish: () => {
        jsPsych.progressBar.progress = Math.min(jsPsych.progressBar.progress + 1 / selected_stims.length, 1);
      }
    };
  });

  let trials = [];
  trials.push(...loadingSequence(experiment_assets));
  trials.push(...instructionSequence);
  trials.push(...slider_trials);
  trials.push(...exitSurveySequence);

  jsPsych.run(trials);
}
