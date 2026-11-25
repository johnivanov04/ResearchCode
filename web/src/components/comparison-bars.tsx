import { useId } from "react";

export type BarGroup = { label: string; a: number; b: number; emphasis?: boolean };

const conditionStyle = {
  A: { name: "Condition A: unstructured", color: "var(--color-series-1)" },
  B: { name: "Condition B: ResearchCode", color: "var(--color-series-2)" },
} as const;

/** Legend shared by every comparison chart: a colour swatch plus a text label, never colour alone. */
export function ConditionLegend() {
  return (
    <ul className="flex flex-wrap gap-x-5 gap-y-1 text-xs text-body" aria-label="Legend">
      {(["A", "B"] as const).map((id) => (
        <li key={id} className="flex items-center gap-1.5">
          <span aria-hidden="true" className="inline-block h-2.5 w-4 rounded-sm" style={{ background: conditionStyle[id].color }} />
          {conditionStyle[id].name}
        </li>
      ))}
    </ul>
  );
}

/**
 * Horizontal bars comparing Condition A and Condition B for a few groups, on one zero-based
 * scale. It is rendered as a real table (group, A, B), so the values are available as text to
 * every reader; the bars are decoration on top of the printed values. Server-rendered, no
 * script. Each bar is labelled with its condition letter and value, so identity never relies on
 * colour.
 */
export function ComparisonBars({
  title,
  description,
  groups,
  max,
  ticks,
  format,
  tickFormat = format,
  groupHeader = "Task",
}: {
  title: string;
  description: string;
  groups: BarGroup[];
  max: number;
  ticks: number[];
  format: (value: number) => string;
  /** Axis labels; defaults to `format`. */
  tickFormat?: (value: number) => string;
  groupHeader?: string;
}) {
  const titleId = useId();
  const share = (value: number) => `${Math.max(0, Math.min(1, value / max)) * 100}%`;
  return (
    <figure aria-labelledby={titleId} className="rounded-xl border border-line bg-white p-5 sm:p-6">
      <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-2">
        <p id={titleId} className="font-semibold text-ink">
          {title}
        </p>
        <ConditionLegend />
      </div>
      <table role="table" className="mt-4 w-full border-collapse text-left text-sm">
        <caption className="sr-only">
          {title}. {description}
        </caption>
        <thead role="rowgroup" className="sr-only">
          <tr role="row">
            <th role="columnheader" scope="col">{groupHeader}</th>
            <th role="columnheader" scope="col">{conditionStyle.A.name}</th>
            <th role="columnheader" scope="col">{conditionStyle.B.name}</th>
          </tr>
        </thead>
        <tbody role="rowgroup">
          {groups.map((group) => (
            <tr
              key={group.label}
              role="row"
              className={`grid grid-cols-1 gap-1 py-2.5 sm:grid-cols-[9.5rem_1fr_1fr] sm:gap-x-0 ${group.emphasis ? "border-t border-line" : ""}`}
            >
              <th role="rowheader" scope="row" className={`pr-3 text-[0.9375rem] leading-6 ${group.emphasis ? "font-semibold text-ink" : "font-medium text-body"}`}>
                {group.label}
              </th>
              {(["A", "B"] as const).map((id) => {
                const value = id === "A" ? group.a : group.b;
                return (
                  <td key={id} role="cell" className="flex items-center gap-2 sm:col-span-2 sm:col-start-2">
                    <span aria-hidden="true" className="w-3 shrink-0 font-mono text-xs text-muted">
                      {id}
                    </span>
                    <span aria-hidden="true" className="relative mr-24 h-3.5 flex-1">
                      <span className="absolute inset-y-0 left-0 w-px bg-navy-200" />
                      <span
                        className="absolute inset-y-0 left-0 rounded-r"
                        style={{ width: share(value), background: conditionStyle[id].color }}
                      />
                      <span
                        className="absolute top-1/2 -translate-y-1/2 whitespace-nowrap pl-1.5 font-mono text-xs text-ink"
                        style={{ left: share(value) }}
                      >
                        {format(value)}
                      </span>
                    </span>
                    <span className="sr-only">{format(value)}</span>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
      <div aria-hidden="true" className="mt-1 grid grid-cols-1 sm:grid-cols-[9.5rem_1fr]">
        <span className="hidden sm:block" />
        <div className="flex gap-2">
          <span className="w-3 shrink-0" />
          <div className="relative mr-24 h-5 flex-1 border-t border-line">
            {ticks.map((tick) => (
              <span
                key={tick}
                className="absolute top-1 -translate-x-1/2 font-mono text-[0.6875rem] text-muted"
                style={{ left: share(tick) }}
              >
                {tickFormat(tick)}
              </span>
            ))}
          </div>
        </div>
      </div>
      <figcaption className="mt-3 text-[0.875rem] leading-6 text-muted">{description}</figcaption>
    </figure>
  );
}
