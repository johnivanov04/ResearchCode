# Running the trials (protocol 1.1: manual sessions, $0 additional cost)

Every trial is a **manual, interactive Claude Code session** that uses your existing **Claude
Pro subscription**. The harness never starts a model session by itself. CI never runs a
session. Nothing here uses an API key, usage credits, or any other paid service.

You work in **VS Code**, but every Claude Code session runs in the **integrated terminal,
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
   this repository. In each terminal where you run trials:

   ```bash
   export CLAUDE_CODE_OAUTH_TOKEN='...'
   ```

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

## 2. Before each sitting: preflight (no trial, no prompt)

```bash
uv run rc-exp preflight
```

Claude Code opens in the agent container with an empty folder. Type:

- `/status`: you are signed in with your Claude subscription (not an API key or Console
  account);
- `/model`: `claude-opus-5-5` is available. If it is not, stop. The model must be changed for
  both conditions and recorded in the protocol before any trial;
- `/usage`: enough plan usage remains for at least one full session (up to 45 minutes).

Then type `/exit`. These commands send no message to the model.

## 3. Run one trial

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
   - Answer only Claude Code's startup dialogs: theme, trusting `/workspace`, and the
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

## 4. The pilot: six trials

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

## 5. If fewer trials are feasible

Continue with confirmatory blocks (`r01`, `r02`, ...) only as far as your subscription allows.
**Stop only at the end of a complete block**, so both conditions and all tasks stay balanced,
and never stop because of results. `rc-exp analyze --kind genuine` reports planned against
achieved trials for every cell and states the statistical limitations. With fewer than 5
valid trials in any cell, there is no hypothesis test.

## 6. Validity and reruns

`rc-exp session` classifies each trial from its session log and your answers
(protocol section 10).

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

## 7. Afterwards

```bash
uv run rc-exp analyze --kind genuine
uv run rc-exp review-packets --out ../review-packets --key ../blinding-key.json
uv run rc-exp network down
```

Keep the blinding key from the reviewer until every packet is scored. Publish the analysis,
including results that do not favour the structured workflow. Update `experiment.json`'s
`status` and the website only after the analysis is complete.
