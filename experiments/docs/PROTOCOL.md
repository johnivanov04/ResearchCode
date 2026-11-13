# Pre-registered protocol: structured vs unstructured AI-assisted scientific coding

| | |
| --- | --- |
| Protocol version | 1.2 |
| Written | 2026-11-11 (version 1.0); revised 2026-11-12 (versions 1.1 and 1.2), before any trial was run |
| Status | Framework implemented; no trials run; the pilot is run manually through a Claude Pro subscription |
| Additional spending | **$0.** Trials use the experimenter's existing Claude Pro subscription; no API usage, credits, or other paid services |
| Machine-readable configuration | [`experiments/experiment.json`](../experiment.json) |
| Freeze record | [`experiments/FREEZE.json`](../FREEZE.json) (SHA-256 of every file that defines the experiment) |

This document fixes the design, scoring, and analysis of the ResearchCode Phase 4 experiment
before any data are collected. The file `experiment.json` holds the same parameters in
machine-readable form; the harness reads it, and the website's tests check that the
published methodology matches it. If the two ever disagree, that is a bug, and it must be
fixed before any trial is run.

**Rules for changing this protocol.** Before the first pilot trial, the protocol may be
corrected; each change is listed in section 13, and the freeze record is regenerated. After
the first pilot trial, the hidden evaluator, the scoring rules, and the analysis plan in
sections 4, 5, and 11 may be changed only to fix a defect, and every such change is listed
in section 13 with its reason and date. Any analysis that differs from section 11 is
reported separately from it and labelled exploratory. Pilot data are never part of the
confirmatory analysis.

## 1. Research question and hypotheses

**Research question.** When the same AI coding agent, with the same model, tools, and
limits, is given the same scientific programming task, does working within ResearchCode's
structured workflow (starter kit, specification, tests, verification) produce more
reliable scientific software than unstructured AI coding ("vibe coding")?

"More reliable" is operationalised as passing more of an independent hidden test suite
that checks scientific correctness, edge cases, invalid-input handling, numerical
robustness, reproducibility, and end-to-end behaviour (section 5).

**H1 (primary, confirmatory).** The mean share of hidden evaluation cases passed differs
between the structured condition (B) and the unstructured condition (A), averaged over
tasks with equal weight. The direction we expect is B > A; the test is two-sided.

**Secondary questions (exploratory; reported with uncertainty, without hypothesis tests):**

- **H2.** B handles invalid input and edge cases better (pass rates in those case categories).
- **H3.** B's own tests are better at detecting known defects (mutation score, section 5.2).
- **H4.** B takes more development effort (wall-clock time, and the messages and tokens recorded
  in Claude Code's session log).
- **H5.** The conditions differ in numerical accuracy, static security findings, and
  maintainability indicators.

We will report the results whatever their direction, including results that do not
favour ResearchCode.

## 2. Experimental conditions

Both conditions use the same agent, model, configuration, container image, network
access, and time limit (section 7). Each trial is a single Claude Code session that starts
from a new, clean workspace. The session is **started and ended by a human operator** but
is otherwise unattended (section 7.1): the operator does not guide, correct, or answer the
agent, apart from one fixed continuation message that is the same in both conditions. The
only difference between conditions is the treatment below.

**Condition A: unstructured AI coding.** The workspace contains only the task statement
(`TASK.md`) and its public examples (`public_examples.json`). The prompt asks the agent to
implement the task and says that it may write and run code. The agent is not told to
write a specification or tests, and it receives no ResearchCode material. Nothing
restricts it beyond what both conditions share: it can install packages, write and run
tests if it chooses, and work as long as the limits allow. This represents a capable
agent used without a structured workflow.

**Condition B: ResearchCode structured development.** The workspace contains the same
`TASK.md` and `public_examples.json`, plus a copy of the ResearchCode scientific starter kit
(`scientific-starter/` at the frozen commit: `AGENTS.md`, `CLAUDE.md`, the specification
template and security checklist, the uv/pytest/Hypothesis/Ruff configuration, the example
package and tests, and the run-metadata module). The prompt asks the agent to follow the
starter kit's workflow: write a specification from the template, write known-answer,
edge-case, and property-based tests, implement, run Ruff and pytest, fix failures, and
document assumptions.

**Shared prompt text.** Both prompts state that no human is available during the session,
so the agent must make and record reasonable decisions instead of waiting for answers.
In Condition B this replaces the starter kit's instruction to stop and ask a human. The
exact prompts are in [`experiments/conditions/`](../conditions/) and are frozen.

**Why no growth-rate task.** The starter kit contains a worked growth-rate example. A
growth-rate task would give Condition B part of a solution, which would confound "a
structured workflow" with "having the answer". The tasks were therefore chosen from other
areas, and the Phase 3 growth-analysis application is not available to either condition.

## 3. Scientific programming tasks

There are three tasks with deliberately different failure modes. Each is a small Python
module with a fixed public interface, so the same hidden evaluator can score any
implementation. The complete statements, shared verbatim by both conditions, are in
[`experiments/tasks/`](../tasks/).

| Task | Module | Main failure modes it exposes |
| --- | --- | --- |
| `serial-dilution`: dilution factors, volume units, colony counts → CFU/mL, C1V1 = C2V2 | `serial_dilution` | Unit conversion (including two different "micro" characters), inverted dilution ratios, out-of-range plates, inclusive bounds, input validation |
| `calibration`: linear standard curve, inverse prediction with standard error and t-based confidence interval, LOD/LOQ, extrapolation flags | `calibration` | Wrong degrees of freedom, normal instead of t quantiles, missing replicate term, clipping negative estimates, numerically unstable sums |
| `enzyme-kinetics`: Michaelis–Menten fit by nonlinear least squares with standard errors, plus a CSV-to-JSON command-line tool | `enzyme_kinetics` | Linearised (biased) fitting, unidentifiable fits returned as numbers, mM/µM units, UTF-8 byte-order marks and blank lines in CSV files, overwriting existing results, partial output after errors |

Each task provides:

- **Shared statement** (`TASK.md`): scientific requirements, exact interface, units,
  validation rules, and the evaluation environment (Python 3.12 with only the standard
  library, NumPy, and SciPy available at run time).
- **Public examples** (`public_examples.json`): a few inputs with expected outputs. These are
  part of the task statement and are not hidden cases.
- **Reference solution**: written independently of the hidden expected values. It must pass
  100% of hidden cases. Private.
- **Hidden cases**: inputs and checks. Expected values are derived independently of the
  reference solution: from exact rational arithmetic, closed-form mathematics, and, for the
  nonlinear fit, a separate one-dimensional profile minimisation. Private.
- **Defective variants (mutants)**: deliberate, realistic defects used to validate the
  evaluator. Private.
- **Task-specific scoring**: the case categories and tolerances in section 4.

**Where the hidden material is kept (version 1.2).** The repository is public, so the hidden
cases, reference solutions, and defective variants (the *genuine evaluator*) are kept outside
it. They live in a separate private Git repository (by default
`~/researchcode-private/phase4-evaluator`), which the harness loads only on the experimenter's
machine. They are never copied into a workspace, the public repository, the website, or CI.
`FREEZE.json` publishes the SHA-256 hash of every private file. Anyone can therefore check,
once the evaluator is released after data collection, that it is exactly what was frozen
before the first trial. Public CI and dry runs use a separate, clearly labelled **fixture
evaluator**: two practice tasks with their own public cases, references, and defects. It
exercises the same machinery, and it never scores a genuine trial. Only aggregate validation
figures for the genuine evaluator are public (`docs/evaluator-validation.json`: case counts
per category and the score of each defect); they contain no inputs, expected values, or code.

## 4. Requirements and scoring rubric

Every hidden case has exactly one category:

| Category | What it checks |
| --- | --- |
| `known_answer` | Correct values on valid inputs, with expected values derived independently |
| `edge_case` | Valid but unusual inputs: boundaries, zero, replicates, extrapolation, no countable plates |
| `invalid_input` | Inputs the statement says must be rejected (a `ValueError`; a `TypeError` is also accepted where the statement says so) |
| `numerical` | Robustness to inputs that break naive floating-point formulas, and fits that need nonlinear estimation |
| `reproducibility` | Identical results on repeated calls, inputs not modified, identical command-line output on reruns |
| `integration` | The command-line tool end to end: files, exit status, output, refusal to overwrite |

**Case scoring is binary.** A case passes only if every check in it passes. Numeric checks
use the tolerance defined with the case. The defaults are relative 1e-9 for closed-form
results, relative 1e-6 for confidence limits (which depend on t quantiles), and relative
1e-5 for iteratively fitted parameters, each with a small absolute tolerance where the
expected value is zero. Field names and types are those in `TASK.md`. Boolean fields must
be booleans (Python or NumPy), status fields must be the exact strings given, and results
may be a mapping or an object with the named attributes.

**Interface failures count as failures.** If the module cannot be imported under the name
the statement requires, every case fails. Import failures are also recorded separately,
so an analysis restricted to importable submissions can be reported as a secondary result.

## 5. Metrics

### 5.1 Primary metric

**Hidden pass rate:** the share of a task's hidden cases that a trial's submission
passes (0 to 1). Each case has equal weight within a task, and each task has equal weight
in the overall comparison. The agent never sees the hidden cases, their expected values,
or their number.

### 5.2 Secondary metrics

Objective metrics are computed automatically and identically for both conditions.

| Metric | Definition |
| --- | --- |
| Category pass rates | Hidden pass rate within each category in section 4 (H2 uses `edge_case` and `invalid_input`) |
| Numerical accuracy | Median relative error over numeric fields in `known_answer` cases (capped at 1); lower is better |
| Mutation score (test quality) | Share of the task's mutants detected by the submission's *own* tests. The submission's tests are run against the reference solution; tests that fail there are excluded as invalid, and so are inherited starter-kit tests (version 1.2). A mutant is detected if at least one valid test fails or errors against it. A submission without valid tests scores 0. |
| Own tests | Number of tests the submission created or adapted for the task, and whether they pass against its own code. Tests inherited from the starter kit are excluded (version 1.2): a test is inherited if its file is byte-identical to a file of `scientific-starter/`. The starter kit's 137 tests would otherwise be credited to every Condition B submission. |
| Static security findings | Ruff `S` (flake8-bandit) findings in non-test code, under a fixed rule set that ignores the submission's own configuration |
| Lint density | Ruff findings per 100 non-blank, non-comment lines of non-test code, same fixed rule set |
| Dependency hygiene | Runtime dependencies outside the standard library, NumPy, and SciPy; whether a lock file is present |
| Development effort | Wall-clock time of the session; assistant messages, operator messages, and tokens **as recorded in Claude Code's session log**. Missing values are recorded as missing, never estimated. Monetary cost is not a metric: no additional money is spent (version 1.1). |

Tests written by a submission are **never** counted as evidence of its correctness; only
the hidden evaluator measures correctness. Their quality is measured only by the mutation
score, which is itself computed by the independent evaluator.

### 5.3 Subjective review (blinded)

A human reviewer scores maintainability with the rubric in
[`REVIEW_RUBRIC.md`](REVIEW_RUBRIC.md) (four criteria, 1–4 each) on review packets that
contain only the implementation module and are labelled with random codes. Blinding is
imperfect: code style can reveal the condition. Subjective scores are reported separately
from objective metrics and are never combined with them.

## 6. Number of trials

- **Pilot:** 1 trial per task and condition (6 trials). It checks the harness, the
  isolation, and the cost. Pilot results are excluded from every analysis and published
  separately.
- **Confirmatory:** 10 trials per task and condition (60 trials).
- **Rationale and limits:** the number is set by available effort, not by a power
  calculation, because no estimate of variance existed before the experiment. Ten trials
  per cell can detect only large differences. If fewer than 5 valid trials remain in any
  cell, that cell is reported descriptively only.
- **Feasibility under a subscription (version 1.1).** Trials consume the experimenter's
  Claude Pro usage, which has limits (section 8). The planned numbers above are targets, not
  guarantees. **Stopping rule, fixed in advance:** trials are run in schedule order, and
  collection stops only at the end of a complete block (one trial of every task and
  condition), either when the planned trials are done or when the experimenter decides that
  the subscription's usage allows no more. Collection never stops because of the results
  seen so far. The achieved number of valid trials per cell is reported next to the plan,
  with its statistical limitations (section 11). Results are never extrapolated to trials
  that were not run.

## 7. AI model and tool configuration

Recorded for every trial in its record (`trial.json`) and fixed in `experiment.json`:

- **Tool:** Claude Code 2.1.319 in **interactive mode**, started by `rc-exp session` with
  the trial prompt as its first message. Claude Code is never run non-interactively, and the
  harness never starts a model session by itself.
- **Access and billing:** the experimenter's existing **Claude Pro subscription**. The only
  credential passed into the container is `CLAUDE_CODE_OAUTH_TOKEN`, created once with
  `claude setup-token` (which requires a Claude subscription). `ANTHROPIC_API_KEY`,
  `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_BASE_URL`, and the cloud-provider switches are never
  passed, even if they are set on the host.
- **Paid usage beyond the plan:** Anthropic calls it usage credits; Claude Code calls it extra
  usage. It must be turned off at claude.ai, Settings > Usage, before every sitting. Additional
  spending: $0.
- **Model:** `claude-opus-5-5`, effort `high`, in both conditions. Before the pilot, the
  operator confirms with `rc-exp preflight` (`/status`, `/model`) that the subscription
  provides this model in Claude Code. If it does not, the model is changed for **both**
  conditions before any trial, and the change is recorded in section 13. Every trial's
  session log records the model and effort used. Assistant messages in the main session
  from a different model, or a different effort, make the trial invalid (section 10).
  Subagents may use the tool's default models, which are the same in both conditions; they
  are recorded.
- **Tools available to the agent:** Claude Code's default tool set without `WebSearch` and
  `WebFetch`, in both conditions. Permission checks are bypassed inside the container so
  that no human approval is needed (`--permission-mode bypassPermissions`).
- **Environment:** a Docker container (`experiments/docker/agent/`) running as a non-root
  user, with Python 3.12, uv, and Node.js. It has a fresh home directory and a new, empty
  Claude configuration directory for every trial, so no user settings, memory, history, or
  instruction files carry over from the experimenter's machine or from earlier trials. Only
  the trial's workspace is mounted. The Claude Code extension for VS Code is **not** used
  for trials, because it runs on the host with access to the whole repository, including
  the hidden evaluator.
- **Network:** the container is on an internal Docker network with no direct internet
  access. A filtering proxy allows only `api.anthropic.com` (the model), `pypi.org`, and
  `files.pythonhosted.org` (Python packages). GitHub and the rest of the web are blocked,
  so the agent cannot retrieve this repository's hidden evaluator.

### 7.1 The operator's role

The operator follows `docs/RUNNING_TRIALS.md` exactly:

1. Run `rc-exp session <trial-id>`. Claude Code opens with the trial prompt already entered.
2. Answer only Claude Code's own startup dialogs (theme, trusting `/workspace`, the
   permission-mode warning).
3. Do not type anything while the agent works.
4. If the agent stops and asks a question before it has finished, send the fixed message in
   `conditions/CONTINUE.md`, at most twice per trial.
5. Type `/exit` when the agent says it has finished.

The container stops automatically at the time limit. After the session the operator
answers four recorded questions:

- how many continuation messages were sent;
- whether anything else was typed;
- whether a usage limit interrupted the session;
- whether extra usage was mentioned.

If tool version or model must change during data collection (for example, because the
model is withdrawn or no longer included in the subscription), collection stops, the change
is listed in section 13, and the trials before and after the change are analysed
separately.

## 8. Execution limits and resource use

| Limit | Value |
| --- | --- |
| Wall-clock time per trial | 45 minutes (the container is stopped at the limit) |
| Model usage | The experimenter's Claude Pro plan limits; no paid usage beyond the plan |
| Agent container | 2 CPUs, 4 GB memory, 512 processes |
| Evaluation sandbox (per case) | No network, read-only file system, non-root, all capabilities dropped, 1 CPU, 1 GB memory, 256 processes, 20 s per hidden case, 300 s per run of the submission's own tests |

A trial that reaches the time limit is valid: the workspace as it stands is evaluated.

**Claude Pro usage limits.** Claude Code shares the subscription's usage with claude.ai. The
plan limits usage over periods that reset (for example, a short rolling window and a weekly
limit). The amounts depend on the model and on how long and how large each session is. They
are not a fixed number of trials, and they can change. Before each session the operator
checks the remaining usage with `/usage` in `rc-exp preflight`. A session is started only if
the operator expects it can finish within the plan's remaining usage. How many trials one
usage period allows is unknown until the pilot. The pilot records the messages and tokens of
each session and the number of trials that fitted in each period. The evaluation (Docker
sandbox) uses no model and has no usage cost.

## 9. Randomisation and ordering

The schedule is generated from the seed in `experiment.json` (20261111). The 60
confirmatory trials form 10 blocks. Each block contains one trial of every task ×
condition combination (6 trials) in a random order. Running the schedule in order
balances the conditions over time, so a change in the model service during collection
affects both conditions equally. Each trial has an identifier
(`<task>--<condition>--r<NN>`). Trials run one at a time.

## 10. Exclusion rules

A trial is **invalid** only for infrastructure failures that are not the agent's
behaviour:

- the model API returns errors that end the session (outage, authentication, rate limits);
- the subscription's usage limit interrupts the session (version 1.1). It is detected from the
  operator's report or, since version 1.2, from API-error messages in the session log; other
  API errors mark the trial for review;
- the container, proxy, or harness fails;
- the experimenter interrupts the run or the isolation checks fail;
- the session's configuration differed from section 7 (version 1.1):
  - a different model in the main session, or a different effort or tool version;
  - a disallowed tool used;
  - extra usage reported;
  - more than two continuation messages, or any other operator input.

An invalid trial is rerun under the same identifier with a new attempt number, at most
twice. Every attempt is kept and published. The agent's own failures are **valid
outcomes** and are scored: wrong code, a module that cannot be imported, giving up,
asking a question instead of finishing, or reaching the time limit. A rerun always starts
from a new workspace and a new Claude configuration; an interrupted session is never resumed.

## 11. Statistical analysis plan

- **Unit of analysis:** the trial (one task, one condition, one replicate).
- **Primary estimand:** Δ = the mean over tasks of (mean hidden pass rate in B − mean hidden
  pass rate in A).
- **Uncertainty:** 95% percentile bootstrap confidence interval for Δ, resampling trials
  with replacement within each task × condition cell, with 10,000 resamples and a fixed seed.
- **Test of H1:** a stratified permutation test that shuffles condition labels within
  each task, with 10,000 permutations and a fixed seed. It is two-sided with α = 0.05. This
  is the only hypothesis test in the confirmatory analysis.
- **Per-task results:** the difference in mean pass rate for each task, with a bootstrap CI.
  These are descriptive.
- **Sensitivity analysis:** the same estimand computed on the *category-balanced* pass rate (the
  unweighted mean of a trial's pass rates in each case category). Tasks differ in how many cases
  each category has. In `serial-dilution`, for example, 23 of 53 cases check invalid input. This
  shows whether a difference depends on that weighting. It is descriptive, with no test.
- **Secondary metrics:** medians and means with bootstrap CIs per condition and task. They
  are descriptive, with no p-values.
- **Distributions:** every trial's value is shown (dot plots), not only the means.
- **Missing values:** effort metrics that the tool did not record are excluded from those
  summaries and counted.
- **Achieved sample size (version 1.1):** the report lists planned and achieved valid trials
  for every cell. If fewer trials than planned were collected, it states that the intervals
  are wider, that moderate differences can be missed, and that observed differences can
  arise by chance. The six pilot trials (one per cell) are analysed only descriptively and
  are never presented as evidence for or against either workflow.
- **Interpretation:** results apply to this agent, model, version, prompt pair, and task
  set. A difference does not show that ResearchCode helps human researchers, or that it
  helps with other tasks or tools.

## 12. Limitations and threats to validity

- **Small task set.** Three small tasks do not represent research software in general.
- **Designer bias.** The tasks, hidden cases, and treatment were designed by the same
  team, with help from the same family of AI model that is being evaluated. Hidden cases
  were written from the task statements, which both conditions receive, not from either
  condition's outputs, and they were frozen before any trial.
- **Agent, not human, participants.** Trials measure an AI agent working alone. Human
  researchers might use either workflow differently.
- **Non-interactive adaptation.** The starter kit tells an assistant to stop and ask a
  human. With no human present, Condition B is told to record its decisions instead. This
  changes the treatment.
- **Model drift and nondeterminism.** The service can change during collection. Blocked
  randomisation spreads this over both conditions, and the model and tool versions are
  recorded.
- **Blinding.** The hidden evaluator is automatic and blind by construction. The
  subjective review is only partly blind.
- **Interface strictness.** A module that ignores the required name or interface scores 0
  even if its science is right. This is part of following a specification, but it is
  reported separately.
- **Restricted web access.** Both conditions lose web search, which some real workflows use.
  This is necessary to keep the hidden evaluator hidden.
- **Training-data contamination.** The tasks are new, but their underlying methods are
  textbook material that both conditions may know equally.
- **Usage reporting.** Message and token counts come from Claude Code's own session log.
  They are not independent measurements. Monetary cost is not measured, because no
  additional money is spent.
- **Manual operation (version 1.1).** A human starts and ends each session. Operator
  behaviour is fixed by section 7.1 and recorded, but timing, when the session ends, and
  the use of the continuation message can still vary. The operator cannot be blind to the
  condition, because the workspace shows it.
- **Subscription limits (version 1.1).** Usage limits may allow fewer trials than planned,
  which reduces statistical power (section 6). Sessions near a limit could behave
  differently; sessions interrupted by a limit are invalid and rerun.
- **Sample size.** Ten trials per cell can show only large effects, and fewer may be feasible;
  see section 6.

## 13. Amendments

| Date | Section | Change | Reason |
| --- | --- | --- | --- |
| 2026-11-11 | 4, 5.2 | While the framework was drafted, before the first freeze and before any trial: the large-offset calibration case was changed to non-integer steps; line length (E501) was removed from lint density; the sandbox now records the submission's declared package name and version as an installation would; trials in which a disallowed tool was available are marked invalid; a category-balanced sensitivity analysis was added. | Found by the evaluator validation and the fixture dry run. The details are in `docs/RESEARCH_LOG.md`. |
| 2026-11-12 | 3, 5.2, 7, 10 | **Version 1.2, before any trial.** (a) Section 3: the genuine evaluator (hidden cases, references, defective variants) moved to a private repository outside the public one. It had never been committed, and its cases, expected values, and reference solutions are byte-identical to version 1.1 (verified by hash); only its import interface changed. `FREEZE.json` publishes its hashes. Public CI uses a labelled fixture evaluator. (b) Section 5.2: tests inherited unchanged from the starter kit no longer count as the submission's tests, and are not used for its mutation score. (c) Section 10: usage-limit and API-error messages in the session log are detected automatically, and credential-like strings are redacted from saved session logs. (d) Section 7: corrected instructions for turning off paid usage credits. | (a) The repository is public, and committing the hidden material would expose it. (b) Without the change, the 137 starter-kit tests would be credited to every Condition B submission. (c, d) Safety review before the pilot. |
| 2026-11-12 | header, 1, 2, 5.2, 6, 7, 8, 10, 11, 12 | **Version 1.1, before any trial: zero additional spending.** Trials are manual, interactive Claude Code sessions through the experimenter's Claude Pro subscription, not automated `claude -p` runs. (Version 1.0 allowed an API key and set a per-trial spending limit.) The automated agent commands were removed. The per-trial spending limit (`--max-budget-usd 10`) and the total-cost estimate were removed; Pro usage limits are documented instead. Added: the operator's role and the fixed continuation message; per-trial Claude configuration directories; session-log recording; validity rules for model, effort, version, usage limits, and extra usage; a stopping rule for reduced samples; reporting of planned against achieved sample sizes. The tasks, hidden evaluator, scoring, metrics, and analysis plan are unchanged. | The experimenter's budget for additional spending is $0. |
