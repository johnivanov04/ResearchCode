"use client";

import { useMemo, useState } from "react";
import { GrowthChart } from "@/components/growth-chart";
import { TRUE_RATE_PER_H, analyseScenario, scenarios, type ScenarioId } from "@/lib/growth";

function formatDoubling(minutes: number): string {
  return minutes >= 120 ? `${(minutes / 60).toFixed(1)} h` : `${minutes.toFixed(1)} min`;
}

function formatError(relative: number): string {
  const percent = relative * 100;
  if (Math.abs(percent) < 0.5) return "within 0.5%";
  return `${percent > 0 ? "+" : "−"}${Math.abs(percent).toFixed(0)}%`;
}

/** Lets readers switch between a correct analysis and common mistakes on the same synthetic data. */
export function GrowthExplorer() {
  const [selected, setSelected] = useState<ScenarioId>("correct");
  const results = useMemo(
    () => Object.fromEntries(scenarios.map((s) => [s.id, analyseScenario(s.id)])) as Record<ScenarioId, ReturnType<typeof analyseScenario>>,
    [],
  );
  const result = results[selected];
  const trueDoublingMin = (Math.LN2 / TRUE_RATE_PER_H) * 60;
  const isCorrect = selected === "correct";

  return (
    <div className="mt-8 grid gap-8 rounded-xl border border-line bg-white p-5 sm:p-6 lg:grid-cols-[18rem_minmax(0,1fr)]">
      <fieldset>
        <legend className="text-sm font-semibold text-ink">Choose an analysis</legend>
        <div className="mt-3 space-y-2">
          {scenarios.map((scenario) => (
            <label
              key={scenario.id}
              className={`flex cursor-pointer gap-3 rounded-lg border px-3 py-2.5 text-sm transition-colors ${
                selected === scenario.id ? "border-navy-600 bg-navy-50" : "border-line hover:border-navy-200"
              }`}
            >
              <input
                type="radio"
                name="growth-scenario"
                value={scenario.id}
                checked={selected === scenario.id}
                onChange={() => setSelected(scenario.id)}
                className="mt-0.5 accent-navy-700"
              />
              <span className="font-medium text-ink">{scenario.label}</span>
            </label>
          ))}
        </div>
      </fieldset>

      <div className="min-w-0">
        <div aria-live="polite">
          <p className="text-sm leading-6 text-body">{result.scenario.description}</p>
          <dl className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
            <div className="rounded-lg border border-line bg-surface p-3">
              <dt className="text-xs text-muted">Reported growth rate</dt>
              <dd className="mt-1 font-mono text-lg font-medium text-ink">
                {result.reportedRatePerH.toFixed(3)} h⁻¹
              </dd>
            </div>
            <div className="rounded-lg border border-line bg-surface p-3">
              <dt className="text-xs text-muted">Implied doubling time</dt>
              <dd className="mt-1 font-mono text-lg font-medium text-ink">
                {formatDoubling(result.reportedDoublingMin)}
              </dd>
            </div>
            <div className={`rounded-lg border p-3 ${isCorrect ? "border-accent-600/40 bg-accent-50" : "border-amber-300 bg-amber-50"}`}>
              <dt className="text-xs text-muted">Error vs. true rate</dt>
              <dd className={`mt-1 font-mono text-lg font-medium ${isCorrect ? "text-accent-800" : "text-amber-900"}`}>
                {formatError(result.relativeError)}
              </dd>
            </div>
          </dl>
          <p className="mt-2 text-xs text-muted">
            True values used to generate the data: {TRUE_RATE_PER_H.toFixed(3)} h⁻¹, doubling time{" "}
            {trueDoublingMin.toFixed(1)} min.
          </p>
        </div>
        <div className="mt-6">
          <GrowthChart result={result} />
        </div>
      </div>
    </div>
  );
}
