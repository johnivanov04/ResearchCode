/**
 * Growth-rate calculations for the illustrative example on /example.
 *
 * The data here is SYNTHETIC: generated from a logistic model with a known
 * growth rate, so we can show exactly how far each common mistake moves the
 * answer. It is not a measurement of any real culture.
 */

export const TRUE_RATE_PER_H = 1.2;
export const BLANK_OD = 0.045;
const INITIAL_SIGNAL = 0.01;
const CARRYING_CAPACITY = 1.1;
const SAMPLE_INTERVAL_MIN = 15;
const DURATION_MIN = 720;

/** Minimum blank-corrected OD used in log transforms; below this, noise dominates. */
export const MIN_CORRECTED_OD = 0.005;
/** Sliding-window length in points (5 points at 15 min spacing = 1 hour). */
export const WINDOW_POINTS = 5;
/** Minimum R² for a window to be accepted as exponential growth. */
export const MIN_R2 = 0.98;

export type Reading = {
  timeMin: number;
  /** Raw OD600 as reported by the instrument, including the blank, to 3 decimals. */
  od: number;
};

export type LinearFit = { slope: number; intercept: number; r2: number };

/** Logistic growth signal (blank-corrected OD) at time t hours. */
export function logisticSignal(timeH: number, rate = TRUE_RATE_PER_H): number {
  const ratio = (CARRYING_CAPACITY - INITIAL_SIGNAL) / INITIAL_SIGNAL;
  return CARRYING_CAPACITY / (1 + ratio * Math.exp(-rate * timeH));
}

/** Illustrative plate-reader readings: logistic signal plus blank, rounded like an instrument export. */
export function illustrativeReadings(): Reading[] {
  const readings: Reading[] = [];
  for (let timeMin = 0; timeMin <= DURATION_MIN; timeMin += SAMPLE_INTERVAL_MIN) {
    const od = BLANK_OD + logisticSignal(timeMin / 60);
    readings.push({ timeMin, od: Math.round(od * 1000) / 1000 });
  }
  return readings;
}

/** Ordinary least-squares fit of y on x. Throws if fewer than two points or x is constant. */
export function linearFit(x: readonly number[], y: readonly number[]): LinearFit {
  if (x.length !== y.length) throw new Error("x and y must have the same length");
  if (x.length < 2) throw new Error("at least two points are required");
  const n = x.length;
  const meanX = x.reduce((sum, v) => sum + v, 0) / n;
  const meanY = y.reduce((sum, v) => sum + v, 0) / n;
  let sxx = 0;
  let sxy = 0;
  let syy = 0;
  for (let i = 0; i < n; i++) {
    const dx = x[i] - meanX;
    const dy = y[i] - meanY;
    sxx += dx * dx;
    sxy += dx * dy;
    syy += dy * dy;
  }
  if (sxx === 0) throw new Error("x values must not all be equal");
  const slope = sxy / sxx;
  const intercept = meanY - slope * meanX;
  const r2 = syy === 0 ? 1 : (sxy * sxy) / (sxx * syy);
  return { slope, intercept, r2 };
}

export type WindowFit = LinearFit & { startIndex: number; endIndex: number };

/**
 * Steepest sliding-window fit whose R² meets `minR2`.
 * Throws if no window qualifies, rather than returning a misleading value.
 */
export function steepestWindow(
  x: readonly number[],
  y: readonly number[],
  windowPoints = WINDOW_POINTS,
  minR2 = MIN_R2,
): WindowFit {
  let best: WindowFit | undefined;
  for (let start = 0; start + windowPoints <= x.length; start++) {
    const end = start + windowPoints;
    const fit = linearFit(x.slice(start, end), y.slice(start, end));
    if (fit.r2 >= minR2 && (!best || fit.slope > best.slope)) {
      best = { ...fit, startIndex: start, endIndex: end - 1 };
    }
  }
  if (!best) throw new Error("no window meets the R² threshold");
  return best;
}

export type ScenarioId = "correct" | "no-blank" | "log10" | "whole-curve" | "minutes";

export type Scenario = {
  id: ScenarioId;
  label: string;
  description: string;
  /** Axis label for the transformed y values. */
  yLabel: string;
};

export const scenarios: readonly Scenario[] = [
  {
    id: "correct",
    label: "Following the specification",
    description:
      "Subtract the blank, take the natural log, and use the steepest 1-hour window with R² ≥ 0.98. Time is in hours.",
    yLabel: "ln(OD − blank)",
  },
  {
    id: "no-blank",
    label: "Blank not subtracted",
    description:
      "The natural log is taken of raw OD. The constant medium background flattens the early curve, so the slope is underestimated.",
    yLabel: "ln(OD)",
  },
  {
    id: "log10",
    label: "Base-10 logarithm",
    description:
      "log10 is used where the method assumes ln. Every slope is smaller by a factor of ln(10) ≈ 2.303.",
    yLabel: "log10(OD − blank)",
  },
  {
    id: "whole-curve",
    label: "One line through the whole curve",
    description:
      "A single straight line is fitted to every point, so the slowdown and stationary phase drag the slope down.",
    yLabel: "ln(OD − blank)",
  },
  {
    id: "minutes",
    label: "Time left in minutes",
    description:
      "The calculation is identical to the correct one, but time stays in minutes while the result is labelled per hour.",
    yLabel: "ln(OD − blank)",
  },
];

export type ScenarioResult = {
  scenario: Scenario;
  /** Points used in the plot: time in hours and the transformed value. */
  points: { timeH: number; y: number }[];
  /** The fitted line in plot coordinates (time in hours). */
  fit: { slope: number; intercept: number; startH: number; endH: number };
  /** The reported growth rate, as the faulty or correct code would report it (per hour). */
  reportedRatePerH: number;
  /** Doubling time implied by the reported rate, in minutes. */
  reportedDoublingMin: number;
  /** Relative error of the reported rate against the true rate. */
  relativeError: number;
};

export function analyseScenario(id: ScenarioId, readings: readonly Reading[] = illustrativeReadings()): ScenarioResult {
  const scenario = scenarios.find((s) => s.id === id);
  if (!scenario) throw new Error(`unknown scenario: ${id}`);

  const subtractBlank = id !== "no-blank";
  const log = id === "log10" ? Math.log10 : Math.log;

  const points = readings
    .map((r) => ({ timeH: r.timeMin / 60, value: subtractBlank ? r.od - BLANK_OD : r.od }))
    .filter((p) => p.value >= MIN_CORRECTED_OD)
    .map((p) => ({ timeH: p.timeH, y: log(p.value) }));

  const x = points.map((p) => p.timeH);
  const y = points.map((p) => p.y);

  let fit: ScenarioResult["fit"];
  if (id === "whole-curve") {
    const line = linearFit(x, y);
    fit = { slope: line.slope, intercept: line.intercept, startH: x[0], endH: x[x.length - 1] };
  } else {
    const window = steepestWindow(x, y);
    fit = { slope: window.slope, intercept: window.intercept, startH: x[window.startIndex], endH: x[window.endIndex] };
  }

  // With time left in minutes, the slope is per minute: 60 times smaller than per hour.
  const reportedRatePerH = id === "minutes" ? fit.slope / 60 : fit.slope;
  const reportedDoublingMin = (Math.LN2 / reportedRatePerH) * 60;

  return {
    scenario,
    points,
    fit,
    reportedRatePerH,
    reportedDoublingMin,
    relativeError: (reportedRatePerH - TRUE_RATE_PER_H) / TRUE_RATE_PER_H,
  };
}
