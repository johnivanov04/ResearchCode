import type { Metadata } from "next";
import Link from "next/link";
import { Callout } from "@/components/callout";
import { CodeBlock } from "@/components/code-block";
import { PageHeader, Section } from "@/components/page-header";
import { StatusBadge, type Status } from "@/components/status-badge";

export const metadata: Metadata = {
  title: "Starter Kit",
  description:
    "The planned ResearchCode scientific Python template: uv, pytest, Ruff, GitHub Actions, specification templates, and AI assistant instructions.",
};

const components: { name: string; detail: string; status: Status }[] = [
  {
    name: "Guides and checklists",
    detail: "The written workflow the template is built around. Available on this site now.",
    status: "available",
  },
  {
    name: "Project layout with uv",
    detail: "pyproject.toml, uv.lock, and .python-version for Python 3.12+, with a src/ package layout.",
    status: "planned",
  },
  {
    name: "pytest test suite",
    detail: "Example known-answer, property, and edge-case tests, with small fixtures in tests/data/.",
    status: "planned",
  },
  {
    name: "Ruff linting and formatting",
    detail: "A curated rule set including bug-prone patterns and security checks, configured in pyproject.toml.",
    status: "planned",
  },
  {
    name: "GitHub Actions CI",
    detail: "Install from the lock file, lint, check formatting, and run tests on every push and pull request.",
    status: "planned",
  },
  {
    name: "Specification template",
    detail: "docs/SPEC_TEMPLATE.md with the sections from the specification guide.",
    status: "planned",
  },
  {
    name: "AI assistant instructions",
    detail: "A CLAUDE.md / AGENTS.md file that tells assistants the project's rules: follow the spec, never edit tests to pass, no unverified dependencies.",
    status: "planned",
  },
  {
    name: "Provenance helper",
    detail: "A small module that records git commit, parameters, and package versions next to every result.",
    status: "planned",
  },
];

const tree = `my-analysis/
├── pyproject.toml          # metadata, dependencies, Ruff and pytest config
├── uv.lock                 # exact, resolved dependency versions
├── .python-version         # pinned Python version
├── README.md               # how to install, test, and reproduce results
├── CLAUDE.md               # rules for AI coding assistants
├── docs/
│   └── SPEC_TEMPLATE.md    # one-page specification template
├── src/my_analysis/
│   ├── __init__.py
│   ├── io.py               # load and validate input data
│   ├── analysis.py         # pure, testable scientific functions
│   ├── provenance.py       # record how results were produced
│   └── cli.py              # single entry point for the full analysis
├── tests/
│   ├── data/               # small reference fixtures
│   └── test_analysis.py
├── data/raw/               # read-only inputs (large files not committed)
├── results/                # generated outputs (not committed)
└── .github/workflows/ci.yml`;

const commands = `uv sync                      # create the environment from uv.lock
uv run pytest                # run the test suite
uv run ruff check .          # lint
uv run ruff format .         # format
uv run python -m my_analysis.cli data/raw/input.csv --out results/run1`;

const agentRules = `# Rules for AI assistants in this project

- Read docs/ for the specification before changing analysis code.
  If the specification is ambiguous, ask; do not guess.
- Never modify files in tests/ or data/raw/ unless explicitly asked.
- Never loosen a numerical tolerance to make a test pass.
- Add dependencies only with \`uv add\`, and only after confirming
  the package name on PyPI.
- Before finishing, run: uv run ruff check . && uv run pytest`;

export default function StarterKitPage() {
  return (
    <>
      <PageHeader eyebrow="Starter Kit" title="A scientific Python template with the safeguards built in">
        <p>
          The starter kit will be a ready-to-use project template that puts the ResearchCode workflow into
          practice from the first commit: pinned environments, tests, linting, continuous integration, and
          instructions that keep AI assistants within your project&apos;s rules.
        </p>
      </PageHeader>

      <div className="mx-auto max-w-6xl px-4 sm:px-6">
        <Callout tone="honesty" title="Not yet available for download">
          The template is planned for Phase 2 and has not been released. There is nothing to download yet.
          This page describes what it will contain so that you can give feedback on the design. Components
          that you can use today are marked <strong>Available</strong>.
        </Callout>
      </div>

      <Section id="components" eyebrow="Contents" title="What the template will include">
        <div className="mt-8 overflow-hidden rounded-xl border border-line">
          <table className="w-full text-left">
            <caption className="sr-only">Starter kit components and their availability</caption>
            <thead className="bg-surface text-sm">
              <tr>
                <th scope="col" className="px-5 py-3 font-semibold text-ink">Component</th>
                <th scope="col" className="hidden px-5 py-3 font-semibold text-ink md:table-cell">Purpose</th>
                <th scope="col" className="px-5 py-3 text-right font-semibold text-ink">Status</th>
              </tr>
            </thead>
            <tbody>
              {components.map((component) => (
                <tr key={component.name} className="border-t border-line align-top">
                  <th scope="row" className="px-5 py-4 font-medium text-ink">
                    {component.name}
                    <p className="mt-1 text-sm font-normal leading-6 text-body md:hidden">{component.detail}</p>
                  </th>
                  <td className="hidden px-5 py-4 text-[0.96875rem] leading-6 text-body md:table-cell">{component.detail}</td>
                  <td className="px-5 py-4 text-right">
                    <StatusBadge status={component.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      <Section
        id="structure"
        eyebrow="Structure"
        title="Intended directory layout"
        intro={
          <p>
            The layout separates what you write (src, tests, docs) from what you receive (data/raw) and what
            the code produces (results). The names are a proposal and may change during Phase 2.
          </p>
        }
      >
        <div className="mt-2 grid gap-8 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
          <div className="min-w-0">
            <CodeBlock code={tree} language="text" title="planned layout" copyable={false} />
          </div>
          <div className="min-w-0">
            <h3 className="mt-6 text-lg font-semibold text-ink">Design principles</h3>
            <ul className="mt-3 space-y-3 leading-7 text-body">
              <li>
                <strong className="text-ink">Scientific logic in pure functions.</strong> Functions in
                analysis.py take arrays and return values, with no file access, so they are easy to test.
              </li>
              <li>
                <strong className="text-ink">Validate at the boundary.</strong> io.py checks units, columns,
                and ranges once, when data enters the program.
              </li>
              <li>
                <strong className="text-ink">One way to run everything.</strong> cli.py is the single entry
                point, so the README can document one command.
              </li>
              <li>
                <strong className="text-ink">Few dependencies.</strong> NumPy and pandas at runtime; pytest and
                Ruff for development.
              </li>
            </ul>
          </div>
        </div>
      </Section>

      <Section
        id="workflow"
        eyebrow="Daily use"
        title="Planned workflow"
        intro={<p>These are the commands the template is designed around. They will be documented in its README.</p>}
      >
        <div className="mt-2 grid gap-8 lg:grid-cols-2">
          <div className="min-w-0">
            <CodeBlock code={commands} language="bash" title="planned commands" copyable={false} />
          </div>
          <div className="min-w-0">
            <CodeBlock code={agentRules} language="markdown" title="CLAUDE.md (draft excerpt)" copyable={false} />
          </div>
        </div>
      </Section>

      <Section id="meanwhile" eyebrow="Today" title="What you can do now">
        <div className="mt-6 grid gap-5 md:grid-cols-3">
          <Link href="/guides/reproducibility" className="rounded-xl border border-line bg-white p-5 hover:border-navy-200">
            <h3 className="font-semibold text-ink">Set up uv yourself</h3>
            <p className="mt-2 text-[0.96875rem] leading-7 text-body">The reproducibility guide shows the commands to pin an environment today.</p>
          </Link>
          <Link href="/guides/testing-generated-code" className="rounded-xl border border-line bg-white p-5 hover:border-navy-200">
            <h3 className="font-semibold text-ink">Add your first tests</h3>
            <p className="mt-2 text-[0.96875rem] leading-7 text-body">Start with one known-answer test for your most important function.</p>
          </Link>
          <Link href="/guides/writing-specifications" className="rounded-xl border border-line bg-white p-5 hover:border-navy-200">
            <h3 className="font-semibold text-ink">Write a specification</h3>
            <p className="mt-2 text-[0.96875rem] leading-7 text-body">Copy the worked example and adapt it to your own analysis.</p>
          </Link>
        </div>
      </Section>
    </>
  );
}
