# Research log: building the Phase 4 framework with an AI assistant

ResearchCode studies how people build scientific software with AI assistants, so this log
records how this phase itself was built. **Everything here is qualitative process evidence.
It is not a result of the controlled experiment. The experiment's outcomes are reported only by
the pre-registered analysis (protocol section 11).**

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

## Pre-pilot defect: the proxy blocked the OAuth token service (2026-11-14, protocol 1.3)

The project owner's first preflight (`rc-exp preflight`, no prompt, no trial) stopped
immediately: "Unable to connect to Anthropic services. Failed to connect to platform.claude.com:
ERR_PROXY_TUNNEL".

- **Root cause.** The proxy's log for that session shows two CONNECT requests to
  `api.anthropic.com` (allowed), then one to `platform.claude.com`, which was refused: "Proxying
  refused on filtered domain". It was the only refused host. Anthropic's network requirements say
  that OAuth token exchange, refresh, and revocation for claude.ai accounts go to this host, and
  that the first-run connectivity check tests it.
- **Why earlier checks missed it.** The no-credential test in the protocol 1.1 revision used
  Claude Code's non-interactive mode, which contacted only `api.anthropic.com`. From that, the
  revision concluded that "the proxy needs no change for subscription tokens". That conclusion
  was wrong for interactive sessions. Only a real interactive start showed it.
- **Fix.** One allowlist entry, `^platform\.claude\.com$`. Other hosts in Anthropic's list were
  not added, because nothing showed they were needed and each widens what an agent can reach:
  - browser sign-in pages (`claude.ai`, `claude.com`, `sso.claude.com`): the token is created
    outside the container;
  - optional services (connectors, downloads, telemetry);
  - GitHub, which must stay blocked.
- **Regression tests** (`tests/test_proxy_allowlist.py`). They build the proxy from the
  repository's files and probe it from a client container with no credentials:
  - the token service and the model API are reachable;
  - GitHub, its raw and API hosts, browser sign-in pages, optional services, other registries,
    arbitrary sites, and look-alike host names are refused by the proxy (HTTP 403);
  - there is no route that avoids the proxy.

  The tests reproduced the defect before the fix. `rc-exp check` now also refuses a proxy built
  from an outdated allowlist, which would otherwise keep failing after the update.
- **What is still unverified.** A real subscription-authenticated session has still not run. The
  next preflight is the test.

## Pre-pilot defect: the first-run login screen ignored the token (2026-11-14, protocol 1.4)

With the proxy fixed, the project owner's next preflight (`rc-exp preflight`, no prompt, no
trial) got past the connection check but stopped at Claude Code's "Select login method" screen
after the theme choice. `CLAUDE_CODE_OAUTH_TOKEN` was set and exported, and `rc-exp check` reported
"ready for manual sessions".

- **The token reached the container.** A check inside the owner's running preflight container
  printed only the variable's presence, length, prefix type, and whether it contained
  whitespace, never its value. It was set under the right name, with the prefix of a
  subscription token.
- **Root cause (harness).** Claude Code 2.1.319 runs its first-run setup whenever
  `~/.claude.json` does not record `hasCompletedOnboarding`. That setup adds the login step even
  when a token is set (upstream issue anthropics/claude-code#46259, closed without a fix).
  Every agent container starts with a fresh home directory, so every session began with the
  first-run setup. This was reproduced with the exact preflight command, a throwaway proxy, and
  **fake placeholder tokens** (no real credential, no prompt):
  - with no token, a well-formed fake token, or a fake token containing a space, the old image
    showed the theme and then the login screen;
  - the rebuilt image went straight to the `/workspace` trust and permission-mode dialogs and
    then to the main screen. With a fake token, the main screen warned that authentication
    was rejected (401), which is how a token that the server refuses appears.
- **Fix.** The agent image writes `~/.claude.json` containing only
  `{"hasCompletedOnboarding": true}`. This is the state Claude Code records after its own
  first-run setup, and Claude Code writes the same flag when it prepares its own sandboxed
  sessions. It exists only inside the container, which is removed after each session. Nothing
  else is configured, and both conditions use the same image.
- **Second finding (operator's token, not the harness).** The owner's token contained a single
  space in the middle, consistent with copying a token that wrapped across terminal lines.
  Claude Code accepts such a value, and the server would reject it. `rc-exp check` now reports
  a token with whitespace, without printing it.
- **Regression tests** (`tests/test_agent_onboarding.py`, plus a CI step): the Dockerfile writes
  exactly this setting and nothing else; `rc-exp check` refuses an image without it (or with
  other content) and a token with whitespace; error messages never contain the token.
- **Expected refusals.** Once the main screen loads, Claude Code also tries `github.com` and
  `downloads.claude.ai`. The proxy refuses both, as intended; the main screen still loads.
- **What is still unverified.** No session has run with a real token. The next preflight is the
  test: `/status` must show the Claude subscription.

## Protocol 1.5: unattended, non-interactive sessions (2026-11-16)

**State before the change.** Seven trials were complete, all as manual, interactive sessions
under protocol 1.4 and evaluated against freeze record `b910a7b7afd0a1fd`: the six pilot trials
and one confirmatory trial, `serial-dilution--B--r01` (Condition B, schedule position 7). All
seven were valid, and no continuation message was sent in any of them. No confirmatory analysis
had been run.

**Decision.** The project owner can no longer supervise each session and authorised running
the remaining trials unattended with Claude Code's non-interactive mode. The amendment is in
protocol section 13. Before anything was changed, the results, the trial folders, and the
version 1.4 protocol, configuration, and freeze record were backed up outside the repository
with SHA-256 manifests, and a restore was tested. The three version 1.4 files are also kept
verbatim in `experiments/freeze-history/`; a test checks them against the original freeze
record's hashes.

**Checks before building it (no credentials, no model usage).** Claude Code 2.1.319's bundled
code and two runs of `claude -p` in the agent image showed the events the batch relies on: a
`system/init` event with `apiKeySource`, model, permission mode, version, and tools; `api_retry`
events with an error kind; `rate_limit_event` messages with `isUsingOverage` and
`overageStatus`; and a final `result`. The two runs were made with no credential and with a
fake placeholder token behind a throwaway proxy, so neither could authenticate. They showed
that an authentication failure ends with `"subtype": "success"` but `"is_error": true` and
`"terminal_reason": "api_error"`. So the batch counts a session as completed only if the
result has `is_error` false, `terminal_reason` `completed`, and exit code 0. Transcripts are
still written in `-p` mode, so the session log is parsed as before. Anthropic's help center
(update of 2026-10-07) states that `claude -p` signed in with a plan draws from the
subscription's usage limits.

**What changed.**

- `rc-exp batch`: sequential, in schedule order, `--limit`, `--dry-run`; resumable; lock file;
  append-only journal.
- Subscription-only checks before launch, and immediate stops during a session.
- `eNN` engineering validation runs.
- The execution mode in every new record.
- An exploratory, separately labelled analysis without interactively run genuine trials.
- The rerun limit, now enforced by the batch.

The tasks, prompts, hidden evaluator, scoring, sample sizes, schedule, and primary analysis
are unchanged; tests compare them with the archived version 1.4.

**Tests (mocked; no model, no network).**

- A mocked Claude process replays synthetic stream-json events through the real streaming
  runner.
- Covered: completion, every stop rule, timeouts (including a process that ignores the
  graceful stop), failing processes, and redaction.
- Whole batches with fake evaluation are also covered: schedule order, limits, dry runs,
  refusals, locking, interruption, resumption after failed collection or evaluation,
  duplicate prevention, the rerun limit, and engineering runs.

**Incident during implementation.** A formatting command (`ruff format .`, then
`ruff check --fix`) was run over the whole `experiments/` directory, which then included the
untracked results. It changed three pilot submission files (`calibration--A--p01`,
`enzyme-kinetics--A--p01`, `serial-dilution--A--p01`) and created four `.ruff_cache` folders in
Condition B submissions. Within minutes, the three files were restored from the backup and the
caches removed. All 171 results files were then verified byte for byte against the backup
manifest. Their evaluations had been made before the change and were not affected. Ruff now
excludes `results/`.

**What was still unverified at the time.** No session with a real token had run in
non-interactive mode. The exact `rate_limit_event` values for a Pro account with extra usage off,
and the `terminal_reason` of a real completed session, had not been seen. The engineering
validation run of 2026-11-16 (next section) settled both.

## Data collection (2026-11-16 to 2026-11-21, protocol 1.5)

This section records how the trials were run and the infrastructure incidents during
collection. **None of it is an experimental outcome.** No result, score, or comparison between
the conditions appears here. Times are UTC, taken from the batch journal
(`~/researchcode-trials/batch-log.jsonl`), the trial records, and the macOS power log.

**Who did what.** The project owner started every batch and carried out every recovery step
(`rc-exp set-validity`, `rc-exp collect`, moving attempts aside). Claude Code investigated each
stop read-only, proposed the steps from `docs/RUNNING_TRIALS.md`, and audited the data after
collection. It started no session and changed no record.

**Engineering validation run: `calibration--A--e01` (2026-11-16).** It ran from 23:35:37 to
23:37:25 (108.2 s) as one unattended session, outside the schedule. Results:

- **Session:** completed, exit code 0, `is_error` false, `terminal_reason` `completed`.
- **Authentication:** `apiKeySource` was `none`, so the subscription token was used and no API key.
- **Usage:** three `rate_limit_event` messages, all `allowed`, with `overageStatus` `rejected`
  and `isUsingOverage` false.
- **Collection and evaluation:** it was collected into `results/engineering/` and evaluated by
  the genuine evaluator under freeze `f09fbb4872529faa`, without an evaluation error.

This confirmed the two values the batch relies on: the `terminal_reason` of a completed session,
and the overage status when extra usage is off. As an engineering run, it is in no analysis, and
it did not change the schedule.

**Batches.** Eleven batches ran the confirmatory trials in schedule order:

| Batch | Start – end | Schedule positions | Sessions started | How it ended |
| --- | --- | --- | --- | --- |
| `…67c5b1` | 2026-11-18 23:01 – 23:10 | 8 | 1 | completed |
| `…83447a` | 2026-11-19 00:52 – 01:38 | 9–18 | 10 | completed |
| `…e6aeca` | 2026-11-19 05:32 – 06:47 | 19–28 | 10 | completed |
| `…3caead` | 2026-11-19 07:15 – 07:58 | 29–33 | 5 | stopped: usage limit (incident 1) |
| `…4757b8` | 2026-11-19 19:27 – 19:49 | 33–36 | 4 | completed |
| `…ce1bb7` | 2026-11-19 21:01 – 21:32 | 37–42 | 6 | completed |
| `…fadb72` | 2026-11-19 21:57 – 22:21 | 43–46 | 4 | completed |
| `…abff9b` | 2026-11-20 00:48 – 01:35 | 47–56 | 10 | completed |
| `…7aea12` | 2026-11-20 01:53 – 14:16 | 57–59 | 3 | stopped: needs review (incident 2) |
| `…fdf646` | 2026-11-21 01:44 – 01:57 | 59–60 | 2 | completed |
| `…c26869` | 2026-11-21 02:01 – 02:49 | 61–66 | 6 | completed |

The pilot (positions 1–6) and position 7 (`serial-dilution--B--r01`) had already been run by hand
under protocol 1.4, from 2026-11-15 to 2026-11-16 (previous section).

**Incident 1: usage limit during `serial-dilution--B--r05` (2026-11-19).**

- **What happened.** Attempt 1 started at 07:32:35 (schedule position 33). The rate-limit status
  had been `allowed_warning` since the session's first event. At 07:36:20 the laptop went into
  clamshell sleep on battery, and the session paused.
- **The stop.** At 07:58:16 a brief system wake let the pending request through. It returned
  HTTP 429, "You've hit your 5-hour limit · resets 10:30am (UTC)". The batch stopped the
  container at once and recorded the trial as invalid (`stop_category` `usage_limit`). It was
  not collected or evaluated.
- **No paid usage.** `overageStatus` was `rejected` and `isUsingOverage` false throughout.
- **Rule.** Protocol section 10: a session interrupted by the usage limit, or stopped by
  `rc-exp batch` for it, is invalid. It is rerun under the same identifier, at most twice.
- **Recovery.** The attempt was collected without evaluation at 19:25:12 and kept as
  `invalid-attempts/serial-dilution--B--r05-attempt1`, both in `results/genuine/` and in the
  trials folder.
- **Attempt 2.** It started at 19:27:48, after the limit had reset, from a new workspace and a
  new Claude configuration. It completed normally (exit code 0) and is valid.
- **Context.** Between 05:32 and 07:58 that morning, 14 sessions completed before this one
  reached the limit. This log has no record of any other use of the subscription in that period.

**Incident 2: the laptop slept overnight with its lid closed on battery (2026-11-20).** The
macOS power log shows clamshell sleep from 02:09:56 on 2026-11-20 (on battery) until the lid was
opened at 17:23:06. In between, the machine woke only briefly ("dark wakes"). A `caffeinate`
process was running, but it cannot keep a Mac awake with the lid closed on battery. Three
things were affected:

- **`enzyme-kinetics--B--r09` (position 57).** Its session ended normally at 02:09:47, before
  the sleep. Collection and evaluation then ran during the sleep.
- **`serial-dilution--B--r09` (position 58).** The session ran from 04:09:34 to 07:23:00 almost
  entirely in dark wakes: 674.1 s of measured time in 3 h 13 min of real time.
  - Claude Code retried 9 requests after connection errors. All recovered, and no API error
    ended the session.
  - It completed normally: exit code 0, `terminal_reason` `completed`, no continuation message.
  - It is **valid** under protocol section 10, which excludes trials only for infrastructure
    failures that end or invalidate a session. It was not excluded.
- **Both evaluations.** Both were evaluated in the Docker sandbox with no evaluation error, no
  sandbox error, no missing case observation, and no time limit reached.
- **`calibration--A--r09` (position 59), attempt 1.** It started at 07:45:36, during a dark wake.
  - After three turns (two `Bash` calls), its next request never completed. Claude Code retried
    10 times, then ended at 14:16:45 with "API Error: Connection dropped (ECONNRESET)", exit
    code 1, `terminal_reason` `api_error`.
  - The proxy container had been running continuously. The connections were lost because the
    host was asleep.
  - Under section 10, an unattended session whose end is uncertain is marked for review, so the
    batch recorded `needs_review` and stopped without collecting it.
  - **Decision.** The project owner reviewed the logs and recorded the attempt as **invalid**:
    "API connection errors (ECONNRESET) ended the session after 10 retries while the host was in
    clamshell sleep on battery; infrastructure failure (protocol section 10); logs reviewed".
    The decision was made before any evaluation, and none exists for this attempt.
  - **Recovery.** The attempt was collected without evaluation at 01:43:39 on 2026-11-21 and
    kept as `invalid-attempts/calibration--A--r09-attempt1`.
  - **Attempt 2.** It started at 01:44:36 from a new workspace and configuration, completed
    normally (exit code 0), and is valid.

Neither incident needed a protocol amendment. Both were handled under the rules in sections 10
and 13 as frozen in version 1.5.

**Other infrastructure observations.**

- **Sessions near the usage limit.** Three valid trials (`calibration--A--r05`,
  `calibration--B--r05`, `calibration--B--r07`) completed normally while the rate-limit status
  was `allowed_warning`. The protocol does not exclude them. Section 12 already lists "sessions
  near a limit could behave differently" as a threat.
- **Container clock.** During incident 2, the clock inside the agent container ran about
  6.5 minutes behind the host. This affects only the timestamps inside that attempt's session
  log. The harness measures durations on the host.

**State at the end of collection (2026-11-21).**

- **Confirmatory trials:** 60 of 60 valid. Each of the six task × condition cells has exactly
  `r01` to `r10` (30 trials per condition), collected and evaluated, in the seeded schedule
  order (seed 20261111).
  - 59 ran unattended under protocol 1.5 and were evaluated with freeze `f09fbb4872529faa`.
  - `serial-dilution--B--r01` ran by hand under protocol 1.4 and was evaluated with freeze
    `b910a7b7afd0a1fd`. It stays in the primary analysis, and the exploratory analysis
    without it is reported separately (protocol 1.5 amendment).
- **Pilot:** 6 of 6 valid, all under protocol 1.4 (freeze `b910a7b7afd0a1fd`). They are kept in
  `results/pilot/`, apart from the confirmatory data, and are analysed only descriptively.
- **Invalid attempts:** two, each attempt 1, each archived in both places and never evaluated.
  The analysis does not read them. No trial needed a second rerun.
- **Freeze:** `rc-exp freeze --check` reports that the public and private files match
  `FREEZE.json` (`f09fbb4872529faa`). The version 1.4 record is kept in `freeze-history/`.
- **Audit:** the outcome-blind audit after collection checked the following against the frozen
  configuration, and found no failure:
  - **Trial records:** schedule, cells, model, effort, Claude Code version, permission mode,
    authentication source, tools, prompts, and initial workspaces;
  - **Evaluation records:** evaluator, sandbox image, case sets, required fields, and
    infrastructure markers.

**Outcome values seen during collection.** The batch journal records each evaluated trial's
hidden pass rate, so anyone who reads it sees outcome values.

- **Positions 8–32.** While investigating incident 1, Claude Code printed the journal and saw the
  values for these trials, which had been evaluated by then. They were not analysed, compared
  between conditions, or reported.
- **The engineering run.** Its value was given to the project owner in the run's verification
  report.
- **Everything else.** No other outcome values were viewed during the investigations or the
  audit. No validity decision depended on a score: neither invalid attempt was evaluated, and
  every other trial's validity was set automatically from its session.

## Analysis, review packets, and the omitted maintainability review (2026-11-22)

This entry was written before the project owner or Claude Code had looked at any comparative
outcome of the analysis. Times are UTC.

**Pre-analysis backup.** `~/researchcode-backups/2026-11-22T051228Z-before-analysis/` holds:

- the collected results and the trial folders, without virtual environments or caches;
- the public repository's full Git history, with its working tree and the uncommitted log;
- the private evaluator, kept apart.

All 3,705 files verified against SHA-256 manifests, and a restore of the repository was tested.

**The pre-registered analysis.** It ran at 05:53:34 with the unchanged command
`uv run rc-exp analyze --kind genuine`, and finished with exit code 0.

- **Before and after the run:** `rc-exp freeze --check --require-private` matched `f09fbb4872529faa`.
- **What it analysed:** 60 trials found, 60 analysed, 0 excluded. That is exactly the 60
  scheduled confirmatory trials, including the two reruns at attempt 2. No pilot, engineering
  run, or archived invalid attempt was read.
- **Raw data:** the 1,584 existing results files still matched the backup manifest afterwards.
- **Output:** five files in `experiments/results/analysis/genuine/`: `analysis.json`, `report.md`,
  and three figures.
- **Verification.** 50 outcome-blind checks passed. They printed only pass or fail:
  - the primary difference and the per-task differences were recomputed independently;
  - the bootstrap intervals and the permutation p-value were reproduced with the frozen
    functions and settings (10,000 resamples, 10,000 permutations, seed 20261112, 95%,
    α = 0.05);
  - the output contains one p-value only;
  - the category-balanced sensitivity analysis and the labelled protocol 1.5 exploratory
    analysis (59 trials, without `serial-dilution--B--r01`, no test) were reproduced.

  The intervals and p-value were reproduced with the same frozen code. This confirms the
  settings and determinism; it is not an independent implementation.
- **Discrepancy between protocol and implementation.** For secondary metrics, protocol
  section 11 calls for "medians and means with bootstrap CIs per condition and task". The frozen
  implementation reports means and medians per condition and task, but its bootstrap intervals
  are for the B − A difference, not for each condition's mean or median. The implementation was
  frozen and was not changed; reports should state the difference.

**Blinded review packets.** They were made at 05:57:09 with the unchanged command
`uv run rc-exp review-packets`. The packets are in `~/researchcode-review/packets/` and the key
in `~/researchcode-review-key/blinding-key.json`. Both are outside the repository and readable
only by the owner (mode 700 or 600).

- **Contents:** 60 packets, 20 per task, each named `<random 8-hex code>-<task>` and holding
  only the task's implementation module. Every trial had a module. The codes are unique and
  match the key, which covers each confirmatory trial once. The key was checked by script
  only; its mapping was never printed or read.
- **No explicit identifiers.** No packet contains a trial ID, condition label, experiment
  wording, file path, starter-kit package name, reference to `AGENTS.md` or `CLAUDE.md`, or
  generator comment.
- **Metadata leak, corrected.** `blind.py` copies a package-shaped module with
  `shutil.copytree`. That copy keeps the original modification times (spread over about 3.3
  days) and mode 644, while single-file modules got the generation time and mode 600. With the
  public schedule and batch times, those timestamps could have linked 18 packets to their
  trials. Every packet file and folder was set to one timestamp, with modes 600 and 700. All
  100 files had identical SHA-256 hashes before and after. The frozen code was not changed;
  the defect remains in `blind.py`.
- **Style can still reveal the condition**, as protocol sections 5.3 and 12 expect. Counted
  across all packets, without linking any packet to a condition:
  - 30 of 60 refer to spec or docs files;
  - 18 are packages and 4 include `py.typed`.

**Post-analysis backup.** `~/researchcode-backups/2026-11-22T055832Z-post-analysis/` holds the
five analysis files, verified against a SHA-256 manifest (manifest hash `a6b74dab71c47845…`).
The pre-analysis backup was not changed.

**Decision: the maintainability review is not conducted (2026-11-22).**

- **Why.** Because of time and resource constraints, the project owner decided not to conduct
  the blinded human maintainability review (protocol section 5.3). The project owner states that
  the decision was made before they viewed the comparative results.
- **No scores.** No human or AI reviewer scored any submission. No AI scoring replaces the
  human review.
- **What is kept.** The review packets and the blinding key are kept unchanged and unused,
  together with the frozen rubric and protocol.
- **What this means.** Maintainability, as defined by the rubric, is **unmeasured**. Omitting it
  is a **deviation from the pre-registered protocol**, in which the review was a subjective
  secondary metric.
- **How it is recorded.** The deviation is recorded here, not as an amendment in protocol
  section 13: the protocol, `experiment.json`, and the rubric are frozen and stay unchanged.
  Any report of the experiment must state the deviation.
- **What is not affected.** The review was never part of the primary estimand, the hypothesis
  test, or the objective metrics. The completed objective analysis is unchanged.

## Measurement diagnostics after unblinding (2026-11-22)

Both problems below were found **after** the pre-registered analysis had run and **after** its
results had been unblinded, while the outcomes were being read. They are post-analysis
measurement diagnostics, not pre-registered changes.

- **Unchanged:** the statistical output, the scores, the evaluation records, the data, the
  protocol, and the freeze record (`f09fbb4872529faa`).
- **Not done:** no trial was excluded and no analysis was rerun or added.

The figures below were read from the existing `evaluation.json` files.

**1. The security metric counts the wrong rules.**

- **The protocol's definition.** Protocol section 5.2 defines static security findings as Ruff
  `S` (flake8-bandit) findings.
- **What the frozen code counts.** `src/rc_experiments/static.py` counts every Ruff code whose
  identifier starts with `S`:

  ```python
  security = {code: n for code, n in by_code.items() if code.startswith("S")}
  ```

  This also matches the `SIM` (flake8-simplify) rules, which the fixed rule set includes.
- **Effect.** Every finding counted as "security" was a `SIM` code. Condition A had 27 such
  findings in 12 of 30 trials (SIM105 9, SIM115 8, SIM101 5, SIM102 3, SIM108 1, SIM300 1).
  Condition B had none.
- **Under the protocol's definition** (codes `S` followed by digits), **both conditions had zero
  security findings.**
- **What the reported −0.90 means.** The reported difference of −0.90 findings (B − A, 95% CI
  [−1.20, −0.63]) is therefore **not a valid security comparison**. The frozen output is kept as
  generated. No report may claim that either condition improved security.
- **What else is affected.** The `SIM` findings are also counted, correctly, in lint density,
  which counts every rule in the fixed set. That metric is not affected.

**2. Three mutation scores of zero despite large test suites.** In `serial-dilution--B--r01`,
`serial-dilution--B--r04`, and `serial-dilution--B--r07`:

- **Tests:** the agent wrote 220, 229, and 252 tests. All of them passed against the
  submission's own code.
- **Against the reference:** none of them passed against the reference implementation. The
  frozen evaluator counts only tests that pass against the reference as valid, so each trial
  had 0 valid tests.
- **Result:** all 9 mutants were recorded as "no valid task tests", and the mutation score is 0.

`serial-dilution--B--r01` is also the trial that was run interactively. Why these tests fail
against the reference has not been investigated, and no explanation is assumed here.

The frozen mutation scores stay as reported. Read them with this limitation in mind: for these
three trials, a score of 0 does not mean that no tests were written. The three zeros are part of
the reported serial-dilution Condition B mean (0.700) and of the pooled Condition B result.

## POST HOC: why three serial-dilution test suites had no valid tests (2026-11-22)

**This whole section is a post-hoc investigation.** It was carried out after the pre-registered
analysis and after unblinding, read-only.

- **Unchanged:** the evaluator, the protocol, the frozen analysis, the data, and the scores. In
  particular, the three mutation scores of 0 and the reported primary and secondary analyses
  are kept exactly as generated.
- **Not done:** no analysis was rerun, no hypothesis test was added, and no trial was excluded.
- **How hidden material was handled:** the reference implementation was checked by script for
  which top-level names it defines; no reference code is reproduced here.

**How the evaluator decides that a test is valid (confirmed from the frozen code).**
`test_quality.py` and `sandbox_scripts/suite_runner.py` work as follows:

- **The run:** they copy the submission, overwrite its module with the reference implementation,
  and run the submission's **entire** pytest suite in one session in the sandbox.
- **The rule:** a test is valid only if its test ID is reported as `passed` in that run.
- **What is kept:** the evaluation record stores only the count (`valid_tests`). It does not keep
  per-test outcomes or pytest's output.
- **The missing option:** the runner does not pass `--continue-on-collection-errors`.

**Confirmed from the files and records.** In `serial-dilution--B--r01`, `r04`, and `r07`:

- **Own tests:** all 220, 229, and 252 collected tests passed against the submission's own code.
- **Against the reference:** 0 tests were valid, so all 9 mutants were recorded as "no valid task
  tests" and the mutation score is 0.
- **The extra import.** Each main test file (`tests/test_serial_dilution.py`) imports, at module
  level, a custom exception class from the submission: `InputTypeError` in r01 and
  `InvalidTypeError` in r04 and r07.
  - The submission defines the class as a subclass of both `TypeError` and `ValueError`, which
    satisfies the task statement's requirement to raise `ValueError` or `TypeError`.
  - The task statement does not name such a class, and the reference does not define it.
  - Each main file refers to the class in two places besides the import.
- **The second test file.** The property-test file (`tests/test_serial_dilution_properties.py`,
  14 to 17 test functions) does not import the class.
- **No other difference.** The module layout (one file, `src/serial_dilution.py`) and the pytest
  configuration are the same as in the seven serial-dilution Condition B trials that scored 1.0.
  Those trials import only the five functions the task statement names.

**Strongly supported mechanism, not directly observed.**

- **The chain:** with the reference in place, the import of the custom class cannot be resolved.
  pytest therefore cannot load the main test file, and by default it then stops the whole
  session ("Interrupted: 1 error during collection") before any test runs. That includes the
  tests in the independent property-test file.
- **The evidence:**
  - static inspection of the test files;
  - a check that the reference defines no such name and no module-level `__getattr__`;
  - a synthetic two-file reproduction in the sandbox image (pytest 9.2.0), which used no
    submission or reference code. In it, one file's unresolved import stopped the session, no
    test ran, and the JUnit report held only the error entry.
- **The limit of the evidence:** the original reference-run output was not kept, and the three
  suites were **not** rerun against the reference. The original errors were therefore not
  observed directly, although the stored record (`reference_status` `ran`, `valid_tests` 0) is
  consistent with the mechanism.
- **The pre-registered option ruled out:** the reference contains no doctest examples, so
  doctests taken from the substituted reference module cannot have added valid tests.

**What the zeros mean.** The three scores of 0 cannot establish that these tests were
ineffective. How much of each suite would have been compatible with the reference, and how many
defects it would have detected, remain **unknown**.

**Scenario bound (post hoc; not a corrected estimate and not a confidence interval).**

- **The assumption:** each of the three trials scored 1.0 instead of 0. Only this scenario was
  computed.
- **The effect:** the serial-dilution Condition B mean would rise from 0.700 to 1.000. The
  serial-dilution difference would rise from +0.578 to +0.878.
- **Overall:** the pooled mean-over-tasks difference (B − A) would rise from **+0.835** to about
  **+0.935** (0.9354).
- **The direction:** the failure can only lower Condition B's mutation scores. The pre-registered
  value of +0.835 is the reported result.

**A related case in another trial.** In `enzyme-kinetics--B--r05`, one test imports
`enzyme_kinetics.__main__`. That submodule does not exist after the package is replaced by the
reference.

- The import is **inside the test function**, not at module level, so it can fail only that test,
  not the collection of the file.
- The trial had 58 of 62 tests valid and a mutation score of 1.0.
- No other test or conftest file in the 60 trials (222 scanned) imports a name or submodule of
  the task module that the reference lacks.

**The fragility of validating tests against a reference.**

- **All-or-nothing per test:** validity depends on every import and every assertion in a test
  matching the reference implementation.
- **The whole suite in one run:** a single unresolvable import at module level can invalidate
  every test in every file. If the problem sits inside one test, it costs only that test.
- **Exclusions elsewhere:** in the trials that kept valid tests, 48% to 94% of the collected
  tests were valid. The reasons for the other exclusions were not investigated.

**Coupling to the submission is also a real limitation.**

- Tests that depend on names or behaviour particular to one implementation (here, a custom
  exception type more specific than the task requires) are less portable. Excluding them is
  what the reference-based rule is designed to do.
- This investigation therefore does **not** show that the excluded tests would all have passed
  against a compatible reference. It shows only that, for these three trials, the measurement
  stopped before any test could be judged.

## DEVIATION: three publication commitments not fulfilled (decided 2026-11-23, after unblinding)

**This is a deviation from the protocol's publication plan. It was decided after the
pre-registered analysis had run (2026-11-22) and after the results had been unblinded. It was
not pre-registered, and it is not an amendment to the experimental methods.**

**The original commitments.** The frozen protocol (the same wording in versions 1.4 and 1.5)
made three publication commitments:

- **Section 3:** the hashes in `FREEZE.json` let anyone check the evaluator "once the evaluator
  is released after data collection";
- **Section 6:** pilot results "are excluded from every analysis and published separately";
- **Section 10:** for rerun trials, "Every attempt is kept and published".

**The decision.** The project owner decided not to fulfil these three commitments in the
public release. The decision records no reason beyond that choice. One consideration recorded
earlier in this log is that per-trial evaluation records list hidden-case identifiers and
per-case details.

- **Released:** the protocol (version 1.5) with its amendment table, and the superseded 1.4
  protocol, configuration, and freeze record; the public framework (tasks, prompts, harness
  including the unattended batch runner, fixture evaluator, and aggregate evaluator
  validation); this research log; the final report in Markdown and PDF; the aggregate results
  (`docs/aggregate-results.json`); the three analysis figures; and the website.
- **Withheld:**
  - the hidden evaluator: its source, cases, expected values, reference solutions, and mutants;
  - the full pilot trial results;
  - the individual confirmatory trial records, submissions, and session logs (transcripts),
    and the full analysis output with its per-trial rows;
  - the two archived invalid attempts;
  - the blinding key, review packets, credentials, and backups.

**What this limits.** Without the withheld material, others cannot:

- check the evaluator against the hashes in `FREEZE.json`;
- rerun the hidden evaluation of any submission;
- inspect submissions or session logs;
- recompute per-trial scores or rerun the analysis;
- examine the pilot or the invalid attempts.

The results can therefore be audited only through the aggregate output, the three figures,
the frozen code, and this log. Independent replication and auditing are limited accordingly.

**What does not change.**

- The protocol keeps its original wording, including the three commitments. It is not edited
  retroactively.
- The freeze record (`f09fbb4872529faa`), the analysis code, and the analysis output are
  unchanged.
- Every recorded outcome is unchanged. No trial was excluded or rescored.

**Trial-level values that are public.** The three figures plot every confirmatory trial's
hidden pass rate, mutation score, and session time as an unlabelled dot, by task and
condition. They name no trial. The report also names a few individual values: the three
serial-dilution Condition B trials with no valid tests, and the enzyme-kinetics trial with 58
of 62 valid tests.

## Team attribution note (2026-11-24)

ResearchCode is a Caltech CS/EE 143 special project of a four-person team: John Ivanov, Bryan
Kim, Riley Coover, and Yurii Ilnytskyi. All four are coauthors of the final report.

Throughout this log, "the project owner" is John Ivanov, who is also the experiment operator.
The log was written during Phase 4 from the project owner's sessions with Claude Code. It does
not itemise the other team members' contributions, and that is not a statement that they made
none. The earlier entries are unchanged: this note neither adds nor removes anyone's documented
participation.

## Open items

- **Publish the analysis**, including results that do not favour the structured workflow. State
  that maintainability was not measured (deviation from protocol section 5.3), and state the
  confidence-interval discrepancy above. State both post-analysis measurement diagnostics:
  - the "security" metric counts `SIM` rules, and no security difference may be claimed;
  - the mutation-score limitation for the three serial-dilution Condition B trials, using the
    post-hoc diagnosis above. The zeros are a measurement failure, not evidence of ineffective
    tests. The +0.935 scenario is a bound, not an estimate.
- **For any future version of the evaluator** (a frozen-file change, so it needs a new freeze and
  an entry in protocol section 13):
  - judge test validity per file, or with `--continue-on-collection-errors`;
  - keep the pytest output of the reference run.

  This does not apply to the present results.
- **Before committing any results:** decided on 2026-11-23. Only aggregate results and the
  three figures are published; the per-trial records stay private (see the deviation above).
  The `evaluation.json` files list hidden-case identifiers and per-case details.
- **After the analysis:** update `experiment.json`'s status and the website. `experiment.json` is
  frozen, so this needs a new freeze record and an entry in protocol section 13.
- **Human review:** this log has no record of the human review of the protocol, tasks, hidden
  cases, and prompts that was listed here before the pilot. Record it if it took place.
