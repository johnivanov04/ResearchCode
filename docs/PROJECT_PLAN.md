# ResearchCode Project Plan

ResearchCode is an open-source educational website and practical toolkit that helps
scientists with limited software engineering experience use AI coding assistants to
build correct, secure, maintainable, and reproducible research software.

Core message: AI makes software easier to generate, but scientific correctness and
engineering rigor remain essential.

Context: Caltech CS/EE 143 special project.

## 1. Repository state at start

The repository was an empty Git repository on `main` with no commits. Everything below
is new. No existing history or files had to be preserved beyond `.git/`.

## 2. Architecture

```
ResearchCode/
├── web/                  Next.js website (Phase 1)
├── scientific-starter/   Python starter template (Phase 2)
├── growth-analysis/      Bacterial growth-curve analysis application (Phase 3)
├── experiments/          Experiment protocol, tasks, raw results (Phase 4, not yet created)
├── docs/                 Design docs, methodology, plans
├── .github/workflows/    CI
├── CLAUDE.md             Persistent agent instructions
└── README.md             Overview and setup
```

### 2.1 Website (`web/`)

| Concern       | Decision                                                                 |
| ------------- | ------------------------------------------------------------------------ |
| Framework     | Next.js (App Router), TypeScript strict mode                             |
| Styling       | Tailwind CSS v4 with a small set of design tokens in `globals.css`       |
| Rendering     | Every page is statically prerendered; no server runtime required         |
| Content       | Guides are typed TypeScript data modules in `web/src/content/`           |
| Fonts         | `next/font` (self-hosted at build time, no runtime third-party requests) |
| Tests         | Vitest + React Testing Library + jsdom for rendering and navigation      |
| Lint          | ESLint flat config from `eslint-config-next` (core-web-vitals + TS)      |
| Deployment    | Vercel (target only; not deployed in Phase 1)                            |
| Backend/Auth  | None. No database, no API keys, no paid services                         |

**Why typed content modules instead of MDX?** The guides need structured elements
(checklists, copyable prompts, callouts, code samples) rendered by consistent
components. Typed data gives compile-time checking of every guide, needs no MDX
toolchain, and keeps contributions reviewable. If guides grow to dozens of long
prose documents, migrating to MDX is straightforward because the section model maps
directly onto MDX components.

**Why Vitest rather than Playwright for Phase 1?** Rendering and navigation
correctness can be verified quickly at the component level without downloading
browsers. End-to-end browser tests are a reasonable Phase 5 addition.

### 2.2 Information architecture

| Route                   | Purpose                                                             |
| ----------------------- | ------------------------------------------------------------------- |
| `/`                     | Headline, the reliability problem, audience, workflow diagram       |
| `/guides`               | Index of guides                                                     |
| `/guides/[slug]`        | Individual guide (statically generated from content modules)        |
| `/starter-kit`          | The Python starter: contents, setup, copy instructions, limits      |
| `/example`              | Growth-rate task, pitfalls, and the working growth-analysis app     |
| `/evaluation`           | Proposed vibe-coding vs structured-workflow study; no results yet   |
| `/about`                | Academic context, mission, roadmap                                  |

## 3. Milestones

### Phase 1 — Website and foundation (status: complete)
- Project plan, README, CLAUDE.md
- Next.js site with six sections and three substantial guides
- Accessibility basics: semantic landmarks, skip link, focus styles, labelled nav,
  sufficient contrast, reduced-motion respect
- Metadata per page, `not-found` and `error` states. No route-level `loading.tsx`: every
  page is prerendered, and a root loading boundary would ship content hidden behind a
  client-side Suspense swap (invisible without JavaScript). Empty states are used where
  content lists could be empty (guides index, evaluation results).
- Root layout exports `ensureStatic = "navigation"` so the build fails if any page
  becomes request-time rendered.
- Component tests for rendering and navigation
- CI workflow running lint, typecheck, tests, build

### Phase 2 — Scientific Python starter kit (status: complete, merged in PR #1)

A self-contained, copyable Python project in `scientific-starter/`. It has no runtime
dependencies, works independently of the website, and lives in this monorepo as a folder
(not a separate GitHub template repository).

| Concern | Decision and reasoning |
| ------- | ---------------------- |
| Packaging | uv with `uv_build` backend, `src/scientific_starter/`, `pyproject.toml`, committed `uv.lock`, `.python-version` 3.12, `requires-python >=3.12`. `uv_build` is uv's default backend; it requires the package folder to match the project name, which the README's rename steps explain. |
| Runtime dependencies | None. The example and the metadata helper need only the standard library; researchers add NumPy and others with `uv add`. |
| Dev dependencies | pytest, Hypothesis, Ruff (dependency group `dev`). |
| Tests | Known-answer, edge-case, invalid-input, Hypothesis property tests, numerical accuracy against a 50-digit `decimal` reference, doctests. pytest runs with warnings as errors and strict config/markers. Hypothesis profiles: `dev` (200 examples) and `ci` (2000). |
| Lint | Ruff rule groups E, W, F, I, B, A, S, UP, SIM, C4, PT, N, DTZ, PTH, NPY, PGH, T10, RUF; `S101` allowed in tests only. |
| Example | `growth.py`: `specific_growth_rate(od1, od2, t1_h, t2_h)` and `doubling_time(rate_per_h)`, specified in `docs/spec-growth-rate.md`. Zero growth returns exactly 0.0 and an infinite doubling time; negative rates are returned, and their doubling time raises `ValueError`. `ln(od2/od1)` uses `log1p` within a factor of two and a difference of logs otherwise, after a property test showed that the naive formula reports zero growth for adjacent large floats. |
| Provenance | `provenance.py`: `write_run_metadata` writes `run_metadata.json` with Python/package versions, `uv.lock` checksum, git commit and dirty flag, seed, parameters, and input file name/size/SHA-256. It omits host names, user names, absolute paths, environment variables, and remote URLs, rejects credential-like parameter names, and refuses to overwrite. |
| Entry point | `cli.py`: reads a two-row CSV, validates it, writes `result.json` and run metadata; refuses to overwrite without `--overwrite`. |
| Docs | `README.md`, `AGENTS.md` (rules for any assistant), `CLAUDE.md` (imports `AGENTS.md`), `.claude/settings.json` (attribution off), `docs/SPEC_TEMPLATE.md`, `docs/spec-growth-rate.md`, `docs/SECURITY_CHECKLIST.md`. |
| CI | `.github/workflows/starter.yml` (monorepo): copies the starter out of the repository, then on Python 3.12 and 3.13 runs `uv sync --locked`, `ruff check`, `ruff format --check`, `pytest`, `uv build`, and an isolated install-and-import of the wheel. `scientific-starter/.github/workflows/ci.yml` runs the same checks once a copy is a repository root. `web.yml` also triggers on `scientific-starter/**` because website tests read it. |
| Website | `/starter-kit` rewritten from `web/src/content/starter-kit.ts`; `starter-kit.test.ts` checks every listed path exists and every shown command appears in the starter README. Home toolkit card and About roadmap marked Available. |

Phase 2 milestones:
1. Python foundation: packaging, lock file, Ruff and pytest configuration.
2. Growth example with specification and full test suite; mutation check that tests catch
   injected bugs.
3. Run metadata helper and command-line entry point with tests.
4. AI assistant instructions, specification template, security checklist, README.
5. CI for the monorepo and for standalone copies.
6. Website integration and documentation updates.

Phase 2 acceptance criteria:
1. From a fresh copy of `scientific-starter/` outside the monorepo: `uv sync --locked`,
   `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, and `uv build`
   all succeed, and the built wheel installs and imports in an isolated environment.
2. The known-answer case OD 0.1 → 0.2 over 0–2 h gives μ ≈ 0.34657359 /h and Td ≈ 2 h.
3. Tests cover known answers, boundaries and invalid input (non-positive OD, NaN, ±inf,
   non-increasing time, wrong types), zero and negative growth, Hypothesis properties, and
   floating-point accuracy.
4. At least one deliberately introduced bug is caught by the tests, and the correct
   implementation is restored.
5. Ruff includes the `S` security rules; the security checklist states that automated
   checks cannot guarantee security.
6. `AGENTS.md`/`CLAUDE.md` cover the ten assistant rules and the no-AI-attribution policy.
7. Run metadata contains no host name, user name, absolute path, or credential.
8. The website's starter-kit page lists only implemented features, explains that the
   starter is a monorepo folder, and is verified against the files by tests.
9. All Phase 1 website checks still pass.

### Phase 3 — Scientific demonstration (status: in progress; implemented on `feat/phase-3-scientific-demo`, awaiting review)

A complete bacterial growth-curve analysis application in `growth-analysis/`, created from a
copy of `scientific-starter/` to demonstrate how a researcher uses the starter kit. It is a
self-contained uv project, independent of the website and of the starter folder.

| Concern | Decision and reasoning |
| ------- | ---------------------- |
| Location | `growth-analysis/` in the monorepo (package `growth_analysis`, command `growth-analyze`). The starter is unchanged. |
| Dependencies | NumPy and Matplotlib (added with `uv add`). Pandas was not added: the standard `csv` module gives line-level control over validation. No SciPy: no model fitting or hypothesis tests are needed. |
| Input | Long-format CSV: `well`, `condition`, `od600`, and exactly one of `time_h`/`time_min`/`time_s` (the unit is part of the column name). Blank wells use the condition `blank`. Every problem (missing values, non-numbers, NaN/inf, duplicates, unsorted times, conflicting conditions, wrong field counts) is reported with its line number; nothing is dropped. |
| Blank and limit | Mean of blank wells subtracted. Quantification limit max(0.005, 10 × blank SD); readings below it are excluded with a recorded reason. |
| Method | Least-squares slopes of ln(OD) in five-reading windows; start at the steepest window and extend over neighbouring windows with slope ≥ 0.8 × steepest; one least-squares fit over the whole region gives μ, SE(μ), R²; Td = ln 2 / μ. Statuses `growth`, `no_growth`, `decline`, `insufficient_data`; `growth` is credible only with R² ≥ 0.98, SE/μ ≤ 0.10, and no excluded reading inside the phase. |
| Why this method | A design study (`growth-analysis/docs/method-study.md`, reproducible with `scripts/method_study.py`) showed the steepest-window method used in the guide overestimates μ by about 3–16% on noisy data, and that a 3-SD blank threshold biased estimates upward. Both findings changed the method; the specification records why. The study also measures a remaining upward bias (about 7%) for slow growth near the quantification limit, documented as a known limitation. All validation is on synthetic data. |
| Outputs | `well_results.csv`, `condition_summary.csv`, `points.csv`, `results.json`, figures (growth curves, per-well fits, comparison by condition; PNG and SVG), `run_metadata.json` (starter's `provenance.py`). Nothing is overwritten without `--overwrite`, checked before writing anything. |
| Validation | Known answers from mathematics (exact exponential data; the logistic derivative bound r(1 − x_end/K) ≤ μ ≤ r(1 − x_start/K); rounding error bound for the website's curve); seeded noise; a bias study; Hypothesis invariances; exact rational least squares; end-to-end CLI tests; regression tests against committed example outputs; deliberately introduced bugs. |
| Data | Synthetic only, generated with fixed seeds by `synthetic.py` and labelled synthetic everywhere: a 12-well sample plate and the website's illustrative well (checked to match `web/src/lib/growth.ts`). |
| CI | `.github/workflows/growth-analysis.yml` copies the project out of the monorepo and on Python 3.12 and 3.13 runs `uv sync --locked`, Ruff, pytest (2000 Hypothesis examples), `uv build`, the wheel's command, the documented CLI on the sample data, output-file checks, an overwrite-refusal check, and a byte-identical rerun check. `web.yml` also triggers on `growth-analysis/**`. |
| Website | `/example` presents the application (status Available), its method, real committed outputs and figures, setup and usage, and how the starter kit shaped it. `web/src/content/growth-analysis.ts` holds every displayed fact; `growth-analysis.test.ts` checks numbers, paths, commands, and figures against the application's files. |

Phase 3 milestones:
1. Specification (`docs/spec-growth-curve.md`) from the starter's template.
2. Input validation, blank correction, exponential-phase detection, credibility, condition summaries.
3. Plots and the command-line tool, with provenance and no-overwrite safety.
4. Design study of the method's defaults on synthetic data; method revised where it found bias.
5. Validation tests, property tests, end-to-end and regression tests; deliberate-bug check.
6. Documentation, CI, and website integration.

Phase 3 acceptance criteria:
1. From a fresh copy of `growth-analysis/`: `uv sync --locked`, `uv run pytest`, `uv run ruff check .`,
   `uv run ruff format --check .`, and `uv build` succeed on Python 3.12 and 3.13, and the built
   wheel's `growth-analyze` command runs.
2. `uv run growth-analyze --input data/sample/synthetic_plate.csv --output results/sample` writes every
   documented output, refuses to overwrite, and reruns byte-identically.
3. Exact exponential data give μ to 1e-9 relative; logistic data obey the derivative bound and never
   exceed r; the website's curve satisfies the bound widened by its rounding error; the mean bias over
   200 noisy curves is under 2% and smaller than the steepest window's.
4. Zero growth, decline, stationary phase, too few readings, readings below the limit, and invalid,
   missing, or duplicated measurements each have tests with specified behaviour.
5. At least one deliberately introduced bug is caught, and the correct code is restored.
6. Run metadata records versions, settings, assumptions, input checksums, and the Git state, with no
   host names, user names, or absolute paths.
7. All sample data are labelled synthetic; no result is presented as an experimental finding.
8. `/example` shows the application as Available only because the above pass, links to the source,
   and is verified against the application's files by tests; all existing website and starter checks
   still pass.

### Phase 4 — Controlled experiment
- Pre-registered protocol in `experiments/` before any data collection
- Tasks, rubrics, hidden test suites, scoring scripts
- Results published on `/evaluation` only after collection and analysis

### Phase 5 — Deployment and polish
- Vercel deployment (with approval), custom domain if available
- End-to-end tests, accessibility audit (axe / Lighthouse), content review

## 4. Phase 1 acceptance criteria

1. `npm run lint`, `npx tsc --noEmit`, `npm test`, and `npm run build` pass in `web/`.
2. All six top-level routes and every guide route render and are statically generated.
3. Primary navigation works on desktop and mobile; current page is indicated with
   `aria-current`.
4. At least three guides, each with actionable checklists and copyable prompts.
5. No download button or link points to an artifact that does not exist.
6. Every sample dataset is explicitly labelled illustrative.
7. The evaluation page contains methodology and planned metrics only — no results.
8. The about page contains no invented people, endorsements, or affiliations beyond
   the stated course context.
9. No secrets, no paid APIs, no runtime backend.

## 5. Important design decisions and principles

- **Honesty over polish.** Planned components are labelled "Planned"; illustrative
  data is labelled "Illustrative"; there are no fabricated results or testimonials.
- **Restrained visual design.** Light background, navy for structure, teal for
  accents and interactive states, no decorative gradients or emoji.
- **Static first.** Static pages are fast, cheap to host, and easy to archive.
- **Minimal dependencies.** Anything added must have a clear purpose.
- **Accessible by default.** WCAG 2.1 AA contrast targets, keyboard-operable
  controls, semantic headings in order.
- **Client components only where needed** (mobile menu, copy-to-clipboard buttons,
  active-link highlighting, error boundary).

## 6. Open questions for later phases

- Final experiment design parameters (participants, tasks, blinding) — to be fixed
  in a pre-registration document before Phase 4.
- Licensing: code under MIT is assumed for the template; content license (e.g.
  CC BY 4.0) to be confirmed with the course instructor.
- Hosting domain and repository visibility.
