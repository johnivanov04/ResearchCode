import Link from "next/link";
import { CodeBlock } from "@/components/code-block";
import { Section } from "@/components/page-header";
import { StatusBadge, type Status } from "@/components/status-badge";
import { WorkflowDiagram } from "@/components/workflow-diagram";
import { site } from "@/content/site";

const heroTest = `def test_recovers_known_growth_rate():
    # Synthetic culture growing at exactly 0.8 / h
    time_h = np.arange(0.0, 6.0, 0.25)
    od = 0.04 + 0.02 * np.exp(0.8 * time_h)

    result = max_specific_growth_rate(
        time_h, od, blank_od=0.04
    )

    # Expected value comes from the model,
    # not from running the code
    np.testing.assert_allclose(
        result.mu_max, 0.8, rtol=1e-6
    )`;

const problems = [
  {
    title: "Code that runs is not code that is correct",
    body: "The costly errors in scientific code rarely crash. A wrong logarithm base, a unit conversion applied twice, or rows dropped without notice still produce a plausible number.",
  },
  {
    title: "Assistants fill gaps with plausible guesses",
    body: "When a request leaves a scientific choice unstated, an AI assistant makes one for you. The guess is often reasonable, rarely flagged, and sometimes wrong for your experiment.",
  },
  {
    title: "Research code outlives the first result",
    body: "Reviewers, collaborators, and your future self need to rerun the analysis. Hidden state on one laptop, unpinned packages, and unrecorded parameters make that impossible.",
  },
];

const audiences = [
  {
    who: "PhD students and postdocs",
    what: "who write most of a lab's analysis code and want a dependable way to use AI assistants without slowing down.",
  },
  {
    who: "Faculty and group leaders",
    what: "who need shared practices that make students' code reviewable and their published results defensible.",
  },
  {
    who: "Research staff and data scientists",
    what: "who maintain pipelines that several projects depend on and must keep them correct as they change.",
  },
];

const toolkit: { title: string; body: string; href: string; status: Status; cta: string }[] = [
  {
    title: "Practical guides",
    body: "Specifications, testing, reviewing AI changes, and reproducibility, each with checklists and copyable prompts.",
    href: "/guides",
    status: "available",
    cta: "Read the guides",
  },
  {
    title: "Scientific Python starter kit",
    body: "A working project template with uv, pytest, Hypothesis, Ruff, GitHub Actions, and instructions for AI assistants.",
    href: "/starter-kit",
    status: "available",
    cta: "Use the starter kit",
  },
  {
    title: "Worked example",
    body: "Estimating bacterial growth rates: a realistic task with several ways to be silently wrong, and a working, tested analysis application built with the starter kit.",
    href: "/example",
    status: "available",
    cta: "Explore the example",
  },
  {
    title: "Evaluation",
    body: "A planned comparison of unstructured prompting and the structured workflow on the same scientific tasks.",
    href: "/evaluation",
    status: "planned",
    cta: "Read the study design",
  },
];

export default function HomePage() {
  return (
    <>
      <section aria-labelledby="hero-heading" className="border-b border-line bg-surface">
        <div className="mx-auto grid max-w-6xl items-center gap-12 px-4 pb-16 pt-14 sm:px-6 sm:pt-20 lg:grid-cols-[1.05fr_1fr]">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wider text-accent-700">
              Open-source guides and toolkit for researchers
            </p>
            <h1
              id="hero-heading"
              className="mt-4 text-4xl font-semibold tracking-tight text-ink sm:text-5xl sm:leading-[1.08]"
            >
              Build research software with AI.{" "}
              <span className="text-navy-700">Trust the results.</span>
            </h1>
            <p className="mt-6 max-w-xl text-lg leading-8 text-body">
              {site.name} helps scientists use AI coding assistants to write analysis code that is
              correct, maintainable, and reproducible. AI makes code easy to generate; it does not
              make it right. We show the engineering habits that close that gap.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link
                href="/guides"
                className="rounded-md bg-navy-800 px-5 py-2.5 text-sm font-semibold text-white hover:bg-navy-900"
              >
                Read the guides
              </Link>
              <a
                href="#workflow"
                className="rounded-md border border-line bg-white px-5 py-2.5 text-sm font-semibold text-ink hover:border-navy-200"
              >
                See the workflow
              </a>
            </div>
          </div>
          <div className="min-w-0">
            <CodeBlock code={heroTest} language="python" title="tests/test_rates.py" />
            <p className="-mt-3 text-sm text-muted">
              A known-answer test: if the code cannot recover a growth rate you put in, it will not recover
              the one in your experiment.
            </p>
          </div>
        </div>
      </section>

      <Section
        id="problem"
        eyebrow="The reliability problem"
        title="AI changes how research code is written, not what makes it trustworthy"
        intro={
          <p>
            Coding assistants let researchers build in an afternoon what used to take weeks. The same speed
            makes it easy to skip the steps that catch mistakes: deciding what correct means, testing against
            known answers, reviewing changes, and recording how results were produced.
          </p>
        }
      >
        <ul className="mt-10 grid gap-5 md:grid-cols-3">
          {problems.map((problem) => (
            <li key={problem.title} className="rounded-xl border border-line bg-white p-6">
              <h3 className="text-lg font-semibold leading-snug text-ink">{problem.title}</h3>
              <p className="mt-3 leading-7 text-body">{problem.body}</p>
            </li>
          ))}
        </ul>
      </Section>

      <Section
        id="workflow"
        eyebrow="The structured workflow"
        title="Five stages from idea to a result you can defend"
        intro={
          <p>
            The workflow keeps scientific decisions with you and gives the assistant well-defined jobs. It
            adds minutes per function, not days, and the artifacts it produces double as documentation.
          </p>
        }
      >
        <WorkflowDiagram />
      </Section>

      <Section
        id="toolkit"
        eyebrow="The toolkit"
        title="What ResearchCode provides"
        intro={
          <p>
            ResearchCode is being built in phases. Each component is labelled with its current status, so you
            always know what you can use today.
          </p>
        }
      >
        <ul className="mt-10 grid gap-5 md:grid-cols-2">
          {toolkit.map((item) => (
            <li key={item.title}>
              <Link
                href={item.href}
                className="group flex h-full flex-col rounded-xl border border-line bg-white p-6 transition-colors hover:border-navy-200 hover:bg-surface"
              >
                <div className="flex items-start justify-between gap-4">
                  <h3 className="text-lg font-semibold text-ink group-hover:text-navy-700">{item.title}</h3>
                  <StatusBadge status={item.status} />
                </div>
                <p className="mt-3 flex-1 leading-7 text-body">{item.body}</p>
                <span className="mt-5 text-sm font-medium text-accent-700">
                  {item.cta} <span aria-hidden="true">→</span>
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </Section>

      <Section
        id="audience"
        eyebrow="Who it is for"
        title="Researchers who write code, but were never trained as software engineers"
        intro={
          <p>
            You do not need a computer science background. If you write Python for your research and use, or
            are considering, tools such as Claude Code, ChatGPT, or GitHub Copilot, this material is for you.
          </p>
        }
      >
        <dl className="mt-10 grid gap-x-8 gap-y-6 border-t border-line pt-8 md:grid-cols-3">
          {audiences.map((audience) => (
            <div key={audience.who}>
              <dt className="font-semibold text-ink">{audience.who}</dt>
              <dd className="mt-2 leading-7 text-body">{audience.what}</dd>
            </div>
          ))}
        </dl>
      </Section>

      <section aria-labelledby="start-heading" className="mx-auto max-w-6xl px-4 pt-20 sm:px-6">
        <div className="flex flex-col gap-6 rounded-2xl bg-navy-900 px-6 py-10 sm:px-10 md:flex-row md:items-center md:justify-between">
          <div className="max-w-xl">
            <h2 id="start-heading" className="text-2xl font-semibold tracking-tight text-white">
              Start with one function
            </h2>
            <p className="mt-3 leading-7 text-navy-100">
              Pick a single function in your current project. Write a one-page specification for it, then
              a known-answer test. The first guide walks through both.
            </p>
          </div>
          <Link
            href="/guides/writing-specifications"
            className="shrink-0 self-start rounded-md bg-white px-5 py-2.5 text-sm font-semibold text-navy-900 hover:bg-navy-50 md:self-auto"
          >
            Write a specification
          </Link>
        </div>
      </section>
    </>
  );
}
