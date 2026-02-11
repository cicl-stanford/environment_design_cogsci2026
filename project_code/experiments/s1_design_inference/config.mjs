function UUID() {
  const baseName =
    Math.floor(Math.random() * 10) +
    "" +
    Math.floor(Math.random() * 10) +
    "" +
    Math.floor(Math.random() * 10) +
    "" +
    Math.floor(Math.random() * 10);
  const template = "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx";
  const id =
    baseName +
    "-" +
    template.replace(/[xy]/g, function (c) {
      let r = (Math.random() * 16) | 0,
        v = c == "x" ? r : (r & 0x3) | 0x8;
      return v.toString(16);
    });
  return id;
}

const gameID = UUID();

// Parse URL parameters
function getUrlParameter(name) {
  const urlParams = new URLSearchParams(window.location.search);
  return urlParams.get(name);
}

// Get condition from URL parameter with strict validation
// 0=cooks, 1=dish, 2=cooks_effort, 3=dish_effort
function getConditionFromUrl() {
  const conditionParam = getUrlParameter('condition');
  const conditionMap = {
    '0': 'cooks',
    '1': 'dish',
    '2': 'cooks_effort',
    '3': 'dish_effort'
  };
  
  if (!conditionMap[conditionParam]) {
    throw new Error(`Invalid condition parameter: ${conditionParam}. Must be 0, 1, 2, or 3.`);
  }
  
  return conditionMap[conditionParam];
}

// Check if condition is effort-based
export function isEffortCondition(condition) {
  return condition === 'cooks_effort' || condition === 'dish_effort';
}

// Get the intention target (cooks vs dish)
export function getIntentionTarget(condition) {
  if (condition === 'cooks' || condition === 'cooks_effort') {
    return 'cooks';
  }
  if (condition === 'dish' || condition === 'dish_effort') {
    return 'dish';
  }
  throw new Error(`Unknown condition: ${condition}`);
}

// Get condition-specific metadata
function getConditionMetadata(condition) {
  const isEffort = isEffortCondition(condition);

  if (isEffort) {
    return {
      datapipe_experiment_id: 'NDZDjZy3wZzX',
      iteration_name: 'post_data_collection',
      preregistration_id: '2mjyu',
      dev_mode: false,
      completion_code: 'CXFFOOQK'
    };
  } else {
    return {
      datapipe_experiment_id: 'e7h3xs0D9Mhj',
      iteration_name: 'post_data_collection', 
      preregistration_id: '8jnza',
      dev_mode: false,
      completion_code: 'CXFFOOQK'
    };
  }
}

const condition = getConditionFromUrl();
const conditionMetadata = getConditionMetadata(condition);

export let settings = {
  study_metadata: {
    project: "environment_design",
    experiment: "s1_design_inference",
    datapipe_experiment_id: conditionMetadata.datapipe_experiment_id,
    iteration_name: conditionMetadata.iteration_name,
    dev_mode: conditionMetadata.dev_mode,
    condition: condition,
    completion_code: conditionMetadata.completion_code,
    preregistration_id: conditionMetadata.preregistration_id,
  },
  session_data: {
    gameID: gameID,
    startExperimentTS: undefined,
    endExperimentTS: undefined,
    comprehensionAttempts: 0,
  },
  experiment_params: {
    time_estimate: 12, // in minutes
  },
  prolific_info: {
    prolificID: getUrlParameter('PROLIFIC_PID'),
    prolificStudyID: getUrlParameter('STUDY_ID'),
    prolificSessionID: getUrlParameter('SESSION_ID'),
  }
};
