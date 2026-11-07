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
├── scientific-starter/   Python starter template (Phase 2, not yet created)
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
| `/starter-kit`          | Planned Python template; explicit planned vs available status       |
| `/example`              | Bacterial growth analysis as a representative task; pitfalls        |
| `/evaluation`           | Proposed vibe-coding vs structured-workflow study; no results yet   |
| `/about`                | Academic context, mission, roadmap                                  |

## 3. Milestones

### Phase 1 — Website and foundation (this phase)
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

### Phase 2 — Scientific Python starter kit
- `scientific-starter/` template: uv, Python 3.12+, pytest, Ruff, GitHub Actions
- AI-assistant instruction file, specification template, README template
- Starter kit page updated from "planned" to "available" per component

### Phase 3 — Scientific demonstration
- Bacterial growth curve analysis built with the starter kit
- Validation against analytically known synthetic curves; documented assumptions
- Example page links to real code and real outputs

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
