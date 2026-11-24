import type { Metadata } from "next";
import type { ReactNode } from "react";
import { Callout } from "@/components/callout";
import { ComparisonBars, type BarGroup } from "@/components/comparison-bars";
import { PageHeader, Section } from "@/components/page-header";
import {
  access,
  caseCategories,
  conditions,
  design,
  evaluatorValidation,
  experimentsUrl,
  isolationSteps,
  limitations,
  materials,
  primaryHypothesis,
  primaryMetric,
  protocol14MergeUrl,
  protocol14Url,
  protocolUrl,
  aggregateResultsUrl,
  reportSourceUrl,
  reportUrl,
  researchLogUrl,
  researchQuestion,
  secondaryMetrics,
  sharedControls,
  tasks,
} from "@/content/evaluation";
import {
  analysisRun,
  primaryResult,
  sample,
  secondaryResults,
  taskLabels,
  taskOrder,
  trialsWithTests,
  type SecondaryMetric,
} from "@/content/evaluation-results";

export const metadata: Metadata = {
  title: "Evaluation",
  description:
    "Results of the pre-registered ResearchCode experiment: in 60 trials on three scientific programming tasks, unstructured AI coding and the structured workflow both passed every hidden evaluation case. The workflow produced far more tests, at about four times the session time.",
};

const inlineLink =
  "font-medium text-accent-700 underline decoration-accent-600/40 underline-offset-2 hover:decoration-accent-700";

const percent = (value: number, digits = 1) => `${(value * 100).toFixed(digits)}%`;
const fixed = (digits: number) => (value: number) =>
  value.toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits });
const signed = (value: number, format: (v: number) => string) => `${value < 0 ? "−" : "+"}${format(Math.abs(value))}`;
const interval = ([low, high]: [number, number], format: (v: number) => string) =>
  `[${low < 0 ? "−" : ""}${format(Math.abs(low))}, ${high < 0 ? "−" : ""}${format(Math.abs(high))}]`;

function groupsFor(metric: SecondaryMetric, scale = 1): BarGroup[] {
  return [
    ...taskOrder.map((task) => ({
      label: taskLabels[task],
      a: metric.perTask[task][0] * scale,
      b: metric.perTask[task][1] * scale,
    })),
    { label: "All 30 trials", a: metric.a * scale, b: metric.b * scale, emphasis: true },
  ];
}

const timeRatio = secondaryResults.wallClockMinutes.b / secondaryResults.wallClockMinutes.a;
const tokenRatio = secondaryResults.outputTokens.b / secondaryResults.outputTokens.a;

const summaryRows: { metric: SecondaryMetric; format: (v: number) => string; diffFormat?: (v: number) => string }[] = [
  { metric: secondaryResults.mutationScore, format: (v) => percent(v), diffFormat: (v) => `${(v * 100).toFixed(1)} pts` },
  { metric: secondaryResults.testsCollected, format: fixed(1) },
  { metric: secondaryResults.wallClockMinutes, format: fixed(2) },
  { metric: secondaryResults.outputTokens, format: fixed(0) },
  { metric: secondaryResults.assistantMessages, format: fixed(1) },
  { metric: secondaryResults.lintPer100Lines, format: fixed(2) },
];

const overview: [string, string][] = [
  ["Tasks", "3 scientific programming tasks: serial dilution, calibration, and enzyme kinetics"],
  ["Conditions", "A: unstructured AI coding. B: ResearchCode's structured workflow"],
  [
    "Trials",
    `${sample.analysedTrials} confirmatory trials: ${sample.trialsPerCondition} per condition, ${sample.trialsPerCell} per task and condition`,
  ],
  ["Agent", `One configuration: Claude Code ${design.toolVersion}, ${design.model}, effort ${design.effort}`],
  ["Scoring", `A hidden evaluator with ${evaluatorValidation.totalCases} cases that the agent never saw`],
  [
    "Analysis",
    `Randomised schedule (seed ${design.scheduleSeed}); the pre-registered analysis ran once with frozen code on ${analysisRun.date}`,
  ],
];

function StatTile({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <div className="rounded-xl border border-line bg-white p-5">
      <dt className="text-sm font-medium text-muted">{label}</dt>
      <dd className="mt-1 text-3xl font-semibold tracking-tight text-ink">{value}</dd>
      <dd className="mt-1 text-[0.9375rem] leading-6 text-body">{detail}</dd>
    </div>
  );
}

function Bullets({ items }: { items: ReactNode[] }) {
  return (
    <ul className="mt-3 space-y-2 text-[0.96875rem] leading-7 text-body">
      {items.map((item, index) => (
        <li key={index} className="flex gap-3">
          <span aria-hidden="true" className="mt-3 h-1.5 w-1.5 shrink-0 rounded-full bg-navy-200" />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

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
  const mutation = secondaryResults.mutationScore;
  return (
    <>
      <PageHeader eyebrow="Evaluation" title="Does a structured workflow produce more reliable research code?">
        <p>
          ResearchCode claims that a few engineering habits make AI-assisted scientific code more reliable. We
          tested that claim with a pre-registered, controlled experiment instead of assuming it. This page
          reports what we found, including the results that do not favour the workflow.
        </p>
      </PageHeader>

      <div className="mx-auto max-w-6xl px-4 sm:px-6">
        <Callout tone="honesty" title="Result: no difference in measured correctness">
          In all {sample.analysedTrials} trials, code from both conditions passed every hidden evaluation case, so
          the structured workflow could not improve measured correctness, and it did not. This is a ceiling: it
          is not evidence that the two workflows are equally reliable in general. The workflow did change what
          the agent produced, and what it cost.
          {reportUrl ? (
            <>
              {" "}
              <a href={reportUrl} className={inlineLink}>
                Read the full research report
              </a>
              .
            </>
          ) : null}
        </Callout>
      </div>

      <Section
        id="overview"
        eyebrow="The experiment"
        title="What we ran"
        intro={
          <p>
            The same AI coding agent solved the same tasks with and without ResearchCode&apos;s workflow, in a
            randomised order, with no one guiding it. The design and analysis were fixed before any trial.{" "}
            <a href="#methods" className={inlineLink}>
              Methods in detail
            </a>
            .
          </p>
        }
      >
        <dl className="mt-8 grid gap-px overflow-hidden rounded-xl border border-line bg-line sm:grid-cols-2 lg:grid-cols-3">
          {overview.map(([term, value]) => (
            <div key={term} className="bg-white p-5">
              <dt className="text-sm font-medium text-muted">{term}</dt>
              <dd className="mt-1 leading-7 text-ink">{value}</dd>
            </div>
          ))}
        </dl>
      </Section>

      <Section
        id="primary-result"
        eyebrow="Primary result"
        title="Both conditions passed every hidden evaluation case"
        intro={
          <p>
            The primary measure is the share of hidden evaluation cases a submission passes, averaged over the
            three tasks. <strong className="font-semibold text-ink">The primary hypothesis, that it differs
            between the conditions, was not supported.</strong>
          </p>
        }
      >
        <dl className="mt-8 grid gap-4 md:grid-cols-3">
          <StatTile label="Condition A: unstructured" value={percent(primaryResult.passRateA)} detail="of hidden cases passed, in every one of 30 trials" />
          <StatTile label="Condition B: ResearchCode" value={percent(primaryResult.passRateB)} detail="of hidden cases passed, in every one of 30 trials" />
          <StatTile
            label="Difference (B − A)"
            value={`${(primaryResult.difference * 100).toFixed(1)} points`}
            detail={`95% bootstrap CI [${(primaryResult.ci[0] * 100).toFixed(1)}, ${(primaryResult.ci[1] * 100).toFixed(1)}]; stratified permutation test p = ${primaryResult.permutationP.toFixed(4)}`}
          />
        </dl>

        <div className="mt-6 overflow-x-auto rounded-xl border border-line bg-white">
          <table className="w-full min-w-[30rem] text-left text-sm">
            <caption className="sr-only">Hidden pass rate by task and condition, with the difference</caption>
            <thead className="bg-surface">
              <tr>
                <th scope="col" className="px-4 py-2.5 font-medium text-ink">Task</th>
                <th scope="col" className="px-4 py-2.5 font-medium text-ink">A: hidden cases passed</th>
                <th scope="col" className="px-4 py-2.5 font-medium text-ink">B: hidden cases passed</th>
                <th scope="col" className="px-4 py-2.5 font-medium text-ink">B − A</th>
              </tr>
            </thead>
            <tbody className="font-mono text-body">
              {taskOrder.map((task) => (
                <tr key={task} className="border-t border-line">
                  <th scope="row" className="px-4 py-2.5 font-sans font-medium text-ink">{taskLabels[task]}</th>
                  <td className="px-4 py-2.5">{percent(primaryResult.perTask[task][0])}</td>
                  <td className="px-4 py-2.5">{percent(primaryResult.perTask[task][1])}</td>
                  <td className="px-4 py-2.5">{((primaryResult.perTask[task][1] - primaryResult.perTask[task][0]) * 100).toFixed(1)} points</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="mt-8 rounded-xl border border-navy-200 bg-navy-50/60 p-6">
          <h3 className="text-lg font-semibold text-ink">A ceiling, not evidence of equivalence</h3>
          <p className="mt-2 max-w-3xl leading-7 text-body">
            Every trial scored 100%, so the measure had no variation and the experiment could not separate the
            conditions on correctness.
          </p>
          <Bullets
            items={[
              <>
                <strong className="font-semibold text-ink">The p-value is forced.</strong> When every value is
                identical, every reshuffling of the condition labels gives the same difference of 0, so p = 1. The
                test could not detect anything; it does not show that the conditions are alike.
              </>,
              <>
                <strong className="font-semibold text-ink">The interval is degenerate.</strong> A bootstrap
                interval of [0, 0] reflects zero observed variation, not precise knowledge of the effect. It does not
                bound the difference that harder tasks or other agents might show.
              </>,
              <>
                <strong className="font-semibold text-ink">What can be said.</strong> On these tasks, with this
                agent, both workflows produced code that the evaluator could not fault, although in validation it
                caught all {evaluatorValidation.totalDefects} deliberately defective versions of the reference
                solutions.
              </>,
              <>
                Every case category, including edge cases and invalid input, was also at 100% in both conditions.
                The pre-registered sensitivity analysis and the exploratory analysis without the one hand-run trial (
                {primaryResult.exploratoryWithoutInteractive.trials} trials) gave the same difference of 0.
              </>,
            ]}
          />
        </div>
      </Section>

      <Section
        id="testing"
        eyebrow="Secondary result: testing"
        title="Condition B wrote far more tests, and they caught most known defects"
        intro={
          <p>
            The mutation score is the share of a task&apos;s deliberate defects that a submission&apos;s own tests
            detect, counting only tests that also pass against the reference solution. This and every other
            secondary result is descriptive: it was not tested as a hypothesis.
          </p>
        }
      >
        <dl className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatTile label="A: trials with any tests" value={`${trialsWithTests.a} of ${trialsWithTests.of}`} detail="both in serial dilution" />
          <StatTile label="B: trials with any tests" value={`${trialsWithTests.b} of ${trialsWithTests.of}`} detail="every trial" />
          <StatTile label="A: tests per submission" value={fixed(1)(secondaryResults.testsCollected.a)} detail="mean over 30 trials" />
          <StatTile label="B: tests per submission" value={fixed(1)(secondaryResults.testsCollected.b)} detail="mean over 30 trials" />
        </dl>

        <div className="mt-6">
          <ComparisonBars
            title="Mutation score: share of known defects the submission's own tests detect"
            description={`Mean per task and over all 30 trials per condition, on a 0–100% scale. B − A over tasks: ${signed(mutation.difference * 100, (v) => v.toFixed(1))} points, 95% bootstrap CI [${(mutation.ci[0] * 100).toFixed(1)}, ${(mutation.ci[1] * 100).toFixed(1)}] (descriptive). A submission without valid tests scores 0.`}
            groups={groupsFor(mutation)}
            max={1}
            ticks={[0, 0.25, 0.5, 0.75, 1]}
            format={(v) => percent(v)}
            tickFormat={(v) => percent(v, 0)}
          />
        </div>

        <h3 className="mt-10 font-semibold text-ink">How to read this</h3>
        <Bullets
          items={[
            <>
              <strong className="font-semibold text-ink">Tests were part of the treatment.</strong> Condition B was
              told to write known-answer, edge-case, invalid-input, and property-based tests. Condition A was
              neither asked nor prevented. The gap is largely a direct consequence of that instruction.
            </>,
            <>
              <strong className="font-semibold text-ink">Three zeros are a measurement failure.</strong> In three
              serial-dilution trials in Condition B, 220 to 252 tests passed against the submission&apos;s own code
              but none counted as valid against the reference solution, most likely because each suite imports a
              custom exception class that the reference does not define. Their recorded scores of 0 do not show
              that the tests were ineffective; they lower B&apos;s serial-dilution and overall means.
            </>,
            <>
              <strong className="font-semibold text-ink">Tests are not evidence of correctness.</strong> A
              submission&apos;s own tests never counted towards its score; only the hidden evaluator measured
              correctness. The mutation score shows that B&apos;s tests could detect realistic defects, not that they
              changed the code that was delivered.
            </>,
          ]}
        />
      </Section>

      <Section
        id="cost"
        eyebrow="Secondary result: effort"
        title={`The workflow took about ${timeRatio.toFixed(1)} times the session time`}
        intro={
          <p>
            Condition B&apos;s sessions also produced about {tokenRatio.toFixed(1)} times the output tokens and fewer
            lint findings. Its workflow ran Ruff, so the lint difference is partly a direct consequence of the
            treatment. No trial reached the {design.wallClockMinutes}-minute limit.
          </p>
        }
      >
        <div className="mt-8 grid gap-5 lg:grid-cols-2">
          <ComparisonBars
            title="Session time (minutes)"
            description="Mean wall-clock minutes per session, on a scale from 0. Time while the host computer slept is not counted."
            groups={groupsFor(secondaryResults.wallClockMinutes)}
            max={12}
            ticks={[0, 3, 6, 9, 12]}
            format={fixed(2)}
            tickFormat={String}
          />
          <ComparisonBars
            title="Output tokens per session"
            description="Mean output tokens as recorded in Claude Code's session log, on a scale from 0."
            groups={groupsFor(secondaryResults.outputTokens)}
            max={50000}
            ticks={[0, 25000, 50000]}
            format={fixed(0)}
            tickFormat={(v) => (v === 0 ? "0" : `${v / 1000}K`)}
          />
          <ComparisonBars
            title="Lint findings per 100 lines"
            description="Mean Ruff findings per 100 non-blank, non-comment lines of non-test code, with a fixed rule set, on a scale from 0."
            groups={groupsFor(secondaryResults.lintPer100Lines)}
            max={7}
            ticks={[0, 2, 4, 6]}
            format={fixed(2)}
            tickFormat={String}
          />
          <ComparisonBars
            title="Assistant messages per session"
            description="Mean assistant messages as recorded in Claude Code's session log, on a scale from 0. Every trial had exactly one human message, the prompt."
            groups={groupsFor(secondaryResults.assistantMessages)}
            max={30}
            ticks={[0, 10, 20, 30]}
            format={fixed(1)}
            tickFormat={String}
          />
        </div>

        <h3 className="mt-10 font-semibold text-ink">All secondary measures</h3>
        <div className="mt-3 overflow-x-auto rounded-xl border border-line bg-white">
          <table className="w-full min-w-[40rem] text-left text-sm">
            <caption className="sr-only">
              Secondary measures: means per condition over 30 trials, and the difference B − A with its 95% bootstrap interval
            </caption>
            <thead className="bg-surface">
              <tr>
                <th scope="col" className="px-4 py-2.5 font-medium text-ink">Measure</th>
                <th scope="col" className="px-4 py-2.5 font-medium text-ink">A: mean</th>
                <th scope="col" className="px-4 py-2.5 font-medium text-ink">B: mean</th>
                <th scope="col" className="px-4 py-2.5 font-medium text-ink">B − A, 95% bootstrap CI</th>
              </tr>
            </thead>
            <tbody className="text-body">
              {summaryRows.map(({ metric, format, diffFormat }) => (
                <tr key={metric.key} className="border-t border-line align-top">
                  <th scope="row" className="px-4 py-2.5 font-medium text-ink">
                    {metric.label}
                    <span className="block text-xs font-normal text-muted">{metric.unit}</span>
                  </th>
                  <td className="px-4 py-2.5 font-mono">{format(metric.a)}</td>
                  <td className="px-4 py-2.5 font-mono">{format(metric.b)}</td>
                  <td className="px-4 py-2.5 font-mono">
                    {signed(metric.difference, diffFormat ?? format)}{" "}
                    <span className="whitespace-nowrap">
                      {interval(metric.ci, diffFormat ? (v) => (v * 100).toFixed(1) : format)}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-4 max-w-3xl text-[0.9375rem] leading-7 text-body">
          These intervals describe uncertainty; they are not hypothesis tests and are not adjusted for multiple
          comparisons. Message and token counts come from Claude Code&apos;s own logs. No security difference is
          shown, because the security metric was misclassified (see limitations). Whether the extra tests pay
          for themselves later, for example by catching a regression when the code changes, was not measured.
        </p>
      </Section>

      <Section
        id="limitations"
        eyebrow="Limitations"
        title="What these results do not show"
        intro={
          <p>
            The results do not show that ResearchCode helps human researchers, that its guides teach effectively,
            or that either workflow is more reliable on harder, longer, or less specified problems. These are the
            main limitations, including problems found after the analysis ran.
          </p>
        }
      >
        <ul className="mt-8 grid gap-5 md:grid-cols-2 lg:grid-cols-3">
          {limitations.map((item) => (
            <li key={item.title} className="rounded-xl border border-line bg-white p-5">
              <h3 className="font-semibold text-ink">{item.title}</h3>
              <p className="mt-2 text-[0.96875rem] leading-7 text-body">{item.body}</p>
            </li>
          ))}
        </ul>
      </Section>

      <Section
        id="report"
        eyebrow="Report and materials"
        title="Read the full research report"
        intro={
          <p>
            The report describes the design, every pre-registered result, the post-hoc diagnostics, and the
            limitations. It is the authoritative account; this page summarises its aggregate results.
          </p>
        }
      >
        {reportUrl ? (
          <div className="mt-6 flex flex-wrap items-center gap-x-5 gap-y-3">
            <a
              href={reportUrl}
              className="rounded-md bg-navy-800 px-5 py-2.5 text-sm font-semibold text-white hover:bg-navy-900"
            >
              Read the full research report (PDF)
            </a>
            <a href={reportSourceUrl} className={inlineLink}>
              Markdown source on GitHub
            </a>
          </div>
        ) : null}
        <div className="mt-8 grid gap-5 md:grid-cols-2">
          {[true, false].map((isPublic) => (
            <section
              key={String(isPublic)}
              aria-labelledby={`materials-${isPublic ? "public" : "private"}`}
              className="rounded-xl border border-line bg-white p-6"
            >
              <h3 id={`materials-${isPublic ? "public" : "private"}`} className="font-semibold text-ink">
                {isPublic ? "Public" : "Kept private"}
              </h3>
              <p className="mt-1 text-sm text-muted">
                {isPublic
                  ? "In the ResearchCode repository and on this site."
                  : "The protocol promised to publish the first three; they were withheld after unblinding. This is a recorded deviation from the publication plan; it changes no method or result."}
              </p>
              <ul className="mt-4 space-y-3">
                {materials
                  .filter((item) => item.public === isPublic)
                  .map((item) => (
                    <li key={item.name}>
                      <p className="font-medium text-ink">{item.name}</p>
                      <p className="text-[0.9375rem] leading-6 text-body">{item.detail}</p>
                    </li>
                  ))}
              </ul>
            </section>
          ))}
        </div>
        <p className="mt-4 max-w-3xl text-[0.9375rem] leading-7 text-body">
          The{" "}
          <a href={protocolUrl} className={inlineLink}>
            protocol
          </a>{" "}
          (version 1.5, with its amendment table), the superseded{" "}
          <a href={protocol14Url} className={inlineLink}>
            version 1.4
          </a>
          , the{" "}
          <a href={aggregateResultsUrl} className={inlineLink}>
            aggregate results
          </a>
          , and the harness are in the{" "}
          <a href={experimentsUrl} className={inlineLink}>
            experiments folder
          </a>
          . Version 1.4 was{" "}
          <a href={protocol14MergeUrl} className={inlineLink}>
            merged on GitHub
          </a>{" "}
          before the first pilot session; the 1.5 amendment was documented within the project during data
          collection and has no independent timestamp before its first unattended trial.
        </p>
      </Section>

      <div id="methods" className="mx-auto mt-24 max-w-6xl border-t border-line px-4 sm:px-6">
        <p className="pt-10 text-sm font-semibold uppercase tracking-wider text-muted">Methods in detail</p>
      </div>

      <Section
        id="question"
        eyebrow="Research question"
        title="What we asked"
        intro={<p>{researchQuestion}</p>}
        className="pt-6!"
      >
        <p className="mt-6 max-w-3xl leading-7 text-body">
          <strong className="font-semibold text-ink">Primary hypothesis.</strong> {primaryHypothesis} Secondary
          questions concerned edge cases and invalid input, the quality of each submission&apos;s own tests,
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
            Each trial was a single session of the same AI coding agent, which no one guided. The structured
            workflow was the only thing that differed between the conditions.
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
        title="How trials were isolated and scored"
        intro={
          <p>
            Generated code was treated as untrusted, and the agent could never reach the hidden evaluator, which
            is kept in a private repository.
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
        title="Unattended sessions at no additional cost"
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

      <Section id="metrics" eyebrow="Metrics" title="What we measured">
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
              ["Confirmatory trials", `${design.confirmatoryTrialsPerCell} per task and condition; all ${sample.analysedTrials} completed`],
              ["Order", `Blocks with every task × condition once, randomised (seed ${design.scheduleSeed})`],
              ["Access", "Claude Code sessions through a Claude Pro subscription, unattended from protocol 1.5; $0 additional spending"],
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
              stratified permutation test of that difference is the only hypothesis test.
            </p>
            <p>
              If any task × condition cell had fewer than {design.minimumValidPerCell} valid trials, all results
              would have been reported as descriptive; every cell had {design.confirmatoryTrialsPerCell}.
              Infrastructure failures were rerun, and the agent&apos;s own failures counted.
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
            A hidden evaluator is only useful if it separates correct code from realistic mistakes. Before any
            trial, we scored our own reference solutions and deliberately defective versions of them. These are
            checks of the scoring system, not experimental results.
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
    </>
  );
}
