# ResearchCode Phase 4: controlled evaluation

**Status: the framework is implemented and verified. No AI trials have been run, so there
are no results yet.** Trials are run as manual Claude Code sessions through the experimenter's
existing Claude Pro subscription, with **$0 additional spending** (protocol 1.1).

This folder holds a pre-registered experiment that asks:

> When the same AI coding agent, with the same model, tools, and budget, is given the same
> scientific programming task, does working within ResearchCode's structured workflow
> produce more reliable scientific software than unstructured AI coding?

| Document | Contents |
| --- | --- |
| [`docs/PROTOCOL.md`](docs/PROTOCOL.md) | The pre-registered protocol: hypotheses, conditions, tasks, metrics, sample size, exclusions, analysis plan, threats to validity |
| [`experiment.json`](experiment.json) | The same parameters, machine-readable (read by the harness and checked by the website's tests) |
| [`FREEZE.json`](FREEZE.json) | SHA-256 of every file that defines the experiment, recorded before any trial |
| [`docs/RUNNING_TRIALS.md`](docs/RUNNING_TRIALS.md) | How to run the trials: manual sessions in VS Code's terminal, through a Claude Pro subscription |
| [`docs/RESEARCH_LOG.md`](docs/RESEARCH_LOG.md) | How the framework was built with an AI assistant: decisions, errors, what the checks caught |
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
│   ├── agent.py               Manual Claude Code sessions in a container (subscription), or fixtures
│   ├── test_quality.py        Mutation score of a submission's own tests
│   ├── static.py              Ruff (fixed rules, isolated), imports, dependencies
│   ├── analysis.py            Pre-registered analysis, tables, figures
│   └── cli.py                 `rc-exp`
├── docker/                    sandbox, agent, and proxy images (base images pinned by digest)
├── results/                   genuine/ and pilot/ trials (empty until trials run)
└── tests/                     Tests of the harness itself
```

## Where the hidden material is

This repository is public, so the **genuine evaluator** is not in it. The genuine evaluator is
the hidden cases with their expected values, the reference solutions, and the deliberately
defective variants for the three experiment tasks. It lives in a separate private Git
repository on the experimenter's machine (default `~/researchcode-private/phase4-evaluator`, or
the path in `RC_PRIVATE_EVALUATOR`). `FREEZE.json` publishes the SHA-256 hash of each of its
files, so its integrity can be checked when it is released after data collection. Genuine and
pilot trials cannot be prepared or evaluated without it.

Public CI and dry runs use the **fixture evaluator** (`src/rc_experiments/fixture_evaluator/`).
These are two clearly labelled practice tasks with their own public cases, references, and
defects. They test the machinery and never score a genuine trial.

## Three kinds of evidence

| Kind | What it shows | Where |
| --- | --- | --- |
| Framework validation | The scoring system works: references score 100%, and every deliberate defect is caught. The sandbox and network isolation hold. | `docs/evaluator-validation.json`, the tests, CI |
| Fixture dry runs | Every stage of the pipeline runs end to end on labelled practice data | Temporary folders only; every table and figure is labelled "FIXTURE DATA - NOT EXPERIMENTAL RESULTS" |
| Genuine observations | What the experiment found | `results/genuine/` and `results/pilot/`, which are **empty: no trial has been run** |

## How a trial is isolated and scored

1. **Workspace.** `rc-exp prepare` creates `~/researchcode-trials/<trial>/workspace/`
   outside the repository. It contains the task statement and public examples and, in
   Condition B only, the tracked files of `scientific-starter/`. The contents are checked
   against the plan and against every hidden file by hash. The trial record is stored next to
   the workspace, not inside it.
2. **Agent.** The operator runs `rc-exp session`, which opens Claude Code interactively in a
   container where only that workspace is mounted. The prompt is already entered, and the
   model and settings are fixed. The container has a fresh home directory and a new, empty
   Claude configuration, so none of the experimenter's settings, memory, or instructions
   are present, and nothing carries over between trials. The only credential passed in is
   the subscription token from `claude setup-token`. The only network route is a proxy that
   allows the model API and PyPI and refuses everything else, including GitHub.
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
(`rc-exp preflight`, `rc-exp session`) is described in
[`docs/RUNNING_TRIALS.md`](docs/RUNNING_TRIALS.md). Every session is started by a person, uses
the Claude Pro subscription, and is never run by CI.

On macOS, if this repository is in an iCloud-synced folder, set `UV_PROJECT_ENVIRONMENT` to a
directory outside it (see the repository's `CLAUDE.md`).
