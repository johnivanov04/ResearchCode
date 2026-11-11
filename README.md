# ResearchCode

**Build research software with AI. Trust the results.**

ResearchCode is an open-source educational website and practical toolkit that helps scientists
with limited software engineering experience use AI coding assistants (Claude Code, ChatGPT,
GitHub Copilot, and others) to build research software that is correct, secure, maintainable, and
reproducible.

It is being developed as a Caltech CS/EE 143 special project. It is not an official Caltech
publication or service.

## Project status

| Phase | Scope                                                        | Status      |
| ----- | ------------------------------------------------------------ | ----------- |
| 1     | Website and project foundation                               | Implemented |
| 2     | Scientific Python starter kit (uv, pytest, Ruff, CI)         | Implemented |
| 3     | Worked bacterial growth analysis built with the starter kit  | In progress (implemented, in review) |
| 4     | Controlled comparison: unstructured vs structured AI coding  | Planned     |
| 5     | Deployment, documentation, and polish                        | Planned     |

See [docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md) for architecture, milestones, and acceptance criteria.

## Repository layout

```
.
├── web/                  Next.js website (App Router, TypeScript, Tailwind CSS)
│   ├── src/app/          Routes: /, /guides, /guides/[slug], /starter-kit, /example, /evaluation, /about
│   ├── src/components/   Shared UI (navigation, code and prompt blocks, checklists, chart)
│   ├── src/content/      Site config and guide content as typed TypeScript modules
│   └── src/lib/          Growth-rate calculations for the interactive example
├── scientific-starter/   Copyable scientific Python project (uv, pytest, Hypothesis, Ruff, CI)
├── growth-analysis/      Bacterial growth-curve analysis application built from the starter (Phase 3)
├── docs/                 Project plan and design documents
├── .github/workflows/    CI for the website (web.yml), the starter (starter.yml), and growth-analysis
├── CLAUDE.md             Instructions for AI coding assistants working in this repo
└── README.md
```

`experiments/` (Phase 4) will be added in a later phase.

## Scientific Python starter kit

`scientific-starter/` is a complete, independent Python project that researchers copy into
their own repository. It contains no runtime dependencies, a worked growth-rate example with
its specification and tests, a run-metadata helper, instructions for AI assistants, a
specification template, and a security checklist. See
[scientific-starter/README.md](scientific-starter/README.md) for setup and usage.

Requirements: [uv](https://docs.astral.sh/uv/getting-started/installation/) (it installs
Python 3.12 automatically). From `scientific-starter/`:

```bash
uv sync --locked             # install exact versions from uv.lock
uv run pytest                # tests (known-answer, edge-case, property-based, doctests)
uv run ruff check .          # lint, including security rules
uv run ruff format --check . # formatting
uv build                     # build wheel and source distribution into dist/
```

GitHub Actions (`.github/workflows/starter.yml`) copies the starter out of the monorepo and runs
these checks on Python 3.12 and 3.13 whenever files in `scientific-starter/` change.

## Growth-curve analysis (Phase 3)

`growth-analysis/` is a working command-line application, built from a copy of the starter
kit, that estimates specific growth rates and doubling times from multi-well optical density
time courses. It detects each well's exponential phase, fits ln(OD), judges whether each fit is
credible, plots every fit, summarises replicate wells by condition, and records run metadata.
All bundled data are synthetic. See [growth-analysis/README.md](growth-analysis/README.md) and
the method specification, [growth-analysis/docs/spec-growth-curve.md](growth-analysis/docs/spec-growth-curve.md).

From `growth-analysis/`:

```bash
uv sync --locked
uv run growth-analyze --input data/sample/synthetic_plate.csv --output results/sample
uv run pytest                # unit, validation, property-based, end-to-end, regression tests
uv run ruff check .
uv run ruff format --check .
uv build
```

GitHub Actions (`.github/workflows/growth-analysis.yml`) copies the project out of the monorepo,
runs these checks on Python 3.12 and 3.13, and runs the command on the sample data.

## Running the website locally

Requirements: Node.js 20.9 or later (Node.js 24 LTS recommended) and npm.

```bash
cd web
npm install
npm run dev
```

Then open <http://localhost:3000>.

To run the production build locally:

```bash
cd web
npm run build
npm start
```

The build downloads the IBM Plex fonts from Google Fonts once (via `next/font`), so it needs
network access. The deployed site serves the fonts itself and makes no third-party requests.

## Checks

All commands run from `web/`:

| Command              | What it does                                              |
| -------------------- | --------------------------------------------------------- |
| `npm run lint`       | ESLint with the Next.js core-web-vitals and TypeScript rules |
| `npx tsc --noEmit`   | TypeScript type check (also `npm run typecheck`)          |
| `npm test`           | Vitest + Testing Library: rendering, navigation, links, content, calculations |
| `npm run build`      | Production build; fails if any page stops being static    |
| `npm run check`      | All of the above, in order                                |

GitHub Actions runs the same checks on every push and pull request that touches `web/`,
`scientific-starter/`, or `growth-analysis/` (the website's tests verify that the starter-kit and
example pages match those directories' files, commands, results, and figures).

### Dependency audit

`npm audit --omit=dev` reports no vulnerabilities in the packages the site ships. The full
`npm audit` reports 8 moderate findings that all trace to one advisory,
[GHSA-g3hv-75wg-m249](https://github.com/advisories/GHSA-g3hv-75wg-m249) (`minimatch` >=7.0.0
<11.0.1, potential denial of service from crafted glob patterns). The affected copy is used only
by the TypeScript ESLint parser, during `npm run lint`, to match glob patterns from the project's
own lint configuration. It never receives untrusted input and is not part of the built site, so
there is no impact on visitors. `npm audit fix --force` would downgrade `eslint-config-next` to
15.x, which does not match Next.js 16, so it has not been applied. Revisit when
`typescript-eslint` updates its `minimatch` dependency.

## Contributing: Git hooks and attribution

After cloning, enable the repository's tracked Git hooks once:

```bash
git config core.hooksPath .githooks
```

The `commit-msg` hook rejects commit messages that credit Claude as a co-author or include
Claude Code or session attribution. `Co-authored-by` trailers for human collaborators are
unaffected. `.claude/settings.json` also turns off Claude Code's automatic commit and pull
request attribution. Use of AI tools is documented in the project's reports and methodology, not in Git
metadata. See the "Git attribution" section of `CLAUDE.md`.

## Adding a guide

1. Create `web/src/content/guides/<slug>.ts` exporting a `Guide` object (see `types.ts`).
2. Add it to the `guides` array in `web/src/content/guides/index.ts`.
3. Run `npm run check`. The content tests require every guide to have a checklist and at least
   one copyable prompt, and the page tests verify that all internal links resolve.

## Principles

- Never fabricate results, data, or endorsements. Sample data is labelled as illustrative and
  unreleased components are labelled as planned.
- Keep the site static, dependency-light, and accessible.

## License

To be confirmed before public release.
