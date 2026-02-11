import { loadingSequence } from "./loading-sequence.mjs";
import { createInstructionsPart1Sequence, createInstructionsPart2Sequence } from "./instructions.mjs";
import { createCookingTrials } from "./cooking-trials.mjs";
import { createDesignTrials } from "./design-trials.mjs";
import { exitSurveySequence } from "./exit-sequence.mjs";
import { getJsPsych } from "./jspsych-singleton.mjs";
import { settings } from "../config.mjs";

let experimentAssetsJson = [];

async function loadExperimentAssets() {
  const response = await fetch('assets/experiment_assets.json');
  experimentAssetsJson = await response.json();
}

/**
 * Load the cooking kitchen layouts
 */
async function loadCookingKitchens() {
  const layout1 = await fetch('assets/trials/cooking_trials/cooking_trial_01.txt');
  const layout2 = await fetch('assets/trials/cooking_trials/cooking_trial_02.txt');
  const layout3 = await fetch('assets/trials/cooking_trials/cooking_trial_03.txt');
  return [
    await layout1.text(),
    await layout2.text(),
    await layout3.text()
  ];
}

/**
 * Load all design configuration JSON files
 */
async function loadDesignConfigs() {
  const configFiles = [
    '6be479f8-4a3f-4d97-8f06-0f301b0acd64.json',
    '74b431e8-e8ca-48fd-b5b4-ab6f32563faf.json',
    '908ba92f-7e3f-40cf-a293-86847bd7f04f.json',
    '923da982-5016-4456-980f-fe08463be1e4.json',
    '94e306f0-ad75-49ba-b2f1-553a5ce7c9c5.json',
    '9869c018-45e4-4d69-80fb-dc3e7ac8cb03.json',
    '9ea49cb3-212e-452f-908a-09b81601fe45.json',
    'a3f0e9a9-0cec-4adb-855a-238beeba7bf9.json',
    'b69ccfaa-7ae4-4bf8-ac1f-a0a9d5fcb40f.json',
    'ccd95ed1-36b4-46f6-a2fc-fd3f110cda80.json',
    'e5abe513-7271-4d97-8f41-c67d5dc744c7.json',
    'e9fc4a2f-efaf-4341-b11b-bf9fbb625dc5.json'
  ];

  const loadPromises = configFiles.map(async (filename) => {
    const response = await fetch(`assets/trials/design_trials/${filename}`);
    const config = await response.json();
    return {
      ...config,
      filename: filename
    };
  });

  return await Promise.all(loadPromises);
}

export async function setupExperiment() {
  const jsPsych = await getJsPsych();

  // Load experiment assets
  await loadExperimentAssets();

  // Load trials
  const cookingKitchens = await loadCookingKitchens();
  const designConfigs = await loadDesignConfigs();

  // Create trial sequences
  const instructionsPart1Sequence = createInstructionsPart1Sequence(jsPsych);
  const cookingTrials = createCookingTrials(jsPsych, cookingKitchens);
  const instructionsPart2Sequence = createInstructionsPart2Sequence(jsPsych);
  const designTrials = createDesignTrials(jsPsych, designConfigs);

  // Build complete timeline
  let timeline = [];

  // 1. Loading
  timeline.push(...loadingSequence(experimentAssetsJson));

  // 2. Instructions Part 1 (environment dynamics)
  timeline.push(...instructionsPart1Sequence);

  // 3. Cooking trials
  timeline.push(...cookingTrials);

  // 4. Instructions Part 2 (design task)
  timeline.push(...instructionsPart2Sequence);

  // 5. Design trials
  timeline.push(...designTrials);

  // 6. Exit
  timeline.push(...exitSurveySequence);

  // Run the experiment
  jsPsych.run(timeline);
}
