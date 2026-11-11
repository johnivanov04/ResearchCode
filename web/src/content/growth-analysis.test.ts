import { existsSync, readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import {
  appDirectory,
  appMethodStudyUrl,
  appPaths,
  appReadmeUrl,
  appSourceUrl,
  appSpecUrl,
  appVersion,
  checkCommands,
  figures,
  ownDataCommand,
  plateBias,
  plateResults,
  quickStart,
  sampleInputPreview,
  websiteWellResult,
} from "@/content/growth-analysis";
import { site } from "@/content/site";
import { BLANK_OD, illustrativeReadings } from "@/lib/growth";

// The application lives next to the website in the monorepo: ResearchCode/growth-analysis.
// (Built with node:path; Vite would treat `new URL(template, import.meta.url)` as an asset import.)
const here = dirname(fileURLToPath(import.meta.url));
const appRoot = resolve(here, "../../..", appDirectory);
const publicRoot = resolve(here, "../../public");
const appFile = (path: string) => join(appRoot, path);
const readme = readFileSync(appFile("README.md"), "utf8");

type WellJson = {
  well: string;
  status: string;
  credible: boolean;
  growth_rate_per_h: number | null;
  doubling_time_h: number | null;
  phase_start_h: number | null;
  phase_end_h: number | null;
  n_points_in_phase: number | null;
  r_squared: number | null;
  steepest_window_rate_per_h: number | null;
};
type ConditionJson = {
  condition: string;
  n_wells: number;
  n_credible: number;
  mean_growth_rate_per_h: number | null;
  sd_growth_rate_per_h: number | null;
  doubling_time_of_mean_rate_h: number | null;
};
type ResultsJson = { wells: WellJson[]; conditions: ConditionJson[] };

const readResults = (example: string): ResultsJson =>
  JSON.parse(readFileSync(appFile(`docs/example-output/${example}/results.json`), "utf8"));

/** Round as the page displays a value, to the number of decimals written in the content. */
function decimalsOf(value: number): number {
  const text = String(value);
  return text.includes(".") ? text.split(".")[1].length : 0;
}
function expectDisplayed(displayed: number | null, actual: number | null) {
  if (displayed === null || actual === null) {
    expect(actual).toBe(displayed);
    return;
  }
  // The displayed value must be the actual value rounded to the displayed precision
  // (at least 2 decimals, so "1.1" may stand for 1.10).
  const decimals = Math.max(decimalsOf(displayed), 2);
  expect(actual.toFixed(decimals)).toBe(displayed.toFixed(decimals));
}

function commandLines(snippet: string): string[] {
  return snippet
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
}

describe("example page matches the growth-analysis application", () => {
  it("finds the application and its version", () => {
    const pyproject = readFileSync(appFile("pyproject.toml"), "utf8");
    expect(pyproject).toMatch(/^name = "growth-analysis"$/m);
    expect(pyproject).toMatch(new RegExp(`^version = "${appVersion.replaceAll(".", "\\.")}"$`, "m"));
  });

  it.each(appPaths.map((path) => [path]))("%s exists", (path) => {
    expect(existsSync(appFile(path)), `missing ${appDirectory}/${path}`).toBe(true);
  });

  it("links point into this repository's main branch", () => {
    expect(appSourceUrl).toBe(`${site.repository}/tree/main/growth-analysis`);
    for (const url of [appReadmeUrl, appSpecUrl, appMethodStudyUrl]) {
      const path = url.replace(`${site.repository}/blob/main/${appDirectory}/`, "");
      expect(existsSync(appFile(path)), url).toBe(true);
    }
  });

  it.each(commandLines([quickStart, ownDataCommand, checkCommands].join("\n")).map((line) => [line]))(
    "README documents the command: %s",
    (line) => {
      expect(readme).toContain(line);
    },
  );

  it("sample input preview is the start of the real sample file", () => {
    const sample = readFileSync(appFile("data/sample/synthetic_plate.csv"), "utf8");
    expect(sample.startsWith(`${sampleInputPreview}\n`)).toBe(true);
  });

  it("plate results match the committed application output", () => {
    const results = readResults("plate");
    expect(plateResults.map((r) => r.condition)).toEqual(results.conditions.map((c) => c.condition));
    for (const row of plateResults) {
      const actual = results.conditions.find((c) => c.condition === row.condition)!;
      expect(row.wells).toBe(actual.n_wells);
      expect(row.credible).toBe(actual.n_credible);
      expectDisplayed(row.meanRatePerH, actual.mean_growth_rate_per_h);
      expectDisplayed(row.sdRatePerH, actual.sd_growth_rate_per_h);
      expectDisplayed(row.doublingTimeH, actual.doubling_time_of_mean_rate_h);
    }
  });

  it("model rates shown for the synthetic plate are the ones documented with the data", () => {
    const dataReadme = readFileSync(appFile("data/sample/README.md"), "utf8");
    for (const row of plateResults.filter((r) => r.modelRatePerH !== null)) {
      expect(dataReadme).toMatch(new RegExp(`\\| \`${row.condition}\` \\|[^\\n]*r = ${row.modelRatePerH!.toFixed(1)} per hour`));
    }
  });

  it("bias figures match the method study", () => {
    const study = readFileSync(appFile("docs/method-study.md"), "utf8");
    for (const row of plateBias) {
      const pattern = new RegExp(
        `^\\| 10 \\| ${row.condition} \\(r = [0-9.]+\\) \\| [0-9.]+ \\| ${row.noiseFreeOverR.toFixed(3)} \\| \\+${row.biasPercent.toFixed(1)}% \\|`,
        "m",
      );
      expect(study).toMatch(pattern);
    }
  });

  it("the illustrative well's result matches the committed application output", () => {
    const [well] = readResults("website-example").wells;
    expect(well.status).toBe("growth");
    expect(well.credible).toBe(true);
    expectDisplayed(websiteWellResult.ratePerH, well.growth_rate_per_h);
    expect((well.doubling_time_h! * 60).toFixed(1)).toBe(websiteWellResult.doublingTimeMin.toFixed(1));
    expect(well.phase_start_h).toBe(websiteWellResult.phaseStartH);
    expect(well.phase_end_h).toBe(websiteWellResult.phaseEndH);
    expect(well.n_points_in_phase).toBe(websiteWellResult.pointsInPhase);
    expect(well.r_squared!.toFixed(3)).toBe(websiteWellResult.rSquared.toFixed(3));
    expect(well.steepest_window_rate_per_h!.toFixed(3)).toBe(websiteWellResult.steepestWindowRatePerH.toFixed(3));
  });

  it("the application's website sample is exactly this page's illustrative data", () => {
    const rows = readFileSync(appFile("data/sample/synthetic_website_example.csv"), "utf8")
      .trim()
      .split("\n")
      .slice(1)
      .map((line) => line.split(","));
    const well = rows.filter((r) => r[1] === "illustrative");
    const blank = rows.filter((r) => r[1] === "blank");
    const readings = illustrativeReadings();
    expect(well).toHaveLength(readings.length);
    well.forEach(([, , time, od], i) => {
      expect(Number(time)).toBe(readings[i].timeMin);
      expect(Number(od)).toBe(readings[i].od);
    });
    expect(blank.every(([, , , od]) => Number(od) === BLANK_OD)).toBe(true);
  });

  it.each(figures.map((f) => [f.src, f]))("figure %s is the application's output, with correct size", (_, figure) => {
    const published = readFileSync(join(publicRoot, figure.src));
    const source = readFileSync(appFile(figure.source));
    expect(published.equals(source)).toBe(true);
    // PNG header: width and height are big-endian 32-bit integers at bytes 16 and 20.
    expect(published.readUInt32BE(16)).toBe(figure.width);
    expect(published.readUInt32BE(20)).toBe(figure.height);
    expect(figure.alt.length).toBeGreaterThan(40);
  });
});
