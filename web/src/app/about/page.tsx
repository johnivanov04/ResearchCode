import type { Metadata } from "next";
import Link from "next/link";
import { PageHeader, Section } from "@/components/page-header";
import { StatusBadge, type Status } from "@/components/status-badge";

export const metadata: Metadata = {
  title: "About",
  description:
    "ResearchCode is an open-source educational project, developed as a Caltech CS/EE 143 special project, on using AI coding assistants responsibly in research.",
};

const principles = [
  {
    title: "Scientific correctness first",
    body: "Speed is welcome, but a fast wrong answer has negative value. Everything we publish is aimed at results a researcher can defend.",
  },
  {
    title: "Practical over theoretical",
    body: "We teach the smallest set of habits that catch the most errors, with examples drawn from real scientific tasks.",
  },
  {
    title: "Honest about status",
    body: "We label what is available, what is in progress, and what is planned. We do not publish invented data, results, or endorsements.",
  },
  {
    title: "Tool-neutral",
    body: "The workflow is meant to work with any capable assistant. We name tools only as examples, and have no commercial relationship with any of them.",
  },
];

const roadmap: { phase: string; title: string; body: string; status: Status }[] = [
  { phase: "Phase 1", title: "Website and foundation", body: "This site, the first guides, and the project's engineering setup.", status: "in-progress" },
  { phase: "Phase 2", title: "Scientific Python starter kit", body: "A reusable template with uv, pytest, Ruff, CI, and AI assistant instructions.", status: "planned" },
  { phase: "Phase 3", title: "Worked scientific application", body: "A complete bacterial growth analysis built with the starter kit.", status: "planned" },
  { phase: "Phase 4", title: "Controlled evaluation", body: "The comparison of unstructured and structured AI-assisted development.", status: "planned" },
  { phase: "Phase 5", title: "Deployment and polish", body: "Public deployment, accessibility audit, and documentation review.", status: "planned" },
];

export default function AboutPage() {
  return (
    <>
      <PageHeader eyebrow="About" title="Why ResearchCode exists">
        <p>
          AI coding assistants have changed who can write research software and how quickly. ResearchCode is an
          open-source effort to make sure the software they help produce is still correct, maintainable, and
          reproducible.
        </p>
      </PageHeader>

      <Section
        id="context"
        eyebrow="Academic context"
        title="A Caltech CS/EE 143 special project"
        intro={
          <>
            <p>
              ResearchCode is being developed as a special project in Caltech&apos;s CS/EE 143. It is a student
              project and an educational resource. It is not an official Caltech publication, service, or
              policy, and it has not been endorsed by any department or faculty member.
            </p>
            <p className="mt-4">
              The intended audience is the wider research community: anyone who writes scientific Python and
              uses AI assistants to do it.
            </p>
          </>
        }
      />

      <Section
        id="mission"
        eyebrow="Mission"
        title="Help researchers move from vibe coding to reliable AI-assisted development"
        intro={
          <p>
            Many researchers learned to program by necessity, not through training in software engineering.
            AI assistants amplify both sides of that: they remove barriers to writing code, and they make it
            easier to produce code that nobody has checked. We want to give researchers a lightweight, practical
            discipline that fits how they already work.
          </p>
        }
      >
        <ul className="mt-10 grid gap-5 md:grid-cols-2">
          {principles.map((principle) => (
            <li key={principle.title} className="rounded-xl border border-line bg-white p-6">
              <h3 className="font-semibold text-ink">{principle.title}</h3>
              <p className="mt-2 leading-7 text-body">{principle.body}</p>
            </li>
          ))}
        </ul>
      </Section>

      <Section id="roadmap" eyebrow="Roadmap" title="Where the project is going">
        <ol className="mt-8 divide-y divide-line rounded-xl border border-line bg-white">
          {roadmap.map((item) => (
            <li key={item.phase} className="flex flex-col gap-3 p-5 sm:flex-row sm:items-start sm:gap-6">
              <span className="w-20 shrink-0 font-mono text-sm text-muted">{item.phase}</span>
              <div className="flex-1">
                <h3 className="font-semibold text-ink">{item.title}</h3>
                <p className="mt-1 leading-7 text-body">{item.body}</p>
              </div>
              <div className="shrink-0">
                <StatusBadge status={item.status} />
              </div>
            </li>
          ))}
        </ol>
      </Section>

      <Section
        id="open-source"
        eyebrow="Open source"
        title="Built in the open"
        intro={
          <p>
            The website, guides, starter kit, and experiment materials will all be published as open source so
            that others can reuse and adapt them. Licensing for code and written content will be confirmed before
            the public release. If you have suggestions for topics the guides should cover, they are welcome once
            the repository is public.
          </p>
        }
      >
        <div className="mt-8">
          <Link href="/guides" className="text-sm font-medium text-accent-700 hover:text-accent-800">
            Start with the guides <span aria-hidden="true">→</span>
          </Link>
        </div>
      </Section>
    </>
  );
}
