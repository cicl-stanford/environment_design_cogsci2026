export function UUID() {
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

// Get condition from URL parameter
function getConditionFromUrl() {
  const conditionParam = getUrlParameter('condition');
  const conditionMap = {
    '0': 'base',
    '1': 'communicative'
  };

  // Require condition to be provided
  if (!conditionParam) {
    throw new Error('condition parameter is required. Must be 0 (base) or 1 (communicative).');
  }

  if (!conditionMap[conditionParam]) {
    throw new Error(`Invalid condition parameter: ${conditionParam}. Must be 0 (base) or 1 (communicative).`);
  }

  return conditionMap[conditionParam];
}

const condition = getConditionFromUrl();

export let settings = {
  study_metadata: {
    project: "environment_design",
    experiment: "overcooked_design",
    datapipe_experiment_id: "kdS9yzF1qPLh",
    randomization: "fully-interleaved", // blocked-by-dish, blocked-by-kitchen, or fully-interleaved
    iteration_name: 'post_data_collection',
    dev_mode: false, // Set to false for production
    condition: condition,
    completion_code: 'XXX',
    preregistration_id: 'h6fqe',
  },
  session_data: {
    gameID: gameID,
    startExperimentTS: undefined,
    endExperimentTS: undefined,
    comprehensionAttempts: 0,
    design_trial_order: [],
  },
  experiment_params: {
    time_estimate: condition === 'base' ? 12 : 15, // in minutes
  },
  prolific_info: {
    prolificID: getUrlParameter('PROLIFIC_PID'),
    prolificStudyID: getUrlParameter('STUDY_ID'),
    prolificSessionID: getUrlParameter('SESSION_ID'),
  }
};
