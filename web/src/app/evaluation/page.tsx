import type { Metadata } from "next";
import { Callout } from "@/components/callout";
import { PageHeader, Section } from "@/components/page-header";
import { StatusBadge, type Status } from "@/components/status-badge";
import {
  access,
  caseCategories,
  conditions,
  design,
  evaluatorValidation,
  experimentsUrl,
  isolationSteps,
  primaryHypothesis,
  primaryMetric,
  protocolUrl,
  protocolVersion,
  researchLogUrl,
  researchQuestion,
  secondaryMetrics,
  sharedControls,
  tasks,
  threats,
} from "@/content/evaluation";

export const metadata: Metadata = {
  title: "Evaluation",
  description:
    "The pre-registered ResearchCode experiment comparing unstructured AI coding with the structured ResearchCode workflow on three scientific programming tasks. The framework is implemented; no trials have been run and there are no results yet.",
};

const inlineLink =
  "font-medium text-accent-700 underline decoration-accent-600/40 underline-offset-2 hover:decoration-accent-700";

const progress: { step: string; detail: string; status: Status }[] = [
  { step: "Protocol pre-registered", detail: `Version ${protocolVersion}, frozen by file hashes before any trial.`, status: "available" },
  {
    step: "Tasks and hidden evaluator built",
    detail: `${evaluatorValidation.totalCases} hidden cases; reference solutions pass all of them, and all ${evaluatorValidation.totalDefects} deliberate defects are caught.`,
    status: "available",
  },
  { step: "Isolated harness and dry run", detail: "Every stage runs end to end with labelled fixtures in place of an AI agent.", status: "available" },
  {
    step: "Pilot trials",
    detail: "6 manual sessions through a Claude Pro subscription, run as its usage allows, to check the harness and how many trials fit.",
    status: "planned",
  },
  {
    step: "Confirmatory trials",
    detail: `Up to ${design.confirmatoryTrialsPerCell} per task and condition (60 in all), as subscription usage allows.`,
    status: "planned",
  },
  { step: "Analysis and results", detail: "The pre-registered analysis, published here, including unfavourable results.", status: "planned" },
];

function TaskCard({ task }: { task: (typeof tasks)[number] }) {
  const counts = evaluatorValidation.tasks.find((t) => t.id === task.id)!;
  const byCategory = counts.casesByCategory as Partial<Record<string, number>>;
  return (
    <section aria-labelledby={`task-${task.id}`} className="flex flex-col rounded-xl border border-line bg-white p-6">
      <p className="font-mono text-xs font-medium text-muted">{task.module}</p>
      <h3 id={`task-${task.id}`} className="mt-1 text-lg font-semibold text-ink">
        {task.title}
      </h3>
      <p className="mt-2 text-[0.96875rem] leading-7 text-body">{task.summary}</p>
      <p className="mt-4 text-sm font-medium text-ink">Failure modes it exposes</p>
      <ul className="mt-2 space-y-1.5 text-[0.9375rem] leading-6 text-body">
        {task.failureModes.map((mode) => (
          <li key={mode} className="flex gap-2.5">
            <span aria-hidden="true" className="mt-2.5 h-1.5 w-1.5 shrink-0 rounded-full bg-navy-200" />
            {mode}
          </li>
        ))}
      </ul>
      <div aria-hidden="true" className="min-h-6 flex-1" />
      <dl className="grid grid-cols-2 gap-x-4 gap-y-1 border-t border-line pt-4 text-sm">
        <dt className="text-muted">Hidden cases</dt>
        <dd className="text-right font-mono text-ink">{counts.cases}</dd>
        {caseCategories
          .filter((category) => byCategory[category.id])
          .map((category) => (
            <div key={category.id} className="contents">
              <dt className="text-muted">{category.label}</dt>
              <dd className="text-right font-mono text-body">{byCategory[category.id]}</dd>
            </div>
          ))}
      </dl>
    </section>
  );
}

export default function EvaluationPage() {
  return (
    <>
      <PageHeader eyebrow="Evaluation" title="Does a structured workflow produce more reliable research code?">
        <p>
          ResearchCode claims that a few engineering habits make AI-assisted scientific code more reliable. We
          are testing that claim with a pre-registered, controlled experiment rather than assuming it. This page
          describes the experiment as it is actually configured.
        </p>
      </PageHeader>

      <div className="mx-auto max-w-6xl px-4 sm:px-6">
        <Callout tone="honesty" title="Framework implemented; results pending">
          The protocol, tasks, hidden evaluator, and isolated harness are built and verified. No AI trials have
          been run, so there are no results and nothing on this page is evidence for or against the workflow.
          The validation figures below check the scoring system, not the workflow.
        </Callout>
      </div>

      <Section id="status" eyebrow="Status" title="Where the experiment stands">
        <ol className="mt-8 divide-y divide-line rounded-xl border border-line bg-white">
          {progress.map((item) => (
            <li key={item.step} className="flex flex-col gap-2 px-5 py-4 sm:flex-row sm:items-center sm:gap-6">
              <div className="sm:w-28 sm:shrink-0">
                <StatusBadge status={item.status} />
              </div>
              <div>
                <p className="font-medium text-ink">{item.step}</p>
                <p className="mt-0.5 text-[0.9375rem] leading-6 text-body">{item.detail}</p>
              </div>
            </li>
          ))}
        </ol>
        <p className="mt-4 max-w-3xl text-[0.9375rem] leading-7 text-body">
          The full design is in the{" "}
          <a href={protocolUrl} className={inlineLink}>
            pre-registered protocol
          </a>
          , and the harness is in the{" "}
          <a href={experimentsUrl} className={inlineLink}>
            experiments folder
          </a>
          .
        </p>
      </Section>

      <Section
        id="question"
        eyebrow="Research question"
        title="What we want to learn"
        intro={<p>{researchQuestion}</p>}
      >
        <p className="mt-6 max-w-3xl leading-7 text-body">
          <strong className="font-semibold text-ink">Primary hypothesis.</strong> {primaryHypothesis} Secondary
          questions concern edge cases and invalid input, the quality of each submission&apos;s own tests,
          development effort, and static code quality. They are reported with uncertainty but without
          hypothesis tests.
        </p>
      </Section>

      <Section
        id="conditions"
        eyebrow="Conditions"
        title="Two conditions, one difference"
        intro={
          <p>
            Each trial is a single session of the same AI coding agent, started and ended by an operator who does not
            guide it. The structured workflow is the only thing that differs between the conditions.
          </p>
        }
      >
        <div className="mt-10 grid gap-5 md:grid-cols-2">
          {conditions.map((condition) => (
            <section
              key={condition.id}
              aria-labelledby={`condition-${condition.id}`}
              className="rounded-xl border border-line bg-white p-6"
            >
              <p className="font-mono text-xs font-medium uppercase tracking-wider text-muted">Condition {condition.id}</p>
              <h3 id={`condition-${condition.id}`} className="mt-1 text-lg font-semibold text-ink">
                {condition.name}
              </h3>
              <p className="mt-4 text-sm font-medium text-ink">Receives</p>
              <ul className="mt-2 space-y-1.5 text-[0.96875rem] leading-7 text-body">
                {condition.receives.map((item) => (
                  <li key={item} className="flex gap-3">
                    <span aria-hidden="true" className="mt-3 h-1.5 w-1.5 shrink-0 rounded-full bg-navy-200" />
                    {item}
                  </li>
                ))}
              </ul>
              <p className="mt-4 text-sm font-medium text-ink">Asked to</p>
              <p className="mt-1 text-[0.96875rem] leading-7 text-body">{condition.prompt}</p>
            </section>
          ))}
        </div>
        <h3 className="mt-10 font-semibold text-ink">Held constant across conditions</h3>
        <ul className="mt-3 grid gap-x-8 gap-y-2 text-[0.96875rem] leading-7 text-body md:grid-cols-2">
          {sharedControls.map((control) => (
            <li key={control} className="flex gap-3">
              <span aria-hidden="true" className="mt-3 h-1.5 w-1.5 shrink-0 rounded-full bg-accent-600" />
              {control}
            </li>
          ))}
        </ul>
      </Section>

      <Section
        id="tasks"
        eyebrow="Tasks"
        title="Three scientific programming tasks"
        intro={
          <p>
            The tasks fail in different ways. Each has a shared statement with public examples, an independent
            reference solution, and a hidden evaluator whose expected values were derived separately. There is
            deliberately no growth-rate task, because the starter kit already contains a growth-rate example.
          </p>
        }
      >
        <div className="mt-10 grid gap-5 lg:grid-cols-3">
          {tasks.map((task) => (
            <TaskCard key={task.id} task={task} />
          ))}
        </div>
      </Section>

      <Section
        id="scoring"
        eyebrow="Scoring"
        title="How trials are isolated and scored"
        intro={
          <p>
            Generated code is treated as untrusted, and the agent must never reach the hidden evaluator. The
            evaluator is kept outside this public repository until data collection ends.
          </p>
        }
      >
        <ol className="mt-8 grid gap-5 md:grid-cols-2">
          {isolationSteps.map((step, index) => (
            <li key={step.title} className="rounded-xl border border-line bg-white p-5">
              <p className="font-mono text-xs font-medium text-muted">Step {index + 1}</p>
              <h3 className="mt-1 font-semibold text-ink">{step.title}</h3>
              <p className="mt-2 text-[0.96875rem] leading-7 text-body">{step.body}</p>
            </li>
          ))}
        </ol>
      </Section>

      <Section
        id="sessions"
        eyebrow="Running trials"
        title="Manual sessions at no additional cost"
        intro={<p>{access.summary}</p>}
      >
        <ol className="mt-8 grid gap-4 md:grid-cols-2">
          {access.operatorSteps.map((step, index) => (
            <li key={step} className="flex gap-3 rounded-xl border border-line bg-white p-5">
              <span className="font-mono text-sm font-medium text-muted">{index + 1}</span>
              <span className="text-[0.96875rem] leading-7 text-body">{step}</span>
            </li>
          ))}
        </ol>
        <p className="mt-4 max-w-3xl text-[0.9375rem] leading-7 text-body">{access.usageNote}</p>
      </Section>

      <Section id="metrics" eyebrow="Metrics" title="What we will measure">
        <div className="mt-8 rounded-xl border border-navy-200 bg-navy-50/60 p-6">
          <p className="text-sm font-semibold uppercase tracking-wider text-navy-700">Primary metric</p>
          <h3 className="mt-1 text-lg font-semibold text-ink">{primaryMetric.name}</h3>
          <p className="mt-2 max-w-3xl leading-7 text-body">{primaryMetric.definition}</p>
        </div>
        <div className="mt-6 overflow-x-auto rounded-xl border border-line bg-white">
          <table className="w-full min-w-[34rem] text-left text-sm">
            <caption className="sr-only">Secondary metrics and how each is measured</caption>
            <thead className="bg-surface">
              <tr>
                <th scope="col" className="px-4 py-2.5 font-medium text-ink">Secondary metric</th>
                <th scope="col" className="px-4 py-2.5 font-medium text-ink">How it is measured</th>
                <th scope="col" className="px-4 py-2.5 font-medium text-ink">Kind</th>
              </tr>
            </thead>
            <tbody className="text-body">
              {secondaryMetrics.map((metric) => (
                <tr key={metric.name} className="border-t border-line align-top">
                  <th scope="row" className="px-4 py-2.5 font-medium text-ink">{metric.name}</th>
                  <td className="px-4 py-2.5 leading-6">{metric.how}</td>
                  <td className="px-4 py-2.5">{metric.kind === "objective" ? "Objective" : "Subjective (blinded)"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-4 max-w-3xl text-[0.9375rem] leading-7 text-body">
          Tests that a submission writes are never counted as evidence that it is correct. Only the hidden
          evaluator measures correctness, and test quality is measured by which known defects those tests catch.
        </p>
      </Section>

      <Section id="design" eyebrow="Design" title="Trials, configuration, and analysis plan">
        <div className="mt-8 grid gap-8 lg:grid-cols-2">
          <dl className="divide-y divide-line rounded-xl border border-line bg-white text-[0.9375rem]">
            {[
              ["Agent", `Claude Code ${design.toolVersion}, model ${design.model}, effort ${design.effort}`],
              ["Pilot", `${design.pilotTrialsPerCell} trial per task and condition (excluded from analysis)`],
              ["Confirmatory trials", `${design.confirmatoryTrialsPerCell} per task and condition`],
              ["Order", `Blocks with every task × condition once, randomised (seed ${design.scheduleSeed})`],
              ["Access", "Manual Claude Code sessions through a Claude Pro subscription; $0 additional spending"],
              ["Time limit per trial", `${design.wallClockMinutes} minutes`],
              ["Evaluation limits", `${design.caseTimeoutSeconds} s per hidden case, no network`],
            ].map(([term, value]) => (
              <div key={term} className="flex flex-col gap-1 px-5 py-3 sm:flex-row sm:gap-6">
                <dt className="font-medium text-ink sm:w-40 sm:shrink-0">{term}</dt>
                <dd className="text-body">{value}</dd>
              </div>
            ))}
          </dl>
          <div className="space-y-4 leading-7 text-body">
            <p>
              The primary estimate is the mean over tasks of the difference in hidden pass rate (B − A), with a
              95% bootstrap interval from {design.bootstrapResamples.toLocaleString("en-US")} resamples. One
              permutation test of that difference is the only hypothesis test.
            </p>
            <p>
              If any task × condition cell has fewer than {design.minimumValidPerCell} valid trials, all results are
              reported as descriptive. Every trial&apos;s score is plotted, not only the averages. Infrastructure
              failures are rerun, and the agent&apos;s own failures count.
            </p>
          </div>
        </div>
      </Section>

      <Section
        id="validation"
        eyebrow="Evaluator validation"
        title="Checking the scoring system before any trial"
        intro={
          <p>
            A hidden evaluator is only useful if it separates correct code from realistic mistakes. We scored our
            own reference solutions and deliberately defective versions of them. These are checks of the scoring
            system, not experimental results.
          </p>
        }
      >
        <div className="mt-8 overflow-x-auto rounded-xl border border-line bg-white">
          <table className="w-full min-w-[32rem] text-left text-sm">
            <caption className="sr-only">Evaluator validation by task: hidden cases, reference score, and defects detected</caption>
            <thead className="bg-surface">
              <tr>
                <th scope="col" className="px-4 py-2.5 font-medium text-ink">Task</th>
                <th scope="col" className="px-4 py-2.5 font-medium text-ink">Hidden cases</th>
                <th scope="col" className="px-4 py-2.5 font-medium text-ink">Reference solution</th>
                <th scope="col" className="px-4 py-2.5 font-medium text-ink">Deliberate defects caught</th>
              </tr>
            </thead>
            <tbody className="text-body">
              {evaluatorValidation.tasks.map((row) => (
                <tr key={row.id} className="border-t border-line">
                  <th scope="row" className="px-4 py-2.5 font-mono font-normal text-ink">{row.id}</th>
                  <td className="px-4 py-2.5 font-mono">{row.cases}</td>
                  <td className="px-4 py-2.5 font-mono">{Math.round(row.referencePassRate * 100)}% passed</td>
                  <td className="px-4 py-2.5 font-mono">
                    {row.defectsDetected} of {row.defects}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-4 max-w-3xl text-[0.9375rem] leading-7 text-body">
          The validation found a weakness in the evaluator itself: a numerically unstable formula passed every
          case, because the test data happened to be exact in floating point. The case was fixed before the
          protocol was frozen. The{" "}
          <a href={researchLogUrl} className={inlineLink}>
            research log
          </a>{" "}
          records this and other problems found while building the framework with an AI assistant.
        </p>
      </Section>

      <Section id="threats" eyebrow="Limitations" title="Threats to validity">
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
            No trials have been run. Results will appear here only after the pre-registered trials and analysis
            are complete, including results that do not favour the structured workflow.
          </p>
        </div>
      </Section>
    </>
  );
}
