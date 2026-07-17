# darvinyi surveys

A hub of living survey-and-taxonomy documents for scientific subfields, deployed
at [surveys.darvinyi.com](https://surveys.darvinyi.com). The site is organized
two levels deep:

- **Fields** (e.g. AI, Statistics, Pathology) -- the landing page, each a card
  with an original emblem.
- **Topics** within a field (e.g. "LLM & Agent Benchmarks and Evaluations") --
  each a full survey built from 100+ papers: a derived taxonomy, an evolution
  narrative, cross-cutting comparisons, and a sortable paper index.

The scaffold ships with **zero fields and zero topics**. New surveys are built
by describing what you want in plain language to Claude Code -- see
[`CLAUDE.md`](./CLAUDE.md) for the exact workflow.

## Stack

Vite 8, React 19, TypeScript, react-router, Tailwind bound to CSS-variable design
tokens (shared with the other darvinyi sites), self-hosted fonts. Survey prose is
plain GitHub-flavored markdown rendered at runtime with `react-markdown` +
`remark-gfm` + `rehype-slug` (not compiled, since it is generated content, not
hand-authored MDX). Static output, no backend.

## Quick start

```bash
npm install
npm run dev          # http://localhost:5173
npm run check        # the full gate: validate, test, build, per-topic survey gates, lint
```

Node 22.22+ or 24+ is required (see `.nvmrc`). The Python scripts need `python3`
(present on macOS and the Ubuntu CI runner). Vercel only runs `npm run build`.

## Commands

| Command             | What it does                                                              |
|----------------------|----------------------------------------------------------------------------|
| `npm run dev`        | Vite dev server (also syncs `content/surveys/**/figures` into `public/`). |
| `npm run build`      | Typecheck, sync figures, production build into `dist/`, write the sitemap. |
| `npm run check`      | The gate: validate, test, build, per-topic survey gates, lint. Definition of mechanical done. |
| `npm run validate`   | Cross-check the queue, the registry, and the survey files.                |
| `npm run test`       | Vitest: page rendering, the survey markdown/corpus loaders, heading ids.  |
| `npm run lint`       | ESLint (advisory in the gate).                                            |
| `npm run preview`    | Serve the production build locally.                                       |

Scaffolding and status changes go through the repo scripts, not by hand:

```bash
python3 scripts/new_topic.py --field ai --topic llm-benchmarks-evals \
  --title "LLM & Agent Benchmarks and Evaluations" \
  --field-name "Artificial Intelligence"   # only needed if the field is new
python3 scripts/mark.py ai/llm-benchmarks-evals draft
```

`new_topic.py` stamps the registry entry, the queue row, and (if the field is
new) an original SVG emblem at `public/fields/<field>.svg`. `mark.py` sets status
in both `content/registry.json` and `prompts/queue.md` at once and refuses,
rolling back, if the result would not validate -- a topic missing `survey.md`,
`corpus.json`, or a non-empty `figures/` cannot be marked `draft`, and `done`
additionally requires an approving critique file on disk. `done` is the critic's
move, never the builder's.

## Deploy

Push to GitHub, import to Vercel (framework preset **Vite**, output **dist**).
`vercel.json` already contains the SPA rewrite so deep links like `/ai/some-topic`
work. `content/registry.json`'s top-level `"url"` drives `dist/sitemap.xml`.

## How the pieces fit

A topic moves through three states: `pending` (not built), `draft` (built,
gate-passing, awaiting critique), `done` (critique-approved). Only the critic
grants `done`, by writing `content/critiques/<field>__<topic>.md` with first line
`verdict: approve`; `npm run validate` enforces that every `done` topic has one.

- `content/registry.json` -- the database: ordered fields, each with ordered
  topics and their status, plus the site `title`, `subtitle`, and `url`.
- `content/surveys/<field>/<topic>/` -- one topic's survey, in the
  `survey-and-taxonomy-research` skill's own output shape: `survey.md`,
  `corpus.json`, `figures.json`, `figures/`.
- `prompts/queue.md` -- the build queue (`field | topic | title | status`). Must
  agree with the registry; `npm run validate` checks that.
- `prompts/critique-rubric.md` -- the survey-specific critic bar (corpus
  adequacy, taxonomy quality, and above all higher-level synthesis) plus the
  builder/critic model guidance.
- `content/critiques/<field>__<topic>.md` -- append-only critique history: line
  1 is the current verdict, everything below is a round-by-round record.
- `src/lib/fields.ts` / `src/lib/surveys.ts` -- typed registry access and the
  lazy loaders for each survey's markdown/corpus/figures.
- `src/pages/` -- `FieldsHome` ("/"), `FieldPage` ("/:field"), `SurveyPage`
  ("/:field/:topic").
- `src/styles/tokens.css` -- the house style, shared across the darvinyi sites.
- `scripts/` -- `new_topic.py`, `validate.py`, `mark.py`, `decide.py`,
  `sync_figures.mjs`, `sitemap.mjs`, `check.sh`, plus vendored copies of the
  survey skill's `corpus_manifest.py` / `figure_manifest.py` so the gate is
  self-contained in CI.
- `.github/workflows/check.yml` runs `npm run check` on every push and pull request.

## Building a survey

Open Claude Code in this repo and describe what you want:

> "I want a survey on LLM and agent benchmarks and evaluations."

Claude Code deduces the field (creating one if none fits) and the topic, stamps
both files, builds with the `survey-and-taxonomy-research` skill, and runs the
build-critique loop to `done` -- reporting the field placement along the way so
you can redirect it. See `CLAUDE.md` for the full workflow, the by-hand verbs
("queue status", "critique <field>/<topic>", "resolve critiques", "rebuild
<field>/<topic>"), and the model guidance (builder: Sonnet; critic: Opus, for a
genuine fresh-eyes review).
