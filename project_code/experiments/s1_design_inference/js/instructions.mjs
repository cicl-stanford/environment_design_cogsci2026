import { settings, isEffortCondition, getIntentionTarget } from "../config.mjs";
import { getJsPsych } from "./jspsych-singleton.mjs";

let jsPsych = getJsPsych();

const getFromLastTrial = (trialType, selector) => {
  const record = jsPsych
    .data
    .get()
    .filter({ trial_type: trialType })
    .last(1)        // grab the last one
    .values()[0];   // pull out the raw object
  return record[selector];
}

// Define all comprehension check content once
const COMPREHENSION_CONTENT = {
  base: {
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
    counterPlacement: {
      prompt: "True or False: It is possible for ingredients to be placed on empty countertops.",
      correctAnswer: "True, it is possible for ingredients to be placed on empty counters.",
      wrongAnswer: "False, ingredients can only be placed on counters with other tools or ingredients on them."
    }
  },
  cooks: {
    inference: {
      agentDesign: {
        prompt: "True or False: Some kitchens are designed for one cook, while others are designed for two cooks.",
        correctAnswer: "True, some kitchens are designed for one cook, while others are designed for two cooks.",
        wrongAnswer: "False, all kitchens are designed to work equally well for any number of cooks."
      }
    },
    cooksPassing: {
      prompt: "True or False: Cooks can directly hand ingredients and plates to each other without placing them down first.",
      correctAnswer: "False, cooks can only pass ingredients and plates to each other by placing them down on counters, cutting boards, and food dispensers.",
      wrongAnswer: "True, cooks can directly hand ingredients and plates to each other without placing them down first."
    }
  },
  dish: {
    inference: {
      recipeDesign: {
        prompt: "True or False: Some kitchens are designed for one dish, while others are designed for the other dish.",
        correctAnswer: "True, some kitchens are designed for one dish, while others are designed for the other dish.",
        wrongAnswer: "False, all kitchens are equally designed for both dishes."
      }
    }
  }
};

// Helper to create question object from content
// Ensures True option always comes before False option
const createQuestion = (name, content) => {
  const trueOption = content.correctAnswer.startsWith('True') ? content.correctAnswer : content.wrongAnswer;
  const falseOption = content.correctAnswer.startsWith('False') ? content.correctAnswer : content.wrongAnswer;
  
  return {
    prompt: content.prompt,
    name: name,
    options: [trueOption, falseOption],
    required: true
  };
};

// Get instruction pages with inline conditional logic
const getInstructionPages = () => {
  const condition = settings.study_metadata.condition;
  const intentionTarget = getIntentionTarget(condition);
  const isEffort = isEffortCondition(condition);
  
  return [
    // Page 1
    `<p>In this study, you will be evaluating different <strong>kitchen layouts</strong>.</p>
     <p>Your task is to ${isEffort ? "estimate how long it would take to make a dish in each kitchen" : "judge how each kitchen was designed to be used"}.</p>`,

    // Page 2: Overview and demo
    `<p>In each kitchen, cooks try to take as few steps as possible to prepare a salad.</p>
    <p>In the figure below, a cook is making a salad using a tomato and a lettuce.</p>
    <img src="assets/instructions/${intentionTarget === "cooks" ? "2_cooks_demo.gif" : "2_dish_demo.gif"}" height="300">`,

    // Page 3: Recipe
    `<p>Cooks complete an order by first chopping the necessary ingredients, then combining them on a plate, and finally delivering it to the serving station.</p>
    ${intentionTarget === "dish" ? `
    <p>There are two possible salads that the cooks make: either a <strong>tomato</strong> salad, or an <strong>onion</strong> salad.</p>
    <img src="assets/instructions/3_two_recipes.png" height="300">` : `<img src="assets/instructions/3_one_recipe.png" height="300">`}`,

    // Page 4: Stations
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
    <img src="assets/instructions/${intentionTarget === "cooks" ? "7_cooks_delivery_demo.gif" : "7_dish_delivery_demo.gif"}" height="300">`,

    // Page 8a: Condition-specific content
    `${intentionTarget === "cooks" ? `
    <p>Cooks can either work alone or collaborate with another cook to make the salad. Some kitchens are designed for one cook to work alone. Others are designed for two cooks.</p>
    <p>Cooks can use counter spaces to pass ingredients and plates to each other over. This includes being able to use normal counters, as well as cutting boards and food dispensers as well!</p>
    <img src="assets/instructions/8_cooks_passing.gif" height="300">` : `
    <p>Some kitchens are designed to make an onion salad. Others are designed to make a tomato salad.</p>
    <img src="assets/instructions/3_two_recipes.png" height="300">`}`,

    // Page 8b: Cooks collision
    ...(intentionTarget === "cooks" ? [`
    <p>Cooks need to be careful when working together — two cooks cannot occupy the same space and can block each other from getting where they want!</p>
    <img src="assets/instructions/8_cooks_collision.gif" height="300">`] : []),

    // Page 9: Examples
    `<p>To get a better understanding of how this works, take a look at how ${intentionTarget === "cooks" ? "one or two cooks make a salad." : "these cooks make an onion and a tomato salad"}</p>
    <img src="assets/instructions/${intentionTarget === "cooks" ? "9_cooks_collaboration1.gif" : "9_dish_recipe1.gif"}" height="300">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
    <img src="assets/instructions/${intentionTarget === "cooks" ? "9_cooks_collaboration2.gif" : "9_dish_recipe2.gif"}" height="300">`,

    // Page 10: Task description
    `<p>Your task is to look at a set of kitchen layouts and answer ${
      condition === "cooks" ? "how many cooks it was designed for." :
      condition === "dish" ? "which dish it was designed for." :
      condition === "cooks_effort" ? "how much time one or two cooks would take to complete the task." :
      "how much time it would take for one cook to make each dish."
    }</p>
    ${intentionTarget === "cooks" ?
      `<p>If there is one cook, they will always start on the blue square. If there are two cooks, the second cook will start on the green square.</p>` :
      `<p>The blue square shows the starting location of the cook.</p>`}
    <img src="assets/instructions/${
      condition === "cooks" ? "10_demo_trial_cook.png" :
      condition === "dish" ? "10_demo_trial_dish.png" :
      condition === "cooks_effort" ? "10_demo_trial_cook_effort.png" :
      "10_demo_trial_dish_effort.png"
    }" height="400">`,

    // Page 11: Comprehension check
    `<p>On the next screen, you will be asked a few questions to make sure everything is clear.</p>
    <p>You\'ll need to answer correctly to move on, but can review the instructions and try again if needed.</p>`
  ];
};

// Export instructions as a function that gets called after condition is set
export const getInstructions = () => {
  return {
    type: jsPsychInstructions,
    pages: getInstructionPages(),
    show_clickable_nav: true,
    allow_backward: true,
    allow_keys: true,
  };
};

const getComprehensionQuestions = () => {
  const condition = settings.study_metadata.condition;
  const intentionTarget = getIntentionTarget(condition);
  const isEffort = isEffortCondition(condition);
  
  const baseQuestions = [
    createQuestion('fewSteps', COMPREHENSION_CONTENT.base.fewSteps),
    createQuestion('platingOrder', COMPREHENSION_CONTENT.base.platingOrder),
    createQuestion('counterPlacement', COMPREHENSION_CONTENT.base.counterPlacement)
  ];
  
  if (intentionTarget === "cooks") {
    return [
      ...baseQuestions,
      ...(isEffort ? [] : [createQuestion('agentDesign', COMPREHENSION_CONTENT.cooks.inference.agentDesign)]),
      createQuestion('cooksPassing', COMPREHENSION_CONTENT.cooks.cooksPassing)
    ];
  } else if (intentionTarget === "dish") {
    return [
      ...baseQuestions,
      ...(isEffort ? [] : [createQuestion('recipeDesign', COMPREHENSION_CONTENT.dish.inference.recipeDesign)])
    ];
  } else {
    throw new Error(`Unknown intention target: ${intentionTarget}`);
  }
};

// Validate comprehension check responses
const validateComprehensionResponses = (responses) => {
  const condition = settings.study_metadata.condition;
  const intentionTarget = getIntentionTarget(condition);
  const isEffort = isEffortCondition(condition);
  
  // Check base questions
  const baseCorrect = (
    responses.fewSteps === COMPREHENSION_CONTENT.base.fewSteps.correctAnswer &&
    responses.platingOrder === COMPREHENSION_CONTENT.base.platingOrder.correctAnswer &&
    responses.counterPlacement === COMPREHENSION_CONTENT.base.counterPlacement.correctAnswer
  );
  
  if (intentionTarget === "cooks") {
    const cooksCorrect = (
      responses.cooksPassing === COMPREHENSION_CONTENT.cooks.cooksPassing.correctAnswer &&
      (isEffort || responses.agentDesign === COMPREHENSION_CONTENT.cooks.inference.agentDesign.correctAnswer)
    );
    return baseCorrect && cooksCorrect;
  } else if (intentionTarget === "dish") {
    return baseCorrect && (
      isEffort || responses.recipeDesign === COMPREHENSION_CONTENT.dish.inference.recipeDesign.correctAnswer
    );
  } else {
    throw new Error(`Unknown intention target: ${intentionTarget}`);
  }
};

const comprehensionFailedTrial = {
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
    return !validateComprehensionResponses(responses);
  }
};

const instructionsLoop = {
  timeline: [
    getInstructions(), 
    {
      type: jsPsychSurveyMultiChoice,
      preamble: "<strong>Comprehension Check</strong>",
      questions: getComprehensionQuestions()
    },
    comprehensionFailedTrial
  ],
  loop_function: (data) => {
    const responses = data['trials'][1]['response'];
    if (validateComprehensionResponses(responses)) {
      return false; // All correct, exit loop
    } else {
      settings.session_data.comprehensionAttempts += 1;
      return true; // Try again
    }
  }
};

const instructionsConclusion = {
  type: jsPsychHtmlButtonResponse,
  stimulus: `
    <p>Congrats! You've learned everything you need to know.</p> \
    <p>In total, you will be making judgments for 18 kitchens.</p> \
    <p>Please click the continue button to get started. Thank you for participating!</p>`,
  choices: ["Continue"],
  margin_vertical: "20px"
}

export const instructionSequence = [instructionsLoop, instructionsConclusion];
