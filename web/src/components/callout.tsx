import type { ReactNode } from "react";

type Tone = "note" | "warning" | "honesty";

const tones: Record<Tone, { box: string; label: string; defaultTitle: string }> = {
  note: { box: "border-navy-200 bg-navy-50/70", label: "text-navy-700", defaultTitle: "Note" },
  warning: { box: "border-amber-300 bg-amber-50", label: "text-amber-900", defaultTitle: "Watch out" },
  honesty: { box: "border-accent-600/40 bg-accent-50", label: "text-accent-800", defaultTitle: "Status" },
};

export function Callout({ tone = "note", title, children }: { tone?: Tone; title?: string; children: ReactNode }) {
  const style = tones[tone];
  return (
    <aside className={`my-6 rounded-lg border-l-4 border-y border-r px-5 py-4 ${style.box}`}>
      <p className={`text-sm font-semibold ${style.label}`}>{title ?? style.defaultTitle}</p>
      <div className="mt-1 text-[0.96875rem] leading-6 text-body">{children}</div>
    </aside>
  );
}
