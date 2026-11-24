import { existsSync, readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import {
  analysisRun,
  mutationValidationFailures,
  primaryResult,
  sample,
  secondaryResults,
  taskOrder,
  trialsWithTests,
} from "@/content/evaluation-results";

const here = dirname(fileURLToPath(import.meta.url));
const experiments = resolve(here, "../../../experiments");
// Public: the aggregate summary published in the repository. Always present, including in CI.
const aggregatePath = resolve(experiments, "docs/aggregate-results.json");
const aggregateText = readFileSync(aggregatePath, "utf8");
const aggregate = JSON.parse(aggregateText);
// Not public: the full analysis output with per-trial rows. Present only on the experimenter's machine.
const analysisPath = resolve(experiments, "results/analysis/genuine/analysis.json");
const hasAnalysis = existsSync(analysisPath);

type Cell = { n: number; mean: number; median: number };
type Metric = {
  per_task: Record<string, { A: Cell; B: Cell; difference_B_minus_A: number; difference_ci: [number, number] }>;
  pooled: { A: Cell; B: Cell };
  difference_B_minus_A: number;
  difference_ci: [number, number];
};

const close = (actual: number, expected: number) =>
  expect(Math.abs(actual - expected), `${actual} vs ${expected}`).toBeLessThanOrEqual(1e-5 * Math.max(1, Math.abs(expected)));

describe("results shown on /evaluation are internally consistent", () => {
  it("each secondary difference is the mean over tasks of the per-task differences", () => {
    for (const metric of Object.values(secondaryResults)) {
      const perTask = taskOrder.map((task) => metric.perTask[task][1] - metric.perTask[task][0]);
      close(perTask.reduce((sum, value) => sum + value, 0) / perTask.length, metric.difference);
      // Pooled means over 30 trials equal the mean of the three cells of 10.
      close(taskOrder.reduce((sum, task) => sum + metric.perTask[task][0], 0) / 3, metric.a);
      close(taskOrder.reduce((sum, task) => sum + metric.perTask[task][1], 0) / 3, metric.b);
      expect(metric.ci[0]).toBeLessThanOrEqual(metric.difference);
      expect(metric.ci[1]).toBeGreaterThanOrEqual(metric.difference);
    }
  });

  it("the primary result is the recorded ceiling", () => {
    expect([primaryResult.passRateA, primaryResult.passRateB, primaryResult.difference]).toEqual([1, 1, 0]);
    expect(primaryResult.ci).toEqual([0, 0]);
    expect(sample.analysedTrials).toBe(sample.plannedTrials);
    expect(sample.interactiveTrials + sample.unattendedTrials).toBe(sample.analysedTrials);
  });
});

describe("results shown on /evaluation match the public aggregate summary", () => {
  it("the summary is aggregate only: no per-trial rows or trial, hidden-case, or private identifiers", () => {
    expect(Object.keys(aggregate)).not.toContain("rows");
    expect(aggregateText).not.toMatch(/--[AB]--[rpe]\d\d/);
    expect(aggregateText).not.toMatch(/case_id|hidden_case|researchcode-private|"min"|"max"/);
  });

  it("comes from the genuine, complete, pre-registered analysis", () => {
    expect(aggregate.data_kind).toBe("genuine");
    expect(aggregate.protocol_version).toBe(analysisRun.protocolVersion);
    expect(aggregate.generated_at.slice(0, 10)).toBe(analysisRun.date);
    expect(aggregate.trials_found).toBe(sample.analysedTrials);
    expect(aggregate.trials_included).toBe(sample.analysedTrials);
    expect(aggregate.trials_excluded).toBe(0);
    expect(aggregate.sample_size.planned_total).toBe(sample.plannedTrials);
    for (const cell of aggregate.sample_size.cells) expect(cell.achieved).toBe(sample.trialsPerCell);
  });

  it("primary outcome, test, sensitivity, and exploratory analyses", () => {
    expect(aggregate.primary.pooled.A.mean).toBe(primaryResult.passRateA);
    expect(aggregate.primary.pooled.B.mean).toBe(primaryResult.passRateB);
    expect(aggregate.primary.difference_B_minus_A).toBe(primaryResult.difference);
    expect(aggregate.primary.difference_ci).toEqual(primaryResult.ci);
    for (const task of taskOrder) {
      expect([aggregate.primary.per_task[task].A.mean, aggregate.primary.per_task[task].B.mean]).toEqual(primaryResult.perTask[task]);
    }
    expect(aggregate.inference.inferential).toBe(true);
    expect(aggregate.inference.permutation_p).toBe(primaryResult.permutationP);
    const balanced = aggregate.secondary.category_balanced_pass_rate;
    expect([balanced.pooled.A.mean, balanced.pooled.B.mean, balanced.difference_B_minus_A]).toEqual([
      primaryResult.categoryBalanced.a,
      primaryResult.categoryBalanced.b,
      primaryResult.categoryBalanced.difference,
    ]);
    const exploratory = aggregate.exploratory_execution_mode;
    expect(exploratory.trials_included).toBe(primaryResult.exploratoryWithoutInteractive.trials);
    expect(exploratory.primary.difference_B_minus_A).toBe(primaryResult.exploratoryWithoutInteractive.difference);
    expect(exploratory.primary.difference_ci).toEqual(primaryResult.exploratoryWithoutInteractive.ci);
    for (const category of Object.values(aggregate.categories) as Metric[]) {
      expect([category.pooled.A.mean, category.pooled.B.mean]).toEqual([1, 1]);
    }
  });

  it.each(Object.values(secondaryResults).map((m) => [m.key, m] as const))("secondary measure %s", (key, shown) => {
    const saved = aggregate.secondary[key] as Metric;
    close(shown.a, saved.pooled.A.mean);
    close(shown.b, saved.pooled.B.mean);
    close(shown.difference, saved.difference_B_minus_A);
    close(shown.ci[0], saved.difference_ci[0]);
    close(shown.ci[1], saved.difference_ci[1]);
    for (const task of taskOrder) {
      close(shown.perTask[task][0], saved.per_task[task].A.mean);
      close(shown.perTask[task][1], saved.per_task[task].B.mean);
    }
  });

  it("aggregate counts", () => {
    expect(aggregate.counts.trials_with_tests).toEqual({ A: trialsWithTests.a, B: trialsWithTests.b });
    const zeros = aggregate.counts.trials_with_mutation_score_zero[mutationValidationFailures.task];
    expect(zeros[mutationValidationFailures.condition]).toBe(mutationValidationFailures.trials);
    expect(aggregate.counts.execution_mode).toEqual({
      "manual-interactive": sample.interactiveTrials,
      "unattended-noninteractive": sample.unattendedTrials,
    });
  });
});

/** Mirrors the derivation that produced aggregate-results.json from the full analysis output. */
// eslint-disable-next-line @typescript-eslint/no-explicit-any -- untyped JSON from the analysis tool
function deriveAggregate(analysis: Record<string, any>) {
  const cell = (c: Cell) => ({ n: c.n, mean: c.mean, median: c.median });
  const metric = (m: Metric) => ({
    per_task: Object.fromEntries(
      Object.entries(m.per_task).map(([task, v]) => [
        task,
        { A: cell(v.A), B: cell(v.B), difference_B_minus_A: v.difference_B_minus_A, difference_ci: v.difference_ci },
      ]),
    ),
    pooled: { A: cell(m.pooled.A), B: cell(m.pooled.B) },
    difference_B_minus_A: m.difference_B_minus_A,
    difference_ci: m.difference_ci,
  });
  const mapValues = (o: Record<string, Metric>) => Object.fromEntries(Object.entries(o).map(([k, v]) => [k, metric(v)]));
  type Row = { task: string; condition: "A" | "B"; tests_collected: number; mutation_score: number; execution_mode: string };
  const rows = analysis.rows as Row[];
  const count = (predicate: (r: Row) => boolean) => rows.filter(predicate).length;
  const modes = [...new Set(rows.map((r) => r.execution_mode))].sort();
  return {
    data_kind: analysis.data_kind,
    protocol_version: analysis.protocol_version,
    generated_at: analysis.generated_at,
    trials_found: analysis.trials_found,
    trials_included: analysis.trials_included,
    trials_excluded: analysis.excluded.length,
    sample_size: {
      planned_per_cell: analysis.sample_size.planned_per_cell,
      planned_total: analysis.sample_size.planned_total,
      achieved_total: analysis.sample_size.achieved_total,
      cells: analysis.sample_size.cells,
    },
    inference: analysis.inference,
    primary: metric(analysis.primary),
    categories: mapValues(analysis.categories),
    secondary: mapValues(analysis.secondary),
    exploratory_execution_mode: {
      label: analysis.exploratory_execution_mode.label,
      trials_included: analysis.exploratory_execution_mode.trials_included,
      primary: metric(analysis.exploratory_execution_mode.primary),
    },
    counts: {
      trials_with_tests: { A: count((r) => r.condition === "A" && r.tests_collected > 0), B: count((r) => r.condition === "B" && r.tests_collected > 0) },
      trials_with_mutation_score_zero: Object.fromEntries(
        Object.keys(analysis.primary.per_task).map((task) => [
          task,
          {
            A: count((r) => r.task === task && r.condition === "A" && r.mutation_score === 0),
            B: count((r) => r.task === task && r.condition === "B" && r.mutation_score === 0),
          },
        ]),
      ),
      execution_mode: Object.fromEntries(modes.map((mode) => [mode, count((r) => r.execution_mode === mode)])),
    },
  };
}

// The full analysis output is not public, so this check runs only where it exists locally.
describe.skipIf(!hasAnalysis)("the public aggregate summary is exactly the aggregate part of the frozen analysis output", () => {
  it("matches field for field", () => {
    const analysis = JSON.parse(readFileSync(analysisPath, "utf8"));
    const { description, ...published } = aggregate;
    expect(description).toMatch(/no per-trial records/);
    expect(published).toEqual(deriveAggregate(analysis));
  });
});
