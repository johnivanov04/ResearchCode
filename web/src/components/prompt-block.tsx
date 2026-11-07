import { CopyButton } from "@/components/copy-button";

/** A copyable example prompt for an AI coding assistant. */
export function PromptBlock({ title, prompt, note }: { title: string; prompt: string; note?: string }) {
  return (
    <figure className="my-6 rounded-lg border border-accent-100 bg-accent-50/60">
      <div className="flex items-center justify-between gap-3 border-b border-accent-100 px-4 py-2.5">
        <figcaption className="flex items-center gap-2 text-sm font-semibold text-ink">
          <span className="rounded bg-accent-700 px-1.5 py-0.5 font-mono text-[0.6875rem] font-medium uppercase tracking-wide text-white">
            Prompt
          </span>
          {title}
        </figcaption>
        <CopyButton text={prompt} />
      </div>
      <pre className="overflow-x-auto whitespace-pre-wrap px-4 py-4 font-mono text-[0.8125rem] leading-6 text-ink">
        {prompt}
      </pre>
      {note ? <p className="border-t border-accent-100 px-4 py-2.5 text-sm text-muted">{note}</p> : null}
    </figure>
  );
}
