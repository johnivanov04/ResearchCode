import type { ReactNode } from "react";

/** Standard page introduction: eyebrow, the page's single h1, and a lede. */
export function PageHeader({ eyebrow, title, children }: { eyebrow: string; title: string; children?: ReactNode }) {
  return (
    <div className="border-b border-line bg-surface">
      <div className="mx-auto max-w-6xl px-4 pb-12 pt-14 sm:px-6 sm:pt-16">
        <p className="text-sm font-semibold uppercase tracking-wider text-accent-700">{eyebrow}</p>
        <h1 className="mt-3 max-w-3xl text-3xl font-semibold tracking-tight text-ink sm:text-[2.5rem] sm:leading-[1.15]">
          {title}
        </h1>
        {children ? <div className="mt-5 max-w-2xl text-lg leading-8 text-body">{children}</div> : null}
      </div>
    </div>
  );
}

export function Section({
  id,
  eyebrow,
  title,
  intro,
  children,
  className = "",
}: {
  id?: string;
  eyebrow?: string;
  title: string;
  intro?: ReactNode;
  children?: ReactNode;
  className?: string;
}) {
  const headingId = id ? `${id}-heading` : undefined;
  return (
    <section id={id} aria-labelledby={headingId} className={`mx-auto max-w-6xl px-4 pt-20 sm:px-6 ${className}`}>
      {eyebrow ? <p className="text-sm font-semibold uppercase tracking-wider text-accent-700">{eyebrow}</p> : null}
      <h2 id={headingId} className="mt-2 max-w-3xl text-2xl font-semibold tracking-tight text-ink sm:text-3xl">
        {title}
      </h2>
      {intro ? <div className="mt-4 max-w-2xl text-[1.0625rem] leading-7 text-body">{intro}</div> : null}
      {children}
    </section>
  );
}
