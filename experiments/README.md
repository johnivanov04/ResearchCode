# ResearchCode Phase 4: controlled evaluation

**Status: complete.** All 60 confirmatory trials were run (three tasks × two conditions ×
10 trials) and the pre-registered analysis ran once, on 2026-11-22. Trials ran as Claude Code
sessions through the experimenter's existing Claude Pro subscription, with **$0 additional
spending** (protocol 1.1): the six pilot trials and the first confirmatory trial as manual
sessions, the other 59 unattended (protocol 1.5).

## Results

- **Primary outcome:** every submission in both conditions passed every hidden evaluation case
  (100% hidden pass rate). The difference was 0.0 percentage points (95% bootstrap CI [0, 0];
  stratified permutation p = 1.0000).
- **Primary hypothesis not supported.** It stated that the hidden pass rate differs between the
  conditions, with B > A expected and a two-sided test. This is a ceiling effect, not evidence
  that the workflows are equivalent in general.
- **Secondary measures** are descriptive only, with no hypothesis tests. The table gives means
  over 30 trials per condition.

  | Measure | A: unstructured | B: ResearchCode |
  | --- | --- | --- |
  | Mutation score of the submission's own tests | 4.1% | 87.6% |
  | Tests written per submission | 0.4 (2 of 30 trials wrote any) | 132.6 (all 30) |
  | Lint findings per 100 lines | 3.20 | 0.42 |
  | Session time (minutes) | 2.02 | 8.69 |
  | Output tokens | 12,281 | 45,225 |

  Condition B was told to write tests and run Ruff, so these differences are partly a direct
  result of the treatment.
- **Post-hoc diagnostics.** The security metric counted Ruff `SIM` rules, so no security
  difference is claimed. Mutation validation failed in three serial-dilution B trials, so
  their recorded zeros are a measurement failure. The planned blinded maintainability review
  was not conducted.

The full account, with uncertainty, limitations, and the publication deviation, is in the
final report: [`docs/FINAL_REPORT.md`](docs/FINAL_REPORT.md), also available
[as a PDF](../web/public/reports/ResearchCode_Final_Report.pdf). The aggregate results are in
[`docs/aggregate-results.json`](docs/aggregate-results.json) and on the website's
[evaluation page](https://researchcode.pages.dev/evaluation).

This folder holds a pre-registered experiment that asks:

> When the same AI coding agent, with the same model, tools, and limits, is given the same
> scientific programming task, does working within ResearchCode's structured workflow
> produce more reliable scientific software than unstructured AI coding?

| Document | Contents |
| --- | --- |
| [`docs/PROTOCOL.md`](docs/PROTOCOL.md) | The pre-registered protocol: hypotheses, conditions, tasks, metrics, sample size, exclusions, analysis plan, threats to validity |
| [`experiment.json`](experiment.json) | The same parameters, machine-readable (read by the harness and checked by the website's tests) |
| [`FREEZE.json`](FREEZE.json) | SHA-256 of every file that defines the experiment (protocol 1.5 record) |
| [`freeze-history/`](freeze-history/) | The superseded protocol 1.4, configuration, and freeze record, made before any trial |
| [`docs/RUNNING_TRIALS.md`](docs/RUNNING_TRIALS.md) | How the trials were run: unattended batches (`rc-exp batch`, protocol 1.5) or manual sessions, through a Claude Pro subscription |
| [`docs/RESEARCH_LOG.md`](docs/RESEARCH_LOG.md) | How the framework was built with an AI assistant, data collection, the analysis, post-hoc diagnostics, and the publication deviation |
| [`docs/FINAL_REPORT.md`](docs/FINAL_REPORT.md) | The final research report |
| [`docs/aggregate-results.json`](docs/aggregate-results.json) | Aggregate results of the pre-registered analysis (no per-trial records) |
| [`docs/REVIEW_RUBRIC.md`](docs/REVIEW_RUBRIC.md) | The blinded maintainability rubric |
| [`docs/evaluator-validation.json`](docs/evaluator-validation.json) | Genuine evaluator validation: aggregate scores of the reference solutions and deliberate defects (not experimental results) |

## Layout

```
experiments/
├── tasks/<task>/              TASK.md + public_examples.json: the only task material agents see
├── conditions/                The two prompts (A: unstructured, B: ResearchCode workflow)
├── src/rc_experiments/
│   ├── evaluators.py          Genuine evaluator (PRIVATE, outside this repository) or fixture evaluator
│   ├── fixture_evaluator/     FIXTURE: two public practice tasks for CI and dry runs (not the experiment)
│   ├── sandbox_scripts/       Runners executed inside the evaluation sandbox (standard library only)
│   ├── checks.py, grading.py  Host-side grading of what the sandbox observed
│   ├── workspace.py           Clean, isolated trial workspaces
│   ├── agent.py               Claude Code sessions in a container (subscription): manual or unattended
│   ├── batch.py               rc-exp batch: unattended trials in schedule order (protocol 1.5)
│   ├── test_quality.py        Mutation score of a submission's own tests
│   ├── static.py              Ruff (fixed rules, isolated), imports, dependencies
│   ├── analysis.py            Pre-registered analysis, tables, figures
│   └── cli.py                 `rc-exp`
├── docker/                    sandbox, agent, and proxy images (base images pinned by digest)
├── results/                   genuine/ and pilot/ trial records (kept private; see below)
└── tests/                     Tests of the harness itself
```

## Where the hidden material is

This repository is public, so the **genuine evaluator** is not in it. The genuine evaluator is
the hidden cases with their expected values, the reference solutions, and the deliberately
defective variants for the three experiment tasks. It lives in a separate private Git
repository on the experimenter's machine (default `~/researchcode-private/phase4-evaluator`, or
the path in `RC_PRIVATE_EVALUATOR`). `FREEZE.json` publishes the SHA-256 hash of each of its
files. The protocol (section 3) committed to releasing the evaluator after data collection, so
that it could be checked against these hashes. After the analysis and unblinding, the project
owner decided not to release it: a deviation from the publication plan, recorded in
`docs/RESEARCH_LOG.md` and the final report. Genuine and pilot trials cannot be prepared or
evaluated without it.

Public CI and dry runs use the **fixture evaluator** (`src/rc_experiments/fixture_evaluator/`).
These are two clearly labelled practice tasks with their own public cases, references, and
defects. They test the machinery and never score a genuine trial.

## Three kinds of evidence

| Kind | What it shows | Where |
| --- | --- | --- |
| Framework validation | The scoring system works: references score 100%, and every deliberate defect is caught. The sandbox and network isolation hold. | `docs/evaluator-validation.json`, the tests, CI |
| Fixture dry runs | Every stage of the pipeline runs end to end on labelled practice data | Temporary folders only; every table and figure is labelled "FIXTURE DATA - NOT EXPERIMENTAL RESULTS" |
| Genuine observations | What the experiment found | Aggregate results in `docs/aggregate-results.json` and `docs/FINAL_REPORT.md`. The per-trial records in `results/` are **kept private** (a publication deviation; see `docs/RESEARCH_LOG.md`) |

## How a trial is isolated and scored

1. **Workspace.** `rc-exp prepare` creates `~/researchcode-trials/<trial>/workspace/`
   outside the repository. It contains the task statement and public examples and, in
   Condition B only, the tracked files of `scientific-starter/`. The contents are checked
   against the plan and against every hidden file by hash. The trial record is stored next to
   the workspace, not inside it.
2. **Agent.** From protocol 1.5, `rc-exp batch` runs Claude Code non-interactively (`claude -p`)
   for the next trials in schedule order (the first seven trials used `rc-exp session`, which
   opens Claude Code interactively). Either way, Claude Code runs in a
   container where only that workspace is mounted. The prompt is already entered, and the
   model and settings are fixed. The container has a fresh home directory (with one setting
   that skips Claude Code's first-run login) and a new, empty Claude configuration, so none
   of the experimenter's settings, memory, or instructions are present, and nothing carries
   over between trials. The only credential passed in is the subscription token from
   `claude setup-token`. The only network route is a proxy that
   allows the model API, Anthropic's OAuth token service (for the subscription sign-in), and PyPI,
   and refuses everything else, including GitHub.
3. **Evaluation.** The submission is copied and run in a new Docker container for every
   evaluation run, with these restrictions:
   - no network;
   - a read-only file system;
   - a non-root user;
   - no Linux capabilities;
   - CPU, memory, process, and time limits.

   The sandbox receives only the inputs of the hidden cases and reports what the code did.
   The comparison with expected values happens on the host, so a submission can never see,
   import, or change its scoring.
4. **Scores.**
   - Hidden pass rate (the primary metric) and pass rates per category.
   - Numerical accuracy.
   - The mutation score of the submission's own tests (run against the reference and against
     known defects).
   - Static security, lint, and dependency findings.
   - Development effort, as Claude Code reports it.

## Commands

```bash
uv sync --locked
uv run pytest                         # tests of the harness (Docker tests skip if Docker is unavailable)
uv run ruff check . && uv run ruff format --check .
uv build

uv run rc-exp validate-evaluator --evaluator fixture   # public practice tasks (as in CI)
uv run rc-exp validate-evaluator      # genuine evaluator: needs the private directory
uv run rc-exp dry-run --out /tmp/rc-dry-run   # every stage with labelled fixtures, no model calls
uv run rc-exp schedule                # the randomised trial order
uv run rc-exp freeze --check          # frozen files unchanged
```

`validate-evaluator` and `dry-run` use Docker by default (`--backend local` runs the trusted
references and fixtures without isolation) and use no model. Running real trials
(`rc-exp preflight`, `rc-exp session`, `rc-exp batch`) is described in
[`docs/RUNNING_TRIALS.md`](docs/RUNNING_TRIALS.md). Every session or batch is started by a
person, uses the Claude Pro subscription, and is never run by CI. Genuine trials also need the
private evaluator, so they cannot be rerun from this repository alone.

On macOS, if this repository is in an iCloud-synced folder, set `UV_PROJECT_ENVIRONMENT` to a
directory outside it (see the repository's `CLAUDE.md`).
