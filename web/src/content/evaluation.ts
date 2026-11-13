import { site } from "@/content/site";

/**
 * Facts about the Phase 4 experiment shown on /evaluation.
 *
 * Every value is copied from experiments/experiment.json, experiments/docs/PROTOCOL.md, and
 * experiments/docs/evaluator-validation.json. `evaluation.test.ts` checks each of them
 * against those files, so the published methodology cannot drift from the experiment's
 * actual configuration. No trial has been run: there are no results here.
 */

export const experimentsDirectory = "experiments";
export const experimentsUrl = `${site.repository}/tree/main/${experimentsDirectory}`;
export const protocolUrl = `${site.repository}/blob/main/${experimentsDirectory}/docs/PROTOCOL.md`;
export const researchLogUrl = `${site.repository}/blob/main/${experimentsDirectory}/docs/RESEARCH_LOG.md`;
export const runningTrialsUrl = `${site.repository}/blob/main/${experimentsDirectory}/docs/RUNNING_TRIALS.md`;

/** Mirrors experiment.json `status`. Only "framework-ready" is possible until trials run. */
export const experimentStatus = "framework-ready" as const;
export const protocolVersion = "1.2";

export const researchQuestion =
  "When the same AI coding agent, with the same model, tools, and limits, is given the same scientific programming task, does working within ResearchCode's structured workflow produce more reliable scientific software than unstructured AI coding?";

export const primaryHypothesis =
  "The mean share of hidden evaluation cases passed differs between the structured condition (B) and the unstructured condition (A), averaged over tasks with equal weight. We expect B > A, but the test is two-sided.";

export type Condition = { id: "A" | "B"; name: string; receives: string[]; prompt: string };

export const conditions: Condition[] = [
  {
    id: "A",
    name: "Unstructured AI coding",
    receives: ["The task statement (TASK.md)", "Its public examples"],
    prompt:
      "Implement the module described in the task, and write and run code as it sees fit. Nothing else restricts it: it may install packages and write tests if it chooses.",
  },
  {
    id: "B",
    name: "ResearchCode structured development",
    receives: [
      "The same task statement and public examples",
      "A copy of the scientific starter kit: AGENTS.md, the specification template, security checklist, and test setup",
    ],
    prompt:
      "Follow the starter kit's workflow: write a specification, write known-answer, edge-case, and property-based tests, implement, run Ruff and pytest, and document assumptions.",
  },
];

export const sharedControls = [
  "Same model and Claude Code version, effort, tools, and time limit",
  "One Claude Code session per trial, started and ended by an operator who does not guide the agent, from a new, clean workspace",
  "The same container image with Python 3.12, uv, and Git, and an empty home directory",
  "Network access only to the model API and the Python package index; web search and GitHub are blocked",
  "Prompts do not mention the experiment, the other condition, or the hidden tests",
];

export type Task = {
  id: string;
  module: string;
  title: string;
  summary: string;
  failureModes: string[];
};

export const tasks: Task[] = [
  {
    id: "serial-dilution",
    module: "serial_dilution",
    title: "Serial dilutions and plate counts",
    summary: "Volume units, dilution factors, CFU per mL from colony counts, and C1V1 = C2V2.",
    failureModes: [
      "Two different “micro” characters in unit strings",
      "Inverted dilution ratios",
      "Plates outside the countable range, with inclusive bounds",
      "Input validation and unmodified arguments",
    ],
  },
  {
    id: "calibration",
    module: "calibration",
    title: "Calibration curve and inverse prediction",
    summary: "A linear standard curve, unknown concentrations with standard errors and t-based intervals, LOD and LOQ.",
    failureModes: [
      "Normal instead of Student t quantiles",
      "Wrong degrees of freedom or a missing replicate term",
      "Clipping negative estimates; missing extrapolation flags",
      "Numerically unstable sums",
    ],
  },
  {
    id: "enzyme-kinetics",
    module: "enzyme_kinetics",
    title: "Michaelis–Menten kinetics and a CSV tool",
    summary: "Nonlinear least-squares fitting with standard errors, plus a command-line tool from CSV to JSON.",
    failureModes: [
      "Biased linearised fits",
      "Undetermined parameters returned as numbers",
      "mM/µM units, byte-order marks, and blank lines in CSV files",
      "Overwriting results or writing output after an error",
    ],
  },
];

export const caseCategories = [
  { id: "known_answer", label: "Known answer" },
  { id: "edge_case", label: "Edge case" },
  { id: "invalid_input", label: "Invalid input" },
  { id: "numerical", label: "Numerical" },
  { id: "reproducibility", label: "Reproducibility" },
  { id: "integration", label: "Integration" },
] as const;

/** From experiments/docs/evaluator-validation.json (checks of the scoring system, not results). */
export const evaluatorValidation = {
  totalCases: 110,
  totalDefects: 24,
  tasks: [
    {
      id: "serial-dilution",
      cases: 53,
      casesByCategory: { known_answer: 17, edge_case: 11, invalid_input: 23, reproducibility: 2 },
      referencePassRate: 1,
      defects: 9,
      defectsDetected: 9,
    },
    {
      id: "calibration",
      cases: 30,
      casesByCategory: { known_answer: 7, edge_case: 7, invalid_input: 12, numerical: 2, reproducibility: 2 },
      referencePassRate: 1,
      defects: 8,
      defectsDetected: 8,
    },
    {
      id: "enzyme-kinetics",
      cases: 27,
      casesByCategory: { known_answer: 3, edge_case: 3, invalid_input: 5, numerical: 2, reproducibility: 2, integration: 12 },
      referencePassRate: 1,
      defects: 7,
      defectsDetected: 7,
    },
  ],
} as const;

export const primaryMetric = {
  name: "Hidden pass rate",
  definition:
    "The share of a task's hidden evaluation cases that a submission passes. Cases have equal weight within a task, and tasks have equal weight overall. The agent never sees the hidden cases.",
};

export const secondaryMetrics: { name: string; how: string; kind: "objective" | "subjective" }[] = [
  { name: "Category pass rates", how: "Pass rate within each case category, such as invalid input and edge cases.", kind: "objective" },
  { name: "Category-balanced pass rate", how: "Sensitivity analysis: every category weighted equally, so that tasks with many validation cases do not dominate.", kind: "objective" },
  { name: "Numerical accuracy", how: "Median relative error of numeric results on known-answer cases.", kind: "objective" },
  { name: "Mutation score", how: "The share of known defects that the submission's own tests detect, using only tests that pass against the reference solution.", kind: "objective" },
  { name: "Static security findings", how: "Ruff security (S) rules on non-test code, with a fixed rule set that ignores the submission's own configuration.", kind: "objective" },
  { name: "Lint density and dependencies", how: "Findings per 100 lines, runtime dependencies beyond NumPy and SciPy, and lock files.", kind: "objective" },
  { name: "Development effort", how: "Wall-clock time, plus the turns, tokens, and cost that Claude Code reports. Unreported values stay missing.", kind: "objective" },
  { name: "Blinded maintainability review", how: "A human scores clarity, units and assumptions, validation, and structure (1–4) on anonymised code.", kind: "subjective" },
];

export const design = {
  pilotTrialsPerCell: 1,
  confirmatoryTrialsPerCell: 10,
  scheduleSeed: 20261111,
  minimumValidPerCell: 5,
  bootstrapResamples: 10000,
  model: "claude-opus-5-5",
  toolVersion: "2.1.319",
  effort: "high",
  wallClockMinutes: 45,
  caseTimeoutSeconds: 20,
  maxContinuationMessages: 2,
};

/** Protocol 1.1: how trials are run and paid for (mirrors experiment.json `billing` and `agent`). */
export const access = {
  additionalSpendingUsd: 0,
  sessionMode: "manual-interactive",
  summary:
    "Each trial is a Claude Code session that the experimenter starts by hand, through an existing Claude Pro subscription. No API key, usage credits, or other paid services are used, and nothing calls the model automatically.",
  operatorSteps: [
    "Run one command, which opens Claude Code in the isolated container with the trial prompt already entered",
    "Answer only Claude Code's own startup dialogs, then leave the agent alone",
    "If the agent stops to ask a question, send one fixed message, the same in both conditions, at most twice",
    "Exit when the agent says it has finished; the container stops by itself after 45 minutes",
  ],
  usageNote:
    "Claude Pro has usage limits that reset over time, so the number of trials that fit is not known in advance. Trials run in schedule order and stop only at the end of a complete block. The report states how many trials were planned and how many were achieved, and what a smaller sample cannot show.",
};

export const isolationSteps = [
  {
    title: "Clean workspace",
    body: "Each trial gets a new directory outside the repository with only the task material and, in Condition B, the starter kit. Its contents are checked against every hidden file by hash.",
  },
  {
    title: "Contained agent",
    body: "Claude Code runs in a container where only that workspace is mounted, with an empty home directory and an allow-list proxy as its only network route.",
  },
  {
    title: "Sandboxed evaluation",
    body: "Generated code runs in a fresh container with no network, a read-only file system, a non-root user, no capabilities, and CPU, memory, process, and time limits.",
  },
  {
    title: "Grading outside the sandbox",
    body: "The sandbox receives only the inputs of the hidden cases. Expected values stay on the host, so a submission cannot see or change its scoring.",
  },
  {
    title: "A private evaluator",
    body: "The hidden cases, reference solutions, and deliberate defects are kept outside this public repository until data collection ends. Their SHA-256 hashes are published in the freeze record, so anyone can check later that they did not change.",
  },
];

export const threats = [
  {
    title: "Small task set and sample",
    body: "Three small tasks and 10 trials per cell can show only large differences, on these tasks. Cells with fewer than 5 valid trials are reported descriptively.",
  },
  {
    title: "Designer bias",
    body: "The tasks and the evaluator were designed by the project team with help from the same family of AI model being evaluated. They were frozen before any trial.",
  },
  {
    title: "Agents, not people",
    body: "The trials measure an AI agent working alone. They do not show how human researchers would use either workflow.",
  },
  {
    title: "Adapted treatment",
    body: "The starter kit tells assistants to stop and ask a human. With no human present, Condition B records its decisions instead.",
  },
  {
    title: "Model drift",
    body: "The model service can change during collection. Blocked randomisation spreads any change across both conditions, and versions are recorded.",
  },
  {
    title: "Manual operation",
    body: "A person starts and ends each session. Their role is fixed and recorded, but session timing can vary, and the operator can see which condition is running.",
  },
  {
    title: "Subscription limits",
    body: "Usage limits may allow fewer trials than planned, which widens the uncertainty. Sessions interrupted by a limit are invalid and rerun from scratch.",
  },
  {
    title: "No web search",
    body: "Both conditions lose web search, which some real workflows use. This also keeps the project's public materials out of the agent's reach.",
  },
];
