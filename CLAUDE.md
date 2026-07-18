# CLAUDE.md

**darvinyi surveys** (deployed at surveys.darvinyi.com) is a hub of living survey-
and-taxonomy documents, organized two levels deep: **fields** (e.g. AI, Statistics,
Pathology) each hold **topics** (e.g. "LLM & Agent Benchmarks and Evaluations"),
and each topic page is a full survey built from 100+ sources with a derived
taxonomy, an evolution narrative, and a sortable index. For **scientific** topics
those 100+ sources are scientific papers, read in full, exactly as always. For
**non-scientific** topics (e.g. Stoicism, work-life balance) the corpus instead
draws on trustable, high-quality sources of any kind -- primary texts, authoritative
books, reputable long-form -- tiered by credibility; see "Classify the survey's
source mode" below. It is a Vite + React + TypeScript site on Vercel. The scaffold
ships with **zero fields and zero topics** -- `content/registry.json` starts as
`{ ..., "fields": [] }` -- and every field/topic is created by the workflow below,
on demand.

This repo intentionally does **not** use the `refsite-runner` skill's chapter/MDX
content model (a survey is a different shape than a book chapter). It reuses that
skill's design system and build-critique *doctrine* (separated builder/critic
roles, an append-only verdict file, a queue) but implements its own two-level
tooling in `scripts/`. For **scientific** topics, content comes straight from the
**`survey-and-taxonomy-research`** skill, whose native output (`survey.md` +
`figures/` + `corpus.json`) drops straight into `content/surveys/<field>/<topic>/`.
For **non-scientific** topics, this repo drives the same skill's Phases 1 and
5-8 (scope, taxonomy, evolution, assembly, verification) but substitutes its own
`*-worker-broad.md` templates for Phases 2-3 and skips Phase 4 entirely -- see
"Classify the survey's source mode" and `prompts/source-credibility.md`.

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
3. **Classify the survey's source mode.** The test: *does answering this topic
   well mean reading the scientific literature, or the field's best books /
   primary texts / authoritative writing?* LLM benchmarks, protein folding, flow
   cytometry -> `scientific` (the default -- unchanged behavior, scientific papers
   read as PDFs via arXiv/Semantic Scholar). Stoicism, work-life balance, the
   history of jazz, negotiation tactics -> `broad` (trustable non-paper sources,
   tiered by credibility per `prompts/source-credibility.md`). **State the
   decision in one line** ("Building this in **broad** source mode -- corpus will
   be primary texts + authoritative secondary sources, not papers"). Only pause
   to ask if genuinely ambiguous (a topic that plausibly wants both, e.g. "the
   psychology of habit formation"); otherwise proceed. I can always override
   afterward.
4. **Deduce the topic.** Derive a slug, title, and blurb from the request. Stamp
   both files, passing the source mode from step 3 (`--source-mode broad` stamps
   `sourceMode: "broad"` into the registry entry so the site can label it; omit
   for `scientific`, the default, which stamps nothing -- identical to every
   pre-existing topic):
   ```
   python3 scripts/new_topic.py --field <f> --topic <t> --title "<T>" \
     [--blurb "..."] [--field-name "<N>" --field-blurb "..." if the field is new] \
     [--source-mode broad]
   ```
5. **Build** (Sonnet, effort high -- see Models below). Before any fan-out,
   record the skill's own Phase 1 (scope statement, 2-4 driving problems, and
   the subareas you plan to dispatch Phase 2 discovery workers across) to
   `.pipeline/run.json`, including the source mode from step 3:
   ```
   python3 scripts/survey_pipeline.py run-init content/surveys/<f>/<t> \
     --field <f> --topic <t> --title "<T>" --scope "<one-line scope>" \
     --driving-problems "<problem1>|<problem2>|<problem3>" \
     --planned-subareas "<subarea1>|<subarea2>|..." \
     --source-mode <scientific|broad>
   ```
   This is what makes the plan itself durable: if a token-limit death hits
   later in the build, a fresh session resumes from what's recorded here
   instead of re-deriving scope and possibly building a *different* survey
   than the half-finished one on disk (see "Resuming an interrupted build"
   below) -- and `source_mode` specifically is what lets a resuming session
   pick the right worker templates without re-classifying the topic. Then run
   the `survey-and-taxonomy-research` skill with output dir
   `content/surveys/<f>/<t>/`, targeting **100+ sources** (fewer only with an
   explicit, convincing justification that the subfield/topic is genuinely
   small -- the critic checks this). Drive the skill's Phase 2 (discovery) and
   Phase 3 (reading) -- the two phases that fan out across many parallel
   workers -- via the **Autonomous build doctrine** below rather than ad hoc
   message passing; it's what lets the pipeline run to completion unattended
   instead of stalling or silently losing a worker's output.

   **In `scientific` mode**, Phases 2-4 run exactly as the skill describes:
   `prompts/workers/discovery-worker.md` and `prompts/workers/reader-worker.md`,
   papers verified via Semantic Scholar/arXiv, PDF figure extraction in Phase 4.

   **In `broad` mode**: Phase 2 dispatches
   `prompts/workers/discovery-worker-broad.md` instead (sources tiered and
   provenance-checked per `prompts/source-credibility.md`, not verified via
   Semantic Scholar); Phase 3 dispatches
   `prompts/workers/reader-worker-broad.md` instead (fetches each source's
   actual text -- web page, canonical online edition of a book/primary text --
   rather than downloading a PDF); **Phase 4 is skipped entirely** -- no paper
   figures are extracted, so the only figures in the document are the authored
   taxonomy/timeline SVGs Phases 5-6 already produce. Phases 1 and 5-8 are
   identical in both modes.

   Its own Phase 8 gates must pass. Then:
   ```
   python3 scripts/mark.py <f>/<t> draft
   ```
   Commit `build: <f>/<t>`.
6. **Critique -> resolve -> approve** (Opus, effort high -- see Models below and
   `prompts/critique-rubric.md`). Loop build-critique automatically: spawn the
   critic as an independent subagent with no memory of the build (the
   `prompts/workers/critic-worker.md` template has the exact invocation
   contract). The critic reads `source_mode` from `run.json` (via
   `survey_pipeline.py status`) and judges against the matching REQUIRED list in
   the rubric -- `scientific` or `broad`, they differ -- then writes
   `content/critiques/<f>__<t>.md`. On `revise`, the builder (Sonnet) fixes
   REQUIRED findings and the critic re-reviews. On `approve`, the critic runs
   `python3 scripts/mark.py <f>/<t> done` and sets `corpusSize` in the registry
   from `corpus.json`. This loop is what "done" means here -- do not skip
   straight to `mark.py ... done` yourself.
7. **Report** what was built: the field decision, source mode, corpus size,
   critique rounds, any open advisories. Do not push or deploy unless I ask (see
   House rules). Leave me to review with `npm run dev`.

### By-hand verbs (for power use, once fields/topics exist)

- **"queue status"** -- run `python3 scripts/decide.py status`, report it.
- **"resume" / "resume `<field>/<topic>`"** -- run
  `python3 scripts/survey_pipeline.py scan`, then `status` on the (chosen)
  interrupted build, and continue from the printed next command. See
  "Resuming an interrupted build after a token refresh" below -- this is the
  procedure to follow any time a build session was cut short, not just when
  explicitly asked to "resume."
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

## Autonomous build doctrine

Phases 2 (corpus discovery) and 3 (paper reading) of the survey skill are the
only phases that fan out across many parallel workers, and fan-out is exactly
where an unsupervised build can silently stall or lose work: a worker's reply
can misroute to the wrong recipient, a worker can go idle with nothing to
show for it, a transient API error can kill a worker mid-batch. The fix is
structural, not vigilance -- **workers hand off through files on disk under
`.pipeline/`, and the coordinator discovers progress by reading the
filesystem, never by waiting on a message it can't independently verify.**

`scripts/survey_pipeline.py` is the resumability spine (run any subcommand
with no args, or read its module docstring, for the full contract):
`candidates-status` / `apply-candidates` drive Phase 2,
`notes-status` / `next-keys` / `claim` drive Phase 3, `apply-corrections`
applies bibliographic fixes a reader flags mid-build. Every command is safe
to re-run -- each one only ever acts on what's actually missing or invalid
on disk, never on what a message claimed happened.

Worker prompt templates live in `prompts/workers/` (`discovery-worker.md`,
`reader-worker.md`, `section-worker.md`, `critic-worker.md`, and their `broad`-mode
counterparts `discovery-worker-broad.md` / `reader-worker-broad.md` -- see "Classify
the survey's source mode" above for which pair a given build uses -- filled in with `{{...}}`
placeholders per dispatch) and encode the two rules that matter most:

- **One level of fan-out, ever.** A discovery or reader worker must not
  spawn its own sub-agents to "parallelize" a big batch -- it reads
  serially instead. A worker that spawns workers is exactly the failure
  mode this doctrine exists to avoid: a grandchild agent's reply routinely
  cannot find its way back to a non-top-level parent, and the coordinator
  has no way to tell "still working" from "waiting on nothing."
- **Write per-item, immediately, not batched at the end.** A reader worker
  writes each paper's note to `.pipeline/notes/<key>.json` as soon as that
  paper is done, not after its whole assigned batch finishes. This is what
  makes partial progress survive a dead or rate-limited worker -- losing a
  worker loses only its current in-flight paper, never everything it had
  already read.
- **Checkpoint at every phase boundary too, not just per-item.** After a
  phase's gate passes, run `python3 scripts/survey_pipeline.py run-set
  content/surveys/<f>/<t> --phase N --status gate_passed` and flush any
  in-context draft to disk before moving on. The coordinator's own context is
  the one thing that does not survive a token-limit death -- never let
  unflushed progress (a half-written taxonomy derivation, an evolution
  narrative drafted but not yet written to a `.pipeline/sections/` fragment)
  accumulate there. See "Resuming an interrupted build" below for what this
  buys.

### The converge loop

Drive Phase 2 and Phase 3 the same way -- and Phase 7's heaviest step (one
method-treatment section per taxonomy node, `prompts/workers/section-worker.md`)
too, once Phase 5 has placed every paper on the taxonomy:

1. Dispatch one round of workers over the current gap (missing/invalid
   candidates or notes, from `candidates-status` / `next-keys` / Phase 7's
   `sections-status`), each with `run_in_background: true`, all in a single
   message so they run concurrently.
2. Wait for the round's completion notifications rather than polling the
   filesystem in a sleep loop -- background-task notifications arrive on
   their own.
3. When the round settles (every dispatched worker has reported, or a
   worker has gone quiet past the watchdog threshold below), re-run the
   relevant `*-status` command. If it's clean, advance to the next phase.
   If not, dispatch a new round covering only what `next-keys` /
   `candidates-status` still reports missing or invalid -- this
   automatically covers workers that silently died, stalled, or wrote
   invalid output, with no special-case handling needed.
4. Repeat until the gate passes, or until two consecutive rounds make zero
   progress (same missing set before and after) -- at that point, stop and
   report the stall to the user rather than looping forever.

### Watchdog and retry

- **A worker idle past ~15 minutes with no new files landing under
  `.pipeline/`** has stalled, not "still thinking" (this happened for
  real: a nested sub-agent's reply misrouted and its parent waited
  indefinitely). Treat it as failed for this round -- its keys reappear in
  the next `next-keys` call automatically, since nothing was written for
  them. Use `claim`'s `--stale-after-seconds` (default 900s) so a second
  round doesn't double-assign a key a first-round worker might genuinely
  still be covering.
- **A worker that dies on a transient error** (rate limit, network
  timeout) mid-batch has already written notes for whatever it finished
  before dying, per the per-item-immediately rule above -- it does not
  need to be resumed from scratch. Just fold its remaining keys into the
  next round.
- **Never fabricate to close a gap.** If `next-keys` keeps returning the
  same key after several rounds, that paper may be genuinely inaccessible
  (a blocked host, a real 404). Say so explicitly in the final report
  rather than writing a placeholder note to force the gate to pass.

## Resuming an interrupted build after a token refresh

A survey build is long by design (100+ papers, read for real) and can
genuinely run out of tokens mid-build. That is not a failure to route around
-- it is expected, and the doctrine above already makes every fan-out phase
resumable by construction. What follows is the deterministic procedure a
*fresh* session (no memory of the interrupted one) follows to pick a build
back up, rather than guessing or -- worse -- re-deriving scope from scratch
and silently building a different survey than the half-finished one on disk.

1. Run `python3 scripts/survey_pipeline.py scan`. It lists every topic that
   is not `done` and has a `.pipeline/` directory -- i.e. every interrupted
   build. (If more than one comes back, ask me which to resume.)
2. Run `python3 scripts/survey_pipeline.py status content/surveys/<f>/<t>`
   on the target. It re-derives the true state of all 8 phases straight from
   disk (never trusting `.pipeline/run.json`'s own claims over what the
   actual gate checks say), prints the current phase and the exact next
   command, and self-heals `run.json` to match what it just measured.
3. **Do not re-derive scope, driving problems, planned subareas, or source
   mode.** Read them from `run.json` (`status` prints them, including a
   `source mode` line, and prints a loud warning if scope/problems/subareas
   were never recorded -- e.g. a build that predates this convention -- in
   which case re-derive them carefully from `corpus.json`'s scope and the
   subareas already represented among existing papers, not from the original
   request in isolation; a missing `source_mode` self-heals to `scientific`,
   the pre-`broad`-mode default, which is correct for every build that
   predates this convention). **Never re-classify the source mode from
   scratch** -- resuming with the wrong mode's worker templates mid-build
   would mix scientific-paper and broad-source conventions in one corpus.
4. Resume the phase `status` printed, using its normal converge loop or next
   command -- dispatching the `-broad.md` worker templates instead of the
   default pair if `source_mode` is `broad`. For Phase 2, 3, and Phase 7's
   per-node fan-out, that means dispatching workers only over the
   `missing`/`invalid`/`stub` set the relevant `*-status` command reports --
   completed per-item work is never redone.
5. Keep checkpointing per the Autonomous build doctrine above as you go, so
   the *next* interruption, if any, is just as cheap to resume from.

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
- `content/surveys/<field>/<topic>/.pipeline/` -- **working artifacts only,
  never a deliverable** (gitignored at any depth by the `.pipeline/` rule in
  `.gitignore`). Written and read by `scripts/survey_pipeline.py` during an
  in-progress build; see the Autonomous build doctrine and "Resuming an
  interrupted build" above. `run.json` (the resumability ledger: scope,
  driving problems, planned subareas, source mode, per-phase status --
  advisory, always reconciled against disk by `status`), `candidates/<subarea>.json` (Phase 2
  discovery output, one file per subarea), `corrections.json` (bibliographic
  fixes flagged mid-build), `notes/<key>.json` (Phase 3 structured notes, one
  file per corpus paper, keyed to `corpus.json`'s `key`),
  `claims/<key>.claim` (in-flight markers so a second dispatch round doesn't
  reassign a paper a live worker still has), `figures-attempted/<key>`
  (Phase 4 markers for a paper that was checked for a figure and had none
  embeddable), `sections/<NN>-<slug>.md` (Phases 6-7 document fragments, one
  per structural part plus one per taxonomy node -- `assemble-sections`
  concatenates them into `survey.md`). Safe to delete entirely once the
  survey reaches `done` -- everything in it is either already folded into
  `corpus.json`/`figures.json`/`survey.md`, or was scratch work.
- `content/critiques/<field>__<topic>.md` -- append-only critic verdict file.
  Line 1 is the machine-read verdict (`approve` | `revise` | `resolved`).
- `prompts/queue.md` -- the ordered build queue (`field | topic | title | status`).
- `prompts/critique-rubric.md` -- the survey-specific critic bar (REQUIRED vs
  ADVISORY, one list per source mode) and the model guidance above.
- `prompts/source-credibility.md` -- the `broad`-mode source-tier model (Tier
  1-3, the balance rule, provenance verification) referenced by the `-broad.md`
  worker templates and the critique rubric's broad-mode REQUIRED list.
- `prompts/workers/` -- reusable worker prompt templates
  (`discovery-worker.md`, `reader-worker.md`, `section-worker.md`,
  `critic-worker.md`, plus `discovery-worker-broad.md` /
  `reader-worker-broad.md` for `broad`-mode builds) filled in per dispatch;
  see the Autonomous build doctrine above.
- `public/fields/<field>.svg` -- original field emblems, generated by
  `scripts/new_topic.py` when a field is created.
- `src/lib/fields.ts` / `src/lib/surveys.ts` -- typed registry access and the
  lazy `import.meta.glob` loaders for each survey's markdown/corpus.
- `src/pages/` -- `FieldsHome` ("/"), `FieldPage` ("/:field"), `SurveyPage`
  ("/:field/:topic", the survey renderer with an in-page TOC sidebar).
- `src/styles/tokens.css` -- the running house style (shared with the other
  darvinyi sites). Treat it as source of truth; do not restyle.
- `scripts/` -- `new_topic.py`, `validate.py`, `mark.py`, `decide.py`,
  `survey_pipeline.py` (the autonomous-build resumability spine -- see
  above), `sync_figures.mjs` (copies `content/surveys/**/figures` to
  `public/` for `<img>` to resolve), `sitemap.mjs`, `check.sh`, plus vendored
  copies of the survey skill's own `corpus_manifest.py` / `figure_manifest.py`
  (so `npm run check` works in CI without the user's global
  `~/.claude/skills/`).

## Licensing rule for graphics

Field and topic card art must always be **original artwork**, never an extracted
paper figure. A topic's card uses its own `figures/taxonomy.svg` (the survey
skill labels this "Original figure, this survey" -- zero licensing question). A
field's card uses a generated SVG emblem. Extracted *paper* figures only ever
appear inside a survey's body prose, under the skill's own scholarly-commentary
and per-paper license-check rules -- never promoted to a landing card. `broad`-mode
surveys never extract source figures at all (Phase 4 is skipped -- see the intake
workflow), so this question doesn't arise there; their only figures are the
authored taxonomy/timeline SVGs, already licensing-clean by construction.

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
