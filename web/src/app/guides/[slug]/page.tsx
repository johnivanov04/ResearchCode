import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { GuideSections } from "@/components/guide-content";
import { guides, getGuide } from "@/content/guides";

type GuidePageProps = { params: Promise<{ slug: string }> };

export function generateStaticParams() {
  return guides.map((guide) => ({ slug: guide.slug }));
}

export async function generateMetadata({ params }: GuidePageProps): Promise<Metadata> {
  const { slug } = await params;
  const guide = getGuide(slug);
  if (!guide) return { title: "Guide not found" };
  return { title: guide.title, description: guide.summary };
}

export default async function GuidePage({ params }: GuidePageProps) {
  const { slug } = await params;
  const guide = getGuide(slug);
  if (!guide) notFound();

  const index = guides.indexOf(guide);
  const previous = index > 0 ? guides[index - 1] : undefined;
  const next = index < guides.length - 1 ? guides[index + 1] : undefined;

  return (
    <article>
      <header className="border-b border-line bg-surface">
        <div className="mx-auto max-w-6xl px-4 pb-10 pt-10 sm:px-6">
          <nav aria-label="Breadcrumb" className="text-sm text-muted">
            <ol className="flex items-center gap-2">
              <li>
                <Link href="/guides" className="hover:text-accent-700">
                  Guides
                </Link>
              </li>
              <li aria-hidden="true">/</li>
              <li aria-current="page" className="truncate text-body">
                {guide.title}
              </li>
            </ol>
          </nav>
          <p className="mt-8 text-sm font-semibold uppercase tracking-wider text-accent-700">
            Workflow stage: {guide.stage}
          </p>
          <h1 className="mt-3 max-w-3xl text-3xl font-semibold tracking-tight text-ink sm:text-[2.5rem] sm:leading-[1.15]">
            {guide.title}
          </h1>
          <p className="mt-5 max-w-2xl text-lg leading-8 text-body">{guide.summary}</p>
          <dl className="mt-6 flex flex-wrap gap-x-8 gap-y-2 text-sm">
            <div className="flex gap-2">
              <dt className="text-muted">Reading time</dt>
              <dd className="font-medium text-ink">{guide.readingMinutes} minutes</dd>
            </div>
            <div className="flex gap-2">
              <dt className="text-muted">For</dt>
              <dd className="max-w-xl font-medium text-ink">{guide.audience}</dd>
            </div>
          </dl>
        </div>
      </header>

      <div className="mx-auto grid max-w-6xl gap-12 px-4 pt-12 sm:px-6 lg:grid-cols-[minmax(0,1fr)_16rem]">
        <div className="min-w-0 max-w-3xl">
          <section aria-labelledby="outcomes-heading" className="mb-12 rounded-xl border border-line p-6">
            <h2 id="outcomes-heading" className="text-base font-semibold text-ink">
              After reading this guide you will be able to
            </h2>
            <ul className="mt-3 space-y-2 text-[0.96875rem] leading-6 text-body">
              {guide.outcomes.map((outcome) => (
                <li key={outcome} className="flex gap-3">
                  <span aria-hidden="true" className="mt-2.5 h-1.5 w-1.5 shrink-0 rounded-full bg-accent-600" />
                  {outcome}
                </li>
              ))}
            </ul>
          </section>

          <GuideSections sections={guide.sections} />

          <nav aria-label="More guides" className="mt-16 grid gap-4 border-t border-line pt-8 sm:grid-cols-2">
            {previous ? (
              <Link href={`/guides/${previous.slug}`} className="rounded-lg border border-line p-4 hover:border-navy-200">
                <span className="text-xs font-medium text-muted">Previous</span>
                <span className="mt-1 block font-semibold text-ink">{previous.title}</span>
              </Link>
            ) : (
              <span />
            )}
            {next ? (
              <Link href={`/guides/${next.slug}`} className="rounded-lg border border-line p-4 text-right hover:border-navy-200">
                <span className="text-xs font-medium text-muted">Next</span>
                <span className="mt-1 block font-semibold text-ink">{next.title}</span>
              </Link>
            ) : (
              <Link href="/example" className="rounded-lg border border-line p-4 text-right hover:border-navy-200">
                <span className="text-xs font-medium text-muted">See it applied</span>
                <span className="mt-1 block font-semibold text-ink">Bacterial growth example</span>
              </Link>
            )}
          </nav>
        </div>

        <aside className="hidden lg:block">
          <nav aria-label="On this page" className="sticky top-24">
            <p className="text-xs font-semibold uppercase tracking-wider text-muted">On this page</p>
            <ul className="mt-3 space-y-2 border-l border-line text-sm">
              {guide.sections.map((section) => (
                <li key={section.id}>
                  <a href={`#${section.id}`} className="-ml-px block border-l border-transparent pl-4 text-body hover:border-accent-600 hover:text-ink">
                    {section.title}
                  </a>
                </li>
              ))}
            </ul>
          </nav>
        </aside>
      </div>
    </article>
  );
}
