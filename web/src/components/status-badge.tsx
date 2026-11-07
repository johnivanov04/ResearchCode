export type Status = "available" | "in-progress" | "planned";

const styles: Record<Status, { label: string; className: string; dot: string }> = {
  available: { label: "Available", className: "border-accent-600/30 bg-accent-50 text-accent-800", dot: "bg-accent-600" },
  "in-progress": { label: "In progress", className: "border-navy-200 bg-navy-50 text-navy-700", dot: "bg-navy-600" },
  planned: { label: "Planned", className: "border-amber-300 bg-amber-50 text-amber-900", dot: "bg-amber-500" },
};

/** Labels whether something exists today. Always includes text, never colour alone. */
export function StatusBadge({ status }: { status: Status }) {
  const style = styles[status];
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium ${style.className}`}
    >
      <span aria-hidden="true" className={`h-1.5 w-1.5 rounded-full ${style.dot}`} />
      {style.label}
    </span>
  );
}
