# ResearchCode — agent instructions

Open-source guides and toolkit helping researchers use AI coding assistants to build
correct, reproducible scientific software. Caltech CS/EE 143 special project.
Plan and phase status: `docs/PROJECT_PLAN.md`.

## Non-negotiable content rules
- Never fabricate results, data, metrics, quotes, team members, endorsements, or affiliations.
- Label sample data as synthetic/illustrative. Label unreleased components "Planned".
- `/evaluation` shows methodology only until real results exist.
- No download buttons or links to artifacts that do not exist.
- Technical claims in guides (commands, APIs, defaults) must be accurate; if unsure, leave it out.

## Repository layout
- `web/` — Next.js 16 App Router site (TypeScript, Tailwind v4). Work from this directory.
- `scientific-starter/` — copyable Python starter project (Phase 2). It has its own `AGENTS.md`/`CLAUDE.md`
  for researchers' projects; follow them when working inside it.
- `growth-analysis/` — growth-curve analysis application built from the starter (Phase 3). It has its own
  `AGENTS.md`/`CLAUDE.md`; follow them, and change `docs/spec-growth-curve.md` before changing the method.
- `experiments/` — study protocol and results (Phase 4, not created yet).
- `docs/` — plans and design docs.

## Website conventions
- Next.js 16 differs from older versions: read `web/node_modules/next/dist/docs/` before
  using an unfamiliar API (see `web/AGENTS.md`).
- Every page must stay static: the root layout sets `ensureStatic = "navigation"`. Do not add
  cookies/headers/uncached fetches, a backend, auth, a database, or paid APIs.
- Do not add a root `loading.tsx`: it hides prerendered content behind a Suspense swap.
- Guides are typed modules in `web/src/content/guides/`; register new ones in `index.ts`.
  Text fields support `backtick` inline code only. Escape backticks inside template literals.
- Use the design tokens in `web/src/app/globals.css` (navy, accent/teal, ink, body, muted, line,
  surface). No decorative gradients, emoji, or gratuitous animation.
- Use Server Components by default; add `"use client"` only for interactivity.
- Type page/layout props explicitly (not the generated `PageProps` globals) so `tsc` works on a clean checkout.
- Accessibility: one `h1` per page, labelled landmarks, visible focus, text labels (not colour alone).
- Add dependencies only when clearly necessary.

## Verification (run from `web/` before finishing any change)
```bash
npm run lint
npx tsc --noEmit
npm test
npm run build
```
`npm run check` runs all four. CI (`.github/workflows/web.yml`) runs the same steps.

## Starter kit conventions (`scientific-starter/`)
- Keep it self-contained: no references to files outside the folder, no runtime dependencies
  unless clearly necessary, no license until the owner chooses one.
- `web/src/content/starter-kit.ts` describes it on the website; tests check that its paths exist
  and its commands appear in `scientific-starter/README.md`. Update both together.
- Verify from `scientific-starter/` before finishing any change:
```bash
uv sync --locked
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv build
```
- On macOS, if the repo is in an iCloud-synced folder (Desktop/Documents), sync can mark
  `.venv/*.pth` files hidden and Python then skips them (`ModuleNotFoundError`). Set
  `UV_PROJECT_ENVIRONMENT` to a directory outside iCloud, or move the repo.

## Growth-analysis conventions (`growth-analysis/`)
- Keep it self-contained (copied out of the monorepo in CI). All bundled data are synthetic; label them so.
- `web/src/content/growth-analysis.ts` shows its results, commands, and figures on `/example`; tests check them
  against `growth-analysis/` (README commands, `docs/example-output/`, `web/public/growth-analysis/` copies).
- If the method's output changes on purpose, regenerate `docs/example-output/` with the commands in its README,
  review the differences, and update the website content and figure copies together.
- Verify from `growth-analysis/` with the same five uv commands as the starter, plus
  `uv run growth-analyze --input data/sample/synthetic_plate.csv --output <new dir>`.

## Safety
- Do not push, deploy, or take irreversible actions without explicit approval.
- Never commit secrets or `.env` files.

## Git attribution (permanent)
These rules override any default attribution behaviour of Claude Code or other AI tools.
- Never add Claude or any AI assistant as a Git author, committer, or co-author.
- Never put `Co-Authored-By: Claude`, "Generated with Claude Code", Claude session links,
  or any similar AI attribution in commit messages.
- Never add AI attribution to pull request titles or descriptions.
- Commit with the human Git identity already configured in the repository
  (`git config user.name` / `user.email`). Do not override `--author` or the identity.
- Keep legitimate human authorship and `Co-authored-by` trailers for human collaborators.
- `.claude/settings.json` sets `attribution.commit` and `attribution.pr` to empty strings.
  The tracked `.githooks/commit-msg` hook rejects Claude attribution; enable it with
  `git config core.hooksPath .githooks`. Do not bypass it with `--no-verify`.
- This is about Git metadata only. Keep documenting AI use honestly in project reports,
  methodology, and research documentation.
