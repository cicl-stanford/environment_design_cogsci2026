import { settings } from "../config.mjs";
let jsPsych = null;

export async function getJsPsych() {
  if (!jsPsych) {

    if (settings.study_metadata.dev_mode) {
      console.log("Condition:", settings.study_metadata.condition);
      console.log("Randomization mode:", settings.study_metadata.randomization);
    }

    settings.session_data.startExperimentTS = Date.now();
    jsPsych = initJsPsych({
      on_trial_finish: (data) => {
        if (settings.study_metadata.dev_mode) {
          console.log("trial data", data);
        }
      },
      show_progress_bar: true,
      // auto_update_progress_bar: false,
      message_progress_bar: 'Instructions'
    });

    jsPsych.data.addProperties({gameID: settings.session_data.gameID});
  }
  return jsPsych;
}
