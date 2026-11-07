import type { Metadata } from "next";
import Link from "next/link";
import { Callout } from "@/components/callout";
import { CodeBlock } from "@/components/code-block";
import { GrowthExplorer } from "@/components/growth-explorer";
import { PageHeader, Section } from "@/components/page-header";
import { PromptBlock } from "@/components/prompt-block";
import { StatusBadge } from "@/components/status-badge";
import { BLANK_OD, MIN_R2, illustrativeReadings } from "@/lib/growth";

export const metadata: Metadata = {
  title: "Example: bacterial growth analysis",
  description:
    "Estimating bacterial growth rates from plate reader data: a representative scientific coding task, its silent failure modes, and how to validate the result.",
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

export default function ExamplePage() {
  const readings = illustrativeReadings();
  const preview = readings.slice(0, 8);
  const csvPreview = ["time_min,od600", ...preview.map((r) => `${r.timeMin},${r.od.toFixed(3)}`), "..."].join("\n");

  return (
    <>
      <PageHeader eyebrow="Example" title="Estimating bacterial growth rates">
        <p>
          A short, common analysis with several ways to be silently wrong. We use it throughout ResearchCode
          to show why specifications, tests, and review matter, even for code that looks simple.
        </p>
      </PageHeader>

      <div className="mx-auto max-w-6xl px-4 sm:px-6">
        <Callout tone="honesty" title="All data on this page is illustrative">
          The readings below are <strong>synthetic</strong>. They were generated from a logistic growth model
          with a known rate of 1.2 per hour and a constant blank of {BLANK_OD}, then rounded to three decimals
          like an instrument export. They do not describe any real organism or experiment. The full analysis
          package, built with the ResearchCode starter kit, is planned for Phase 3.
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

      <Section id="status" eyebrow="What comes next" title="The full demonstration">
        <div className="mt-6 flex flex-col gap-4 rounded-xl border border-line bg-surface p-6 sm:flex-row sm:items-start">
          <StatusBadge status="planned" />
          <p className="leading-7 text-body">
            In Phase 3 we will build a complete growth-curve analysis package with the ResearchCode starter
            kit: a written specification, a test suite with known-answer and property tests, multi-well input
            handling, plots of every fit, and provenance records. This page will then link to the real code
            and its outputs.
          </p>
        </div>
      </Section>
    </>
  );
}
