# Instructions for AI coding assistants

This file tells AI coding assistants (Claude Code, GitHub Copilot, Codex, Cursor, and
others) how to work in this repository. Humans should read it too: it describes the
project's rules. Edit it to fit your project, but keep the principles.

This is a scientific analysis project. A result that looks plausible but is wrong is worse
than no result. The people who own this project are responsible for its scientific
validity; your job is to help them produce code they can check.

## Project layout

- `src/<package>/`: analysis code. Scientific calculations live in small, pure functions
  (inputs in, values out, no file access), like `growth.py`.
- `src/<package>/cli.py`: the command-line entry point. File reading, validation of input
  data, and writing of results happen here, at the boundary.
- `src/<package>/provenance.py`: `write_run_metadata` records how each result was produced.
- `tests/`: pytest tests, including Hypothesis property-based tests.
- `docs/`: specifications. `docs/SPEC_TEMPLATE.md` is the template;
  `docs/spec-growth-rate.md` is a completed example.
- `data/`: input data. Treat it as read-only.

## Rules

### 1. Understand the scientific requirement before writing code

- Read the relevant specification in `docs/` first. If none exists for the task, propose
  one based on `docs/SPEC_TEMPLATE.md` and wait for the human to agree before implementing.
- If the specification is ambiguous or incomplete (units, logarithm base, how to handle
  missing values, which data to include), **stop and ask**. Do not guess. A guess about a
  scientific choice is a hidden decision that changes results.

### 2. Document assumptions explicitly

- State every assumption you make in the code (docstring or comment), in the
  specification, and in your summary to the human.
- Put units in variable and parameter names or docstrings (for example `t1_h`, `od600`).

### 3. Make small, reviewable changes

- One logical change at a time. Prefer several small changes over one large one.
- Do not reformat, rename, or refactor code unrelated to the task.
- Explain what you changed and why, in a few sentences, at the end of each task.

### 4. Add meaningful tests

- Every new scientific function gets tests in `tests/`:
  - known-answer tests whose expected values come from mathematics, published references,
    or hand calculation, **never from running the code under test**;
  - edge-case and invalid-input tests (zero, negative, NaN, infinity, empty, unsorted);
  - property-based tests with Hypothesis for relationships that must always hold.
- Write or extend tests before or alongside the implementation, not after it is "done".
- **Never** weaken, skip, delete, or loosen a test or a tolerance to make it pass. If you
  believe a test is wrong, explain why and let the human decide.

### 5. Verify mathematical and scientific correctness

- Check formulas against the specification line by line: units, log base, sign
  conventions, off-by-one indexing, and the order of operations.
- Use tolerances for floating-point comparisons (`pytest.approx`, `math.isclose`) and
  explain the tolerance.
- Prefer numerically stable formulations, and say when you have chosen one.

### 6. Run the checks before you say a task is finished

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

Fix every failure. Report the actual outcome. If you could not run a check, say so.

### 7. Avoid unnecessary dependencies

- Use the standard library or existing dependencies when they are adequate.
- Add a dependency only with the human's agreement, only with `uv add <package>` (never
  `pip install`), and only after confirming the exact package name exists on PyPI and is
  maintained.

### 8. Never fabricate

- Never invent data, results, figures, citations, references, DOIs, or test outcomes.
- Do not claim that tests pass, that code was run, or that a result was validated unless
  you actually did it in this session and saw the output.
- Sample or synthetic data must be labelled as such in file names or accompanying notes.

### 9. Report unresolved issues and limitations

- At the end of each task, list anything unfinished, any assumption the human must
  confirm, and any known limitation of the method or implementation.

### 10. Humans are responsible for scientific validation

- You may help, but a human decides whether a method is scientifically appropriate and
  whether results are valid. Flag anything that needs their judgement.

## Safety

- Never read, print, or commit secrets (`.env` files, API keys, tokens, passwords).
- Never modify or delete files in `data/` unless explicitly asked.
- Do not overwrite results; the example command and `write_run_metadata` refuse to by
  default.
- Do not use `pickle`, `eval`, `exec`, `yaml.load`, or `shell=True` on anything derived
  from input. See `docs/SECURITY_CHECKLIST.md`.
- Do not push, publish, or delete branches without the human's explicit approval.

## Git authorship and attribution

- Commits are made under the human's own Git identity. Never set an AI assistant as a
  Git author, committer, or co-author.
- Do not add AI attribution lines (such as `Co-Authored-By` trailers or "Generated with"
  notes) to commit messages or pull request descriptions. `.claude/settings.json` turns
  off Claude Code's automatic attribution.
- Keep `Co-authored-by` trailers for human collaborators.
- This concerns Git metadata only. Disclose the use of AI tools honestly where your field
  or publisher requires it, for example in a paper's methods section or the project
  README.
