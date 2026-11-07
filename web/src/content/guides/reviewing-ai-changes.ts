import type { Guide } from "./types";

export const reviewingAiChanges: Guide = {
  slug: "reviewing-ai-changes",
  title: "Review AI changes before you accept them",
  summary:
    "Read every diff with a scientist's eye: catch silent data handling, unsafe patterns, and unverified dependencies before they reach your results.",
  stage: "Review",
  readingMinutes: 11,
  audience: "Researchers who accept code changes from an AI assistant into a project that others rely on.",
  outcomes: [
    "Keep AI changes small enough to review properly",
    "Recognise the correctness red flags most common in generated analysis code",
    "Avoid common security mistakes with secrets, untrusted files, and new dependencies",
  ],
  sections: [
    {
      id: "small-changes",
      title: "Make changes small enough to read",
      blocks: [
        {
          type: "paragraph",
          text: "You cannot review a 600-line change carefully, and neither can anyone else. Ask the assistant for one focused change at a time, commit it, and only then move on. Version control turns each change into something you can inspect and, if necessary, undo.",
        },
        {
          type: "code",
          language: "bash",
          title: "terminal",
          code: `git switch -c fix-blank-correction   # work on a branch
git diff --stat                       # which files changed, and how much?
git diff                              # read every line
uv run ruff check . && uv run pytest  # automated checks before committing
git add -p                            # stage hunks you have actually read
git commit -m "Apply blank correction before log transform"`,
        },
        {
          type: "callout",
          tone: "note",
          text: "If `git diff --stat` shows files you did not expect to change, stop and ask why before reading further. Unrequested edits to tests, configuration, or data files deserve extra scrutiny.",
        },
      ],
    },
    {
      id: "correctness",
      title: "Correctness red flags in generated analysis code",
      blocks: [
        {
          type: "paragraph",
          text: "These patterns are not always wrong, but each one makes a decision about your data. Each needs a reason you agree with.",
        },
        {
          type: "list",
          items: [
            "Silent data removal or replacement: `dropna()`, `fillna(0)`, `np.clip`, or filtering rows without logging how many were affected.",
            "Broad exception handling such as `except Exception: pass`, which turns errors into missing results.",
            "Unstated constants: thresholds, window sizes, or conversion factors with no comment or source.",
            "Logarithm and unit choices: `np.log` is natural log, `np.log10` is base 10, `np.log2` is base 2. Check that units are converted exactly once.",
            "Axis and alignment mistakes: the wrong `axis=` in NumPy reductions, or pandas operations that align on index labels when you expected positional order.",
            "Changes to tests or tolerances that make a failing test pass.",
            "New behaviour you did not ask for, such as extra parameters, caching, or automatic outlier removal.",
          ],
        },
        {
          type: "prompt",
          title: "Explain a change before you accept it",
          prompt: `Here is a diff you produced. For each changed function:

1. Summarise in plain language what it now does differently.
2. List every way it can change, drop, fill, or reorder data values.
3. List every numeric constant and where its value came from.
4. List any behaviour that was not part of my request.
5. Name the tests that exercise this change, or say that none do.

Be specific and quote the relevant lines. Do not modify any code.

<paste the output of git diff>`,
        },
      ],
    },
    {
      id: "security",
      title: "Security basics for research code",
      blocks: [
        {
          type: "paragraph",
          text: "Research code often handles credentials for cloud storage or instruments, and sometimes sensitive data. A few habits prevent the most common problems.",
        },
        {
          type: "list",
          items: [
            "Keep secrets out of code. Read API keys and passwords from environment variables, keep local `.env` files out of version control with `.gitignore`, and never paste a secret into a prompt.",
            "Check your institution's policy before sharing unpublished data, human-subjects data, or proprietary code with an AI service.",
            "Do not load untrusted files with `pickle.load`, or with other loaders built on pickle: unpickling can execute arbitrary code. Prefer formats such as CSV, Parquet, HDF5, or NPY without object arrays.",
            "Use `yaml.safe_load`, not `yaml.load` with an unsafe loader, for configuration files.",
            "Avoid `eval`, `exec`, and `subprocess` calls with `shell=True` on any input you did not write yourself. Pass command arguments as a list instead.",
          ],
        },
        {
          type: "code",
          language: "python",
          title: "Secrets from the environment",
          code: `import os

api_token = os.environ.get("INSTRUMENT_API_TOKEN")
if api_token is None:
    raise RuntimeError(
        "Set INSTRUMENT_API_TOKEN in your environment; see README.md."
    )`,
        },
      ],
    },
    {
      id: "dependencies",
      title: "Verify every new dependency",
      blocks: [
        {
          type: "paragraph",
          text: "Assistants sometimes suggest packages that do not exist, or names that are close to a popular package. Attackers can register such names on package indexes and publish malicious code under them. Before adding a dependency:",
        },
        {
          type: "list",
          ordered: true,
          items: [
            "Confirm the package exists on PyPI and that its project page links to the source repository you expect.",
            "Check that it is maintained and widely used, or that you have a specific reason to trust it.",
            "Ask whether the standard library or an existing dependency already does the job.",
            "Add it with `uv add` so it is recorded in `pyproject.toml` and pinned in `uv.lock`.",
          ],
        },
      ],
    },
    {
      id: "automation",
      title: "Let tools catch what they can",
      blocks: [
        {
          type: "paragraph",
          text: "Automated checks do not replace reading the code, but they catch many problems cheaply. Ruff can lint, format, and flag common security issues through its `S` rule set, which is derived from the Bandit project.",
        },
        {
          type: "code",
          language: "bash",
          title: "terminal",
          code: `uv run ruff check .                # lint for likely bugs and style issues
uv run ruff check . --select S     # security-focused rules
uv run ruff format --check .       # verify consistent formatting
uv run pytest                      # your scientific tests`,
        },
      ],
    },
    {
      id: "checklist",
      title: "Checklist",
      blocks: [
        {
          type: "checklist",
          title: "Before you accept an AI-generated change",
          items: [
            "The change does one thing, and you asked for that thing.",
            "You read every changed line, including tests and configuration.",
            "Any dropped, filled, clipped, or reordered data has a reason you agree with.",
            "Every new constant has a comment or source.",
            "No secrets, absolute paths, or personal data were added.",
            "No untrusted input reaches `pickle`, `eval`, or a shell.",
            "Every new dependency was verified and added with `uv add`.",
            "Linting and tests pass, and the commit message explains the change.",
          ],
        },
      ],
    },
  ],
};
