# Security review checklist

Use this checklist when you review a change, especially one written or suggested by an AI
coding assistant. Research code is rarely a target in itself, but it often handles
credentials (cloud storage, instrument APIs, databases), unpublished data, and personal
or clinical data, and it runs on shared lab machines and clusters.

> **Automated checks cannot guarantee secure software.** Ruff's security rules (the `S`
> rules, based on Bandit) recognise common risky patterns in individual lines of code.
> They do not understand your data, your threat model, or what a function is supposed to
> do, and they miss many real problems. A clean `ruff check` means "no known pattern
> found", not "secure". Human review is still required.

## How the automated checks help

`uv run ruff check .` runs on every change locally and in CI. Examples of what it flags in
this project's configuration:

| Rule      | What it catches                                                     |
| --------- | ------------------------------------------------------------------- |
| `S105`    | A string that looks like a hard-coded password assigned to a variable |
| `S301`    | `pickle` loading, which can execute code from a malicious file     |
| `S506`    | `yaml.load` without a safe loader                                   |
| `S602`    | `subprocess` with `shell=True`                                       |
| `S307`    | `eval()`                                                            |
| `S608`    | SQL built by string formatting (possible SQL injection)            |
| `NPY002`  | Legacy global NumPy random seeding (a reproducibility issue)       |
| `DTZ005`  | Timestamps without a time zone                                      |

If you silence a rule with `# noqa: <code>`, write the reason on the same line or the line
above, as in `src/scientific_starter/provenance.py`. A bare `# noqa` is itself flagged.

## Checklist

### Secrets and credentials

- [ ] No passwords, API keys, tokens, or private keys appear in code, notebooks, tests,
      configuration files, or commit history.
- [ ] Secrets are read from environment variables or a secrets manager at run time, and
      the program fails with a clear message if one is missing.
- [ ] Local `.env` files are listed in `.gitignore` and never committed.
- [ ] Secrets are not printed, logged, written to results, or recorded in run metadata.
      (`write_run_metadata` rejects parameter names that look like credentials, as a
      safety net only.)
- [ ] No secret has been pasted into an AI assistant's chat or prompt.
- [ ] If a secret was ever committed, it has been **revoked and replaced**. Deleting it in a
      later commit does not remove it from history.

### Input validation

- [ ] Data entering the program (files, command-line arguments, API responses) is checked
      once, at the boundary: required columns, types, units, and valid ranges.
- [ ] Invalid input raises a clear error. It is not silently dropped, clipped, or replaced.
- [ ] NaN, infinity, empty input, and duplicated or unsorted values are handled
      deliberately.
- [ ] File names, sample IDs, and other values from data files are never used to build
      shell commands, SQL queries, or code.

### Dependencies

- [ ] Each new dependency is necessary; the standard library or an existing dependency
      cannot do the job reasonably.
- [ ] The package name was checked on PyPI. AI assistants sometimes suggest packages that
      do not exist or have names similar to popular ones (typosquatting).
- [ ] The package is actively maintained, widely used, and its source repository is
      linked from PyPI.
- [ ] It was added with `uv add <package>` (never `pip install`), so `pyproject.toml` and
      `uv.lock` record it, and both files are committed.
- [ ] Dependencies are updated deliberately (`uv lock --upgrade-package <name>`), with tests
      run after each update.
- [ ] GitHub Actions use trusted publishers' actions. For stronger protection, pin them to
      a full commit SHA instead of a version tag.

### Unsafe deserialisation and code execution

- [ ] `pickle`, `joblib`, `torch.load`, `numpy.load(..., allow_pickle=True)`, and
      `pandas.read_pickle` are only used on files you created yourself. Loading such a
      file from elsewhere can run arbitrary code.
- [ ] Data is exchanged in formats that cannot carry code: CSV, JSON, Parquet, HDF5, NetCDF,
      or NumPy `.npy` without pickling.
- [ ] YAML is read with `yaml.safe_load`.
- [ ] No `eval()` or `exec()` on anything derived from input. Use `ast.literal_eval` for
      Python literals, or a proper parser.

### Filesystem operations

- [ ] Raw data is opened read-only and never modified. Results go to a separate directory.
- [ ] Code does not delete or overwrite files without an explicit option. (Both
      `write_run_metadata` and the example command refuse to overwrite by default.)
- [ ] `shutil.rmtree`, `os.remove`, and similar calls operate only on paths the program
      created, and never on a path built from user or data input without checking it.
- [ ] Paths built from input cannot escape the intended directory (watch for `..` and
      absolute paths).
- [ ] No hard-coded absolute paths such as `/Users/yourname/...`; they leak user names and
      break on other machines.
- [ ] Temporary files use the `tempfile` module, not fixed names in `/tmp`.
- [ ] Archives (`zip`, `tar`) from outside sources are extracted with protection against
      path traversal (for `tarfile`, use `filter="data"`).

### Reviewing AI-generated changes

- [ ] You read every line of the change and can explain what it does.
- [ ] The change does only what was asked. Unrequested edits (especially to tests, CI,
      `.gitignore`, or dependency files) are questioned or reverted.
- [ ] No test was deleted, skipped, or loosened to make it pass.
- [ ] New dependencies, network calls, subprocess calls, and file deletions were noticed
      and justified.
- [ ] Error handling does not hide failures (for example, a bare `except: pass`).
- [ ] Results, citations, and test outcomes reported by the assistant were checked by
      running the tests yourself and reading the sources.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, and `uv run pytest` pass
      locally and in CI.
