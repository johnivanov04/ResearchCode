import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { Callout } from "@/components/callout";
import { CodeBlock } from "@/components/code-block";
import { GrowthExplorer } from "@/components/growth-explorer";
import { PageHeader, Section } from "@/components/page-header";
import { PromptBlock } from "@/components/prompt-block";
import { StatusBadge } from "@/components/status-badge";
import {
  appBlobUrl,
  appMethodStudyUrl,
  appReadmeUrl,
  appSourceUrl,
  appSpecUrl,
  checkCommands,
  figures,
  methodSteps,
  outputs,
  ownDataCommand,
  plateBias,
  plateResults,
  quickStart,
  sampleInputPreview,
  starterContributions,
  websiteWellResult,
} from "@/content/growth-analysis";
import { BLANK_OD, MIN_R2, TRUE_RATE_PER_H, illustrativeReadings } from "@/lib/growth";

export const metadata: Metadata = {
  title: "Example: bacterial growth analysis",
  description:
    "Estimating bacterial growth rates from plate reader data: a representative scientific coding task, its silent failure modes, and a working, tested analysis application built with the ResearchCode starter kit.",
};

const pitfalls = [
  {
    title: "Skipping blank correction",
    body: "Medium and plastic absorb light too. Taking the log of raw OD compresses early growth and lowers the apparent rate. The size of the error depends on how large the blank is relative to the early signal.",
  },
  {
    title: "Mixing logarithm bases",
    body: "The specific growth rate is the slope of the natural log. A slope from log10 is smaller by a factor of about 2.303, and a slope from log2 is a rate in doublings per hour. All three are valid only if labelled correctly.",
  },
  {
    title: "Losing track of time units",
    body: "Plate readers often export time in seconds or minutes, sometimes as a clock time string. A rate computed per minute and labelled per hour is off by a factor of 60.",
  },
  {
    title: "Fitting the wrong part of the curve",
    body: "Only the exponential phase has a constant log slope. Including lag or stationary phase in a single linear fit underestimates the maximum rate. Choosing the window by eye is not reproducible.",
  },
  {
    title: "Ignoring the instrument's linear range",
    body: "At high optical density, readings stop being proportional to cell density. The usable range depends on the instrument, path length, and organism, so it must be checked rather than assumed.",
  },
  {
    title: "Non-positive values before a log",
    body: "After blank subtraction, early readings can be zero or negative. NumPy returns -inf or NaN with only a warning, and downstream code may drop those points without telling you.",
  },
  {
    title: "Averaging replicates at the wrong step",
    body: "Averaging OD across wells and then fitting is not the same as fitting each well and averaging the rates. Either may be appropriate, but the choice should be stated, and the spread across replicates reported.",
  },
];

const inlineLink = "font-medium text-accent-700 underline underline-offset-2 hover:text-accent-800";

function FigureBlock({ figure }: { figure: (typeof figures)[number] }) {
  return (
    <figure className="min-w-0 rounded-xl border border-line bg-white p-3">
      <Image
        src={figure.src}
        alt={figure.alt}
        width={figure.width}
        height={figure.height}
        unoptimized
        className="h-auto w-full"
      />
      <figcaption className="mt-3 px-1 text-sm leading-6 text-muted">
        {figure.caption}{" "}
        <a href={`${appBlobUrl}/${figure.source}`} className={inlineLink}>
          Full-size figure on GitHub
        </a>
        .
      </figcaption>
    </figure>
  );
}

export default function ExamplePage() {
  const [biasA, biasB] = plateBias;
  const readings = illustrativeReadings();
  const preview = readings.slice(0, 8);
  const csvPreview = ["time_min,od600", ...preview.map((r) => `${r.timeMin},${r.od.toFixed(3)}`), "..."].join("\n");

  return (
    <>
      <PageHeader eyebrow="Example" title="Estimating bacterial growth rates">
        <p>
          A short, common analysis with several ways to be silently wrong. We use it throughout ResearchCode
          to show why specifications, tests, and review matter, even for code that looks simple. It is also
          the subject of a{" "}
          <a href="#application" className={inlineLink}>
            working analysis application
          </a>{" "}
          built with the ResearchCode starter kit.
        </p>
      </PageHeader>

      <div className="mx-auto max-w-6xl px-4 sm:px-6">
        <Callout tone="honesty" title="All data on this page is illustrative">
          Every reading on this page is <strong>synthetic</strong>. The interactive example uses a logistic
          growth model with a known rate of 1.2 per hour and a constant blank of {BLANK_OD}, rounded to three
          decimals like an instrument export. The application&apos;s sample plate was generated from models
          with known parameters and seeded noise. None of it describes a real organism or experiment, and none
          of the numbers below is an experimental finding.
        </Callout>
      </div>

      <Section
        id="task"
        eyebrow="The task"
        title="From optical density to a growth rate"
        intro={
          <>
            <p>
              A microplate reader measures the optical density at 600 nm (OD600) of bacterial cultures every
              few minutes. During exponential growth, cell density follows N(t) = N₀·e<sup>μt</sup>, so the
              natural log of the blank-corrected OD rises in a straight line whose slope is the specific
              growth rate μ. The doubling time is ln 2 / μ.
            </p>
            <p className="mt-4">
              The goal is to estimate the maximum specific growth rate, μ<sub>max</sub>, and the doubling
              time for each well. It is the kind of task researchers now routinely hand to an AI assistant.
            </p>
          </>
        }
      >
        <div className="mt-10 grid gap-8 lg:grid-cols-2">
          <div className="min-w-0">
            <h3 className="text-lg font-semibold text-ink">Sample input</h3>
            <p className="mt-2 leading-7 text-body">
              One well, read every 15 minutes for 12 hours. A medium-only blank well reads {BLANK_OD.toFixed(3)}{" "}
              throughout.
            </p>
            <CodeBlock code={csvPreview} language="csv" title="plate1_well_B3.csv (synthetic, first rows)" />
          </div>
          <div className="min-w-0">
            <h3 className="text-lg font-semibold text-ink">Two ways to ask for the code</h3>
            <PromptBlock
              title="Unstructured"
              prompt="Here's my plate reader CSV. Write Python to get the growth rate."
              note="Every decision listed under Pitfalls below is left to the assistant."
            />
            <PromptBlock
              title="Structured"
              prompt="Implement max_specific_growth_rate() as defined in docs/spec-growth-rate.md. Time is in minutes in the CSV; convert to hours. Do not write tests. Stop and ask if anything in the spec is ambiguous."
              note="The specification fixes units, log base, blank handling, and the window rule."
            />
          </div>
        </div>
      </Section>

      <Section
        id="explorer"
        eyebrow="Interactive"
        title="Same data, five analyses"
        intro={
          <p>
            Each option below runs on the same synthetic readings. Only the first follows the specification
            from the{" "}
            <Link href="/guides/writing-specifications" className="font-medium text-accent-700 underline underline-offset-2">
              specification guide
            </Link>
            : subtract the blank, take the natural log, and use the steepest one-hour window with R² ≥ {MIN_R2}.
            None of the mistakes raises an error.
          </p>
        }
      >
        <GrowthExplorer />
      </Section>

      <Section
        id="pitfalls"
        eyebrow="Pitfalls"
        title="What can go wrong without an error message"
        intro={<p>Each of these produces a plausible-looking number. Most are easy to miss in a code review that only checks whether the code runs.</p>}
      >
        <ol className="mt-10 grid gap-5 md:grid-cols-2">
          {pitfalls.map((pitfall, index) => (
            <li key={pitfall.title} className="flex gap-4 rounded-xl border border-line bg-white p-5">
              <span className="font-mono text-sm font-medium text-accent-700">{String(index + 1).padStart(2, "0")}</span>
              <div>
                <h3 className="font-semibold text-ink">{pitfall.title}</h3>
                <p className="mt-2 text-[0.96875rem] leading-7 text-body">{pitfall.body}</p>
              </div>
            </li>
          ))}
        </ol>
      </Section>

      <Section
        id="validation"
        eyebrow="Validation"
        title="How to know the answer is right"
        intro={<p>No single check is enough. Together, these make a silent error unlikely to survive.</p>}
      >
        <div className="mt-10 grid gap-5 md:grid-cols-2">
          {[
            {
              title: "Recover a known rate",
              body: "Generate synthetic data with a rate you choose and confirm the code returns it within a justified tolerance. This page does exactly that.",
              link: { href: "/guides/testing-generated-code", label: "Testing guide" },
            },
            {
              title: "Test invariants",
              body: "Scaling the signal or shifting the time axis must not change the rate. These tests catch errors that a single example can miss.",
              link: { href: "/guides/testing-generated-code", label: "Property tests" },
            },
            {
              title: "Look at the fit",
              body: "Plot the log-transformed data with the selected window and fitted line for every well. A human glance catches windows in the wrong phase.",
            },
            {
              title: "Compare independently",
              body: "Check a subset of wells against an established growth-curve tool or a manual calculation, and check that values are plausible for your organism and conditions.",
            },
          ].map((item) => (
            <div key={item.title} className="rounded-xl border border-line bg-white p-5">
              <h3 className="font-semibold text-ink">{item.title}</h3>
              <p className="mt-2 text-[0.96875rem] leading-7 text-body">{item.body}</p>
              {item.link ? (
                <Link href={item.link.href} className="mt-3 inline-block text-sm font-medium text-accent-700 hover:text-accent-800">
                  {item.link.label} <span aria-hidden="true">→</span>
                </Link>
              ) : null}
            </div>
          ))}
        </div>

        <details className="mt-10 rounded-xl border border-line bg-white">
          <summary className="cursor-pointer px-5 py-4 text-sm font-semibold text-ink">
            View all {readings.length} synthetic readings as a table
          </summary>
          <div className="max-h-96 overflow-auto border-t border-line">
            <table className="w-full text-left text-sm">
              <caption className="sr-only">Synthetic OD600 readings for one well, generated from a logistic model</caption>
              <thead className="sticky top-0 bg-surface">
                <tr>
                  <th scope="col" className="px-5 py-2 font-medium text-ink">Time (min)</th>
                  <th scope="col" className="px-5 py-2 font-medium text-ink">Raw OD600</th>
                  <th scope="col" className="px-5 py-2 font-medium text-ink">OD600 − blank</th>
                </tr>
              </thead>
              <tbody className="font-mono text-body">
                {readings.map((r) => (
                  <tr key={r.timeMin} className="border-t border-line">
                    <td className="px-5 py-1.5">{r.timeMin}</td>
                    <td className="px-5 py-1.5">{r.od.toFixed(3)}</td>
                    <td className="px-5 py-1.5">{(r.od - BLANK_OD).toFixed(3)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      </Section>

      <Section
        id="application"
        eyebrow="Phase 3"
        title="The working application: growth-analysis"
        intro={
          <>
            <p>
              <code className="font-mono text-[0.9375rem]">growth-analysis</code> is a command-line tool that
              reads optical density time courses for many wells, finds each well&apos;s exponential phase,
              estimates the specific growth rate and doubling time, judges whether each fit is credible, plots
              every fit, and summarises replicate wells by condition. It was built from the{" "}
              <Link href="/starter-kit" className={inlineLink}>
                starter kit
              </Link>
              , following a written specification and validated against known answers on synthetic data.
            </p>
          </>
        }
      >
        <div className="mt-8 flex flex-col gap-4 rounded-xl border border-line bg-surface p-6 sm:flex-row sm:items-start">
          <StatusBadge status="available" />
          <div className="leading-7 text-body">
            <p>
              The source, specification, tests, synthetic sample data, and example outputs are in the{" "}
              <a href={appSourceUrl} className={inlineLink}>
                growth-analysis folder of the ResearchCode repository
              </a>
              . Like the starter kit, it is a folder you clone or copy, not a published package. Read the{" "}
              <a href={appReadmeUrl} className={inlineLink}>
                README
              </a>{" "}
              for every option and output.
            </p>
          </div>
        </div>

        <div className="mt-10 max-w-4xl">
          <h3 className="text-lg font-semibold text-ink">Run it on the sample data</h3>
          <p className="mt-2 leading-7 text-body">
            Install <a href="https://docs.astral.sh/uv/" className={inlineLink}>uv</a> once; it also installs
            Python. Then:
          </p>
          <CodeBlock code={quickStart} language="bash" title="Terminal" />
          <p className="leading-7 text-body">For your own plate, export it in the same format and run:</p>
          <CodeBlock code={ownDataCommand} language="bash" title="Terminal" />
          <p className="leading-7 text-body">The checks that CI runs on every change:</p>
          <CodeBlock code={checkCommands} language="bash" title="Terminal" />
        </div>

        <div className="mt-6 grid gap-8 lg:grid-cols-2">
          <div className="min-w-0">
            <h3 className="text-lg font-semibold text-ink">Input: one row per reading</h3>
            <p className="mt-2 leading-7 text-body">
              Columns <code className="font-mono text-sm">well</code>,{" "}
              <code className="font-mono text-sm">condition</code>,{" "}
              <code className="font-mono text-sm">od600</code>, and a time column whose name states its unit (
              <code className="font-mono text-sm">time_h</code>, <code className="font-mono text-sm">time_min</code>,
              or <code className="font-mono text-sm">time_s</code>). Blank wells use the condition{" "}
              <code className="font-mono text-sm">blank</code>.
            </p>
            <CodeBlock code={sampleInputPreview} language="csv" title="data/sample/synthetic_plate.csv (synthetic, first rows)" />
          </div>
          <div className="min-w-0">
            <h3 className="text-lg font-semibold text-ink">Output</h3>
            <dl className="mt-3 divide-y divide-line rounded-xl border border-line bg-white">
              {outputs.map((output) => (
                <div key={output.file} className="px-4 py-3 sm:grid sm:grid-cols-[13.5rem_minmax(0,1fr)] sm:gap-4">
                  <dt className="font-mono text-sm text-ink [overflow-wrap:anywhere]">{output.file}</dt>
                  <dd className="mt-1 text-sm leading-6 text-body sm:mt-0">{output.contents}</dd>
                </div>
              ))}
            </dl>
          </div>
        </div>
      </Section>

      <Section
        id="method"
        eyebrow="Method"
        title="How the growth rate is estimated"
        intro={
          <p>
            During exponential growth, OD(t) = OD₀·e<sup>μt</sup>, so ln OD(t) = ln OD₀ + μt is a straight line
            whose slope is the specific growth rate μ, and the doubling time is ln 2 / μ. The work is in choosing
            which readings belong to that straight line. The full rules are in the{" "}
            <a href={appSpecUrl} className={inlineLink}>
              specification
            </a>
            .
          </p>
        }
      >
        <ol className="mt-10 grid gap-5 md:grid-cols-2 lg:grid-cols-3">
          {methodSteps.map((step, index) => (
            <li key={step.title} className="flex gap-4 rounded-xl border border-line bg-white p-5">
              <span className="font-mono text-sm font-medium text-accent-700">{String(index + 1).padStart(2, "0")}</span>
              <div>
                <h3 className="font-semibold text-ink">{step.title}</h3>
                <p className="mt-2 text-[0.96875rem] leading-7 text-body">{step.body}</p>
              </div>
            </li>
          ))}
        </ol>

        <div className="mt-10 max-w-3xl rounded-xl border border-line bg-surface p-6">
          <h3 className="font-semibold text-ink">Why not report the steepest window?</h3>
          <p className="mt-2 leading-7 text-body">
            The interactive example above, like many analyses, reports the steepest one-hour window. With noisy
            readings, the steepest of many windows is biased upward: in a{" "}
            <a href={appMethodStudyUrl} className={inlineLink}>
              study on synthetic data
            </a>
            , on exponential curves with noise proportional to OD, it overestimated the rate by about 3%, 9%,
            and 16% at increasing noise levels, while the application&apos;s estimate was off by 0.0%, 0.2%,
            and 3.2%. The same study showed that keeping readings within three blank standard deviations let
            noise near the blank inflate the estimates, which is why the application requires ten. It also
            showed that this does not remove the problem: for slow growth starting near that limit, estimates
            remain biased upward (section below).
          </p>
        </div>
      </Section>

      <Section
        id="results"
        eyebrow="Example output"
        title="What the application reports on synthetic data"
        intro={
          <p>
            These results are the application&apos;s actual output, committed to the repository and checked by
            the website&apos;s tests. Because the data are synthetic, the parameters that generated them are
            known, and the estimates can be compared with them.
          </p>
        }
      >
        <div className="mt-10 grid items-start gap-8 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
          <div className="min-w-0">
            <h3 className="text-lg font-semibold text-ink">This page&apos;s illustrative well</h3>
            <dl className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
              <div className="rounded-lg border border-line bg-white p-3">
                <dt className="text-xs text-muted">Growth rate</dt>
                <dd className="mt-1 font-mono text-lg font-medium text-ink">{websiteWellResult.ratePerH.toFixed(3)} h⁻¹</dd>
              </div>
              <div className="rounded-lg border border-line bg-white p-3">
                <dt className="text-xs text-muted">Doubling time</dt>
                <dd className="mt-1 font-mono text-lg font-medium text-ink">{websiteWellResult.doublingTimeMin.toFixed(1)} min</dd>
              </div>
              <div className="rounded-lg border border-line bg-white p-3">
                <dt className="text-xs text-muted">Exponential phase</dt>
                <dd className="mt-1 font-mono text-lg font-medium text-ink">
                  {websiteWellResult.phaseStartH}–{websiteWellResult.phaseEndH} h
                </dd>
              </div>
            </dl>
            <p className="mt-4 leading-7 text-body">
              The curve was generated with a logistic intrinsic rate of {TRUE_RATE_PER_H} per hour, but the
              application reports {websiteWellResult.ratePerH.toFixed(3)}. That is expected, not an error. In
              logistic growth the rate falls as the culture grows, and the application reports the average rate
              over the whole exponential phase ({websiteWellResult.pointsInPhase} readings, R² ={" "}
              {websiteWellResult.rSquared.toFixed(3)}), which is lower than the intrinsic rate. The tests check it
              against a mathematical bound instead of demanding 1.2. The steepest one-hour window here gives{" "}
              {websiteWellResult.steepestWindowRatePerH.toFixed(3)} per hour, close to the intrinsic rate, because
              these readings carry almost no noise and logistic growth is fastest at the start.
            </p>
          </div>
          <FigureBlock figure={figures[0]} />
        </div>

        <h3 className="mt-14 text-lg font-semibold text-ink">A synthetic plate with three conditions</h3>
        <p className="mt-2 max-w-3xl leading-7 text-body">
          Three replicate wells per condition, three blank wells, readings every 15 minutes for 16 hours, with
          multiplicative and additive noise. Only credible fits enter the condition means.
        </p>
        <div className="mt-6 overflow-x-auto rounded-xl border border-line bg-white">
          <table className="w-full min-w-[36rem] text-left text-sm">
            <caption className="sr-only">Growth rates by condition estimated from the synthetic sample plate</caption>
            <thead className="bg-surface">
              <tr>
                <th scope="col" className="px-4 py-2.5 font-medium text-ink">Condition</th>
                <th scope="col" className="px-4 py-2.5 font-medium text-ink">Model rate r (h⁻¹)</th>
                <th scope="col" className="px-4 py-2.5 font-medium text-ink">Credible wells</th>
                <th scope="col" className="px-4 py-2.5 font-medium text-ink">Mean μ ± SD (h⁻¹)</th>
                <th scope="col" className="px-4 py-2.5 font-medium text-ink">Doubling time of mean (h)</th>
              </tr>
            </thead>
            <tbody className="text-body">
              {plateResults.map((row) => (
                <tr key={row.condition} className="border-t border-line">
                  <th scope="row" className="px-4 py-2.5 font-mono font-normal text-ink">{row.condition}</th>
                  <td className="px-4 py-2.5 font-mono">{row.modelRatePerH === null ? "no growth" : row.modelRatePerH.toFixed(1)}</td>
                  <td className="px-4 py-2.5 font-mono">
                    {row.credible} of {row.wells}
                  </td>
                  <td className="px-4 py-2.5 font-mono">
                    {row.meanRatePerH === null
                      ? "no growth detected"
                      : `${row.meanRatePerH.toFixed(3)} ± ${row.sdRatePerH?.toFixed(3)}`}
                  </td>
                  <td className="px-4 py-2.5 font-mono">{row.doublingTimeH === null ? "—" : row.doublingTimeH.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-4 max-w-3xl leading-7 text-body">
          Even without noise, the method reports an average over the exponential phase that is below r:{" "}
          {biasA.noiseFreeOverR.toFixed(3)} r for condition_A and {biasB.noiseFreeOverR.toFixed(3)} r for
          condition_B. condition_A&apos;s estimate is close to that. condition_B&apos;s is not: it is above its
          noise-free value, and two wells even exceed r. Over 150 simulated plates, condition_B&apos;s estimates
          averaged {biasB.biasPercent.toFixed(1)}% too high (condition_A&apos;s {biasA.biasPercent.toFixed(1)}%), because for slow growth starting near the
          quantification limit the window search still favours noisy readings. The method study found and
          measured this bias; it is documented as a limitation, not yet corrected. This is why the figures,
          standard errors, and replicates matter, and why synthetic results like these say nothing about real
          cultures.
        </p>
        <div className="mt-10 grid items-start gap-8 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
          <FigureBlock figure={figures[1]} />
          <FigureBlock figure={figures[2]} />
        </div>
      </Section>

      <Section
        id="starter"
        eyebrow="Built with the starter kit"
        title="How the ResearchCode workflow shaped it"
        intro={
          <p>
            The application started as a copy of the Phase 2 starter kit. Its specification template, test
            setup, security rules, assistant instructions, and run-metadata module carried over, and the same
            workflow found and fixed two real weaknesses in the first version of the method.
          </p>
        }
      >
        <div className="mt-10 grid gap-5 md:grid-cols-2 lg:grid-cols-3">
          {starterContributions.map((item) => (
            <div key={item.title} className="rounded-xl border border-line bg-white p-5">
              <h3 className="font-semibold text-ink">{item.title}</h3>
              <p className="mt-2 text-[0.96875rem] leading-7 text-body">{item.body}</p>
            </div>
          ))}
        </div>
        <p className="mt-8 max-w-3xl leading-7 text-body">
          <strong className="font-semibold text-ink">Limits.</strong> One exponential phase per well; no lag-time
          or growth-model fitting; one constant blank per plate; descriptive comparisons without significance
          tests; an upward bias for slow growth near the quantification limit; validated on synthetic data
          only, not on real experimental measurements. CI runs on Ubuntu with Python 3.12 and 3.13. Always
          look at the figure for every well before using a number.
        </p>
      </Section>
    </>
  );
}
