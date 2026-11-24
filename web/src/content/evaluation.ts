import { site } from "@/content/site";

/**
 * Facts about the Phase 4 experiment shown on /evaluation.
 *
 * Every value is copied from experiments/experiment.json, experiments/docs/PROTOCOL.md, and
 * experiments/docs/evaluator-validation.json. `evaluation.test.ts` checks each of them
 * against those files, so the published methodology cannot drift from the experiment's
 * actual configuration. The experiment is complete; its aggregate results are in
 * `evaluation-results.ts`, checked against the frozen analysis output.
 */

export const experimentsDirectory = "experiments";
export const experimentsUrl = `${site.repository}/tree/main/${experimentsDirectory}`;
export const protocolUrl = `${site.repository}/blob/main/${experimentsDirectory}/docs/PROTOCOL.md`;
export const researchLogUrl = `${site.repository}/blob/main/${experimentsDirectory}/docs/RESEARCH_LOG.md`;
export const runningTrialsUrl = `${site.repository}/blob/main/${experimentsDirectory}/docs/RUNNING_TRIALS.md`;
export const reportSourceUrl = `${site.repository}/blob/main/${experimentsDirectory}/docs/FINAL_REPORT.md`;
export const aggregateResultsUrl = `${site.repository}/blob/main/${experimentsDirectory}/docs/aggregate-results.json`;
export const protocol14Url = `${site.repository}/blob/main/${experimentsDirectory}/freeze-history/PROTOCOL-1.4.md`;
/** The merge that gave protocol 1.4 its only third-party timestamp, before the first pilot session. */
export const protocol14MergeUrl = `${site.repository}/pull/5`;

/**
 * Mirrors experiment.json `status`. That file is frozen by hash, so the field still reads
 * "data-collection" although all trials and the pre-registered analysis are complete; completion
 * is recorded by the analysis output and the research log, not by this field.
 */
export const experimentStatus = "data-collection" as const;
export const protocolVersion = "1.5";

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
  "One Claude Code session per trial from a new, clean workspace, with no one guiding the agent: the first seven started and ended by an operator, the rest unattended",
  "The same container image with Python 3.12, uv, and Git, and a fresh home directory",
  "Network access only to the model API, the sign-in token service, and the Python package index; web search and GitHub are blocked",
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
  { name: "Blinded maintainability review", how: "Planned: a human scores clarity, units and assumptions, validation, and structure (1–4) on anonymised code. Not conducted.", kind: "subjective" },
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
  sessionMode: "unattended-noninteractive",
  summary:
    "Every trial used an existing Claude Pro subscription and nothing else: no API key, usage credits, or other paid services. The pilot and the first confirmatory trial were run by hand. Under protocol 1.5, the experimenter started batches that ran the remaining 59 trials unattended, in the randomised order; a batch refused to start if any other credential was present.",
  operatorSteps: [
    "The operator checked that paid extra usage was turned off and that only the subscription token was set",
    "A batch ran the next trials one at a time in the randomised order, each in the isolated container with its prompt",
    "No one guided the agent and no message was sent after the prompt; each session ended when the agent finished, or would have ended after 45 minutes",
    "A batch stopped at once on any sign of an API key, paid usage, a usage limit, or a sign-in error, and after any trial that needed a decision",
  ],
  usageNote:
    "All 60 planned confirmatory trials were completed and analysed. Two attempts were stopped by infrastructure, one by the subscription's usage limit and one by dropped connections while the host computer slept, and both were rerun from a new workspace under the pre-registered rule. Neither stopped attempt was evaluated.",
};

export const isolationSteps = [
  {
    title: "Clean workspace",
    body: "Each trial gets a new directory outside the repository with only the task material and, in Condition B, the starter kit. Its contents are checked against every hidden file by hash.",
  },
  {
    title: "Contained agent",
    body: "Claude Code runs in a container where only that workspace is mounted, with a fresh home directory and an allow-list proxy as its only network route.",
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
    body: "The hidden cases, reference solutions, and deliberate defects are kept in a private repository. Their SHA-256 hashes are in the freeze record. The protocol promised to release them after data collection; they were not released (see limitations).",
  },
];

/**
 * Limitations of the completed experiment, including problems found after the analysis ran.
 * Each is stated in the final report (not yet public) and the research log.
 */
export const limitations = [
  {
    title: "A ceiling, not equivalence",
    body: "Every submission passed every hidden case, so the primary measure had no variation and could not separate the conditions. Harder or less specified tasks might.",
  },
  {
    title: "One configuration, three small tasks",
    body: "One agent (Claude Code 2.1.319, claude-opus-5-5, high effort), three small and precisely specified tasks, and 10 trials per task and condition. Other models, tools, and tasks may behave differently.",
  },
  {
    title: "Tests were part of the treatment",
    body: "Condition B was told to write tests and run Ruff; Condition A was neither asked nor prevented. More tests and fewer lint findings in B are partly a direct consequence of those instructions.",
  },
  {
    title: "Mutation measurement failed in three trials",
    body: "In three serial-dilution trials in Condition B, no test counted as valid, so the mutation score was recorded as 0. Each suite imports a custom exception class that the reference solution does not define, which most likely stopped the whole test run against the reference; the original run output was not kept. Those zeros record a measurement failure, not ineffective tests, and can only lower B's average.",
  },
  {
    title: "The security metric was misclassified",
    body: "The security count also included Ruff's SIM (simplification) rules. Counting only true security (S) rules, both conditions had zero findings. No security difference is claimed.",
  },
  {
    title: "No maintainability review",
    body: "The planned blinded human review of code quality was not conducted, for reasons of time and resources decided before the results were seen. Maintainability is unmeasured.",
  },
  {
    title: "An amendment during data collection",
    body: "Protocol 1.5 switched from hand-run to unattended sessions after the first confirmatory trial. Its records are timestamped by the project itself, and it was first published on GitHub with these results, so it has no independent timestamp that predates the first unattended trial. Protocol 1.4 was merged on GitHub before the first pilot session.",
  },
  {
    title: "Evaluator built by the same project",
    body: "The tasks, hidden cases, and evaluator were designed by this project, with help from the same family of AI model that was evaluated, and validated only by the project. No external team checked them.",
  },
  {
    title: "Publication commitments not kept",
    body: "The protocol promised to release the evaluator after data collection, to publish the pilot results, and to publish every attempt. After the analysis and unblinding, these were withheld. This deviation from the publication plan was not pre-registered and changes no method or result, but it limits independent replication and auditing.",
  },
  {
    title: "Agents, not people",
    body: "The trials measure an AI agent working alone with web search blocked. They do not show how human researchers would use either workflow.",
  },
];

/**
 * What the public release contains, worded to be true once it is published. The report PDF is
 * served by this site from web/public; `reportUrl` must point at a file that exists there.
 */
export const reportUrl: string | null = "/reports/ResearchCode_Final_Report.pdf";

export const materials: { name: string; detail: string; public: boolean }[] = [
  {
    name: "Final research report",
    detail: "As a PDF on this site and as Markdown in the repository.",
    public: true,
  },
  {
    name: "Pre-registered protocol 1.4",
    detail: "Merged on GitHub before the first pilot session, its only independent timestamp; kept verbatim with its configuration and freeze record.",
    public: true,
  },
  {
    name: "Protocol 1.5 amendment and batch runner",
    detail: "Documented in the protocol's amendment table and a new freeze record during data collection, and first published with these results.",
    public: true,
  },
  {
    name: "Tasks, prompts, harness, and fixture evaluator",
    detail: "With the aggregate evaluator validation and the freeze record's file hashes.",
    public: true,
  },
  {
    name: "Research log",
    detail: "Including data collection, the analysis, and the post-hoc diagnostics.",
    public: true,
  },
  {
    name: "Aggregate results",
    detail: "Means, medians, and intervals per condition and task, on this page and as a JSON summary in the repository.",
    public: true,
  },
  {
    name: "Analysis figures",
    detail: "Three figures in the report that plot every confirmatory trial's value as an unlabelled dot, by task and condition.",
    public: true,
  },
  {
    name: "Hidden evaluator",
    detail: "Cases, expected values, reference solutions, and deliberate defects. The protocol promised to release it after data collection.",
    public: false,
  },
  {
    name: "Pilot results",
    detail: "The six pilot trials. The protocol promised to publish them separately.",
    public: false,
  },
  {
    name: "Per-trial confirmatory results and invalid attempts",
    detail: "Trial records, submissions, session logs, the full analysis output, and the two invalid attempts. The protocol promised to publish every attempt. Evaluation records name hidden cases.",
    public: false,
  },
  {
    name: "Review packets and blinding key",
    detail: "Prepared for the maintainability review that was not conducted; never used.",
    public: false,
  },
];
