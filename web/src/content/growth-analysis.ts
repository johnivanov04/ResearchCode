import { site } from "@/content/site";

/**
 * Facts about the Phase 3 growth-analysis application shown on /example.
 *
 * Every number here is copied from the committed example output in
 * growth-analysis/docs/example-output/, which the application produced from SYNTHETIC
 * sample data. `growth-analysis.test.ts` checks each number, path, command, and figure
 * against those files, so this page cannot drift from what the code actually produces.
 */

export const appDirectory = "growth-analysis";
export const appSourceUrl = `${site.repository}/tree/main/${appDirectory}`;
export const appBlobUrl = `${site.repository}/blob/main/${appDirectory}`;
export const appReadmeUrl = `${appBlobUrl}/README.md`;
export const appSpecUrl = `${appBlobUrl}/docs/spec-growth-curve.md`;
export const appMethodStudyUrl = `${appBlobUrl}/docs/method-study.md`;
export const appVersion = "0.1.0";

/** Paths (relative to growth-analysis/) that the page refers to. */
export const appPaths = [
  "README.md",
  "docs/spec-growth-curve.md",
  "docs/method-study.md",
  "data/sample/synthetic_plate.csv",
  "data/sample/synthetic_website_example.csv",
  "src/growth_analysis/exponential.py",
  "src/growth_analysis/provenance.py",
  "tests/test_validation.py",
] as const;

export const quickStart = `git clone --depth 1 ${site.repository}.git
cd ResearchCode/${appDirectory}
uv sync --locked
uv run growth-analyze --input data/sample/synthetic_plate.csv --output results/sample`;

export const ownDataCommand = "uv run growth-analyze --input path/to/plate.csv --output results/plate1";

export const checkCommands = `uv run pytest
uv run ruff check .
uv run ruff format --check .`;

/** First rows of data/sample/synthetic_plate.csv (synthetic). */
export const sampleInputPreview = `well,condition,time_min,od600
A1,blank,0,0.040
A2,blank,0,0.041
A3,blank,0,0.042
B2,condition_A,0,0.044
B3,condition_A,0,0.043`;

export const methodSteps: { title: string; body: string }[] = [
  {
    title: "Validate the file",
    body: "Required columns, a time column whose name states its unit, numbers that are finite, no duplicate readings, and times in order. Every problem is reported with its line number; nothing is dropped or repaired.",
  },
  {
    title: "Subtract the blank",
    body: "The mean of the medium-only wells is subtracted from every reading. Readings below ten blank standard deviations (at least 0.005) are excluded from fitting, with the reason recorded.",
  },
  {
    title: "Find the exponential phase",
    body: "Fit a line to ln(OD) in every five-reading window. Start at the steepest window and extend over neighbouring windows whose slope is at least 80% of it.",
  },
  {
    title: "Fit one line to the whole phase",
    body: "The slope of ln(OD) over all readings in the phase is the specific growth rate μ; the doubling time is ln 2 / μ.",
  },
  {
    title: "Judge credibility",
    body: "A fit is credible only with R² ≥ 0.98, a relative standard error ≤ 10%, and no excluded reading inside the phase. Wells that grew less than two-fold are reported as no growth or decline.",
  },
  {
    title: "Summarise and record",
    body: "Replicate wells are summarised by condition. Tables, figures for every well, and run metadata (versions, settings, input checksum, Git commit) are written; existing results are never overwritten.",
  },
];

export const outputs: { file: string; contents: string }[] = [
  { file: "well_results.csv", contents: "Rate, standard error, doubling time, R², phase, status, and flags for every well" },
  { file: "condition_summary.csv", contents: "Mean, SD, SEM, and range of credible rates per condition, and wells left out with the reason" },
  { file: "points.csv", contents: "Every reading, whether it was used in the fit, and why not" },
  { file: "results.json", contents: "All of the above with the settings, blank, assumptions, and warnings" },
  { file: "figures/", contents: "Growth curves, the fit for every well, and a comparison by condition (PNG and SVG)" },
  { file: "run_metadata.json", contents: "Python and package versions, lock file checksum, Git commit, settings, input checksum" },
];

/** Condition summary from docs/example-output/plate/ (synthetic plate). */
export const plateResults: {
  condition: string;
  modelRatePerH: number | null;
  wells: number;
  credible: number;
  meanRatePerH: number | null;
  sdRatePerH: number | null;
  doublingTimeH: number | null;
}[] = [
  { condition: "condition_A", modelRatePerH: 1.0, wells: 3, credible: 3, meanRatePerH: 0.937, sdRatePerH: 0.023, doublingTimeH: 0.74 },
  { condition: "condition_B", modelRatePerH: 0.6, wells: 3, credible: 3, meanRatePerH: 0.633, sdRatePerH: 0.038, doublingTimeH: 1.1 },
  { condition: "condition_C", modelRatePerH: null, wells: 3, credible: 0, meanRatePerH: null, sdRatePerH: null, doublingTimeH: null },
];

/**
 * Bias on the synthetic plate model at the default quantification limit (10 blank SDs), from
 * growth-analysis/docs/method-study.md, section 3: the method's noise-free value as a
 * fraction of r, and the mean of 150 noisy plates relative to that value (percent).
 */
export const plateBias: { condition: string; noiseFreeOverR: number; biasPercent: number }[] = [
  { condition: "condition_A", noiseFreeOverR: 0.923, biasPercent: 0.7 },
  { condition: "condition_B", noiseFreeOverR: 0.919, biasPercent: 7.4 },
];

/** Result for this page's illustrative well, from docs/example-output/website-example/. */
export const websiteWellResult = {
  ratePerH: 1.121,
  doublingTimeMin: 37.1,
  phaseStartH: 0,
  phaseEndH: 3,
  pointsInPhase: 13,
  rSquared: 0.999,
  steepestWindowRatePerH: 1.2,
};

export type Figure = {
  /** Path under web/public. */
  src: string;
  /** The committed application output it is copied from, relative to growth-analysis/. */
  source: string;
  width: number;
  height: number;
  alt: string;
  caption: string;
};

export const figures: Figure[] = [
  {
    src: "/growth-analysis/website-example-well-B3.png",
    source: "docs/example-output/website-example/figures/wells/B3.png",
    width: 1600,
    height: 680,
    alt: "Two panels for the illustrative well. Left: blank-corrected OD600 rising from 0.01 to a plateau near 1.1 over 12 hours, with the fitted exponential curve over the first 3 hours. Right: the same data on a log scale, where the readings from 0 to 3 hours fall on a straight fitted line.",
    caption: "The illustrative well from this page, analysed by the application. The shaded band is the detected exponential phase (0–3 h); filled markers are the readings used in the fit.",
  },
  {
    src: "/growth-analysis/plate-exponential-fits.png",
    source: "docs/example-output/plate/figures/exponential_fits.png",
    width: 2080,
    height: 1680,
    alt: "Nine log-scale panels, one per well of the synthetic plate. Wells B2 to B4 and C2 to C4 show a shaded exponential phase with a fitted line and their growth rates; wells D2 to D4 are flat and labelled no growth detected. Early readings below the quantification limit are marked with crosses.",
    caption: "Every well of the synthetic sample plate: the detected exponential phase (shaded), readings used (filled), not used (hollow), excluded below the quantification limit (×), and the fitted curve.",
  },
  {
    src: "/growth-analysis/plate-growth-rate-comparison.png",
    source: "docs/example-output/plate/figures/growth_rate_comparison.png",
    width: 1140,
    height: 760,
    alt: "Growth rate by condition. condition_A wells near 0.92 to 0.96 per hour with a mean of 0.94; condition_B wells near 0.59 to 0.66 per hour with a mean of 0.63; condition_C has no credible growth rate.",
    caption: "Growth rates by condition on the synthetic plate, with the mean and ±1 SD of the credible wells.",
  },
];

/** How the Phase 2 starter kit shaped the application. */
export const starterContributions: { title: string; body: string }[] = [
  {
    title: "Specification first",
    body: "The method, units, edge cases, and tolerances were written in docs/spec-growth-curve.md from the starter's template before any code.",
  },
  {
    title: "Tests with independent answers",
    body: "Expected values come from mathematics: exact exponential data, a proven bound for logistic data, and exact rational arithmetic. Hypothesis checks invariances on random curves.",
  },
  {
    title: "Validation that found real problems",
    body: "A study on synthetic data showed that the steepest-window method overestimates noisy growth rates and that a three-SD blank threshold biased estimates upward. Both were changed, and the bias that remains for slow growth is measured and documented.",
  },
  {
    title: "Bugs introduced on purpose",
    body: "An off-by-one, log10 instead of ln, reporting the steepest window, and skipping the blank were each caught by the tests, and the correct code was restored.",
  },
  {
    title: "Provenance and locked environments",
    body: "The starter's run-metadata module records every run; uv.lock pins every package; reruns produce byte-identical tables.",
  },
  {
    title: "Rules for AI assistants",
    body: "The starter's AGENTS.md (never fabricate, never loosen a test, ask when the science is ambiguous) applies to the application too.",
  },
];
