import type { Metadata } from "next";
import { Callout } from "@/components/callout";
import { PageHeader, Section } from "@/components/page-header";

export const metadata: Metadata = {
  title: "Evaluation",
  description:
    "The proposed ResearchCode study comparing unstructured AI prompting with a structured AI-assisted workflow on scientific coding tasks. Methodology and planned metrics; no results yet.",
};

function slug(text: string): string {
  return text.toLowerCase().replace(/[^a-z0-9]+/g, "-");
}

const conditions = [
  {
    name: "Unstructured (vibe coding)",
    label: "Condition A",
    points: [
      "Participants use an AI assistant however they normally would.",
      "No specification, test, or review step is required.",
      "Same task description, time limit, data, and assistant as Condition B.",
    ],
  },
  {
    name: "Structured workflow",
    label: "Condition B",
    points: [
      "Participants follow the ResearchCode workflow: specify, test, generate, review, reproduce.",
      "They start from the starter kit template and its assistant instructions.",
      "Same task description, time limit, data, and assistant as Condition A.",
    ],
  },
];

const metrics: { group: string; items: { name: string; how: string }[] }[] = [
  {
    group: "Correctness",
    items: [
      { name: "Hidden test pass rate", how: "Share of a held-out test suite, unseen by participants, that the submission passes." },
      { name: "Numerical error", how: "Relative error of reported growth rates against values known from synthetic data generation." },
      { name: "Silent failure count", how: "Number of planted pitfalls (units, blanks, invalid values) that produce a wrong result without an error." },
    ],
  },
  {
    group: "Reproducibility",
    items: [
      { name: "Fresh-clone success", how: "Whether the documented command reproduces the results on a clean machine, without help." },
      { name: "Environment pinned", how: "Presence of a lock file and pinned Python version." },
      { name: "Provenance recorded", how: "Whether outputs can be traced to a code version and parameters." },
    ],
  },
  {
    group: "Maintainability and security",
    items: [
      { name: "Lint findings", how: "Ruff findings per 100 lines under a fixed rule set, including security rules." },
      { name: "Test coverage", how: "Line coverage of the participant's own tests, reported alongside test quality, not as a target." },
      { name: "Review rubric score", how: "Blinded rating of readability, structure, and documentation using a published rubric." },
    ],
  },
  {
    group: "Cost and experience",
    items: [
      { name: "Time to completion", how: "Wall-clock time until the participant declares the task finished." },
      { name: "Assistant interactions", how: "Number of prompts and accepted changes, from session logs." },
      { name: "Confidence calibration", how: "Participants' stated confidence in their result compared with its actual correctness." },
    ],
  },
];

const threats = [
  {
    title: "Small samples",
    body: "A course project can recruit only a limited number of participants. We will report effect sizes with uncertainty intervals, and avoid claims the data cannot support.",
  },
  {
    title: "Learning and order effects",
    body: "If one person completes both conditions, the second task benefits from the first. A within-subjects design would need counterbalanced order and different but comparable tasks.",
  },
  {
    title: "Task representativeness",
    body: "One growth-curve task does not represent all research code. We will describe the task precisely so readers can judge how far results generalise.",
  },
  {
    title: "Model drift and nondeterminism",
    body: "Assistant behaviour changes between versions and between runs. We will record model names, versions, and dates, and repeat automated runs.",
  },
  {
    title: "Rater bias",
    body: "Raters who know the condition may score differently. Rubric scoring will be blinded to condition where possible.",
  },
];

export default function EvaluationPage() {
  return (
    <>
      <PageHeader eyebrow="Evaluation" title="Does a structured workflow produce better research code?">
        <p>
          ResearchCode makes a claim: that a few engineering habits make AI-assisted scientific code more
          correct and more reproducible, at an acceptable cost in time. We plan to test that claim rather than
          assume it. This page describes the proposed study.
        </p>
      </PageHeader>

      <div className="mx-auto max-w-6xl px-4 sm:px-6">
        <Callout tone="honesty" title="Proposed study: no data collected yet">
          This is a study design, not a report. No participants have been recruited and no results exist. The
          design may change before data collection begins; any changes will be documented. Results will appear
          here only after the study has been run and analysed.
        </Callout>
      </div>

      <Section
        id="question"
        eyebrow="Research question"
        title="What we want to learn"
        intro={
          <p>
            When researchers use the same AI coding assistant on the same scientific task, does following a
            structured workflow, rather than prompting freely, change the correctness, reproducibility, and
            maintainability of the resulting code, and how much time does it cost?
          </p>
        }
      >
        <div className="mt-10 grid gap-5 md:grid-cols-2">
          {conditions.map((condition) => (
            <section key={condition.label} aria-labelledby={`${slug(condition.label)}-heading`} className="rounded-xl border border-line bg-white p-6">
              <p className="font-mono text-xs font-medium uppercase tracking-wider text-muted">{condition.label}</p>
              <h3 id={`${slug(condition.label)}-heading`} className="mt-1 text-lg font-semibold text-ink">
                {condition.name}
              </h3>
              <ul className="mt-4 space-y-2 text-[0.96875rem] leading-7 text-body">
                {condition.points.map((point) => (
                  <li key={point} className="flex gap-3">
                    <span aria-hidden="true" className="mt-3 h-1.5 w-1.5 shrink-0 rounded-full bg-navy-200" />
                    {point}
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      </Section>

      <Section id="method" eyebrow="Methodology" title="Proposed design">
        <ol className="mt-8 space-y-6 border-l-2 border-line pl-6">
          {[
            {
              title: "Pre-register the protocol",
              body: "Before any data collection, publish the tasks, hypotheses, metrics, and analysis plan in the repository's experiments/ directory, so the analysis cannot be adjusted to fit the results.",
            },
            {
              title: "Build the tasks and hidden tests",
              body: "Write a growth-curve analysis task based on the example on this site, with synthetic data whose true parameters are known and planted pitfalls such as minutes-versus-hours time columns and wells near the blank.",
            },
            {
              title: "Pilot with AI agents only",
              body: "Run an AI coding agent many times under each condition's instructions. This tests the tasks and scoring scripts and gives a first, human-free comparison.",
            },
            {
              title: "Run with researchers",
              body: "If participants are recruited, assign them to conditions at random, with the same assistant and time limit. Before recruiting anyone, we will ask Caltech's Institutional Review Board whether the study requires review.",
            },
            {
              title: "Score and analyse",
              body: "Score submissions with automated scripts and a blinded rubric. Compare conditions using the pre-registered analysis, report uncertainty, and publish the data, scripts, and anonymised submissions where permitted.",
            },
          ].map((step, index) => (
            <li key={step.title} className="relative">
              <span
                aria-hidden="true"
                className="absolute -left-[2.1rem] top-0.5 flex h-6 w-6 items-center justify-center rounded-full border-2 border-white bg-navy-800 font-mono text-[0.6875rem] text-white"
              >
                {index + 1}
              </span>
              <h3 className="font-semibold text-ink">{step.title}</h3>
              <p className="mt-1 max-w-3xl leading-7 text-body">{step.body}</p>
            </li>
          ))}
        </ol>
      </Section>

      <Section
        id="metrics"
        eyebrow="Planned metrics"
        title="What we will measure"
        intro={<p>Metrics are grouped by the property they assess. Final definitions will be fixed in the pre-registration.</p>}
      >
        <div className="mt-10 grid gap-5 lg:grid-cols-2">
          {metrics.map((group) => (
            <section key={group.group} aria-labelledby={`metric-${slug(group.group)}`} className="rounded-xl border border-line bg-white p-6">
              <h3 id={`metric-${slug(group.group)}`} className="text-lg font-semibold text-ink">
                {group.group}
              </h3>
              <dl className="mt-4 divide-y divide-line">
                {group.items.map((item) => (
                  <div key={item.name} className="py-3 first:pt-0 last:pb-0">
                    <dt className="font-medium text-ink">{item.name}</dt>
                    <dd className="mt-1 text-[0.96875rem] leading-6 text-body">{item.how}</dd>
                  </div>
                ))}
              </dl>
            </section>
          ))}
        </div>
      </Section>

      <Section id="threats" eyebrow="Limitations" title="Threats to validity we are planning for">
        <ul className="mt-8 grid gap-5 md:grid-cols-2 lg:grid-cols-3">
          {threats.map((threat) => (
            <li key={threat.title} className="rounded-xl border border-line bg-white p-5">
              <h3 className="font-semibold text-ink">{threat.title}</h3>
              <p className="mt-2 text-[0.96875rem] leading-7 text-body">{threat.body}</p>
            </li>
          ))}
        </ul>
      </Section>

      <Section id="results" eyebrow="Results" title="Results">
        <div className="mt-6 rounded-xl border border-dashed border-navy-200 bg-surface px-6 py-12 text-center">
          <p className="font-semibold text-ink">No results yet</p>
          <p className="mx-auto mt-2 max-w-lg leading-7 text-body">
            Data collection has not started. When the study is complete, this section will report the
            pre-registered analyses, including results that do not favour the structured workflow.
          </p>
        </div>
      </Section>
    </>
  );
}
