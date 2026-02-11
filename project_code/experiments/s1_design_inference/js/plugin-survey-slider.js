var jsPsychSurveySlider = (function (jspsych) {
  "use strict";

  var version = "2.0.0";

  const info = {
    name: "survey-slider",
    version,
    parameters: {
      /** Questions that will be displayed to the participant. */
      questions: {
        type: jspsych.ParameterType.COMPLEX,
        array: true,
        pretty_name: "Questions",
        default: undefined,
        nested: {
          stimulus: {
            type: jspsych.ParameterType.HTML_STRING,
            pretty_name: "Stimulus",
            default: "",
          },
          prompt: {
            type: jspsych.ParameterType.STRING,
            pretty_name: "Prompt",
            default: undefined,
            description:
              "Content to be displayed below the stimulus and above the slider",
          },
          labels: {
            type: jspsych.ParameterType.STRING,
            pretty_name: "Labels",
            default: [],
            array: true,
            description: "Labels of the sliders.",
          },
          ticks: {
            type: jspsych.ParameterType.HTML_STRING,
            pretty_name: "Ticks",
            default: [],
            array: true,
            description: "Ticks of the sliders.",
          },
          name: {
            type: jspsych.ParameterType.STRING,
            pretty_name: "Question Name",
            default: "",
            description:
              "Controls the name of data values associated with this question",
          },
          min: {
            type: jspsych.ParameterType.INT,
            pretty_name: "Min slider",
            default: 0,
            description: "Sets the minimum value of the slider.",
          },
          max: {
            type: jspsych.ParameterType.INT,
            pretty_name: "Max slider",
            default: 100,
            description: "Sets the maximum value of the slider",
          },
          slider_start: {
            type: jspsych.ParameterType.INT,
            pretty_name: "Slider starting value",
            default: 50,
            description: "Sets the starting value of the slider",
          },
          step: {
            type: jspsych.ParameterType.INT,
            pretty_name: "Step",
            default: 1,
            description: "Sets the step of the slider",
          },
          min_label: {
            type: jspsych.ParameterType.HTML_STRING,
            default: "0",
            description: "HTML to display under the left side of the slider",
          },
          max_label: {
            type: jspsych.ParameterType.HTML_STRING,
            default: "100",
            description: "HTML to display under the right side of the slider",
          },
        },
      },
      randomize_question_order: {
        type: jspsych.ParameterType.BOOL,
        pretty_name: "Randomize Question Order",
        default: false,
        description: "If true, the order of the questions will be randomized",
      },
      preamble: {
        type: jspsych.ParameterType.HTML_STRING,
        pretty_name: "Preamble",
        default: null,
        description: "String to display at top/left of the page.",
      },
      button_label: {
        type: jspsych.ParameterType.STRING,
        pretty_name: "Button label",
        default: "Continue",
        description: "Label of the button.",
      },
      autocomplete: {
        type: jspsych.ParameterType.BOOL,
        pretty_name: "Allow autocomplete",
        default: false,
        description: "Enable browser auto-complete for the form.",
      },
      require_movement: {
        type: jspsych.ParameterType.BOOL,
        pretty_name: "Require movement",
        default: false,
        description:
          "If true, participant must move each slider before continuing.",
      },
      slider_width: {
        type: jspsych.ParameterType.INT,
        pretty_name: "Slider width",
        default: 500,
        description: "Width of the slider in pixels.",
      },
    },
    data: {
      rt: { type: jspsych.ParameterType.INT },
      response: { type: jspsych.ParameterType.STRING },
      question_order: { type: jspsych.ParameterType.STRING },
      question_info: { type: jspsych.ParameterType.STRING },
      preamble: { type: jspsych.ParameterType.STRING },
    },
  };

  class SurveySliderPlugin {
    constructor(jsPsych) {
      this.jsPsych = jsPsych;
    }
    static {
      this.info = info;
    }

    trial(display_element, trial) {
      // ensure every question has a .value
      for (let q of trial.questions) {
        if (typeof q.value === "undefined") {
          q.value = "";
        }
      }

      const half_thumb_width = 7.5;
      let html = "";

      // wrapper + container
      html +=
        '<div id="jspsych-html-slider-response-wrapper" style="margin:100px 0;">';
      html +=
        '<div class="jspsych-html-slider-response-container" style="position:relative; margin:0 auto 3em auto; ';
      html +=
        trial.slider_width !== null
          ? `width:${trial.slider_width}px;`
          : "width:auto;";
      html += '">';

      // open form
      html += trial.autocomplete
        ? '<form id="jspsych-survey-slider-form">'
        : '<form id="jspsych-survey-slider-form" autocomplete="off">';

      // ── LEFT / RIGHT FLEX LAYOUT ─────────────────────────
      if (trial.preamble !== null) {
        // flex container: preamble on left, questions on right
        // html += '<div class="jspsych-survey-slider-flex" style="display:flex; align-items:flex-start;">';
        html +=
          '<div class="jspsych-survey-slider-flex" style="display:flex; align-items:center;">';
        // LEFT COLUMN: the preamble
        html += `
          <div id="jspsych-survey-slider-preamble"
               class="jspsych-survey-slider-preamble"
               style="flex:1; padding-right:50px;">
            ${trial.preamble}
          </div>`;

        // RIGHT COLUMN: questions stack
        html +=
          '<div class="jspsych-survey-slider-questions" style="flex:1; display:flex; flex-direction:column; justify-content:flex-start;">';
      } else {
        // if no preamble, just full-width questions
        html +=
          '<div class="jspsych-survey-slider-questions" style="display:flex; flex-direction:column;">';
      }

      // determine order
      let question_order = trial.questions.map((_, i) => i);
      if (trial.randomize_question_order) {
        question_order = this.jsPsych.randomization.shuffle(question_order);
      }

      // render each question
      for (let idx = 0; idx < trial.questions.length; idx++) {
        const q = trial.questions[question_order[idx]];

        html += `<div id="jspsych-html-slider-response-stimulus">${q.stimulus}</div>`;
        html += `<label class="jspsych-survey-slider-statement" style="font-size:24px;">${q.prompt}</label><br>`;

        // optional labels (above/below)
        if (q.labels.length > 0) {
          html += `<div style="font-size:100%; font-weight:bold; position:absolute; left:calc(-15%);">
                     ${q.labels[0]}
                   </div>`;
        }

        // Add CSS to hide handles when slider_start is null
        if (q.slider_start === null) {
          html += `
            <style>
              #jspsych-html-slider-response-response-${idx}::-webkit-slider-thumb {
                opacity: 0;
                transition: opacity 0.2s ease;
              }
              #jspsych-html-slider-response-response-${idx}::-moz-range-thumb {
                opacity: 0;
                transition: opacity 0.2s ease;
              }
              #jspsych-html-slider-response-response-${idx}.show-handles::-webkit-slider-thumb {
                opacity: 1;
              }
              #jspsych-html-slider-response-response-${idx}.show-handles::-moz-range-thumb {
                opacity: 1;
              }
            </style>`;
        }

        // the slider input
        html += `
          <input
            type="range"
            class="jspsych-slider"
            style="width:100%"
            value="${q.slider_start}"
            min="${q.min}"
            max="${q.max}"
            step="${q.step}"
            id="jspsych-html-slider-response-response-${idx}"
            name="Q${idx}"
            data-name="${q.name}"
          ></input>`;


        // min/max HTML labels underneath
        html += `
          <div class="jspsych-slider-labels"
               style="display:flex; justify-content:space-between; width:100%; margin-top:0.7em;">
            <span>${q.min_label}</span>
            <span>${q.max_label}</span>
          </div>`;

        // second optional label
        if (q.labels.length > 1) {
          html += `<div style="font-size:100%; font-weight:bold; position:absolute; left:calc(-15%);">
                     ${q.labels[1]}
                   </div>`;
        }

        // tick marks
        for (let j = 0; j < q.ticks.length; j++) {
          const label_width_perc = 100 / (q.ticks.length - 1);
          const percent_of_range = j * (100 / (q.ticks.length - 1));
          const percent_from_center = ((percent_of_range - 50) / 50) * 100;
          const offset = (percent_from_center * half_thumb_width) / 100;
          html += `
            <div style="
              position:absolute;
              left:calc(${percent_of_range}% - (${label_width_perc}% / 2) - ${offset}px);
              text-align:center;
              width:${label_width_perc}%;
              border:1px solid transparent;
            ">
              <span style="font-size:100%;">${q.ticks[j]}</span>
            </div>`;
        }

        html += idx === trial.questions.length - 1 ? "" : "<br/><br/>";
      }

      // close the questions column
      html += "</div>";
      // close the flex container if we opened it
      if (trial.preamble !== null) {
        html += "</div>";
      }

      // submit button
      html += `
        <br/>
        <input
          type="submit"
          id="jspsych-survey-slider-next"
          class="jspsych-survey-slider jspsych-btn"
          value="${trial.button_label}"
        ></input>`;

      // close form + containers
      html += "</form></div></div>";

      display_element.innerHTML = html;

      // ── Add event listeners for hidden handles ─────────────
      document.querySelectorAll(".jspsych-slider").forEach((slider, index) => {
        const q = trial.questions[question_order[index]];
        if (q.slider_start === null) {
          const showHandles = () => {
            slider.classList.add('show-handles');
          };
          slider.addEventListener('mousedown', showHandles);
          slider.addEventListener('touchstart', showHandles);
        }
      });

      // ── require movement logic ─────────────────
      if (trial.require_movement) {
        const check = () => {
          const sliders = Array.from(
            document.querySelectorAll(".jspsych-slider")
          );
          return sliders.every((s) => s.classList.contains("clicked"));
        };
        document.getElementById("jspsych-survey-slider-next").disabled = true;
        document.querySelectorAll(".jspsych-slider").forEach((slider) => {
          slider.addEventListener("click", () => {
            slider.classList.add("clicked");
            if (check())
              document.getElementById(
                "jspsych-survey-slider-next"
              ).disabled = false;
          });
          slider.addEventListener("change", () => {
            slider.classList.add("clicked");
            if (check())
              document.getElementById(
                "jspsych-survey-slider-next"
              ).disabled = false;
          });
        });
      }

      // ── form submission ───────────────────────────────────
      display_element
        .querySelector("#jspsych-survey-slider-form")
        .addEventListener("submit", (e) => {
          e.preventDefault();
          const endTime = performance.now();
          const rt = endTime - startTime;
          const data = {};
          document.querySelectorAll('input[type="range"]').forEach((el, i) => {
            const name = el.getAttribute("data-name") || el.name;
            data[name] = el.value;
          });
          this.jsPsych.finishTrial({
            rt,
            response: JSON.stringify(data),
            question_order: JSON.stringify(question_order),
            questions: JSON.stringify(trial.questions),
            preamble: JSON.stringify(trial.preamble),
          });
        });

      const startTime = performance.now();
    }
  }

  return SurveySliderPlugin;
})(jsPsychModule);
