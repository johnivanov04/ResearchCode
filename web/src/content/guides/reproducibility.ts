import type { Guide } from "./types";

export const reproducibility: Guide = {
  slug: "reproducibility",
  title: "Make your analysis reproducible",
  summary:
    "Pin the environment, protect raw data, record provenance, and prove that a fresh clone produces the same results.",
  stage: "Reproduce",
  readingMinutes: 14,
  audience: "Researchers whose analysis must be rerun by a collaborator, a reviewer, or themselves months from now.",
  outcomes: [
    "Pin Python and package versions with uv so every machine uses the same environment",
    "Separate raw data, code, and generated results, and record how each result was made",
    "Run a fresh-clone check that catches hidden dependencies on your own computer",
  ],
  sections: [
    {
      id: "why",
      title: "What reproducible means here",
      blocks: [
        {
          type: "paragraph",
          text: "In this guide, an analysis is reproducible if someone else can take your repository and your raw data, follow written instructions, and obtain the same figures and numbers. That person is often you, six months later, responding to a reviewer.",
        },
        {
          type: "paragraph",
          text: "AI assistants make it easy to accumulate hidden state: a package installed in one chat, a path that only exists on your laptop, a notebook cell run out of order, a random seed that was never set. None of these show up in the code you commit. Each of them can make your result impossible to regenerate.",
        },
      ],
    },
    {
      id: "environment",
      title: "Pin the environment",
      blocks: [
        {
          type: "paragraph",
          text: "Record the Python version and the exact version of every package. The tool `uv` does both: `pyproject.toml` lists the packages you depend on, and `uv.lock` records the exact versions that were resolved. Commit both files.",
        },
        {
          type: "code",
          language: "bash",
          title: "terminal",
          code: `uv init growth-analysis       # create a project with pyproject.toml
cd growth-analysis
uv python pin 3.12            # record the Python version in .python-version
uv add numpy pandas           # runtime dependencies
uv add --dev pytest ruff      # development-only tools
uv run pytest                 # run commands inside the project environment

# On another machine, or in CI:
uv sync --locked              # install exactly what uv.lock specifies`,
          caption: "uv sync --locked fails if uv.lock is out of date, instead of silently resolving new versions.",
        },
        {
          type: "callout",
          tone: "warning",
          title: "Avoid ad hoc installs",
          text: "If an assistant suggests `pip install something` in the middle of a session, add the package with `uv add` instead. Otherwise the package exists on your machine but not in the project's record of dependencies.",
        },
      ],
    },
    {
      id: "data",
      title: "Treat raw data as read-only",
      blocks: [
        {
          type: "list",
          items: [
            "Keep instrument exports in `data/raw/` and never edit them by hand. Every cleaning step should be code.",
            "Write derived data and figures to a separate directory, such as `results/`, that can be deleted and regenerated at any time.",
            "Record a checksum for each raw file so you can tell if a file has changed.",
            "If raw data is too large or too sensitive to commit, document where it is stored, who can access it, and its checksum.",
          ],
        },
        {
          type: "code",
          language: "bash",
          title: "terminal",
          code: `# Record checksums once, when the raw data arrives (macOS: shasum -a 256)
sha256sum data/raw/*.csv > data/raw/SHA256SUMS

# Verify before every analysis run
sha256sum --check data/raw/SHA256SUMS`,
        },
      ],
    },
    {
      id: "provenance",
      title: "Record provenance with every result",
      blocks: [
        {
          type: "paragraph",
          text: "A figure without a record of how it was made is hard to defend. Save a small metadata file next to each set of results that records the code version, the parameters, and the environment.",
        },
        {
          type: "code",
          language: "python",
          title: "src/growth/provenance.py",
          code: `import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], capture_output=True, text=True, check=True
    ).stdout.strip()


def write_provenance(out_dir: Path, parameters: dict) -> None:
    """Write provenance.json describing how the results in out_dir were made."""
    record = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git("rev-parse", "HEAD"),
        "uncommitted_changes": bool(_git("status", "--porcelain")),
        "python": sys.version,
        "platform": platform.platform(),
        "packages": {name: version(name) for name in ("numpy", "pandas")},
        "parameters": parameters,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "provenance.json").write_text(json.dumps(record, indent=2))`,
          caption: "If uncommitted_changes is true, the result cannot be tied to a specific version of the code.",
        },
      ],
    },
    {
      id: "randomness-and-paths",
      title: "Control randomness and paths",
      blocks: [
        {
          type: "list",
          items: [
            "Create one random generator with an explicit seed, such as `rng = np.random.default_rng(20240611)`, pass it to the functions that need it, and record the seed in provenance.",
            "Avoid the legacy global `np.random.seed`; it is easy for one library call to change the global state unexpectedly.",
            "Never hard-code absolute paths such as `/Users/yourname/Desktop/plate1.csv`. Accept paths as command-line arguments, or build them relative to the project root with `pathlib`.",
            "Expect small floating-point differences across operating systems and BLAS libraries. Compare results with a tolerance, and document the tolerance.",
          ],
        },
      ],
    },
    {
      id: "entry-point",
      title: "One command to regenerate everything",
      blocks: [
        {
          type: "paragraph",
          text: "Write the full sequence of steps, from raw data to final figures, as code that runs with a single documented command. Notebooks are useful for exploration, but before sharing one, restart the kernel and run all cells from top to bottom. Move functions you rely on into modules, where they can be tested.",
        },
        {
          type: "code",
          language: "bash",
          title: "README.md (excerpt)",
          code: `# Reproduce all results
uv sync --locked
sha256sum --check data/raw/SHA256SUMS
uv run python -m growth.cli data/raw/plate1.csv --out results/plate1`,
        },
      ],
    },
    {
      id: "fresh-clone",
      title: "Prove it with a fresh clone",
      blocks: [
        {
          type: "paragraph",
          text: "The most reliable reproducibility test is to start from nothing. Clone the repository into a new directory, follow only the README, and compare the outputs. Anything that relies on your own machine will fail here instead of in a reviewer's hands.",
        },
        {
          type: "code",
          language: "bash",
          title: "terminal",
          code: `git clone <your-repository-url> /tmp/repro-check
cd /tmp/repro-check
uv sync --locked
uv run pytest
# then run the documented analysis command and compare outputs`,
        },
        {
          type: "paragraph",
          text: "Continuous integration, such as GitHub Actions, performs a version of this check automatically on every push: it starts from a clean machine, installs from the lock file, and runs the tests.",
        },
        {
          type: "prompt",
          title: "Audit a repository for reproducibility",
          prompt: `Review this repository for reproducibility problems. Do not change
any files yet.

Look for and list, with file and line references:
1. Absolute or user-specific file paths.
2. Imports of packages that are not declared in pyproject.toml.
3. Random number generation without an explicit, recorded seed.
4. Steps that modify files in data/raw/ or depend on manual actions.
5. Results written without recording parameters or code version.
6. Notebook cells that depend on execution order or hidden state.
7. Anything in the README instructions that would fail on a fresh clone.

For each problem, explain the risk in one sentence and propose a fix.
Rank them by how likely they are to change a scientific result.`,
          note: "Ask for a list first and make the fixes in small, separately reviewed commits.",
        },
      ],
    },
    {
      id: "checklist",
      title: "Checklist",
      blocks: [
        {
          type: "checklist",
          title: "Before you share results",
          items: [
            "`pyproject.toml`, `uv.lock`, and `.python-version` are committed.",
            "Raw data is unchanged, checksummed, and stored separately from results.",
            "Every result directory contains provenance with the git commit and parameters.",
            "Random seeds are explicit and recorded.",
            "No absolute or user-specific paths remain in the code.",
            "A single documented command regenerates every figure and table.",
            "A fresh clone, following only the README, reproduces the results.",
            "Tests pass in continuous integration.",
          ],
        },
      ],
    },
  ],
};
