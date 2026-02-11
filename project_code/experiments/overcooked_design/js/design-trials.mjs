import { settings } from "../config.mjs";
import { getJsPsych } from "./jspsych-singleton.mjs";

// Access plugin from global JsPsychOvercooked namespace
const { OvercookedDesignPlugin } = JsPsychOvercooked;

// Helper functions
function createDesignPreamble(condition) {
  const baseText = "Help the cook make this dish in as few steps as possible!";
  const reminder = condition === 'communicative'
    ? "<br><p style='font-size: 14px; margin-top: 0px; margin-bottom: 8px; line-height: 1.5;'>Remember: the cook does not know which dish to make</p>"
    : "";
  return baseText + reminder;
}

function renderDesignIntent(goal, imageWidth = 220) {
  const isTomato = goal === 'Salad';
  const highlightStyle = "border: 3px solid #4CAF50; padding: 4px; border-radius: 4px;";
  const normalStyle = "padding: 4px;";
  
  return `
    <div style="${isTomato ? highlightStyle : normalStyle}">
      <img src="assets/trials/intent_TomatoSalad.png" width="${imageWidth}">
      <p style="margin-top: 0px; margin-bottom: 0px;"><strong>Tomato Salad</strong></p>
    </div>
    <div style="${!isTomato ? highlightStyle : normalStyle}">
      <img src="assets/trials/intent_OnionSalad.png" width="${imageWidth}">
      <p style="margin-top: 0px; margin-bottom: 0px;"><strong>Onion Salad</strong></p>
    </div>
  `;
}

// Goal configurations
const GOALS = {
  Salad: {
    dish: "Salad",
    dish_name: "Tomato Salad",
    block_intro_intent: '<img src="assets/trials/intent_TomatoSalad.png" width="450"><p style="margin-top: 0px;">Tomato Salad</p>',
    getDesignIntent: renderDesignIntent,
    getPreamble: createDesignPreamble
  },
  SaladOL: {
    dish: "SaladOL",
    dish_name: "Onion Salad",
    block_intro_intent: '<img src="assets/trials/intent_OnionSalad.png" width="450"><p style="margin-top: 0px;">Onion Salad</p>',
    getDesignIntent: renderDesignIntent,
    getPreamble: createDesignPreamble
  }
};

/**
 * Helper function to create a single design trial
 */
function createDesignTrial(jsPsych, config, goal, trialNum, blockNum, trialNumInBlock) {
  const goalConfig = GOALS[goal];
  
  // Track trial order
  settings.session_data.design_trial_order.push(`${config.id}_${goalConfig.dish}`);
  
  return {
    type: OvercookedDesignPlugin,
    floor_plan: config.floor_plan,
    design_space: {
      furniture: [
        {
          ...config.furniture,
          count: 1,
          must_place_all: true
        }
      ]
    },
    design_intent: goalConfig.getDesignIntent(goal),
    preamble: goalConfig.getPreamble(settings.study_metadata.condition),
    dish: goalConfig.dish,
    validate_recipe_access: false,
    data: {
      trial_id: config.filename.replace('.json', ''),
      trial_num: trialNum,
      block_num: blockNum,
      trial_num_in_block: trialNumInBlock,
      phase: 'design',
      config_filename: config.filename,
    },
    on_start: (trial) => {
      jsPsych.progressBar.message = `Design Trial ${trialNum + 1} of 24`;
      jsPsych.progressBar.update();
    },
    on_finish: (data) => {
      // Log in dev mode
      if (settings.study_metadata.dev_mode) {
        console.log("Design trial complete:", data);
      }
    }
  };
}

/**
 * Generate design trial objects from loaded configs
 * Supports three randomization modes: blocked-by-dish, blocked-by-kitchen, fully-interleaved
 */
export function createDesignTrials(jsPsych, designConfigs) {
  const randomization = settings.study_metadata.randomization;
  const goals = ['Salad', 'SaladOL'];
  const totalDesignTrials = designConfigs.length * 2; // 12 configs × 2 dishes = 24
  const allTrials = [];
  
  // Initialize trial order tracking
  settings.session_data.design_trial_order = [];
  
  let designTrialNumber = 0; // Track design trial number (0-23)

  if (randomization === 'blocked-by-dish') {
    // Mode 1: 2 blocks by dish with introductions
    // Shuffle goal order randomly (client-side)
    const shuffledGoals = _.shuffle([...goals]);
    
    shuffledGoals.forEach((goal, blockIdx) => {
      const goalConfig = GOALS[goal];

      // Add block introduction trial
      allTrials.push({
        type: jsPsychHtmlButtonResponse,
        stimulus: `
          <p>In the following trials, your goal is to design kitchens to help cooks prepare an <strong>${goalConfig.dish_name}</strong>.</p>
          ${goalConfig.block_intro_intent}
          ${settings.study_metadata.condition === 'communicative'
            ? "<p>Remember: the cook <strong>does not</strong> know which dish they will have to make.</p>"
            : ""
          }
        `,
        choices: ['Start designing'],
        data: {
          phase: 'block_intro',
          goal: goal,
          block_num: blockIdx,
        },
        on_start: () => {
          jsPsych.progressBar.message = "Design Trials";
          jsPsych.progressBar.update();
        }
      });

      // Shuffle configs independently for this block
      const shuffledConfigs = _.shuffle([...designConfigs]);

      shuffledConfigs.forEach((config, configIdx) => {
        const trial = createDesignTrial(jsPsych, config, goal, designTrialNumber, blockIdx, configIdx);
        allTrials.push(trial);
        designTrialNumber++;
      });
    });
    
  } else if (randomization === 'blocked-by-kitchen') {
    // Mode 2: 12 blocks by kitchen layout, no introductions
    // Shuffle configs randomly
    const shuffledConfigs = _.shuffle([...designConfigs]);
    
    shuffledConfigs.forEach((config, blockIdx) => {
      // Shuffle dish order independently for this block
      const shuffledDishes = _.shuffle([...goals]);
      
      shuffledDishes.forEach((goal, dishIdx) => {
        const trial = createDesignTrial(jsPsych, config, goal, designTrialNumber, blockIdx, dishIdx);
        allTrials.push(trial);
        designTrialNumber++;
      });
    });
    
  } else if (randomization === 'fully-interleaved') {
    // Mode 3: No blocks, all 24 trials randomized together
    // Generate all 24 trials first
    const allDesignTrials = [];
    
    designConfigs.forEach((config) => {
      goals.forEach((goal) => {
        allDesignTrials.push({
          config,
          goal,
          blockNum: 0, // No blocks in this mode
          trialNumInBlock: 0 // Will be set after shuffling
        });
      });
    });
    
    // Shuffle all trials together randomly
    const shuffledTrials = _.shuffle(allDesignTrials);
    
    shuffledTrials.forEach((trialInfo, idx) => {
      const trial = createDesignTrial(
        jsPsych,
        trialInfo.config,
        trialInfo.goal,
        designTrialNumber,
        trialInfo.blockNum,
        idx
      );
      allTrials.push(trial);
      designTrialNumber++;
    });
    
  } else {
    throw new Error(`Unknown randomization mode: ${randomization}`);
  }

  if (settings.study_metadata.dev_mode) {
    console.log("Design trial order:", settings.session_data.design_trial_order);
  }

  return allTrials;
}
