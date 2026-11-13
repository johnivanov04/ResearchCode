# Instructions for AI coding assistants working in `experiments/`

This folder is a pre-registered experiment. Its credibility depends on rules that are easy to
break by accident. Read `docs/PROTOCOL.md` before changing anything.

## Never

- Copy anything from the private genuine evaluator (`~/researchcode-private/phase4-evaluator`) into
  this public repository, a trial workspace, a task statement, a prompt, CI, or the website. This
  includes hidden cases, expected values, reference solutions, defective variants, and any line of
  their test data. Only aggregate validation figures are public. Public tests and CI use the fixture
  evaluator.
- Start a trial or preflight session (`rc-exp session`, `rc-exp preflight`) or anything else that
  calls a model. Sessions are run by the human operator, through their Claude Pro subscription.
  Never add a model call to CI, never use or request an API key, and never add a command that runs
  Claude Code non-interactively (`claude -p`). The budget for additional spending is $0.
- Create, edit, or delete anything in `results/genuine/` or `results/pilot/` by hand. Never write
  fixture or mock data there.
- Invent results, usage figures, costs, or statistics. Values the tool did not report stay
  missing.
- Change a frozen file (see `FREEZE.json`) after the first pilot trial, except to fix a defect
  recorded in the protocol's section 13.
- Evaluate generated code with the local backend. Generated code runs only in the Docker sandbox.

## Always

- Keep the protocol, `experiment.json`, and the website consistent; the tests check this.
- After changing a frozen file before trials start, run `uv run rc-exp freeze` and record the
  change in the protocol's amendment table and in `docs/RESEARCH_LOG.md`.
- After changing the genuine evaluator (in its private repository), run
  `uv run rc-exp validate-evaluator --write` and `uv run pytest ~/researchcode-private/phase4-evaluator/tests`.
  Confirm that the references score 100%, every defect is detected, and no private content appears
  in this repository.
- Run `uv sync --locked`, `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, and
  `uv build` before finishing.
