# Scientific Python starter

A ready-to-use starting point for research code that is **correct, tested, and
reproducible**, designed for researchers who use AI coding assistants. It is part of
[ResearchCode](https://github.com/johnivanov04/ResearchCode), a Caltech CS/EE 143 special
project.

You get a working project with the safeguards already set up:

| Component | What it does for you | Where |
| --------- | -------------------- | ----- |
| uv project | One command installs exact, locked versions of Python packages | `pyproject.toml`, `uv.lock`, `.python-version` |
| pytest + Hypothesis | Known-answer, edge-case, and property-based tests | `tests/` |
| Ruff | Linting, formatting, and security checks | `[tool.ruff]` in `pyproject.toml` |
| GitHub Actions | Runs every check on every push, on Python 3.12 and 3.13 | `.github/workflows/ci.yml` |
| Specification template | Decide what "correct" means before writing code | `docs/SPEC_TEMPLATE.md` |
| AI assistant rules | Tells assistants to follow the spec, test, and never fabricate | `AGENTS.md`, `CLAUDE.md` |
| Run metadata | Records versions, parameters, seeds, and input checksums with each result | `src/scientific_starter/provenance.py` |
| Security checklist | What to check when reviewing a change | `docs/SECURITY_CHECKLIST.md` |
| Worked example | A small growth-rate calculation with its specification and full test suite | `growth.py`, `docs/spec-growth-rate.md` |

The example is small on purpose. Replace it with your own analysis once you have seen how
the pieces fit together.

## Quick start

### 1. Install uv

[uv](https://docs.astral.sh/uv/) manages Python versions, packages, and project
environments. Install it once per computer:

```bash
# macOS and Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Other options, such as Homebrew (`brew install uv`), are listed in the
[uv installation guide](https://docs.astral.sh/uv/getting-started/installation/). You do
not need to install Python separately: uv downloads the version this project needs.

### 2. Make your own copy

The starter currently lives inside the ResearchCode repository, in the
`scientific-starter/` folder. It is not a separate GitHub template repository, so copy the
folder out into a new project:

```bash
git clone --depth 1 https://github.com/johnivanov04/ResearchCode.git
cp -R ResearchCode/scientific-starter my-analysis   # PowerShell: Copy-Item -Recurse
rm -rf ResearchCode                                 # the clone is no longer needed
cd my-analysis
git init
```

The copy is a complete, independent project. Nothing in it refers back to ResearchCode.

### 3. Install and check

```bash
uv sync --locked             # create .venv with the exact versions in uv.lock
uv run pytest                # run the tests
uv run ruff check .          # lint, including security rules
uv run ruff format --check . # check formatting
```

All four should succeed. `uv run` runs a command inside the project's environment, so you
never need to "activate" anything.

### 4. Try the example

```bash
uv run python -m scientific_starter.cli data/example/two_readings.csv --out results/example
```

This reads two illustrative optical density readings, prints a growth rate of 0.346574 per
hour and a doubling time of 2 hours, and writes `results/example/result.json` and
`results/example/run_metadata.json`. Running it again into the same folder fails on
purpose rather than overwriting the earlier result; add `--overwrite` if you mean it.

## Everyday commands

| Task | Command |
| ---- | ------- |
| Install or update the environment after pulling changes | `uv sync` |
| Run all tests | `uv run pytest` |
| Stop at the first failure, with less output | `uv run pytest -x -q` |
| Run tests whose names contain "growth" | `uv run pytest -k growth` |
| Lint | `uv run ruff check .` |
| Fix lint problems that are safe to fix automatically | `uv run ruff check . --fix` |
| Format the code | `uv run ruff format .` |
| Add a runtime package | `uv add numpy` |
| Add a development-only package | `uv add --dev <package>` |
| Build the package (wheel and source archive in `dist/`) | `uv build` |

Never use `pip install` in this project: the package would be missing from `pyproject.toml`
and `uv.lock`, so nobody else (including CI) would get it.

## Make it your project

### Rename the package

`uv_build` requires the folder in `src/` to match the project name in `pyproject.toml`,
with dashes replaced by underscores. To rename `scientific-starter` to, say,
`plate-growth`:

1. In `pyproject.toml`, change `name = "scientific-starter"` to `name = "plate-growth"`.
2. Rename the folder `src/scientific_starter` to `src/plate_growth`.
3. Replace `scientific_starter` with `plate_growth` in `src/`, `tests/`, this README,
   `AGENTS.md`, and the last step of `.github/workflows/ci.yml`.
4. Run `uv lock`, then `uv sync`, then `uv run pytest` to confirm everything still works.

### Add your own analysis

Work in this order. It is the ResearchCode workflow, and each step is supported by a file
in this project.

1. **Specify.** Copy `docs/SPEC_TEMPLATE.md` to `docs/spec-<name>.md` and fill it in:
   inputs and units, the method, known-answer examples, edge cases, and tolerances.
   `docs/spec-growth-rate.md` shows a completed one.
2. **Test.** Turn the known answers and edge cases into tests in `tests/` before (or
   together with) the code. Expected values must come from the mathematics or a trusted
   reference, never from running the code you are testing.
3. **Implement.** Put calculations in small, pure functions in `src/<package>/` (values in,
   values out, no file access), and validate inputs at the start of each function.
4. **Check.** Run `uv run pytest`, `uv run ruff check .`, and `uv run ruff format --check .`.
5. **Record.** Read input files and write results in an entry point like `cli.py`, and
   call `write_run_metadata` next to every result.

Then delete the example files you no longer need: `growth.py`, `cli.py`, their tests,
`docs/spec-growth-rate.md`, and `data/example/`.

## The tests

`tests/` shows the kinds of tests that catch scientific errors, not just crashes:

- **Known-answer tests** (`test_growth.py`): OD doubling from 0.1 to 0.2 in 2 hours must
  give mu = ln(2)/2 = 0.34657359 per hour and a doubling time of 2 hours.
- **Edge cases and invalid input** (`test_growth.py`): zero and negative growth, zero or
  negative OD, NaN, infinity, wrong types, and times that do not increase.
- **Property-based tests** (`test_growth_properties.py`): Hypothesis generates thousands of
  inputs and checks relationships that must always hold, such as "multiplying both ODs by
  the same factor does not change the rate".
- **Numerical accuracy** (`test_growth_properties.py`): results are compared with a
  50-digit `decimal` calculation, with tolerances derived from how rounding errors
  propagate.
- **Doctests**: the examples in docstrings are run as tests, so they cannot go out of date.

These tests have caught real problems. While the starter was being built, a property test
found that the textbook formula `log(od2) - log(od1)` reports exactly zero growth when two
large readings differ in the last digit, and that `log(od2 / od1)` can be off by 50% in
the same situation. `growth.py` now uses a formulation that is accurate for all positive
inputs. In another check, a deliberately introduced bug (using `log10` for large changes)
passed the "OD doubles in 2 hours" test but was caught by two other known-answer tests
(ten-fold and eight-fold increases) and three property tests. One known answer is never
enough.

pytest is configured to treat warnings as errors and to reject unknown options and markers.
In CI, set `HYPOTHESIS_PROFILE=ci` to run 2000 examples per property test instead of 200.

## Recording how results were produced

```python
from scientific_starter.provenance import write_run_metadata

write_run_metadata(
    "results/run1",
    {"window_points": 5, "min_r2": 0.98, "time_unit": "h"},
    seed=20240611,  # if your analysis uses randomness
    input_files=["data/raw/plate1.csv"],
    packages=["numpy"],  # extra packages to record, if any
)
```

This writes `results/run1/run_metadata.json` with the time (UTC), Python version,
operating system family, package versions, a checksum of `uv.lock`, the git commit and
whether there were uncommitted changes, the seed, the parameters, and the name, size, and
SHA-256 checksum of each input file.

To protect privacy, it does **not** record the host name, your user name, absolute paths,
environment variables, or git remote URLs, and it rejects parameter names that look like
credentials (such as `api_key` or `password`). It refuses to overwrite an existing
metadata file unless you pass `overwrite=True`.

If `uncommitted_changes` is `true`, the result cannot be tied to an exact version of the
code. Commit before producing results you intend to keep.

## Continuous integration

`.github/workflows/ci.yml` runs on every push to `main` and every pull request once this
folder is the root of a GitHub repository. On Python 3.12 and 3.13 it:

1. installs exactly what `uv.lock` specifies (`uv sync --locked` fails if the lock file is
   out of date),
2. runs `ruff check` and `ruff format --check`,
3. runs the tests with the larger Hypothesis profile,
4. builds the package, then installs the built wheel in a clean environment and imports it.

## Working with AI coding assistants

`AGENTS.md` contains the project's rules for assistants; `CLAUDE.md` imports it for Claude
Code. They tell the assistant to read the specification first, ask instead of guessing,
make small changes, write meaningful tests, never loosen a test to make it pass, avoid
unnecessary dependencies, never fabricate results or citations, run the checks, and leave
scientific judgement to you. Adapt them to your project.

`.claude/settings.json` turns off Claude Code's automatic "Co-Authored-By" commit trailers
and pull request attribution, so commits carry only human authorship. Disclose AI use
where your field or journal requires it, for example in a methods section.

## Security

Read `docs/SECURITY_CHECKLIST.md` before sharing code or accepting AI-generated changes.
Ruff's security rules flag common risky patterns (hard-coded passwords, `pickle`, `eval`,
`shell=True`, unsafe YAML loading, SQL built from strings), but automated checks cannot
guarantee that software is secure. Review every change.

## Troubleshooting

**`uv sync --locked` fails with a message that the lock file needs to be updated.** You (or
an assistant) changed dependencies in `pyproject.toml` without updating the lock. Run
`uv lock`, review the change to `uv.lock`, and commit both files.

**`ModuleNotFoundError: No module named 'scientific_starter'` on macOS, although
`uv sync` succeeded.** This can happen when the project is inside a folder synced by
iCloud Drive (for example Desktop or Documents with "Desktop & Documents Folders" turned
on). The sync can mark files in `.venv` as hidden, and Python skips hidden `.pth` files,
which is how the project's own package is made importable. Move the project outside the
synced folders, or keep the environment elsewhere by setting
`UV_PROJECT_ENVIRONMENT` to a directory outside them, then run `uv sync` again.

**Tests fail with a warning turned into an error.** That is deliberate. Read the warning:
in scientific code it usually means a real problem, such as taking the log of zero.

## Limitations

- The example computes a growth rate from exactly two readings. It does not select the
  exponential phase or fit a full growth curve; that is a separate scientific task.
- CI is tested on Ubuntu with Python 3.12 and 3.13. Windows and macOS are expected to work
  with uv but are not tested in CI.
- Run metadata records package versions and a lock file checksum, not a full copy of the
  environment. Keep `uv.lock` under version control.
- ResearchCode has not chosen a license yet. Check the ResearchCode repository before
  reusing this code outside your own research.
