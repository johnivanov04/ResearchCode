import Link from "next/link";
import { workflowStages } from "@/content/workflow";

/**
 * The five-stage workflow drawn as an ordered list, so it reads correctly to
 * screen readers and reflows on small screens. Connectors are decorative.
 */
export function WorkflowDiagram() {
  return (
    <figure className="mt-10">
      <ol className="grid gap-3 lg:grid-cols-5 lg:gap-0">
        {workflowStages.map((stage, index) => (
          <li key={stage.name} className="relative flex lg:pr-6 lg:last:pr-0">
            <div className="flex w-full flex-col rounded-xl border border-line bg-white p-5">
              <div className="flex items-center gap-3">
                <span className="flex h-7 w-7 items-center justify-center rounded-full bg-navy-800 font-mono text-xs font-medium text-white">
                  {index + 1}
                </span>
                <h3 className="text-lg font-semibold text-ink">{stage.name}</h3>
              </div>
              <p className="mt-3 text-sm font-medium leading-6 text-ink">{stage.summary}</p>
              <dl className="mt-4 space-y-3 text-sm leading-6">
                <div>
                  <dt className="text-xs font-semibold uppercase tracking-wider text-navy-600">You</dt>
                  <dd className="text-body">{stage.you}</dd>
                </div>
                <div>
                  <dt className="text-xs font-semibold uppercase tracking-wider text-accent-700">Assistant</dt>
                  <dd className="text-body">{stage.assistant}</dd>
                </div>
              </dl>
              <div className="mt-auto flex items-center justify-between gap-2 pt-4">
                <span className="inline-block rounded border border-line bg-surface px-2 py-0.5 font-mono text-xs text-body">
                  {stage.artifact}
                </span>
                {stage.guideSlug ? (
                  <Link
                    href={`/guides/${stage.guideSlug}`}
                    className="text-sm font-medium text-accent-700 hover:text-accent-800"
                  >
                    Guide<span className="sr-only">: {stage.name}</span> <span aria-hidden="true">→</span>
                  </Link>
                ) : null}
              </div>
            </div>
            {index < workflowStages.length - 1 ? (
              <svg
                aria-hidden="true"
                viewBox="0 0 24 24"
                className="absolute right-0 top-1/2 hidden h-6 w-6 -translate-y-1/2 text-navy-200 lg:block"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M5 12h12m-4-4 4 4-4 4" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            ) : null}
          </li>
        ))}
      </ol>
      <figcaption className="mt-5 flex items-start gap-3 rounded-lg border border-dashed border-navy-200 bg-navy-50/50 px-4 py-3 text-sm leading-6 text-body">
        <svg aria-hidden="true" viewBox="0 0 20 20" className="mt-0.5 h-5 w-5 shrink-0 text-navy-600" fill="none" stroke="currentColor" strokeWidth="1.6">
          <path d="M16 10a6 6 0 1 1-1.76-4.24M16 4v3.5h-3.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        <span>
          The cycle repeats for every function or module. When review or reproduction reveals a problem,
          return to the specification and tests first, then regenerate the code.
        </span>
      </figcaption>
    </figure>
  );
}
