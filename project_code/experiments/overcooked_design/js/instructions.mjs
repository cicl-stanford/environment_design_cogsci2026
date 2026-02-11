import { settings } from "../config.mjs";

// ============================================================================
// PART 1: OVERCOOKED ENVIRONMENT DYNAMICS
// ============================================================================

/**
 * Create environment instructions sequence
 * @param {object} jsPsych - jsPsych instance
 * @returns {array} Timeline array for environment instructions
 */
export function createInstructionsPart1Sequence(jsPsych) {
  // Helper function to get data from last trial
  const getFromLastTrial = (trialType, selector) => {
    const record = jsPsych
      .data
      .get()
      .filter({ trial_type: trialType })
      .last(1)        // grab the last one
      .values()[0];   // pull out the raw object
    return record[selector];
  };

  const environmentInstructions = {
    type: jsPsychInstructions,
    pages: [
      // Page 1: Overview
      `<p>In this study, you will be designing <strong>kitchen layouts</strong>.</p>
       <p>Your task is to arrange furniture in kitchens to help cooks prepare dishes efficiently.</p>
       <p>Before you start designing, you'll first get familiar with how kitchens work by cooking some dishes yourself!</p>`,

      // Page 2: Kitchen basics and demo
      `<p>In each kitchen, cooks try to take as few steps as possible to prepare a salad.</p>
       <p>In this video, a cook is making a salad using tomato and lettuce.</p>
       <img src="assets/instructions/2_dish_demo.gif" height="300">`,

      // Page 3: Recipes
      `<p>Cooks complete an order by first <strong>chopping</strong> the necessary ingredients, then <strong>combining</strong> them on a plate, and finally <strong>delivering</strong> it to the serving station.</p>
       <p>There are two possible salads that cooks can make: either a <strong>tomato</strong> salad, or an <strong>onion</strong> salad.</p>
       <img src="assets/instructions/3_two_recipes.png" height="300">`,

      // Page 4: Food dispensers
      `<p>Salad ingredients are stored in <strong>food dispensers</strong>. To grab a tomato, for example, a cook walks up to the tomato dispenser and interacts with it to grab one.</p>
       <img src="assets/instructions/4_food_dispenser_demo.gif" height="300">`,

      // Page 5: Chopping
      `<p>Cooks chop ingredients at the <strong>chopping board</strong>. To use it, they must first move in front of the board and interact with it while holding an ingredient.</p>
       <p>Chopping boards cannot be moved around.</p>
       <img src="assets/instructions/5_chopping_demo.gif" height="300">`,

      // Page 6: Combining and plating
      `<p>After the ingredients are chopped, they can be put on a plate and combined into a salad. Ingredients may be combined and plated in any order.</p>
       <p>For example, in the left video, the cook first combines the ingredients together before putting it on the plate.</p>
       <p>In the right video, the cook first plates the chopped lettuce before adding in the tomato.</p>
       <img src="assets/instructions/6_plating_order1.gif" height="300">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
       <img src="assets/instructions/6_plating_order2.gif" height="300">`,

      // Page 7: Delivery
      `<p>After the dish has been plated, it is now ready for delivery! To finish the order, the cook must bring it to the delivery station so it can be sent out to the customer.</p>
      <p><strong>Important:</strong> If the cook delivers the wrong dish, they will lose all their progress and have to start over from the beginning!</p>
       <img src="assets/instructions/7_dish_delivery_demo.gif" height="300">`,

      // Page 9: Condition-specific page
      settings.study_metadata.condition === 'communicative'
        ? `<p>In this study, the cook <strong>does not know</strong> which dish they need to make when they enter the kitchen.</p>
           <p>The cook knows that the environment was designed for one of the two dishes, but they don't know which one.</p>
           <p>To deliver the right order in few steps, the cook will have to guess which dish to start with based on what they see in the kitchen.</p>`
        : `<p>In this study, when the cook enters the kitchen, they will <strong> always know</strong> which dish they are supposed to make.</p>`,

      // Page 10: Comprehension check
      `<p>On the next screen, you will be asked a few questions to make sure everything is clear.</p>
      <p>You'll need to answer correctly to move on, but can review the instructions and try again if needed.</p>`
    ],
    show_clickable_nav: true,
    allow_keys: true,
    allow_backward: true,
  };

  // Comprehension check content for environment dynamics
  const ENVIRONMENT_COMPREHENSION = {
    fewSteps: {
      prompt: "True or False: Cooks try to take as few steps as possible to complete an order.",
      correctAnswer: "True, cooks try to take as few steps as possible to complete an order.",
      wrongAnswer: "False, cooks do not try to minimize the number of steps they take to complete an order."
    },
    platingOrder: {
      prompt: "True or False: The vegetables must be combined prior to being plated.",
      correctAnswer: "False, ingredients may be combined and plated in any order.",
      wrongAnswer: "True, the vegetables must be combined prior to being plated."
    },
    wrongDishReset: {
      prompt: "True or False: If the cook delivers the wrong dish, the kitchen resets and they must start over.",
      correctAnswer: "True, if the cook delivers the wrong dish, the kitchen resets and they must start over.",
      wrongAnswer: "False, the cook can deliver any dish without consequence."
    },
    cookKnowledge: {
      prompt: "True or False: The cook will know which dish they need to make.",
      correctAnswer: settings.study_metadata.condition === 'base'
        ? "True, the cook will know which dish they need to make."
        : "False, the cook will not know which dish they need to make.",
      wrongAnswer: settings.study_metadata.condition === 'base'
        ? "False, the cook will not know which dish they need to make."
        : "True, the cook will know which dish they need to make."
    }
  };

  // Validate environment comprehension responses
  const validateEnvironmentComprehension = (responses) => {
    return (
      responses.few_steps === ENVIRONMENT_COMPREHENSION.fewSteps.correctAnswer &&
      responses.plating_order === ENVIRONMENT_COMPREHENSION.platingOrder.correctAnswer &&
      responses.wrong_dish_reset === ENVIRONMENT_COMPREHENSION.wrongDishReset.correctAnswer &&
      responses.cook_knowledge === ENVIRONMENT_COMPREHENSION.cookKnowledge.correctAnswer
    );
  };

  const environmentComprehensionCheck = {
    type: jsPsychSurveyMultiChoice,
    preamble: "<p><b>Comprehension Check</b></p>",
    questions: [
      {
        prompt: ENVIRONMENT_COMPREHENSION.fewSteps.prompt,
        name: 'few_steps',
        options: [
          ENVIRONMENT_COMPREHENSION.fewSteps.correctAnswer,
          ENVIRONMENT_COMPREHENSION.fewSteps.wrongAnswer
        ],
        required: true,
      },
      {
        prompt: ENVIRONMENT_COMPREHENSION.platingOrder.prompt,
        name: 'plating_order',
        options: [
          ENVIRONMENT_COMPREHENSION.platingOrder.wrongAnswer,
          ENVIRONMENT_COMPREHENSION.platingOrder.correctAnswer
        ],
        required: true,
      },
      {
        prompt: ENVIRONMENT_COMPREHENSION.wrongDishReset.prompt,
        name: 'wrong_dish_reset',
        options: [
          ENVIRONMENT_COMPREHENSION.wrongDishReset.correctAnswer,
          ENVIRONMENT_COMPREHENSION.wrongDishReset.wrongAnswer
        ],
        required: true,
      },
      {
        prompt: ENVIRONMENT_COMPREHENSION.cookKnowledge.prompt,
        name: 'cook_knowledge',
        options: ENVIRONMENT_COMPREHENSION.cookKnowledge.correctAnswer.startsWith("True")
          ? [
              ENVIRONMENT_COMPREHENSION.cookKnowledge.correctAnswer,
              ENVIRONMENT_COMPREHENSION.cookKnowledge.wrongAnswer
            ]
          : [
              ENVIRONMENT_COMPREHENSION.cookKnowledge.wrongAnswer,
              ENVIRONMENT_COMPREHENSION.cookKnowledge.correctAnswer
            ],
        required: true,
      },
    ],
  };

  const environmentComprehensionFailedTrial = {
    timeline: [
      {
        type: jsPsychHtmlButtonResponse,
        stimulus: `<p>Unfortunately, you did not answer all the questions correctly.</p> \
                   <p>Please review the instructions and try again.</p>`,
        choices: ["Try Again"],
        margin_vertical: "20px"
      }
    ],
    conditional_function: function() {
      const responses = getFromLastTrial("survey-multi-choice", "response");
      return !validateEnvironmentComprehension(responses);
    }
  };

  const environmentComprehensionLoop = {
    timeline: [
      environmentInstructions,
      environmentComprehensionCheck,
      environmentComprehensionFailedTrial
    ],
    loop_function: (data) => {
      const responses = data['trials'][1]['response'];
      if (validateEnvironmentComprehension(responses)) {
        return false; // All correct, exit loop
      } else {
        settings.session_data.comprehensionAttempts += 1;
        return true; // Try again
      }
    }
  };

  const transitionToCooking = {
    type: jsPsychHtmlButtonResponse,
    stimulus: `
      <p>Now you will control the cook to make some salads yourself. Try to make the correct dish in as few steps as possible!</p>
      ${settings.study_metadata.condition === 'communicative'
        ? "<p>You won't be told which dish to make. Regardless, you should try to make the correct dish on your first attempt.</p>"
        : ''
      }
      <br>
      <p><b>Controls</b></p>
      <p>Use the arrow keys to move and interact with objects.</p>
      <p>For example, to grab an ingredient, stand next to the ingredient dispenser and press the arrow key pointing toward it to grab one.</p>
      <p>If at any point you get stuck, you can click "undo" to go back to the previous step. You can also click "reset" to start over from the beginning of your last attempt.</p>
      <p>The trial will automatically end when you have completed the correct dish.</p>
    `,
    choices: ['Start'],
  };

  return [
    environmentComprehensionLoop,
    transitionToCooking
  ];
}

// ============================================================================
// PART 2: DESIGN TASK INSTRUCTIONS
// ============================================================================

/**
 * Create design instructions sequence
 * @param {object} jsPsych - jsPsych instance
 * @returns {array} Timeline array for design instructions
 */
export function createInstructionsPart2Sequence(jsPsych) {
  const designInstructions = {
    type: jsPsychInstructions,
    pages: [
      // Page 1: Transition
      `<p><b>Nice work!</b> Now you understand how cooks prepare dishes in these kitchens.</p>
       <p>In the next part, you'll be <strong>designing</strong> kitchens to help cooks work efficiently.</p>`,

      // Page 2: Design goal
      `<p>You will be asked to design a kitchen to help a cook make either an <strong>onion salad</strong> or a <strong>tomato salad</strong> in as few steps as possible.</p>
      <img src="assets/instructions/3_two_recipes.png" height="400">`,

      // Page 3: How to design
      `<p>To design a kitchen, you can drag furniture from the inventory panel (on the right) into the kitchen.</p>
      <p>Once placed, you are free to move it around as needed. You can also drag it back to the inventory to remove it.</p>
      <p>You must place the furniture down before you can submit your design.</p>
      <img src="assets/instructions/8_furniture_placement_${settings.study_metadata.condition}.gif" height="300">`,

      // Page 4: Ready
      `<p>Once you're satisfied with your design, click <strong>"Submit Design"</strong>.</p>
      <p><b>That's it!</b> You are now ready to start designing the kitchens.</p>`,
    ],
    show_clickable_nav: true,
    allow_keys: true,
    allow_backward: true,
    on_start: () => {
      jsPsych.progressBar.message = "Instructions";
      jsPsych.progressBar.update();
    },
  };

  return [designInstructions];
}
