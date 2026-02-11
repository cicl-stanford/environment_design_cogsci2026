import { settings } from "../config.mjs";
import { getJsPsych } from "./jspsych-singleton.mjs";

const jsPsych = getJsPsych();

const preSurveyMessage = {
  type: jsPsychHtmlButtonResponse,
  stimulus: () => {
    return `<p>You've completed the experiment!\
      </br>On the next page, you'll be shown a brief set of questions about how the experiment went.\
      </br>Once you submit your answers, your data will be recorded.</p>`;
  },
  choices: ["Continue"],
  margin_vertical: "20px",
};

const exitSurvey = {
  type: jsPsychSurvey,
  survey_json: {
    showQuestionNumbers: false,
    elements: [
      {
        type: "dropdown",
        name: "participantGender",
        title: "What is your gender?",
        choices: ["Male", "Female", "Non-binary", "Other"],
        isRequired: true,
      },
      {
        type: "text",
        name: "participantYears",
        title: "How many years old are you?",
        placeholder: "18",
        isRequired: true,
      },
      {
        type: "dropdown",
        name: "participantRace",
        title: "What is your race?",
        choices: [
          "White",
          "Black/African American",
          "American Indian/Alaska Native",
          "Asian",
          "Native Hawaiian/Pacific Islander",
          "Multiracial/Mixed",
          "Other",
        ],
        isRequired: true,
      },
      {
        type: "dropdown",
        name: "participantEthnicity",
        title: "What is your ethnicity?",
        choices: ["Hispanic", "Non-Hispanic"],
        isRequired: true,
      },
      {
        type: "dropdown",
        name: "inputDevice",
        title:
          "Which of the following devices did you use to complete this study?",
        choices: ["Mouse", "Trackpad", "Touch Screen", "Stylus", "Other"],
        isRequired: true,
      },
      {
        type: "rating",
        name: "judgedDifficulty",
        title: "How difficult did you find this study?",
        minRateDescription: "Very Easy",
        maxRateDescription: "Very Hard",
        rateValues: [1, 2, 3, 4, 5],
        isRequired: true,
      },
      {
        type: "rating",
        name: "participantEffort",
        title:
          "How much effort did you put into the game? Your response will not effect your final compensation.",
        minRateDescription: "Low Effort",
        maxRateDescription: "High Effort",
        rateValues: [1, 2, 3, 4, 5],
        isRequired: true,
      },
      {
        type: "text",
        name: "participantComments",
        title:
          "What factors influenced how you decided to respond? Do you have any other comments or feedback to share with us about your experience?",
        placeholder: "I had a lot of fun!",
        isRequired: false,
        size: 100,
      },
      {
        type: "text",
        name: "TechnicalDifficultiesFreeResp",
        title:
          "If you encountered any technical difficulties, please briefly describe the issue.",
        placeholder: "I did not encounter any technical difficulities.",
        isRequired: false,
        size: 100,
      },
    ],
  },
  on_finish: function () {
    settings.session_data.endExperimentTS = Date.now();
    jsPsych.data.get().push({...settings.study_metadata, ...settings.session_data, ...settings.prolific_info});
  }
};

const saveData = {
  type: jsPsychPipe,
  action: "save",
  experiment_id: settings.study_metadata.datapipe_experiment_id,
  filename: `${settings.study_metadata.project}-${settings.study_metadata.experiment}-${settings.study_metadata.iteration_name}-${settings.study_metadata.condition}-${settings.session_data.gameID}.csv`,
  data_string: () => jsPsych.data.get().csv(),
};

const goodbye = {
  type: jsPsychHtmlButtonResponse,
  stimulus: `<p>Thank you for participating in our study!</p>
             <p>Your responses have been recorded. Click the button below to finish the study.</p>`,
  choices: ["Finish"],
  margin_vertical: "20px",
  on_finish: () => {
    window.onbeforeunload = null;
    document.onfullscreenchange = null;
    const completion_url = `https://app.prolific.co/submissions/complete?cc=${settings.study_metadata.completion_code}`;
    window.open(completion_url, '_self');
  },
};

export const exitSurveySequence = [
  preSurveyMessage,
  exitSurvey,
  saveData,
  goodbye,
];
