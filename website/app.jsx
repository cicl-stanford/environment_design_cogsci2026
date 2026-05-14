/* Main page sections — hero, abstract, study cards, BibTeX, footer. */

const STUDY1_CONDITIONS = [
  {
    id: 0,
    title: "Cooks",
    question: "How many cooks was this kitchen designed for?",
    accent: "tomato",
  },
  {
    id: 1,
    title: "Dish",
    question: "Which dish was this kitchen designed for?",
    accent: "cabbage",
  },
  {
    id: 2,
    title: "Cooks · effort",
    question: "How much effort would each layout take?",
    accent: "onion",
  },
  {
    id: 3,
    title: "Dish · effort",
    question: "How long to make each dish here?",
    accent: "plate",
  },
];

const STUDY2_CONDITIONS = [
  {
    id: 0,
    title: "Base",
    subtitle: "Cook knows which dish to make",
    accent: "tomato",
  },
  {
    id: 1,
    title: "Communicative",
    subtitle: "Cook does not know which dish",
    accent: "cabbage",
  },
];

function Hero() {
  return (
    <section className="hero">
      <div className="hero-inner">

        <h1 className="hero-title">
          From <span className="hl-plum">chopped</span> to <span className="hl-plum">cooked</span>:
          <span className="hero-sub-title"> Design and inference in physical environments</span>
        </h1>

        <ol className="hero-authors">
          <li><span>Justin Yang</span></li>
          <li><span>Lionel Wong</span></li>
          <li><span>Judith E. Fan</span></li>
          <li><span>Tobias Gerstenberg</span></li>
        </ol>
        <ol className="hero-affil">
          <li>Stanford University</li>
        </ol>

        <div className="hero-cta">
          <a className="cta cta-primary" href="https://github.com/cicl-stanford/environment_design_cogsci2026/blob/main/environment_design_cogsci2026.pdf" target="_blank" rel="noopener">
            <span>Paper</span>
            <ArrowIcon />
          </a>
          <a className="cta" href="#study-1">Demos</a>
          <a className="cta cta-ghost" href="https://github.com/cicl-stanford/environment_design_cogsci2026" target="_blank" rel="noopener">
            <GitHubIcon /> Code
          </a>
        </div>
      </div>

      <aside className="hero-side">
        <KitchenTeaser />
      </aside>
    </section>
  );
}

function Abstract() {
  return (
    <section className="abstract">
      <div className="abstract-label">Abstract</div>
      <div className="abstract-body-wrap">
        <p className="abstract-body">
          Physical spaces are often designed to support specific uses. But how do people <em>create</em> such environments,
          and how do users <em>infer</em> their intended function? We propose that design and inference about design are
          complementary processes, grounded in a capacity to mentally simulate goal-directed actions. We tested this using
          “Overcooked”-style kitchens where participants either judged what a kitchen was designed for (Study 1) or designed
          kitchens for cooks with varying goals and beliefs (Study 2).
        </p>
        <p className="abstract-body">
          In Study 1, participants inferred that kitchens were designed for tasks the layout made easier to complete,
          consistent with the prediction of a simulation-based computational model. In Study 2, participants made designs
          that helped cooks efficiently complete their task, adjusting their choices when cooks faced uncertainty about
          which task to perform.
        </p>
      </div>
    </section>
  );
}

function Study1() {
  return (
    <section className="study" id="study-1">
      <div className="study-head">
        <div className="study-num">Study 1</div>
        <h2 className="study-title">Inferring what kitchens are designed for</h2>
      </div>

      <div className="cond-grid cond-grid-4">
        {STUDY1_CONDITIONS.map(c => (
          <article key={c.id} className={`cond cond-${c.accent}`}>
            <header className="cond-head">
              <h3>{c.title}</h3>
            </header>
            <p className="cond-q">{c.question}</p>
            <a className="cond-link" href={`s1_design_inference/index.html?condition=${c.id}`} target="_blank" rel="noopener">
              Open demo <ArrowIcon />
            </a>
          </article>
        ))}
      </div>
    </section>
  );
}

function Study2() {
  return (
    <section className="study study-alt" id="study-2">
      <div className="study-head">
        <div className="study-num">Study 2</div>
        <h2 className="study-title">Designing kitchens</h2>
      </div>

      <div className="cond-grid cond-grid-2">
        {STUDY2_CONDITIONS.map(c => (
          <article key={c.id} className={`cond cond-large cond-${c.accent}`}>
            <header className="cond-head">
              <h3>{c.title}</h3>
            </header>
            <p className="cond-q">{c.subtitle}</p>
            <a className="cond-link" href={`overcooked_design/index.html?condition=${c.id}`} target="_blank" rel="noopener">
              Open demo <ArrowIcon />
            </a>
          </article>
        ))}
      </div>
    </section>
  );
}

const BIBTEX = `@inproceedings{yang2026environmentdesign,
  title     = {From chopped to cooked: Design and inference in physical environments},
  booktitle = {Proceedings of the 48th Annual Conference of the Cognitive Science Society},
  author    = {Yang, Justin and Wong, Lionel and Fan, Judith E. and Gerstenberg, Tobias},
  year      = {2026},
}`;

function Resources() {
  const [copied, setCopied] = React.useState(false);
  const onCopy = async () => {
    try {
      await navigator.clipboard.writeText(BIBTEX);
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch (e) {}
  };
  return (
    <section className="resources" id="resources">
      <div className="bibtex">
        <pre>{BIBTEX}</pre>
        <button className="bibtex-copy" onClick={onCopy}>{copied ? "Copied" : "Copy"}</button>
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer className="site-foot">
      <div className="foot-bottom">
        <span><a href="https://cicl.stanford.edu/" target="_blank" rel="noopener">Causality in Cognition Lab</a> · <a href="https://cogtoolslab.github.io/" target="_blank" rel="noopener">Cognitive Tools Lab</a></span>
        <span>Stanford University</span>
      </div>
    </footer>
  );
}

function ArrowIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path d="M3 8h10M9 4l4 4-4 4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
function GitHubIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
      <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/>
    </svg>
  );
}

function App() {
  return (
    <>
      <Hero />
      <Abstract />
      <Study1 />
      <Study2 />
      <Resources />
    </>
  );
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<App />);
