# Running the trials (protocol 1.5: unattended batches, $0 additional cost)

Every trial uses your existing **Claude Pro subscription** and nothing else: no API key, usage
credits, or other paid service. The pilot and the first confirmatory trial were **manual,
interactive sessions** (protocols 1.1 to 1.4, section 4). From protocol 1.5, the remaining
trials run **unattended**: `rc-exp batch` runs them one at a time in schedule order with Claude
Code's non-interactive mode, then collects and evaluates each one (section 3). A session starts
only when you run `rc-exp preflight`, `rc-exp session`, or `rc-exp batch`. CI never runs one.

You work in **VS Code**, but every Claude Code session runs from the **integrated terminal,
inside the agent container**. Do **not** use the Claude Code extension panel for trials. The
extension runs on your Mac with access to this whole repository, including the hidden
evaluator, and with your own settings and memory.

All `rc-exp` commands run from `experiments/` (`cd experiments`, then `uv run rc-exp ...`). On this
Mac, set `UV_PROJECT_ENVIRONMENT` to a folder outside iCloud first (see the repository's
`CLAUDE.md`).

## 1. One-time setup

0. **The private evaluator.** The genuine hidden cases, references, and defects are in
   `~/researchcode-private/phase4-evaluator`, a private Git repository outside this public one.
   Keep a backup. If you publish it before the experiment ends, make it a private repository.
   Check it before the pilot:

   ```bash
   uv run rc-exp validate-evaluator                 # references 100%, every defect detected
   uv run rc-exp freeze --check --require-private   # public and private files match FREEZE.json
   ```

1. **Turn off paid usage beyond your plan.** Anthropic calls it *usage credits*; Claude Code
   calls it *extra usage*.
   - Open [claude.ai/settings/usage](https://claude.ai/settings/usage) (Settings > Usage).
   - Make sure usage credits are **off**, including any automatic reload.
   - Anthropic's help article
     ([Using extra usage](https://support.claude.com/en/articles/12429409-using-extra-usage))
     says that once they are disabled, "you'll only have access to your plan's included usage".

   This is the only way a Pro session could cost money. Check the setting again before every
   sitting: some users have reported it being re-enabled unexpectedly (unofficial reports). If
   Claude Code ever says that extra usage is covering your requests, type `/exit` at once. The
   trial is invalid.
2. **Create a subscription token** in a normal terminal (outside any trial):

   ```bash
   claude setup-token
   ```

   Follow the browser sign-in with your Claude account. The command prints a long-lived
   token that uses your subscription. Store it in your password manager, never in a file in
   this repository. A long token can wrap across lines in the terminal. Copy it as one
   unbroken line, with no spaces or line breaks. In each terminal where you run trials, set it
   without showing it or saving it in your shell history:

   ```bash
   read -rs CLAUDE_CODE_OAUTH_TOKEN && export CLAUDE_CODE_OAUTH_TOKEN
   ```

   Paste the token and press Enter; nothing is displayed. `rc-exp check` reports a token that
   is missing or contains whitespace, without printing it.

   Do **not** set `ANTHROPIC_API_KEY`. The harness never passes it into a trial, and it warns
   if it is set.
3. **Build the images and start the network.** The images are free downloads, and the
   network makes no model calls.

   ```bash
   uv sync --locked
   uv run rc-exp build-images
   uv run rc-exp network up
   uv run rc-exp check          # must print "ready for manual sessions"
   ```

**After updating the repository**, rebuild the images and restart the proxy. `rc-exp check`
reports an outdated agent image or proxy:

```bash
uv run rc-exp build-images
uv run rc-exp network down && uv run rc-exp network up
```

## 2. Before each sitting: preflight (no trial, no prompt)

```bash
uv run rc-exp preflight
```

Claude Code opens in the agent container with an empty folder. It does not ask for a theme
or a login. Answer the `/workspace` trust and permission-mode dialogs, then type:

- `/status`: you are signed in with your Claude subscription (not an API key or Console
  account). If Claude Code shows a login screen, or warns that authentication was rejected
  (401), stop: the token is not accepted. Create a new one with `claude setup-token`;
- `/model`: `claude-opus-5-5` is available. If it is not, stop. The model must be changed for
  both conditions and recorded in the protocol before any trial;
- `/usage`: enough plan usage remains for at least one full session (up to 45 minutes).

Then type `/exit`. These commands send no message to the model.

The proxy log (`docker logs rc-trials-proxy`) normally shows Claude Code's requests to
`github.com` and `downloads.claude.ai` being refused. That is intended: neither is needed for a
session. Never add a host to the allowlist without an amendment to the protocol.

## 3. Run the remaining trials unattended (protocol 1.5)

`rc-exp batch` takes the next trials from the randomised schedule (the same order as
`rc-exp next`), runs each one with `claude -p` in the same container, with the same prompt,
model, effort, tools, and 45-minute limit as a manual session, and then collects and evaluates
it. No message is sent to the agent after the prompt. Each trial records its execution mode
(`unattended-noninteractive`).

### Before every batch

1. **Extra usage is off** at [claude.ai/settings/usage](https://claude.ai/settings/usage)
   (section 1, step 1). Check it on the day.
2. **Preflight** (section 2): `/status` shows your subscription; `/usage` shows enough plan
   usage. Choose `--limit` so the sessions fit. A session that reaches the usage limit is
   stopped and is invalid.
3. **Only the subscription token is set** in this terminal (section 1, step 2). The batch refuses
   to start if any `ANTHROPIC_*`, `CLAUDE_CODE_USE_*`, or `CLAUDE_CODE_API_KEY*` variable is set.
   This lists their names, never their values:

   ```bash
   env | cut -d= -f1 | grep -E '^(ANTHROPIC_|CLAUDE_CODE_USE_|CLAUDE_CODE_API_KEY)' || echo "none set"
   ```

4. `uv run rc-exp check` prints "ready for manual sessions". This also means the images and the
   proxy are up to date.

### See what would run (starts and writes nothing)

```bash
uv run rc-exp batch --dry-run --limit 5
```

It lists the next trials in schedule order and every check that would stop a real batch.

### Run

```bash
uv run rc-exp batch --confirm-extra-usage-off --limit 5
```

`--confirm-extra-usage-off` is your statement that you checked step 1 today; without it the
batch refuses to start. `--limit` is the maximum number of new sessions (default 1, at most
60). You do not need to watch the sessions. Do not open or edit a trial's workspace while the
batch runs.

The batch **refuses to start** (exit code 2, nothing run) if the token is missing, malformed,
or not a token from `claude setup-token`, if another credential variable is set, if files
differ from `FREEZE.json`, if `rc-exp check` finds a problem, or if another batch is running.

During a session it **stops the container at once** if Claude Code reports an API key as its
credential, paid overage in use or available, the plan's usage limit, an authentication,
billing, or rate-limit error, any mention of extra usage, or a model, permission mode,
version, or tool set that differs from the protocol.

After each trial, the batch **continues** only if the session completed normally and the trial
was collected and evaluated. Otherwise it **stops** (exit code 1) and tells you why. It never
skips a trial and never starts a trial twice. Run it again after you have dealt with the stop:
it first finishes any collection or evaluation that did not complete, then continues with the
next trial in the schedule.

### Logs

- `~/researchcode-trials/batch-log.jsonl`: one line per step of every batch (`tail -n 20` shows
  the latest). It never contains credentials.
- `~/researchcode-trials/<trial-id>/agent-stream.jsonl` and `agent-stderr.txt`: Claude Code's
  output, with anything that looks like a credential redacted. They are copied into
  `results/<kind>/<trial-id>/agent-output/` when the trial is collected. The stream includes
  Claude Code's `total_cost_usd` field: under a subscription this is a notional estimate at API
  prices, not a charge, and it is not analysed.
- `trial.json`: the trial's record, including `agent.execution_mode`, `agent.completion`, and
  `agent.stop_reason`.

### When the batch stops

| What it says | What happened | What to do |
| --- | --- | --- |
| `REFUSED` | A check failed before anything started | Fix the named problem and run it again |
| usage limit / rate limit | The plan's limit was reached; the trial is invalid | Wait for the limit to reset, then rerun the trial (below) |
| extra usage / overage | Paid usage was in use or available; the trial is invalid | Turn extra usage off at claude.ai, then rerun the trial (below) |
| authentication or billing error | The token was rejected; the trial is invalid | Create a new token with `claude setup-token`, set it (section 1), then rerun the trial (below) |
| API key source, or a model, version, or tool that differs | The configuration was wrong; the trial is invalid | Do not continue. Find the cause (for example a changed Claude Code version), then rerun the trial (below) |
| the session's end is uncertain (`needs_review`) | Claude Code did not report a normal end | Read `agent-stream.jsonl` and the session log in the trial folder, then decide (below) |
| wall-clock limit | The agent used all 45 minutes. The trial is valid, and was collected and evaluated | Look at its log, then run the batch again |
| collecting or evaluating failed | The session is safe on disk | Fix the cause (for example, build the sandbox image), then run the batch again |
| interrupted, or a session started but never recorded | The batch was stopped during a session (Ctrl-C, crash, power loss) | Record it as invalid (below); it is never resumed |
| another batch holds the lock | A batch is running, or one crashed | Check with `pgrep -fl "rc-exp batch"`. If none is running, read the end of the batch log, then delete `~/researchcode-trials/.rc-batch.lock` |

**Deciding a `needs_review` trial.** If the log shows a normal session, record it as valid and
collect it yourself, then run the batch again:

```bash
uv run rc-exp set-validity <trial-id> valid --reason "unattended session ended normally; log reviewed"
uv run rc-exp collect <trial-id>
uv run rc-exp evaluate <trial-id>
```

Otherwise record it as invalid and rerun it. Never decide from the trial's score.

**Rerunning an invalid trial.** Keep the attempt, move it aside, and run the batch again; it
starts a new attempt from a new workspace:

```bash
uv run rc-exp set-validity <trial-id> invalid --reason "<what happened>"   # if not already invalid
uv run rc-exp collect <trial-id>                                           # keeps the attempt's logs
mkdir -p results/<kind>/invalid-attempts ~/researchcode-trials/invalid-attempts
mv results/<kind>/<trial-id> results/<kind>/invalid-attempts/<trial-id>-attempt<N>
mv ~/researchcode-trials/<trial-id> ~/researchcode-trials/invalid-attempts/<trial-id>-attempt<N>
```

`<kind>` is `genuine` for confirmatory trials. The batch refuses a fourth attempt (protocol
section 10: at most two reruns).

### Testing the harness first: an engineering validation run

Before the first unattended confirmatory trial, run one trial outside the schedule to see the
whole path work with your real token:

```bash
uv run rc-exp batch --dry-run --engineering-validation calibration--A
uv run rc-exp batch --confirm-extra-usage-off --engineering-validation calibration--A
```

It uses a real task, prompt, and the hidden evaluation, but gets the replicate `e01` (then
`e02`, ...), is stored in `results/engineering/`, does not change the schedule, and is never
part of the pilot or confirmatory analysis. It uses plan usage like any session.

## 4. Manual sessions (protocols 1.1 to 1.4)

The pilot and `serial-dilution--B--r01` were run this way. It is kept for the record and for
preflight checks; the remaining trials use section 3.

### Run one trial

1. Find the next trial in the randomised schedule:

   ```bash
   uv run rc-exp next
   ```

2. Start it. The command prepares a clean workspace if needed, opens Claude Code in the
   container with the prompt already entered, and evaluates the result after you exit:

   ```bash
   uv run rc-exp session <trial-id> --collect
   ```

3. **During the session:**
   - Answer only Claude Code's startup dialogs: trusting `/workspace` and the
     permission-mode warning.
   - Do not type anything while the agent works. Do not answer, guide, or correct it.
   - If the agent stops and **asks a question before it has finished**, send exactly the
     message in `conditions/CONTINUE.md`, at most twice:

     > No one is available to answer questions. Make a reasonable decision, note it, and continue until the task is finished.

   - When the agent says it has finished, type `/exit`.
   - If Claude Code reports a **usage limit** or **extra usage**, type `/exit` immediately.
   - At 45 minutes the container is stopped automatically.
4. **After the session**, answer the four questions in the terminal. The answers are recorded
   in `trial.json`. With `--collect`, the workspace is then copied to `results/pilot/` or
   `results/genuine/` and evaluated in the Docker sandbox. Evaluation uses no model.
5. Check progress at any time:

   ```bash
   uv run rc-exp progress
   ```

Do not open or edit the trial workspace (`~/researchcode-trials/<trial-id>/workspace/`) while
a session runs.

## 5. The pilot: six trials

The first six trials in the schedule (`p01`) are the pilot, one per task and condition, in
schedule order. Run them as your plan's usage allows. They can be spread over several
sittings or days; check `/usage` in a preflight before each one. After each pilot trial,
note the time, the messages and tokens it recorded (`rc-exp progress` and the trial's
`trial.json`), and how much plan usage it took. That shows how many trials one usage period
allows.

When all six are done:

```bash
uv run rc-exp analyze --kind pilot
```

The pilot is descriptive only. Its analysis is labelled as pilot data and never counts as
evidence for or against either workflow.

## 6. If fewer trials are feasible

Continue with confirmatory blocks (`r01`, `r02`, ...) only as far as your subscription allows.
**Stop only at the end of a complete block**, so both conditions and all tasks stay balanced,
and never stop because of results. `rc-exp analyze --kind genuine` reports planned against
achieved trials for every cell and states the statistical limitations. With fewer than 5
valid trials in any cell, there is no hypothesis test.

## 7. Validity and reruns

`rc-exp session` classifies each trial from its session log and your answers, and
`rc-exp batch` from Claude Code's streamed output and its session log (protocol section 10).
For unattended trials, see also "When the batch stops" in section 3.

**Invalid trials** include:

- a usage-limit interruption;
- extra usage;
- a different model, effort, or Claude Code version;
- a disallowed tool used;
- more than two continuation messages, or any other input from you.

**Rerunning an invalid trial:**

1. Move its folders aside: `results/<kind>/<trial-id>` to `results/<kind>/invalid-attempts/<trial-id>-attempt<N>`,
   and `~/researchcode-trials/<trial-id>` to `~/researchcode-trials/invalid-attempts/<trial-id>-attempt<N>`.
2. Run `rc-exp session` again. A rerun always starts from a new workspace; never resume a
   session.
3. Rerun a trial at most twice.

If a trial is marked `needs_review`, read its session log (`results/<kind>/<trial-id>/session-logs/`)
and record your decision:

```bash
uv run rc-exp set-validity <trial-id> valid --reason "session ended normally; log reviewed"
```

Never mark a trial invalid because of its score.

## 8. Afterwards

```bash
uv run rc-exp analyze --kind genuine
uv run rc-exp review-packets --out ../review-packets --key ../blinding-key.json
uv run rc-exp network down
```

The genuine analysis keeps every valid trial in the primary result, whatever its execution
mode. Because the first confirmatory trial was run interactively, the report also contains a
section labelled **exploratory** that repeats the primary estimand without it (protocol 1.5).

Keep the blinding key from the reviewer until every packet is scored. Publish the analysis,
including results that do not favour the structured workflow. Update `experiment.json`'s
`status` and the website only after the analysis is complete.
