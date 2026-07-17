# AGENTS.md

**darvinyi surveys** (deployed at surveys.darvinyi.com) is a hub of living survey-
and-taxonomy documents, organized two levels deep: **fields** (e.g. AI, Statistics,
Pathology) each hold **topics** (e.g. "LLM & Agent Benchmarks and Evaluations"),
and each topic page is a full survey built from 100+ papers with a derived
taxonomy, an evolution narrative, and a sortable paper index. It is a Vite +
React + TypeScript site on Vercel. The scaffold ships with **zero fields and zero
topics** -- `content/registry.json` starts as `{ ..., "fields": [] }` -- and every
field/topic is created by the workflow below, on demand.

This repo intentionally does **not** use the `refsite-runner` skill's chapter/MDX
content model (a survey is a different shape than a book chapter). It reuses that
skill's design system and build-critique *doctrine* (separated builder/critic
roles, an append-only verdict file, a queue) but implements its own two-level
tooling in `scripts/`. Content itself comes from the **`survey-and-taxonomy-
research`** skill, whose native output (`survey.md` + `figures/` + `corpus.json`)
drops straight into `content/surveys/<field>/<topic>/`.

See `CLAUDE.md` for the full intake workflow, the by-hand verbs, the model/effort
guidance for the builder and critic roles, and the repo layout. That file is the
canonical version of these instructions; this file exists for agents that read
`AGENTS.md` specifically and should be kept in sync with it.

## House rules

- The scaffold ships empty on purpose. Never hand-seed fields or topics outside
  the intake workflow in `CLAUDE.md`.
- Never auto-commit to `main` and push, and never deploy, unless explicitly asked.
  End each run with a summary and leave review to `npm run dev`.
- `npm run check` is the mechanical half of done (validate + tests + build +
  per-topic survey gates). An independent critic approval is the other half. A
  topic is never marked `done` by the builder -- `python3 scripts/validate.py`
  enforces that `done` requires an approving critique file, and `mark.py`
  refuses and rolls back otherwise.
