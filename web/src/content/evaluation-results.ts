/**
 * Aggregate results of the completed Phase 4 experiment, shown on /evaluation.
 *
 * Every number is copied from the frozen, pre-registered analysis output, produced once on
 * 2026-11-22 by `uv run rc-exp analyze --kind genuine`. Only aggregates appear here: no
 * per-trial records, trial identifiers, hidden cases, or evaluator material.
 *
 * `evaluation-results.test.ts` checks every value against the public aggregate summary,
 * experiments/docs/aggregate-results.json, in every checkout including CI. Where the full,
 * non-public analysis output (experiments/results/analysis/genuine/analysis.json) is present,
 * it also checks that the summary is exactly the aggregate part of that file.
 *
 * The primary comparison is the only hypothesis test. Every secondary difference is
 * descriptive: a bootstrap interval for B − A, with no p-value and no adjustment for multiple
 * comparisons.
 */

export type TaskId = "serial-dilution" | "calibration" | "enzyme-kinetics";

export const taskLabels: Record<TaskId, string> = {
  "serial-dilution": "Serial dilution",
  calibration: "Calibration",
  "enzyme-kinetics": "Enzyme kinetics",
};

export const taskOrder: TaskId[] = ["serial-dilution", "calibration", "enzyme-kinetics"];

/** analysis.json `generated_at` and `protocol_version`. */
export const analysisRun = { date: "2026-11-22", protocolVersion: "1.5" };

export const sample = {
  plannedTrials: 60,
  analysedTrials: 60,
  trialsPerCondition: 30,
  trialsPerCell: 10,
  /** Trials run by hand under protocol 1.4 (one) and unattended under 1.5 (59). */
  interactiveTrials: 1,
  unattendedTrials: 59,
  /** Attempts stopped by infrastructure (a usage limit; a dropped connection while the host slept), rerun from scratch. */
  invalidAttemptsRerun: 2,
};

/** Primary outcome: share of hidden evaluation cases passed. */
export const primaryResult = {
  passRateA: 1,
  passRateB: 1,
  perTask: { "serial-dilution": [1, 1], calibration: [1, 1], "enzyme-kinetics": [1, 1] } as Record<TaskId, [number, number]>,
  difference: 0,
  ci: [0, 0] as [number, number],
  permutationP: 1,
  /** Exploratory analysis without the one interactively run confirmatory trial (59 trials). */
  exploratoryWithoutInteractive: { trials: 59, difference: 0, ci: [0, 0] as [number, number] },
  /** Category-balanced pass rate (pre-registered sensitivity analysis). */
  categoryBalanced: { a: 1, b: 1, difference: 0 },
};

export type SecondaryMetric = {
  key: string;
  label: string;
  unit: string;
  /** Pooled means over the 30 trials per condition. */
  a: number;
  b: number;
  /** Mean over tasks of (B − A), with its 95% bootstrap interval. */
  difference: number;
  ci: [number, number];
  perTask: Record<TaskId, [number, number]>;
  digits: number;
};

/** analysis.json `secondary`, pooled and per task (A, B means). */
export const secondaryResults = {
  mutationScore: {
    key: "mutation_score",
    label: "Mutation score of the submission's own tests",
    unit: "share of known defects detected",
    a: 0.040741,
    b: 0.87619,
    difference: 0.83545,
    ci: [0.72328, 0.93545],
    perTask: { "serial-dilution": [0.122222, 0.7], calibration: [0, 1], "enzyme-kinetics": [0, 0.928571] },
    digits: 3,
  },
  testsCollected: {
    key: "tests_collected",
    label: "Tests written",
    unit: "tests per submission",
    a: 0.4,
    b: 132.6,
    difference: 132.2,
    ci: [126.1325, 138.400833],
    perTask: { "serial-dilution": [1.2, 221.9], calibration: [0, 100.4], "enzyme-kinetics": [0, 75.5] },
    digits: 1,
  },
  wallClockMinutes: {
    key: "wall_clock_minutes",
    label: "Session time",
    unit: "minutes",
    a: 2.016111,
    b: 8.688444,
    difference: 6.672333,
    ci: [5.42781, 8.194775],
    perTask: { "serial-dilution": [1.441333, 6.594667], calibration: [1.655333, 8.6395], "enzyme-kinetics": [2.951667, 10.831167] },
    digits: 2,
  },
  outputTokens: {
    key: "output_tokens",
    label: "Output tokens",
    unit: "tokens per session",
    a: 12280.866667,
    b: 45225.266667,
    difference: 32944.4,
    ci: [30136.7325, 35959.739167],
    perTask: { "serial-dilution": [9818.4, 41139.7], calibration: [10020.1, 44799.7], "enzyme-kinetics": [17004.1, 49736.4] },
    digits: 0,
  },
  assistantMessages: {
    key: "assistant_messages",
    label: "Assistant messages",
    unit: "messages per session",
    a: 8.1,
    b: 20.966667,
    difference: 12.866667,
    ci: [10.833333, 15.033333],
    perTask: { "serial-dilution": [7, 15.4], calibration: [7.4, 21], "enzyme-kinetics": [9.9, 26.5] },
    digits: 1,
  },
  lintPer100Lines: {
    key: "lint_per_100_lines",
    label: "Lint findings",
    unit: "per 100 lines of non-test code",
    a: 3.201258,
    b: 0.42151,
    difference: -2.779748,
    ci: [-3.531521, -2.091396],
    perTask: { "serial-dilution": [0.709942, 0], calibration: [2.849479, 0], "enzyme-kinetics": [6.044352, 1.264529] },
    digits: 2,
  },
} satisfies Record<string, SecondaryMetric>;

/** Counted from analysis.json `rows`: trials whose submission contained at least one test. */
export const trialsWithTests = { a: 2, b: 30, of: 30 };

/** Condition B trials whose recorded mutation score of 0 was a measurement failure (no valid tests). */
export const mutationValidationFailures = { task: "serial-dilution" as TaskId, condition: "B" as const, trials: 3 };
