import type { Metadata } from "next";
import Link from "next/link";
import { PageHeader } from "@/components/page-header";
import { guides } from "@/content/guides";

export const metadata: Metadata = {
  title: "Guides",
  description:
    "Practical guides for researchers using AI coding assistants: writing specifications, testing generated code, reviewing changes, and reproducibility.",
};

export default function GuidesPage() {
  return (
    <>
      <PageHeader eyebrow="Guides" title="Practical guides for AI-assisted research code">
        <p>
          Each guide covers one stage of the ResearchCode workflow. They are written for researchers
          who are comfortable with Python but have not had formal software engineering training. Every
          guide ends with a checklist and includes prompts you can copy into your assistant.
        </p>
      </PageHeader>

      <div className="mx-auto max-w-6xl px-4 pt-12 sm:px-6">
        <h2 className="sr-only">All guides</h2>
        {guides.length === 0 ? (
          <p className="rounded-lg border border-dashed border-line p-8 text-center text-muted">
            No guides have been published yet.
          </p>
        ) : (
          <ol className="grid gap-5 md:grid-cols-2">
            {guides.map((guide, index) => (
              <li key={guide.slug}>
                <Link
                  href={`/guides/${guide.slug}`}
                  className="group flex h-full flex-col rounded-xl border border-line bg-white p-6 transition-colors hover:border-navy-200 hover:bg-surface"
                >
                  <div className="flex items-center gap-3 text-xs font-medium text-muted">
                    <span className="font-mono text-accent-700">{String(index + 1).padStart(2, "0")}</span>
                    <span className="rounded-full border border-line px-2 py-0.5">{guide.stage}</span>
                    <span>{guide.readingMinutes} min read</span>
                  </div>
                  <h3 className="mt-4 text-xl font-semibold tracking-tight text-ink group-hover:text-navy-700">
                    {guide.title}
                  </h3>
                  <p className="mt-2 flex-1 leading-7 text-body">{guide.summary}</p>
                  <span className="mt-5 text-sm font-medium text-accent-700">
                    Read the guide <span aria-hidden="true">→</span>
                  </span>
                </Link>
              </li>
            ))}
          </ol>
        )}

        <div className="mt-12 grid gap-6 rounded-xl border border-line bg-surface p-6 md:grid-cols-3">
          <div>
            <h2 className="font-semibold text-ink">Read in order</h2>
            <p className="mt-1 text-sm leading-6 text-body">
              The guides follow the workflow: specify, test, review, reproduce. Later guides refer back to
              the growth-rate example introduced in the first.
            </p>
          </div>
          <div>
            <h2 className="font-semibold text-ink">Adapt the prompts</h2>
            <p className="mt-1 text-sm leading-6 text-body">
              The example prompts are starting points, not magic phrases. They work with any capable
              assistant, including Claude Code, ChatGPT, and GitHub Copilot.
            </p>
          </div>
          <div>
            <h2 className="font-semibold text-ink">Keep your judgement</h2>
            <p className="mt-1 text-sm leading-6 text-body">
              The assistant can propose; you decide. Every guide marks the points where a scientific
              decision belongs to you.
            </p>
          </div>
        </div>
      </div>
    </>
  );
}
