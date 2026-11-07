import { useId } from "react";
import { InlineText } from "@/components/inline-text";

/**
 * A checklist readers can tick off while they work. Uses native checkboxes, so
 * it is keyboard accessible and needs no client-side JavaScript. State is not saved.
 */
export function Checklist({ title, items }: { title: string; items: readonly string[] }) {
  const id = useId();
  return (
    <section aria-labelledby={id} className="my-6 rounded-lg border border-line bg-white p-5">
      <h3 id={id} className="flex items-center gap-2 text-base font-semibold text-ink">
        <svg aria-hidden="true" viewBox="0 0 16 16" className="h-4 w-4 text-accent-700" fill="none" stroke="currentColor" strokeWidth="1.75">
          <rect x="1.5" y="1.5" width="13" height="13" rx="2.5" />
          <path d="m4.5 8.2 2.3 2.3 4.7-5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        {title}
      </h3>
      <ul className="mt-3 space-y-2.5">
        {items.map((item, index) => {
          const inputId = `${id}-${index}`;
          return (
            <li key={inputId} className="flex gap-3">
              <input
                id={inputId}
                type="checkbox"
                className="mt-1 h-4 w-4 shrink-0 cursor-pointer rounded border-line accent-accent-700"
              />
              <label htmlFor={inputId} className="cursor-pointer text-[0.96875rem] leading-6 text-body">
                <InlineText text={item} />
              </label>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
