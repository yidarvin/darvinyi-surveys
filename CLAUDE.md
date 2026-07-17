# CLAUDE.md

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

## The intake workflow -- how to ask for a new survey

**Just describe the survey topic.** Do not name a field, a slug, or a file path
-- deduce all of that. For example, if I say:

> "I want a survey on LLM and agent benchmarks and evaluations."

do this, without further prompting:

1. **Interpret the need.** Identify the subfield to survey and its 2-4 driving
   problems (the `survey-and-taxonomy-research` skill formalizes exact scope in
   its own Phase 1 -- this step is just enough to pick a field and a title).
2. **Deduce the field.** Read `content/registry.json`. If an existing field
   clearly fits, use it. If none does, create a new one (needs a slug, a display
   name, a one-line blurb, and an original SVG emblem -- `new_topic.py` generates
   the emblem automatically). **State the placement decision in one line** ("Placing
   this under a new field *Artificial Intelligence*" / "under existing field
   *AI*"). Only pause to ask if genuinely ambiguous; otherwise proceed. I can
   always override afterward ("put it under Pathology instead").
3. **Deduce the topic.** Derive a slug, title, and blurb from the request. Stamp
   both files:
   ```
   python3 scripts/new_topic.py --field <f> --topic <t> --title "<T>" \
     [--blurb "..."] [--field-name "<N>" --field-blurb "..." if the field is new]
   ```
4. **Build** (Sonnet, effort high -- see Models below). Run the
   `survey-and-taxonomy-research` skill with output dir
   `content/surveys/<f>/<t>/`, targeting **100+ papers** (fewer only with an
   explicit, convincing justification that the subfield is genuinely small --
   the critic checks this). Its own Phase 8 gates must pass. Then:
   ```
   python3 scripts/mark.py <f>/<t> draft
   ```
   Commit `build: <f>/<t>`.
5. **Critique -> resolve -> approve** (Opus, effort high -- see Models below and
   `prompts/critique-rubric.md`). Loop build-critique automatically: spawn the
   critic as an independent subagent with no memory of the build, judge against
   the rubric, write `content/critiques/<f>__<t>.md`. On `revise`, the builder
   (Sonnet) fixes REQUIRED findings and the critic re-reviews. On `approve`, the
   critic runs `python3 scripts/mark.py <f>/<t> done` and sets `corpusSize` in
   the registry from `corpus.json`. This loop is what "done" means here -- do
   not skip straight to `mark.py ... done` yourself.
6. **Report** what was built: the field decision, corpus size, critique rounds,
   any open advisories. Do not push or deploy unless I ask (see House rules).
   Leave me to review with `npm run dev`.

### By-hand verbs (for power use, once fields/topics exist)

- **"queue status"** -- run `python3 scripts/decide.py status`, report it.
- **"critique <field>/<topic>"** -- run the critique step alone on a `draft` topic.
- **"resolve critiques"** -- work every `content/critiques/*.md` with line 1
  `verdict: revise`, in queue order.
- **"rebuild <field>/<topic>"** -- rerun the survey skill on an existing topic,
  `mark.py ... draft`, and set the existing critique file's line 1 to
  `verdict: resolved` with a dated `## Rebuild note` (never truncate it).
- **"add a field <name>"** -- create an empty field (no topics) via
  `new_topic.py`'s field-creation path, or by hand in `content/registry.json` +
  a generated emblem.
- **"reprioritize"** -- reorder rows in `prompts/queue.md`, mirror the order in
  `content/registry.json`, run `npm run validate`.

## Models and effort

Builder and critic are different roles and should run as different agents, so
the critique is genuine fresh-eyes review rather than the builder grading its
own work:

- **Builder** (research, corpus assembly, writing `survey.md`, deriving the
  taxonomy, resolving REQUIRED critique findings) -- **Sonnet**, effort **high**.
  This is execution: following the survey skill's phases and gates precisely.
- **Critic** (judging corpus adequacy, taxonomy validity, and above all
  synthesis quality) -- **Opus**, effort **high**. Judgment work benefits from
  the stronger model; spawn it as its own subagent (e.g. the Agent tool with
  `model: "opus"`) so it reviews only the artifacts on disk, not the
  conversation that built them.
- Any other agentic step (field-placement deduction, corpus discovery fan-out)
  defaults to Sonnet at effort high unless it is itself a judgment/critique
  step, in which case it is Opus.

Full detail: `prompts/critique-rubric.md`.

## Where things live in this repo

- `content/registry.json` -- the database: ordered fields, each with ordered
  topics (`slug`, `title`, `blurb`, `hero`, `status`, `corpusSize`).
- `content/surveys/<field>/<topic>/` -- one survey's native output from the
  `survey-and-taxonomy-research` skill: `survey.md`, `corpus.json`,
  `figures.json`, `figures/` (including `taxonomy.svg`, used as that topic's
  card art -- see the licensing rule below).
- `content/critiques/<field>__<topic>.md` -- append-only critic verdict file.
  Line 1 is the machine-read verdict (`approve` | `revise` | `resolved`).
- `prompts/queue.md` -- the ordered build queue (`field | topic | title | status`).
- `prompts/critique-rubric.md` -- the survey-specific critic bar (REQUIRED vs
  ADVISORY) and the model guidance above.
- `public/fields/<field>.svg` -- original field emblems, generated by
  `scripts/new_topic.py` when a field is created.
- `src/lib/fields.ts` / `src/lib/surveys.ts` -- typed registry access and the
  lazy `import.meta.glob` loaders for each survey's markdown/corpus.
- `src/pages/` -- `FieldsHome` ("/"), `FieldPage` ("/:field"), `SurveyPage`
  ("/:field/:topic", the survey renderer with an in-page TOC sidebar).
- `src/styles/tokens.css` -- the running house style (shared with the other
  darvinyi sites). Treat it as source of truth; do not restyle.
- `scripts/` -- `new_topic.py`, `validate.py`, `mark.py`, `decide.py`,
  `sync_figures.mjs` (copies `content/surveys/**/figures` to `public/` for
  `<img>` to resolve), `sitemap.mjs`, `check.sh`, plus vendored copies of the
  survey skill's own `corpus_manifest.py` / `figure_manifest.py` (so `npm run
  check` works in CI without the user's global `~/.claude/skills/`).

## Licensing rule for graphics

Field and topic card art must always be **original artwork**, never an extracted
paper figure. A topic's card uses its own `figures/taxonomy.svg` (the survey
skill labels this "Original figure, this survey" -- zero licensing question). A
field's card uses a generated SVG emblem. Extracted *paper* figures only ever
appear inside a survey's body prose, under the skill's own scholarly-commentary
and per-paper license-check rules -- never promoted to a landing card.

## House rules

- The scaffold ships empty on purpose. Never hand-seed fields or topics outside
  the intake workflow above.
- Never auto-commit to `main` and push, and never deploy, unless I say so. End
  each run with a summary and let me review with `npm run dev`.
- `npm run check` is the mechanical half of done (validate + tests + build +
  per-topic survey gates). An independent critic approval is the other half --
  see the intake workflow. A topic is never marked `done` by the builder.
- `python3 scripts/validate.py` (or `npm run validate`) enforces that a `done`
  topic has an approving critique on file; `mark.py` refuses and rolls back
  otherwise.
