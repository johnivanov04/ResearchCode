import type { Metadata } from "next";
import Link from "next/link";
import { Callout } from "@/components/callout";
import { CodeBlock } from "@/components/code-block";
import { PageHeader, Section } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import {
  checkCommands,
  copyCommands,
  dailyCommands,
  exampleCommand,
  starterComponents,
  starterDirectory,
  starterSourceUrl,
  starterTree,
  starterVersion,
} from "@/content/starter-kit";

export const metadata: Metadata = {
  title: "Starter Kit",
  description:
    "A working scientific Python starter project: uv, pytest, Hypothesis, Ruff with security rules, GitHub Actions, a specification template, AI assistant instructions, and run metadata.",
};

const benefits = [
  {
    title: "The same environment everywhere",
    body: "uv installs the exact package versions recorded in uv.lock, on your laptop, a collaborator's machine, and in CI.",
  },
  {
    title: "Tests that check the science",
    body: "The example tests compare against known answers and a high-precision reference, not just whether the code runs.",
  },
  {
    title: "Guardrails for AI-written code",
    body: "Assistant instructions, a specification template, Ruff's security rules, and CI catch many problems before they reach a result.",
  },
  {
    title: "Results you can trace",
    body: "Every result can carry a record of the code version, package versions, parameters, seeds, and input checksums.",
  },
];

const notIncluded = [
  "Growth-curve fitting over many readings, phase detection, or replicate handling. The starter's example covers two readings only; the full analysis is a separate application built from the starter (see below).",
  "A separate GitHub template repository or a published package. You copy a folder, as described above.",
  "Testing on Windows or macOS in CI. The workflow runs on Ubuntu with Python 3.12 and 3.13.",
  "A license. ResearchCode has not chosen one yet.",
];

const inlineLink = "font-medium text-accent-700 underline underline-offset-2 hover:text-accent-800";

export default function StarterKitPage() {
  return (
    <>
      <PageHeader eyebrow="Starter Kit" title="A scientific Python template with the safeguards built in">
        <p>
          A working project you can copy and build on: a locked environment, meaningful tests, linting with
          security rules, continuous integration, and instructions that keep AI assistants within your
          project&apos;s rules.
        </p>
      </PageHeader>

      <div className="mx-auto max-w-6xl px-4 sm:px-6">
        <Callout tone="honesty" title="Where the starter lives">
          The starter kit (version {starterVersion}) is the <code className="code-inline">{starterDirectory}/</code>{" "}
          folder of the ResearchCode repository. It is not a separate GitHub template repository and there is no
          download package: you copy the folder into a new project, as shown below.{" "}
          <a href={starterSourceUrl} className={inlineLink}>
            View the source on GitHub
          </a>
          .
        </Callout>
      </div>

      <Section
        id="components"
        eyebrow="Contents"
        title="What the starter includes"
        intro={<p>Every component below is implemented and checked by the starter&apos;s own tests and CI.</p>}
      >
        <div className="mt-8 overflow-hidden rounded-xl border border-line">
          <table className="w-full text-left">
            <caption className="sr-only">Starter kit components, their purpose, files, and availability</caption>
            <thead className="bg-surface text-sm">
              <tr>
                <th scope="col" className="px-5 py-3 font-semibold text-ink">Component</th>
                <th scope="col" className="hidden px-5 py-3 font-semibold text-ink md:table-cell">Purpose</th>
                <th scope="col" className="px-5 py-3 text-right font-semibold text-ink">Status</th>
              </tr>
            </thead>
            <tbody>
              {starterComponents.map((component) => (
                <tr key={component.name} className="border-t border-line align-top">
                  <th scope="row" className="px-5 py-4 font-medium text-ink">
                    {component.name}
                    <p className="mt-1 text-sm font-normal leading-6 text-body md:hidden">{component.detail}</p>
                    <p className="mt-1.5 font-mono text-xs font-normal leading-5 text-muted [overflow-wrap:anywhere]">
                      {component.paths.join(", ")}
                    </p>
                  </th>
                  <td className="hidden px-5 py-4 text-[0.96875rem] leading-6 text-body md:table-cell">{component.detail}</td>
                  <td className="px-5 py-4 text-right">
                    <StatusBadge status="available" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      <Section id="benefits" eyebrow="Why use it" title="What the safeguards give you">
        <ul className="mt-8 grid gap-5 md:grid-cols-2">
          {benefits.map((benefit) => (
            <li key={benefit.title} className="rounded-xl border border-line bg-white p-6">
              <h3 className="font-semibold text-ink">{benefit.title}</h3>
              <p className="mt-2 leading-7 text-body">{benefit.body}</p>
            </li>
          ))}
        </ul>
      </Section>

      <Section
        id="setup"
        eyebrow="Get started"
        title="Copy it into your own project"
        intro={
          <p>
            You need <a href="https://docs.astral.sh/uv/getting-started/installation/" className={inlineLink}>uv</a>{" "}
            and git. uv downloads the right Python version itself. The commands below work in a macOS or Linux
            terminal; the starter&apos;s README gives the Windows equivalents.
          </p>
        }
      >
        <ol className="mt-8 space-y-8">
          <li className="min-w-0">
            <h3 className="text-lg font-semibold text-ink">1. Copy the starter out of the ResearchCode repository</h3>
            <p className="mt-2 max-w-2xl leading-7 text-body">
              The copy is a complete, independent project. Replace <code className="code-inline">my-analysis</code> with
              your project&apos;s name.
            </p>
            <CodeBlock code={copyCommands} language="bash" title="terminal" />
          </li>
          <li className="min-w-0">
            <h3 className="text-lg font-semibold text-ink">2. Install and run every check</h3>
            <p className="mt-2 max-w-2xl leading-7 text-body">
              <code className="code-inline">uv sync --locked</code> installs exactly what <code className="code-inline">uv.lock</code>{" "}
              specifies. The other three commands are the checks CI runs on every push.
            </p>
            <CodeBlock code={checkCommands} language="bash" title="terminal" />
          </li>
          <li className="min-w-0">
            <h3 className="text-lg font-semibold text-ink">3. Run the example</h3>
            <p className="mt-2 max-w-2xl leading-7 text-body">
              It reads two illustrative readings in which optical density doubles in two hours, prints a growth rate of
              0.346574 per hour and a doubling time of 2 hours, and writes the result with its run metadata.
            </p>
            <CodeBlock code={exampleCommand} language="bash" title="terminal" />
          </li>
          <li className="min-w-0">
            <h3 className="text-lg font-semibold text-ink">4. Make it yours</h3>
            <p className="mt-2 max-w-2xl leading-7 text-body">
              Rename the package (four steps in the README), write a specification from{" "}
              <code className="code-inline">docs/SPEC_TEMPLATE.md</code>, turn its known answers into tests, then
              implement. Push the project to your own GitHub repository and its CI workflow starts running.
            </p>
          </li>
        </ol>
      </Section>

      <Section
        id="structure"
        eyebrow="Structure"
        title="What is in the folder"
        intro={
          <p>
            Calculations live in pure functions that are easy to test; reading files and writing results happen in
            one entry point; inputs are read-only and results are never overwritten silently.
          </p>
        }
      >
        <div className="mt-2 grid gap-8 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
          <div className="min-w-0">
            <CodeBlock code={starterTree.map((entry) => entry.line).join("\n")} language="text" title="scientific-starter/" copyable={false} />
          </div>
          <div className="min-w-0">
            <h3 className="mt-6 text-lg font-semibold text-ink">Everyday commands</h3>
            <CodeBlock code={dailyCommands} language="bash" title="terminal" />
            <p className="text-sm leading-6 text-muted">
              Never use <code className="code-inline">pip install</code> in the project: packages added that way are missing
              from <code className="code-inline">uv.lock</code>, so collaborators and CI do not get them.
            </p>
          </div>
        </div>
      </Section>

      <Section
        id="example"
        eyebrow="Worked example"
        title="A small calculation, tested properly"
        intro={
          <p>
            The example computes the specific growth rate between two optical density readings, μ = ln(OD₂ / OD₁) /
            (t₂ − t₁), and the doubling time ln 2 / μ. It is small, but its specification defines units, zero and
            negative growth, and every invalid input, and its tests check the mathematics.
          </p>
        }
      >
        <div className="mt-8 grid gap-5 md:grid-cols-3">
          <div className="rounded-xl border border-line bg-white p-5">
            <h3 className="font-semibold text-ink">Known answers</h3>
            <p className="mt-2 text-[0.96875rem] leading-7 text-body">
              OD doubling from 0.1 to 0.2 in 2 hours must give μ = ln 2 / 2 ≈ 0.34657359 per hour and a doubling time
              of 2 hours, within a stated tolerance.
            </p>
          </div>
          <div className="rounded-xl border border-line bg-white p-5">
            <h3 className="font-semibold text-ink">Properties</h3>
            <p className="mt-2 text-[0.96875rem] leading-7 text-body">
              Hypothesis checks thousands of inputs: rescaling OD or shifting the time origin must not change μ, and
              results must match a 50-digit reference calculation.
            </p>
          </div>
          <div className="rounded-xl border border-line bg-white p-5">
            <h3 className="font-semibold text-ink">A real catch</h3>
            <p className="mt-2 text-[0.96875rem] leading-7 text-body">
              During development, a property test showed that the textbook ln(OD₂) − ln(OD₁) reports zero growth for
              two nearly equal large readings. The implementation was fixed, not the test.
            </p>
          </div>
        </div>
        <p className="mt-6 max-w-2xl leading-7 text-body">
          The <Link href="/example" className={inlineLink}>example page</Link> shows what goes wrong in a full
          growth-curve analysis and presents growth-analysis, a working application built from this starter. The{" "}
          <Link href="/guides/writing-specifications" className={inlineLink}>specification guide</Link> explains how to
          write a specification like the one in the starter.
        </p>
      </Section>

      <Section id="limitations" eyebrow="Scope" title="What the starter does not include">
        <ul className="mt-6 max-w-3xl list-disc space-y-3 pl-5 leading-7 text-body marker:text-muted">
          {notIncluded.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
        <p className="mt-6 max-w-3xl leading-7 text-body">
          For a complete multi-well analysis built from this starter, see{" "}
          <Link href="/example#application" className={inlineLink}>
            the growth-analysis application
          </Link>
          .
        </p>
        <p className="mt-4 max-w-3xl leading-7 text-body">
          Automated checks cannot guarantee correct or secure software. The starter makes many mistakes visible early;
          a person still has to review every change and decide whether the science is right.
        </p>
      </Section>
    </>
  );
}
