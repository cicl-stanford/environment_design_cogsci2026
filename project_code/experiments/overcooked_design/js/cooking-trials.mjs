import { settings } from "../config.mjs";
import { getJsPsych } from "./jspsych-singleton.mjs";

// Access plugin from global JsPsychOvercooked namespace
const { OvercookedCookingPlugin } = JsPsychOvercooked;

// Helper functions
function createCookingPreamble(condition) {
  const baseText = "Make the correct dish in as few steps as possible!";
  const reminder = condition === 'communicative'
    ? "<br><p style='font-size: 14px; margin-top: 0px; margin-bottom: 8px; line-height: 1.5;'>Try making the correct dish on your first try!</p>"
    : "";
  return baseText + reminder;
}

function renderDishPair(condition, correctDish, imageWidth = 220) {
  const isTomato = correctDish === 'Salad';
  const highlightStyle = "border: 3px solid #4CAF50; padding: 4px; border-radius: 4px;";
  const normalStyle = "padding: 4px;";
  
  if (condition === 'communicative') {
    return `<img src="assets/trials/intent_TomatoSalad.png" width="${imageWidth}"><p style="margin-top: 0px; margin-bottom: 0px;"><strong>Tomato Salad</strong></p><img src="assets/trials/intent_OnionSalad.png" width="${imageWidth}"><p style="margin-top: 0px; margin-bottom: 0px;"><strong>Onion Salad</strong></p>`;
  } else {
    const tomatoStyle = isTomato ? highlightStyle : normalStyle;
    const onionStyle = !isTomato ? highlightStyle : normalStyle;
    return `
      <div style="${tomatoStyle}">
        <img src="assets/trials/intent_TomatoSalad.png" width="${imageWidth}">
        <p style="margin-top: 0px; margin-bottom: 0px;"><strong>Tomato Salad</strong></p>
      </div>
      <div style="${onionStyle}">
        <img src="assets/trials/intent_OnionSalad.png" width="${imageWidth}">
        <p style="margin-top: 0px; margin-bottom: 0px;"><strong>Onion Salad</strong></p>
      </div>
    `;
  }
}

// Hardcoded cooking trial metadata
const COOKING_TRIALS_METADATA = [
  {
    filename: "cooking_trial_01.txt",
    dish: "Salad",
    getPreamble: createCookingPreamble,
    getRecipeIntent: (condition) => renderDishPair(condition, 'Salad')
  },
  {
    filename: "cooking_trial_02.txt",
    dish: "SaladOL",
    getPreamble: createCookingPreamble,
    getRecipeIntent: (condition) => renderDishPair(condition, 'SaladOL')
  },
  {
    filename: "cooking_trial_03.txt",
    // For communicative: use incorrectDish to make first submission always wrong
    // For base: randomly assign either Tomato or Onion
    getDish: (condition) => {
      if (condition === 'communicative') {
        return 'incorrectDish';
      } else {
        return Math.random() < 0.5 ? 'Salad' : 'SaladOL';
      }
    },
    getPreamble: createCookingPreamble,
    getRecipeIntent: (condition, dish) => renderDishPair(condition, dish)
  }
];

/**
 * Generate cooking trial objects
 * These trials familiarize participants with making both dishes
 * Uses separate kitchen layouts for each trial
 */
export function createCookingTrials(jsPsych, kitchenLayouts) {
  const numCookingTrials = COOKING_TRIALS_METADATA.length;
  const condition = settings.study_metadata.condition;

  return COOKING_TRIALS_METADATA.map((trialMeta, idx) => {
    // Determine dish (static for trials 1-2, dynamic for trial 3)
    const dish = trialMeta.getDish ? trialMeta.getDish(condition) : trialMeta.dish;

    // Get condition-dependent preamble and recipe_intent
    const preamble = trialMeta.getPreamble(condition);
    const recipe_intent = trialMeta.getRecipeIntent(condition, dish);

    return {
      type: OvercookedCookingPlugin,
      kitchen: kitchenLayouts[idx],
      dish: dish,
      preamble: preamble,
      recipe_intent: recipe_intent,
      allow_undo: true,
      allow_reset: true,
      data: {
        trial_id: trialMeta.filename.replace('.txt', ''),
        trial_num: idx,
        phase: 'cooking',
      },
      on_start: (trial) => {
        jsPsych.progressBar.message = `Cooking Trial ${idx + 1} of ${numCookingTrials}`;
        jsPsych.progressBar.update();
      },
      on_finish: (data) => {
        // Progress bar will be updated by setup.js based on total trials
        // Log in dev mode
        if (settings.study_metadata.dev_mode) {
          console.log("Cooking trial complete:", data);
        }
      }
    };
  });
}
