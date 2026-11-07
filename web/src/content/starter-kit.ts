import { site } from "@/content/site";

/**
 * Facts about the scientific Python starter kit shown on /starter-kit.
 *
 * `starter-kit.test.ts` checks every file path below against the real
 * `scientific-starter/` directory and every command against its README, so this page
 * cannot silently drift from the implementation.
 */

export const starterDirectory = "scientific-starter";
export const starterSourceUrl = `${site.repository}/tree/main/${starterDirectory}`;
export const starterVersion = "0.1.0";

export type StarterComponent = {
  name: string;
  detail: string;
  /** Paths relative to scientific-starter/. */
  paths: string[];
};

export const starterComponents: StarterComponent[] = [
  {
    name: "uv project",
    detail: "Python 3.12+, a src/ package layout, and exact dependency versions locked in uv.lock.",
    paths: ["pyproject.toml", "uv.lock", ".python-version"],
  },
  {
    name: "pytest and Hypothesis tests",
    detail:
      "Known-answer, edge-case, invalid-input, property-based, and numerical-accuracy tests for the example, plus doctests.",
    paths: ["tests/test_growth.py", "tests/test_growth_properties.py", "tests/conftest.py"],
  },
  {
    name: "Ruff linting, formatting, and security rules",
    detail: "A curated rule set including the S (Bandit) security rules, configured in pyproject.toml.",
    paths: ["pyproject.toml"],
  },
  {
    name: "GitHub Actions CI",
    detail:
      "Installs from the lock file, lints, checks formatting, runs the tests, and builds and installs the package on Python 3.12 and 3.13.",
    paths: [".github/workflows/ci.yml"],
  },
  {
    name: "Specification template",
    detail: "Objective, inputs and units, assumptions, known answers, edge cases, tolerances, and acceptance criteria, with a completed example.",
    paths: ["docs/SPEC_TEMPLATE.md", "docs/spec-growth-rate.md"],
  },
  {
    name: "AI assistant instructions",
    detail:
      "Rules for any assistant: follow the specification, ask instead of guessing, test properly, never loosen tests, never fabricate, and leave scientific validation to people.",
    paths: ["AGENTS.md", "CLAUDE.md", ".claude/settings.json"],
  },
  {
    name: "Run metadata",
    detail:
      "Records Python and package versions, the lock file checksum, the git commit, seeds, parameters, and input checksums next to each result, without host names or absolute paths.",
    paths: ["src/scientific_starter/provenance.py", "tests/test_provenance.py"],
  },
  {
    name: "Security review checklist",
    detail: "Secrets, input validation, dependencies, unsafe deserialisation, filesystem operations, and reviewing AI-generated changes.",
    paths: ["docs/SECURITY_CHECKLIST.md"],
  },
  {
    name: "Worked example",
    detail: "Specific growth rate and doubling time from two optical density readings, with a command-line entry point and illustrative input data.",
    paths: [
      "src/scientific_starter/growth.py",
      "src/scientific_starter/cli.py",
      "tests/test_cli.py",
      "data/example/two_readings.csv",
    ],
  },
];

/** Directory tree shown on the page. Every entry with a `path` must exist. */
export const starterTree: { line: string; path?: string }[] = [
  { line: "scientific-starter/" },
  { line: "├── pyproject.toml          # dependencies and tool settings", path: "pyproject.toml" },
  { line: "├── uv.lock                 # exact versions of every package", path: "uv.lock" },
  { line: "├── .python-version         # Python version for local work", path: ".python-version" },
  { line: "├── README.md               # setup and daily use", path: "README.md" },
  { line: "├── AGENTS.md               # rules for AI coding assistants", path: "AGENTS.md" },
  { line: "├── CLAUDE.md               # imports AGENTS.md for Claude Code", path: "CLAUDE.md" },
  { line: "├── .claude/settings.json   # no AI commit attribution", path: ".claude/settings.json" },
  { line: "├── .github/workflows/ci.yml", path: ".github/workflows/ci.yml" },
  { line: "├── docs/", path: "docs" },
  { line: "│   ├── SPEC_TEMPLATE.md", path: "docs/SPEC_TEMPLATE.md" },
  { line: "│   ├── spec-growth-rate.md  # completed example", path: "docs/spec-growth-rate.md" },
  { line: "│   └── SECURITY_CHECKLIST.md", path: "docs/SECURITY_CHECKLIST.md" },
  { line: "├── src/scientific_starter/", path: "src/scientific_starter" },
  { line: "│   ├── growth.py           # pure scientific functions", path: "src/scientific_starter/growth.py" },
  { line: "│   ├── provenance.py       # run metadata", path: "src/scientific_starter/provenance.py" },
  { line: "│   └── cli.py              # reads input, writes results", path: "src/scientific_starter/cli.py" },
  { line: "├── tests/", path: "tests" },
  { line: "│   ├── test_growth.py", path: "tests/test_growth.py" },
  { line: "│   ├── test_growth_properties.py", path: "tests/test_growth_properties.py" },
  { line: "│   ├── test_provenance.py", path: "tests/test_provenance.py" },
  { line: "│   └── test_cli.py", path: "tests/test_cli.py" },
  { line: "└── data/example/           # illustrative input, not measurements", path: "data/example" },
];

export const copyCommands = `git clone --depth 1 ${site.repository}.git
cp -R ResearchCode/${starterDirectory} my-analysis
rm -rf ResearchCode
cd my-analysis
git init`;

export const checkCommands = `uv sync --locked
uv run pytest
uv run ruff check .
uv run ruff format --check .`;

export const exampleCommand =
  "uv run python -m scientific_starter.cli data/example/two_readings.csv --out results/example";

export const dailyCommands = `uv sync                    # update environment
uv run pytest -x -q        # stop at first failure
uv run ruff check . --fix  # safe lint fixes
uv run ruff format .       # format code
uv add numpy               # add a package
uv build                   # build into dist/`;
