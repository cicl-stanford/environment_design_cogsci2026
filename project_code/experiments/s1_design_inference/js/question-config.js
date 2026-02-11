// Question configurations for all conditions
export const QUESTION_CONFIGS = {
  cooks: [
    {
      prompt: "How many cooks was this kitchen made for?",
      name: "intent_agents",
      slider_start: null,
      min_label: "<img src='assets/trial/one_cook.png' style='height: 60px;'>",
      max_label: "<img src='assets/trial/two_cooks.png' style='height: 60px;'>",
    }
  ],
  
  dish: [
    {
      prompt: "Which dish was this kitchen made for?",
      name: "intent_recipe",
      slider_start: null,
      min_label: "<img src='assets/trial/tomato_lettuce.png' style='height: 60px;'>",
      max_label: "<img src='assets/trial/onion_lettuce.png' style='height: 60px;'>",
    }
  ],
  
  cooks_effort: [
    {
      prompt: "How much time would it take for <strong>one cook</strong> to complete this trial?",
      name: "effort_one_cook",
      slider_start: null,
      min_label: "Not much time",
      max_label: "A lot of time",
    },
    {
      prompt: "How much time would it take for <strong>two cooks</strong> to complete this trial?",
      name: "effort_two_cooks",
      slider_start: null,
      min_label: "Not much time",
      max_label: "A lot of time",
    }
  ],
  
  dish_effort: [
    {
      prompt: "How much time would it take for a cook to make a <strong>tomato salad</strong>?",
      name: "effort_tomato",
      slider_start: null,
      min_label: "Not much time",
      max_label: "A lot of time",
    },
    {
      prompt: "How much time would it take for a cook to make an <strong>onion salad</strong>?",
      name: "effort_onion",
      slider_start: null,
      min_label: "Not much time",
      max_label: "A lot of time",
    }
  ]
};
