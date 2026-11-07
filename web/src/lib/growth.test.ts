import { describe, expect, it } from "vitest";
import {
  BLANK_OD,
  TRUE_RATE_PER_H,
  analyseScenario,
  illustrativeReadings,
  linearFit,
  scenarios,
  steepestWindow,
} from "@/lib/growth";

describe("linearFit", () => {
  it("recovers slope and intercept of an exact line", () => {
    const x = [0, 1, 2, 3, 4];
    const y = x.map((v) => 2.5 * v - 1);
    const fit = linearFit(x, y);
    expect(fit.slope).toBeCloseTo(2.5, 12);
    expect(fit.intercept).toBeCloseTo(-1, 12);
    expect(fit.r2).toBeCloseTo(1, 12);
  });

  it("rejects mismatched, too short, or constant input", () => {
    expect(() => linearFit([1, 2], [1])).toThrow();
    expect(() => linearFit([1], [1])).toThrow();
    expect(() => linearFit([2, 2, 2], [1, 2, 3])).toThrow();
  });
});

describe("steepestWindow", () => {
  it("finds the exact rate of noise-free exponential data", () => {
    const x = Array.from({ length: 24 }, (_, i) => i * 0.25);
    const y = x.map((t) => Math.log(0.02 * Math.exp(0.8 * t)));
    expect(steepestWindow(x, y).slope).toBeCloseTo(0.8, 10);
  });

  it("throws instead of returning a value when no window qualifies", () => {
    const x = [0, 1, 2, 3, 4, 5];
    const y = [0, 5, -3, 4, -2, 6];
    expect(() => steepestWindow(x, y)).toThrow(/R²/);
  });
});

describe("illustrative data", () => {
  it("covers 12 hours at 15-minute intervals and includes the blank", () => {
    const readings = illustrativeReadings();
    expect(readings).toHaveLength(49);
    expect(readings[0].timeMin).toBe(0);
    expect(readings.at(-1)?.timeMin).toBe(720);
    expect(Math.min(...readings.map((r) => r.od))).toBeGreaterThan(BLANK_OD);
  });
});

describe("scenarios", () => {
  it("recovers the true rate within 1% when the specification is followed", () => {
    const result = analyseScenario("correct");
    expect(Math.abs(result.relativeError)).toBeLessThan(0.01);
    expect(result.reportedDoublingMin).toBeCloseTo((Math.LN2 / result.reportedRatePerH) * 60, 10);
  });

  it("log10 understates the rate by a factor of ln(10)", () => {
    const ratio = analyseScenario("correct").reportedRatePerH / analyseScenario("log10").reportedRatePerH;
    expect(ratio).toBeCloseTo(Math.LN10, 6);
  });

  it("leaving time in minutes understates the rate by a factor of 60", () => {
    const ratio = analyseScenario("correct").reportedRatePerH / analyseScenario("minutes").reportedRatePerH;
    expect(ratio).toBeCloseTo(60, 10);
  });

  it("every mistake underestimates the true rate by more than 10%", () => {
    for (const scenario of scenarios.filter((s) => s.id !== "correct")) {
      const result = analyseScenario(scenario.id);
      expect(result.reportedRatePerH, scenario.id).toBeLessThan(TRUE_RATE_PER_H * 0.9);
    }
  });
});
