# surveys.darvinyi.com — Scaffold Plan

A hub site that opens to **fields** (e.g. AI, Statistics, Pathology), each field links to
**topics**, and each topic page is a full **survey + taxonomy** of a subfield built from
100+ papers. Hosted on Vercel at `surveys.darvinyi.com`; source is a **public GitHub repo**
like the other darvinyi sites. New topics are built with Claude Code using the
`survey-and-taxonomy-research` skill, then approved by a **critic loop**.

This file is the implementation brief. Build it in the order under "Scaffold task list".
The scaffold ships **with no fields and no topics** — an empty, correct, deployable shell.
Fields and topics are created later, on demand, by the intake workflow in §9.

## Decisions (confirmed with the user)

1. **Render engine:** `react-markdown` + `remark-gfm` at runtime (not MDX-at-build).
2. **Critic loop:** **in scope.** Every topic goes builder → critic → done; done is granted
   by the critic, never taken by the builder (adapted from `refsite-runner` doctrine, §8).
3. **No seed content.** Registry ships with `fields: []`. No AI/Statistics/Pathology
   pre-seeded. The landing page renders a correct empty state.
4. **One long page per survey** with an in-page table-of-contents sidebar (no sub-routes).
5. **Intake is conversational.** The user just describes the survey need; Claude deduces the
   field (creating one if none fits), the topic slug/title, scaffolds it, builds, and
   critiques. The user does not hand-write paths or flags (§9).
6. **GitHub:** initialize a public repo under the same owner as the other sites and push the
   scaffold (§8, step 10).

---

## 1. Architecture decision (why this shape)

Two skills are in play, doing different jobs:

- **`refsite-runner`** owns the *web scaffold* and the *build/critic discipline*: the
  Vite + React + TS + Tailwind-token stack, the Vercel deploy, the `npm run check` gate, the
  queue/registry model, and the **builder → critic → done** loop. We reuse its
  infrastructure, design system, and loop doctrine so this site matches the other darvinyi
  sites. We do **not** reuse its flat *chapter* content model — this repo "ships its own
  domain pipeline," which that skill explicitly defers to ("the repo's contract wins").
- **`survey-and-taxonomy-research`** owns the *content of each topic*: it reads ≥25 (here we
  target **100+**) papers, extracts and attributes figures, derives a taxonomy, writes an
  evolution narrative, and emits **one markdown document + a `figures/` dir + `corpus.json` +
  `figures.json`**. That native output is exactly what a topic page renders. We keep its
  pipeline and its gates intact and add a rendering layer on top.

So: **template infra + refsite critic loop + a new two-level content contract + survey skill
as the topic engine.**

Rendering: the survey skill emits **plain GitHub-flavored markdown**, not MDX. Render it at
runtime with `react-markdown` + `remark-gfm` (tables) rather than pushing generated files
through the MDX build step — generated content is data, and keeping it out of the compile
step means a weird figure caption can never break the build. The one gotcha is image paths
(§4).

Quality has two halves per topic: (a) the survey skill's own Phase-8 gates (coverage
`--strict`, figure `check`, reference-resolution curl) are the **mechanical** half of
*draft*; (b) an independent **critic** pass is the other half of *done* (§8).

---

## 2. Final directory layout

```
darvinyi-surveys/
├── content/
│   ├── registry.json                 # NEW SHAPE: site meta + fields[] (starts EMPTY) — §3
│   ├── surveys/
│   │   └── <field>/<topic>/           # one dir per topic = survey skill's native output
│   │       ├── survey.md              # the survey document (rendered as the page body)
│   │       ├── corpus.json            # paper set → stats, paper table, taxonomy grouping
│   │       ├── figures.json           # figure manifest (attribution audit)
│   │       └── figures/               # taxonomy.svg, timeline.svg, extracted paper figs
│   └── critiques/
│       └── <field>__<topic>.md        # append-only critic verdict file (§8)
├── public/
│   ├── fields/<field>.svg             # original field-emblem art (generated on field create)
│   └── surveys/<field>/<topic>/figures/   # figures synced here so <img> resolves (§4)
├── prompts/
│   ├── queue.md                       # topic build queue (field/topic rows, PENDING/DONE)
│   ├── critique-rubric.md             # survey-specific critic rubric (§8)
│   └── notes/<field>__<topic>.md      # optional per-topic scope notes for a build run
├── scripts/
│   ├── new_topic.py                   # stamp a topic (+ create the field if it's new)
│   ├── validate.py                    # registry ↔ queue ↔ survey dirs ↔ critiques consistency
│   ├── mark.py                        # set a topic status (pending|draft|done|skipped)
│   ├── decide.py                      # queue-status dashboard (no writes)
│   ├── sync_figures.mjs               # copy content/**/figures → public/** (build prestep)
│   ├── sitemap.mjs                    # 3-level sitemap from published topics
│   └── check.sh                       # typecheck + build + validate + per-topic survey gates
├── src/
│   ├── App.tsx                        # 3-level router (§5)
│   ├── lib/
│   │   ├── fields.ts                  # typed access to registry.json (fields/topics)
│   │   └── surveys.ts                 # glob loaders: survey.md (?raw), corpus.json, figures
│   ├── pages/
│   │   ├── FieldsHome.tsx             # "/"              grid of field cards + graphics
│   │   ├── FieldPage.tsx              # "/:field"        grid of topic cards + graphics + status
│   │   ├── SurveyPage.tsx             # "/:field/:topic" the survey renderer (§4)
│   │   └── NotFound.tsx               # keep from template
│   ├── components/
│   │   ├── Layout.tsx                 # keep; adapt breadcrumb (Home / Field / Topic)
│   │   ├── FieldCard.tsx / TopicCard.tsx      # cards with graphic + blurb + status
│   │   ├── SurveyMarkdown.tsx         # react-markdown + remark-gfm + image URL rewrite
│   │   ├── PaperTable.tsx             # sortable/filterable table from corpus.json
│   │   ├── SurveyToc.tsx              # in-page section nav from survey.md headings
│   │   └── ScrollToTop.tsx / ErrorBoundary.tsx   # keep from template
│   └── styles/tokens.css, index.css   # keep template design tokens as-is
├── CLAUDE.md                          # documents the contract + the intake/critic commands
├── index.html · vercel.json · configs # from template, names/meta updated
```

Delete from the copied template: `src/chapters/**`, `src/pages/Chapter.tsx`,
`src/pages/Home.tsx`, `src/lib/chapters.ts`, `src/lib/registry.ts`, the demo
`content/critiques/how-this-book-is-built.md`, and the demo test
`src/test/chapters.test.tsx` (replace per §8-tests). Rewrite the Python scripts for the
two-level + survey model (§7); keep `check.sh`'s section-gated structure.

---

## 3. Content contract: `content/registry.json`

Two-level, ordered. Fields are ordered on the landing page; topics are ordered within a
field. `status` drives whether a topic card links or shows dimmed as "planned." **Ships
empty:**

```jsonc
{
  "title": "darvinyi surveys",
  "subtitle": "living surveys and taxonomies of scientific subfields",
  "url": "https://surveys.darvinyi.com",
  "fields": []
}
```

A field, once the intake workflow creates it, looks like:

```jsonc
{
  "slug": "ai",
  "name": "Artificial Intelligence",
  "blurb": "Benchmarks, training, and the systems around large models.",
  "graphic": "ai.svg",                 // public/fields/ai.svg — original emblem (§6)
  "topics": [
    {
      "slug": "llm-benchmarks-evals",
      "title": "LLM & Agent Benchmarks and Evaluations",
      "blurb": "How the field measures capability, and what the numbers miss.",
      "hero": "taxonomy.svg",          // topic card art = its taxonomy figure (§6)
      "status": "pending",             // pending | draft | done
      "corpusSize": null               // filled from corpus.json when built
    }
  ]
}
```

`src/lib/fields.ts` exposes typed `Field` / `Topic` interfaces and helpers: `fields`,
`fieldBySlug`, `topicBySlug(field, topic)`, `publishedTopics(field)`. All pages must handle
the **empty case** (no fields) and the **field-with-no-built-topics** case gracefully.

---

## 4. Survey rendering pipeline (`SurveyPage` + `src/lib/surveys.ts`)

`surveys.ts` uses Vite globs so each survey is bundled and lazily loaded:

```ts
const md   = import.meta.glob("../../content/surveys/**/survey.md",  { query: "?raw", import: "default" });
const meta = import.meta.glob("../../content/surveys/**/corpus.json", { import: "default" });
```

Key by `<field>/<topic>` parsed from the path. `SurveyPage` for `/:field/:topic`, a single
long page:

1. **Header** — title, blurb, at-a-glance stats from `corpus.json` (paper count, #subareas,
   year range). Breadcrumb: Home / Field / Topic.
2. **In-page TOC sidebar** (`<SurveyToc>`) — anchors derived from the `##`/`###` headings in
   `survey.md`; sticky on desktop, collapsible on mobile. This is the confirmed nav model.
3. **Taxonomy** — embed `figures/taxonomy.svg` (original figure, always safe to show).
4. **Body** — `<SurveyMarkdown>` renders `survey.md` (`react-markdown` + `remark-gfm`), with
   heading anchors matching the TOC.
5. **Paper index** — `<PaperTable>` from `corpus.json` (title, authors, year, venue,
   subarea, link); sortable + filter-by-subarea. The "summarize the papers" surface.

**Image-path gotcha (must handle):** `survey.md` references figures relatively
(`![...](figures/taxonomy.svg)`). Relative URLs resolve against the route, not the file, so
give `react-markdown` a `urlTransform` that rewrites a leading `figures/` to the topic's
public base `"/surveys/<field>/<topic>/figures/"` (feed the base in as a prop). Figures reach
`public/` via `scripts/sync_figures.mjs`, wired as `predev`/`prebuild`. Add deps:
`react-markdown`, `remark-gfm`.

---

## 5. Routing (`src/App.tsx`)

```
/                 → FieldsHome     (field cards, each with graphic + blurb; empty-state ok)
/:field           → FieldPage      (topic cards for that field, graphic + blurb + status)
/:field/:topic    → SurveyPage     (the survey renderer)
*                 → NotFound
```

Drop `MDXProvider` (no hand-written MDX remains). Keep `ScrollToTop`. `vercel.json`'s SPA
rewrite covers deep links. Topic cards with `status: "pending"` or `"draft"` render dimmed
and unlinked (draft = built, awaiting critic; not yet public).

---

## 6. Graphics & the licensing rule (important)

Every field card and topic card needs a graphic. **Card graphics must be original artwork,
never extracted paper figures.** Extracted paper figures live *inside* the survey body under
a recorded scholarly-commentary rationale (the survey skill enforces this); putting them on
landing cards is a different, decorative use with no license basis.

- **Topic card graphic** = that topic's **`figures/taxonomy.svg`** — original ("Original
  figure, this survey"), thematic, already produced by the survey skill. Zero licensing
  question. This is the "something from the survey" the brief asks for. Before build (topic
  `pending`), the card shows a neutral placeholder emblem.
- **Field card graphic** = a small **original SVG emblem** generated when the field is
  created, stored at `public/fields/<slug>.svg`.

Design tokens, fonts, and the dark/light system come straight from the template's
`src/styles/tokens.css` — do not restyle; match the other sites.

---

## 7. Tooling (rewrite the template's Python scripts for the two-level + survey model)

- **`new_topic.py --field <f> --topic <t> --title "<T>" [--blurb "…"] [--field-name "<N>"
  --field-blurb "…"]`** — add a `pending` topic under the field in `registry.json`, add a
  `PENDING` row to `queue.md`, create empty `content/surveys/<f>/<t>/`. **If the field slug
  does not exist, create the field entry too** (needs `--field-name`) and generate its
  `public/fields/<f>.svg` emblem. Idempotent.
- **`validate.py`** — invariants: every registry topic ↔ a queue row (same `<field>/<topic>`
  key, agreeing status, same order); every field slug unique; every `done` topic has
  `survey.md` + non-empty `figures/` + `corpus.json` **and** an approving critique file
  (`content/critiques/<field>__<topic>.md` line 1 `verdict: approve`); no orphan survey dirs;
  no `done` without critic approval. Exit nonzero on any breach.
- **`mark.py <field>/<topic> <pending|draft|done|skipped>`** — flip status in registry +
  queue in one write, refusing if the result won't validate. In practice the builder only
  sets `draft`/`skipped`/`pending`; **`done` is the critic's move** and validate refuses it
  without an approving critique on file.
- **`decide.py status`** — queue dashboard (counts, per-topic registry/queue/critique state,
  open revises, single next step). No writes.
- **`sync_figures.mjs`** — copy `content/surveys/**/figures` → `public/surveys/**`; wire as
  `predev` + `prebuild`.
- **`sitemap.mjs`** — 3-level URL space from published topics.
- **`check.sh`** — `tsc --noEmit` + `vite build` + `python3 scripts/validate.py`, then for
  each `done` topic run the survey skill's own gates against its dir
  (`figure_manifest.py check figures.json --document survey.md`, `corpus_manifest.py coverage
  corpus.json`). Green = shippable.

`prompts/queue.md` row shape (human-readable, aligned pipes):

```
| field | topic                 | title                                   | status  |
|-------|-----------------------|-----------------------------------------|---------|
| ai    | llm-benchmarks-evals  | LLM & Agent Benchmarks and Evaluations  | PENDING |
```

---

## 8. The critic loop (adapted from `refsite-runner` doctrine)

**States.** A topic moves `pending → draft → done`. Builder takes it to `draft` (survey
built, survey-skill gates pass). A separate **critic** pass takes it to `done`. Done is
granted by the critic, never taken by the builder.

**Verdict file.** `content/critiques/<field>__<topic>.md`, **append-only**. Line 1 is the
only machine-read verdict: `verdict: approve | revise | resolved`. Each critic round and each
builder resolution is appended below, forming the audit trail. `validate.py` enforces that a
`done` topic has line 1 `verdict: approve`.

**Roles are separated.** The critic never edits survey content — it only writes the critique
file and, on approve, runs `mark.py <field>/<topic> done`. The builder never writes verdicts.

**`prompts/critique-rubric.md`** — the survey-specific bar. REQUIRED items block approval;
ADVISORY items are optional. Author it to require at least:

- **Corpus adequacy** — 100+ papers, or a smaller N with an explicit, convincing
  justification that the subfield is genuinely small; `coverage --strict` passes (no subarea
  over half, none under 2 papers).
- **Grounding** — every method claim traces to a corpus paper; nothing ungrounded is left
  unlabeled.
- **Taxonomy quality** — axes derived from the corpus (not a template), each justified in one
  sentence; **every** paper placed on the taxonomy.
- **Higher-level insight** — the document delivers real synthesis: the taxonomy, the
  evolution narrative with causes, and cross-cutting comparison(s). A doc that is only
  per-paper summaries with no field-level insight is a REQUIRED miss. *(This is the thing the
  user cares most about — weight it heavily.)*
- **Consistent depth** across taxonomy nodes (no fan-page imbalance).
- **Figures** — each attributed; licensing respected; taxonomy/timeline original.
- **References** — all resolve (HTTP 200).

**Loop (three verbs, mirroring refsite-runner):**

- *build* → runs the survey skill, passes its gates, `mark.py … draft`, commits
  `build: <field>/<topic>`.
- *critique* → critic reads the survey/taxonomy/corpus in full, re-runs the survey gates
  (a failing gate on a draft is itself REQUIRED), judges against the rubric, appends a round,
  sets line 1 `approve`/`revise`. On approve, `mark.py … done`. Commit `critique: … approve|revise`.
- *resolve* → builder fixes REQUIRED items (may re-run parts of the survey skill: add papers,
  redo taxonomy, fix refs), re-verifies every prior round's fixes still hold, re-runs gates,
  appends `## Builder resolution`, sets line 1 `resolved`. Commit `resolve critique: …`.
  The critic re-reviews `resolved` files next round.

In the conversational intake (§9) these three run back-to-back automatically until the critic
approves; the user does not issue them by hand.

---

## 9. Intake workflow — "I want a survey on X" (the primary command)

The user describes a survey need in plain language. They do **not** specify field, slug, or
paths. Claude deduces everything, builds, and critiques. Document this in `CLAUDE.md` as the
main entry point. Steps for a run:

1. **Interpret the need.** From the description, identify the subfield to survey and the 2–4
   driving problems it organizes around (the survey skill will formalize scope in its Phase 1).
2. **Deduce the field.** Read `registry.json`. If the topic clearly belongs to an existing
   field, use it. If none fits, **create a new field**: derive `slug`, `name`, `blurb`, and
   generate an original `public/fields/<slug>.svg` emblem. **Report the placement decision in
   one line** ("Placing this under a new field *Statistics*" / "under existing field *AI*").
   Only pause to ask when the field assignment is genuinely ambiguous; otherwise proceed. The
   user can always override ("put it under Pathology instead").
3. **Deduce the topic.** Derive `slug`, `title`, `blurb` from the need. Run
   `python3 scripts/new_topic.py --field <f> --topic <t> --title "<T>" [--field-name … if new]`.
4. **Build.** Invoke `survey-and-taxonomy-research` with output dir
   `content/surveys/<f>/<t>/`, **target 100+ papers** (fall back to fewer only if the subfield
   is genuinely small — and then the critic must see the justification). All its Phase-8 gates
   pass. `mark.py <f>/<t> draft`; commit `build: <f>/<t>`.
5. **Critique → resolve → approve** (§8), looping automatically until the critic approves.
   On approve the critic runs `mark.py <f>/<t> done`; set the topic's `corpusSize` from
   `corpus.json`.
6. **Report** what was built, the field decision, the corpus size, and the critique rounds.
   Do **not** push or deploy unless the user asks (the one authorized exception is the initial
   scaffold push in §8/step 10). Leave the user to review with `npm run dev`.

Also document the by-hand verbs for power use: "queue status", "critique <field>/<topic>",
"resolve critiques", "rebuild <field>/<topic>", "add a field <name>".

---

## 10. Scaffold task list (order of operations)

1. **Bootstrap** — copy `darvinyi-refsite-template` contents (not its `.git`) into this repo;
   `npm install`; set `package.json` name → `darvinyi-surveys`; set `index.html`
   title/description/og → surveys.darvinyi.com; set `LICENSE` holder; keep `vercel.json`,
   tsconfig, tailwind/postcss, eslint, fonts, `tokens.css` as-is.
2. **Strip** the flat-book pieces (§2).
3. **Content contract** — write the empty `content/registry.json` (§3). Create empty
   `content/surveys/`, `content/critiques/`, `public/fields/`, `prompts/notes/`.
4. **Data libs** — `src/lib/fields.ts`, `src/lib/surveys.ts` (§3, §4).
5. **Pages + components** — `FieldsHome`, `FieldPage`, `SurveyPage`, `FieldCard`, `TopicCard`,
   `SurveyMarkdown`, `PaperTable`, `SurveyToc`; rewrite `App.tsx` (§5); adapt `Layout.tsx`
   breadcrumb. Add `react-markdown` + `remark-gfm`. Every page handles empty states.
6. **Graphics** — an original placeholder topic emblem; field-emblem generator used by
   `new_topic.py` (§6). (No field emblems exist yet — none are seeded.)
7. **Tooling** — `new_topic.py`, `validate.py`, `mark.py`, `decide.py`, `sync_figures.mjs`,
   `sitemap.mjs`, `check.sh`; wire `predev`/`prebuild` (§7). Seed an **empty** `queue.md`
   (header + column row, no data rows) and author `prompts/critique-rubric.md` (§8).
8. **Tests** — render tests for `FieldsHome` (empty state + lists fields when present),
   `FieldPage` (lists topics, dims pending/draft), and `SurveyPage` (renders a fixture
   `survey.md` + `corpus.json` under a `__fixtures__` topic excluded from the registry).
9. **Verify** — `npm run dev` shows a correct empty landing page; `npm run check` is green;
   `npm run build` succeeds. No real survey is built during scaffolding.
10. **Git + GitHub** — `git init`; ensure `.gitignore` covers `node_modules`, `dist`;
    initial commit `scaffold: surveys hub`. Create a **public** GitHub repo under the same
    owner as the other darvinyi sites (owner appears to be `yidarvin` — confirm the active
    `gh` account first with `gh auth status`), e.g.
    `gh repo create yidarvin/darvinyi-surveys --public --source=. --remote=origin --push`.
    This initial push is authorized by the user. (Vercel project + `surveys.darvinyi.com`
    DNS is the user's step; do not deploy without being asked.)

---

## 11. First survey after scaffolding

No seeds exist, so the first real use is the intake workflow (§9): the user describes a
survey need, Claude deduces the field + topic, builds with the survey skill, and runs the
critic loop to done. Nothing about fields or slugs is hand-specified.
