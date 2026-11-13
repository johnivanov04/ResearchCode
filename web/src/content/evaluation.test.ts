import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import {
  access,
  caseCategories,
  conditions,
  design,
  evaluatorValidation,
  experimentStatus,
  experimentsDirectory,
  primaryMetric,
  protocolUrl,
  protocolVersion,
  researchLogUrl,
  researchQuestion,
  runningTrialsUrl,
  secondaryMetrics,
  tasks,
} from "@/content/evaluation";
import { site } from "@/content/site";

// The experiment lives next to the website in the monorepo: ResearchCode/experiments.
const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, "../../..", experimentsDirectory);
const readJson = (path: string) => JSON.parse(readFileSync(join(root, path), "utf8"));
const config = readJson("experiment.json");
const validation = readJson("docs/evaluator-validation.json");
const protocol = readFileSync(join(root, "docs/PROTOCOL.md"), "utf8");

describe("the evaluation page matches the experiment's actual configuration", () => {
  it("shows the configured status, protocol version, and research question", () => {
    expect(experimentStatus).toBe(config.status);
    expect(protocolVersion).toBe(config.protocol_version);
    expect(researchQuestion).toBe(config.research_question);
  });

  it("lists the configured conditions and tasks", () => {
    expect(conditions.map((c) => [c.id, c.name])).toEqual(config.conditions.map((c: { id: string; name: string }) => [c.id, c.name]));
    expect(tasks.map((t) => [t.id, t.module, t.title.replace("–", "-")])).toEqual(
      config.tasks.map((t: { id: string; module: string; title: string }) => [t.id, t.module, t.title]),
    );
    for (const task of tasks) {
      expect(existsSync(join(root, "tasks", task.id, "TASK.md")), task.id).toBe(true);
    }
  });

  it("states the configured design parameters", () => {
    expect(design).toEqual({
      pilotTrialsPerCell: config.design.pilot_trials_per_cell,
      confirmatoryTrialsPerCell: config.design.confirmatory_trials_per_cell,
      scheduleSeed: config.design.schedule_seed,
      minimumValidPerCell: config.design.minimum_valid_trials_per_cell_for_inference,
      bootstrapResamples: config.analysis.bootstrap_resamples,
      model: config.agent.model,
      toolVersion: config.agent.tool_version,
      effort: config.agent.effort,
      wallClockMinutes: config.agent.wall_clock_limit_minutes,
      caseTimeoutSeconds: config.evaluation.case_timeout_seconds,
      maxContinuationMessages: config.agent.max_continuation_messages,
    });
  });

  it("describes the zero-cost, manual subscription procedure as configured", () => {
    expect(access.additionalSpendingUsd).toBe(config.billing.additional_spending_usd);
    expect(access.additionalSpendingUsd).toBe(0);
    expect(config.billing.automated_model_calls).toBe(false);
    expect(access.sessionMode).toBe(config.agent.session_mode);
    expect(access.summary).toMatch(/Claude Pro subscription/);
    expect(access.summary).toMatch(/nothing calls the model automatically/);
    expect(access.operatorSteps.join(" ")).toContain(`after ${config.agent.wall_clock_limit_minutes} minutes`);
    expect(protocol).toContain("Additional spending | **$0.**");
    expect(JSON.stringify(config)).not.toContain("max_budget_usd");
  });

  it("uses the configured metrics and case categories", () => {
    expect(primaryMetric.name).toBe(config.metrics.primary.name);
    expect(caseCategories.map((c) => c.id)).toEqual(config.case_categories);
    const configured = config.metrics.secondary as { kind: string }[];
    expect(secondaryMetrics.filter((m) => m.kind === "subjective")).toHaveLength(configured.filter((m) => m.kind === "subjective").length);
    expect(secondaryMetrics.length).toBeGreaterThanOrEqual(configured.length - 2);
  });

  it("reports the evaluator validation exactly as recorded", () => {
    expect(validation.problems).toEqual([]);
    expect(evaluatorValidation.totalCases).toBe(validation.total_cases);
    expect(evaluatorValidation.totalDefects).toBe(validation.total_mutants);
    expect(evaluatorValidation.tasks.map((t) => t.id)).toEqual(Object.keys(validation.tasks));
    for (const task of evaluatorValidation.tasks) {
      const saved = validation.tasks[task.id];
      expect(task.cases).toBe(saved.cases);
      expect(task.casesByCategory).toEqual(saved.cases_by_category);
      expect(task.referencePassRate).toBe(saved.reference_pass_rate);
      expect(task.defects).toBe(saved.mutants.length);
      expect(task.defectsDetected).toBe(saved.mutants_detected);
    }
  });

  it("agrees with the protocol text", () => {
    expect(protocol).toContain(`Protocol version | ${protocolVersion}`);
    expect(protocol).toContain(`Claude Code ${design.toolVersion}`);
    expect(protocol).toContain(`${design.confirmatoryTrialsPerCell} trials per task and condition`);
  });

  it("links to documents that exist in the experiments folder", () => {
    for (const url of [protocolUrl, researchLogUrl, runningTrialsUrl]) {
      const path = url.replace(`${site.repository}/blob/main/${experimentsDirectory}/`, "");
      expect(existsSync(join(root, path)), url).toBe(true);
    }
  });

  it("publishes no results while no trials have been run", () => {
    expect(config.status).toBe("framework-ready");
    for (const kind of ["genuine", "pilot"]) {
      const folder = join(root, "results", kind);
      const trials = readdirSync(folder).filter((name) => statSync(join(folder, name)).isDirectory());
      expect(trials, `${kind} trials exist; update the page with real results`).toEqual([]);
    }
  });
});
