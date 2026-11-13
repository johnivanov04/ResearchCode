# Research log: building the Phase 4 framework with an AI assistant

ResearchCode studies how people build scientific software with AI assistants, so this log
records how this phase itself was built. **Everything here is qualitative process evidence.
It is not a result of the controlled experiment, which has not been run.**

## Who did what

- **Human (project owner).** Set the research question, the two conditions, the requirement for
  pre-registration, hidden tests, and isolation, and the constraints: no paid model usage
  without approval, no fabricated results, no commits without approval. At the time of writing,
  the human has not yet reviewed the Phase 4 code or protocol. That review is the next step.
- **Claude Code (Claude Opus 5.5, Claude Code 2.1.319).** Wrote the protocol, the task
  statements, the hidden cases and their derivations, the reference solutions, the defective
  variants, the harness, the Docker files, the tests, this log, and the website changes. It ran
  every check reported below.
- **Automated checks.** The test suite, the evaluator validation, and the end-to-end dry run.
  Their findings are listed below with the fixes.

The same model family that will be evaluated designed the tasks and the evaluator. The
protocol lists this as a threat to validity (section 12).

## Important decisions

| Decision | Reason |
| --- | --- |
| No growth-rate task | The starter kit contains a worked growth-rate example. A growth task would give Condition B part of an answer and confound the treatment with the solution. |
| Three tasks with different failure modes | Units and validation (serial dilution); statistics and numerical stability (calibration); nonlinear fitting and file handling (enzyme kinetics). Three near-identical exercises would measure one thing three times. |
| Fixed function interfaces | The same hidden evaluator can then score any implementation. Interface failures are recorded separately so they can be distinguished from scientific errors. |
| The sandbox observes and the host grades | Expected values never enter the sandbox, so generated code cannot read or alter its scoring even though it runs in the same process as the observer. |
| Expected values derived independently of the reference solutions | Exact rational arithmetic, closed forms, and a separate profile-likelihood fit. The reference solutions passing 100% is therefore a real cross-check, not a tautology. |
| Agent in a container behind an allow-list proxy | The repository is public. An agent with web or GitHub access could find the hidden evaluator. Both conditions lose web search equally. |
| Claude Code run without `--bare` in an empty home directory | Condition B then receives the starter kit's `CLAUDE.md` exactly as a real user would, and the experimenter's own settings and memory are absent from both conditions. |
| Mutation score for test quality | Counting tests would reward Condition B for writing tests whether or not they find defects. Running each submission's tests against known defects measures what the tests actually catch. |
| Prompts never mention the experiment | Agents should not know that they are compared or that hidden tests exist. A test checks every agent-facing file for such words. |

## What the automated checks caught during development

Each item was found by a check, not by inspection, and was fixed before the framework was frozen.
No trial had been run.

1. **The evaluator missed a numerical-stability defect.** The "uncentred sums" variant of the
   calibration reference passed all 30 hidden cases. The large-offset case used integer
   concentrations (10⁶ + k), whose squares are exact in floating point, so naive formulas lost no
   precision. The case now uses steps of 0.2, and the defect fails 2 cases. Without the
   deliberate-defect check, the evaluator would have claimed to test numerical stability
   without doing so.
2. **A defect patch did not apply.** The patch for "Greek mu not accepted" looked for an escaped
   string, but the reference file contained the literal character. The rule that every patch
   must match exactly once caught it immediately instead of silently creating a variant
   identical to the reference.
3. **Missing public examples.** The first end-to-end dry run stopped because two tasks had no
   `public_examples.json` yet. The task material was incomplete, and preparing a workspace would
   have failed for real trials.
4. **A scoring bias against Condition B (line length).** In the dry run, almost every lint
   finding was E501. Ruff's isolated default (88 characters) would have penalised code that
   follows the starter kit's own setting (100). Line length is now excluded from lint density.
5. **A scoring bias against Condition B (package metadata).** The starter kit's provenance test
   failed in the sandbox only because the sandbox imports code without installing it. The
   sandbox now records the project's declared name and version the way an installation would,
   for both conditions.
6. **A configuration that would invalidate trials.** A real Claude Code transcript (recorded in
   the agent container with no credentials, so with no model call) showed that the default tool
   set includes `WebFetch` and `WebSearch`. Every trial's reported tool list is now checked, and
   a trial in which a disallowed tool was available is marked invalid.
7. **Wrong assumptions in the assistant's own tests.** One test expected Ruff to flag
   `import subprocess`. It does not by default, so the test was corrected to the findings Ruff
   actually reports. The assistant also first reported 25 defective variants; the evaluator
   validation counted 24.

## Where AI assistance helped

- It produced a large, consistent framework quickly: harness, tests, Docker isolation, and
  documentation.
- It suggested and implemented checks a hurried human might skip:
  - independent derivation of expected values;
  - deliberate-defect validation;
  - hash-based isolation checks;
  - a freeze record;
  - refusal to mix fixture and genuine data.
- It verified claims instead of asserting them:
  - t quantiles against SciPy and printed tables;
  - nonlinear fits against `curve_fit`;
  - network isolation from inside the container.

## Where AI assistance introduced risk or complexity

- **Size.** The harness is much larger than the tasks it evaluates. Every component is a place
  for a bug that could bias the comparison. Items 4 and 5 above were exactly such bugs.
- **Self-evaluation.** The assistant designed both the treatment's evaluation and the tasks.
  Hidden cases were written from the task statements before any trial. They are frozen, and
  human review is still required.
- **Confident wrong details.** Items 2 and 7 were small factual errors stated with confidence.
  The checks caught them; reading alone might not have.
- **Unverifiable parts.** The behaviour of a full agent session (turn counts, how the budget
  limit ends a session, the result message after a successful run) cannot be confirmed without
  a paid run. The parser treats every such value as optional, and the pilot is meant to check it.

## Qualitative evidence from Phase 3 (not a Phase 4 finding)

In Phase 3, the structured workflow's validation step changed the growth-analysis method
twice. It also measured a remaining upward bias of about 7% for slow growth that starts near
the quantification limit; the bias is documented and not corrected. This shows that
verification can find real scientific errors and can also show where a method remains
imperfect. It is one case study, built by the same team, without a comparison condition. It is
**not** evidence that the structured workflow outperforms unstructured coding. Only the
controlled trials defined in `PROTOCOL.md` can test that.

## Revision to protocol 1.1: zero additional spending (2026-11-12, before any trial)

The project owner set the budget for additional spending to $0. Trials must use their
existing Claude Pro subscription through manually operated Claude Code sessions. Claude Code
changed the framework as follows. The tasks, hidden evaluator, scoring, and analysis plan did
not change.

- **Removed:**
  - automated agent runs (`run-agent`, `run-trial`, `claude -p`);
  - the per-trial spending limit and total-cost estimate;
  - cost as a metric.
- **Added:**
  - `rc-exp session`, an interactive Claude Code session in the same isolated container, with
    the prompt pre-entered, a new empty Claude configuration per trial, and a time limit;
  - `rc-exp preflight` (login, model, and usage checks without a prompt);
  - `next` and `progress`;
  - a fixed continuation message;
  - recorded operator answers;
  - parsing of Claude Code's session logs;
  - validity rules for model, effort, version, usage limits, and extra usage;
  - a stopping rule and planned-against-achieved reporting for reduced samples.
- **Credential handling:** only `CLAUDE_CODE_OAUTH_TOKEN` (from `claude setup-token`) is passed
  into a container. API keys and alternative endpoints are never passed, and tests check
  this.

What was verified, and how:

- **Subscription facts from the installed tool.** These were taken from Claude Code 2.1.319
  itself, not assumed:
  - the `/usage`, `/status`, and `setup-token` commands exist;
  - subscriptions can have paid extra usage, which Claude Code reports in the session ("Extra
    usage is now covering your requests");
  - Claude Code also accepts `ANTHROPIC_API_KEY` and `ANTHROPIC_AUTH_TOKEN`.
- **The proxy.** It needs no change for subscription tokens. A deliberately invalid token
  reached only `api.anthropic.com` and was rejected (`401 OAuth access token is invalid`, cost
  0), so no model could run and nothing could be charged.
- **Session-log format.** It was read from a real 2.1.319 log on the development machine:
  structure only, no content copied. Each assistant message is written once per content
  block, so usage is counted once per message id; a naive sum would have overcounted tokens
  up to sixfold in that log. The test fixture is synthetic and mirrors that structure.
- **What cannot be verified without a real trial:** how many sessions fit in the
  subscription's usage periods, whether `claude-opus-5-5` is offered to this subscription in
  Claude Code, and the exact first-run dialogs inside the container. The preflight and the
  pilot exist to check these. Nothing about them is assumed in the protocol.

## Revision to protocol 1.2: keeping the evaluator private, and counting tests fairly (2026-11-12, before any trial)

The final review before the first commit found two problems.

1. **The hidden evaluator would have been published.** The repository is public. The hidden
   cases with their expected values, the reference solutions, and the defective variants sat
   inside the harness package, and committing it would have exposed them. Nothing had been
   committed yet.
   - Claude Code copied them to a private Git repository outside the public one and checked
     that the copy was byte-identical.
   - It committed them there, re-ran the genuine validation through the new loader, and only
     then removed them from the public tree. The validation was identical: 110 cases, 24 defects
     detected at the same pass rates.
   - The case and reference files have the same SHA-256 as in the version 1.1 freeze record;
     only the package's import interface changed.
   - Public CI now uses a separate, labelled fixture evaluator (two practice tasks).
   - Private tests check that no private file, and no line of its numeric test data, appears
     in the public repository.
2. **Condition B was credited with 137 tests it did not write.** The workspace starts with
   the starter kit's own tests. Tests whose file is byte-identical to a starter-kit file are now
   excluded from the counts and the mutation analysis. Regression tests show three things:
   - the starter kit alone yields 0 counted tests;
   - task tests next to it are counted, with the same mutation score as without it;
   - an adapted starter file counts.

Also added: automatic detection of usage-limit and API-error messages in session logs,
redaction of credential-like strings from saved logs, a CI step proving that `ANTHROPIC_*`
variables on the host never reach an agent container, and corrected instructions for turning
off paid usage credits (from Anthropic's help article).

One error during the move: Claude Code first relabelled the docstrings of the private case and
reference files, which would have changed their hashes. It reverted that before committing, so
the hashes match the earlier freeze record.

## Open items

- Human review of the protocol, tasks, hidden cases, and prompts before the pilot.
- The pilot (6 trials) is run by the project owner through their Claude Pro subscription, as
  usage allows. It will show how many sessions fit in the plan's usage limits and check the
  parts of the harness that cannot be exercised without a model.
