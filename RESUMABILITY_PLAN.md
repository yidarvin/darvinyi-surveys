# Resumability Plan — surviving a token-limit death mid-build

**Goal.** A survey build is long by design (100+ papers, read for real). If a
session runs out of tokens at any point, a fresh session started after the limit
refreshes must be able to **pick the build back up exactly where it stopped**,
without re-doing completed work and without silently producing a *different*
survey than the half-built one on disk.

**Doctrine (unchanged, extended).** The existing `.pipeline/` spine already makes
Phases 2–3 (the fan-out phases) recoverable: workers hand off through files, the
coordinator discovers progress by reading the filesystem. This plan extends the
same "hand off through files, discover from disk" rule to **the whole workflow** —
the outer intake steps, the Phase 1 plan, the monolithic writing phases, figures,
and the critique loop — and adds a **single deterministic resume entrypoint** so a
fresh session never has to guess where it died.

**Implementer:** Sonnet 5, effort high. **Scope approved:** Tiers A–E (all).

---

## Ground truth: what already survives, what doesn't

Durable on disk today (survives a dead session):
`registry.json`, `queue.md`, `corpus.json` (scope + every paper + subarea +
`taxonomy_node`), `.pipeline/candidates/*.json`, `.pipeline/notes/*.json`,
`.pipeline/claims/*.claim`, `.pipeline/corrections.json`, `figures/` +
`figures.json`, `survey.md` (whole-file), `critiques/<f>__<t>.md`.

Gap-detection already exists for Phases 2–3: `survey_pipeline.py candidates-status`,
`notes-status`, `next-keys` — all re-runnable, all act only on what's missing.

Lost on a token-death today (lives only in the coordinating agent's context):

1. **Which workflow step we were on** — no top-level ledger, no resume entrypoint.
2. **The Phase 1 plan** — driving problems + the *planned* subarea decomposition.
   `corpus.json.scope` is one line; re-deriving the rest risks a *different* survey.
3. **Intra-phase progress in Phases 6 & 7** — `survey.md` is one big write; a
   mid-write death leaves a partial file with no map of done/stub/missing parts.
4. **Phase 4 figure progress** — no way to tell "not attempted" from "attempted,
   nothing embeddable."
5. **Critique-resolution progress** — which REQUIRED findings are resolved vs open.

Everything below closes one of these.

---

## Conventions used throughout

- `<dir>` = `content/surveys/<field>/<topic>/` (the survey output dir).
- All new working state lives under `<dir>/.pipeline/` — already gitignored at any
  depth, already deleted-safe once a topic reaches `done`.
- Every new `survey_pipeline.py` subcommand follows the existing exit-code
  convention: **0 = gate passed**, **2 = keep working**, **1 = usage/data error**.
- Every new command is **idempotent and safe to re-run** — it reads disk and acts
  only on what is actually missing or invalid, never on what a ledger *claims*.
- **Disk wins over the ledger.** When `run.json` and the actual gate state
  disagree, the gate state on disk is authoritative; `status` reports the disk
  truth and rewrites the ledger to match.

---

## Tier A — Durable run-ledger + one resume entrypoint

### A1. `run.json` — the workflow's single source of truth

New file: `<dir>/.pipeline/run.json`. Written by the builder at Phase 1, updated
(one cheap `Write`) at **every phase boundary** and after **every per-item unit**.

Schema:

```json
{
  "field": "ai",
  "topic": "llm-benchmarks-evals",
  "title": "LLM & Agent Benchmarks and Evaluations",
  "slug": "ai/llm-benchmarks-evals",
  "scope": "one-line scope statement, verbatim as it goes to corpus.json",
  "driving_problems": ["...", "...", "..."],
  "planned_subareas": ["subarea-a", "subarea-b", "..."],
  "phase": 3,
  "phase_status": {
    "1": "gate_passed", "2": "gate_passed", "3": "in_progress",
    "4": "not_started", "5": "not_started", "6": "not_started",
    "7": "not_started", "8": "not_started"
  },
  "updated_at": "2026-07-17T18:04:00Z",
  "next_action": "python3 scripts/survey_pipeline.py next-keys content/surveys/ai/llm-benchmarks-evals"
}
```

`phase_status` values: `not_started | in_progress | gate_passed`. `updated_at` is
a plain ISO string the builder passes in (agents don't have a clock helper — write
whatever timestamp the environment reports, or leave the previous value; it is
advisory only). `next_action` is a human/agent hint, **not** authoritative — the
`status` command recomputes the real next step from disk.

Add two tiny helpers to `survey_pipeline.py` so the builder never hand-writes JSON:

- `run-init <dir> --field --topic --title --scope --driving-problems "a|b|c"
  --planned-subareas "x|y|z"` — creates `run.json` with all phases `not_started`
  except Phase 1 = `gate_passed`.
- `run-set <dir> --phase N --status <not_started|in_progress|gate_passed>
  [--next-action "..."]` — updates one phase's status + `phase`/`updated_at`.

### A2. `status <dir>` — recompute the real state from disk

New subcommand `survey_pipeline.py status <dir>`. It **ignores `run.json` for the
truth** and re-derives each gate independently, then reconciles:

| Phase | Gate check (reuse existing tooling) |
|---|---|
| 1 scope | `corpus.json` exists with non-empty `topic` + `scope` |
| 2 corpus | `corpus_manifest.py coverage corpus.json --strict` exits 0 |
| 3 reading | `notes-status <dir>` exits 0 |
| 4 figures | `figures-status <dir>` exits 0 (Tier D) |
| 5 taxonomy | `coverage corpus.json` prints no "Not yet placed" line **and** `figures/taxonomy.svg` registered |
| 6 narrative | `sections-status <dir>` shows the evolution-narrative part present (Tier C) |
| 7 assemble | `sections-status <dir>` exits 0 (all parts + all nodes present, non-stub) |
| 8 verify | `figure_manifest.py check figures.json --document survey.md` exits 0 **and** refs resolve |

Output: a per-phase table (`gate_passed` / `in_progress` / `not_started`), the
**first** phase whose gate is not passed = "current phase," and the **exact next
command** to run for it. Then rewrite `run.json` to match what it just measured
(self-healing: even a build whose ledger was never written gets a correct one).
Exit 0 only if Phase 8 passes; else exit 2.

### A3. `scan` — find every interrupted build

New subcommand `survey_pipeline.py scan`. Walk `content/surveys/*/*/`; for each
topic whose `registry.json` status ≠ `done` **and** that has a `.pipeline/`
directory, print one line: `<field>/<topic> — Phase N (<current phase name>)`.
This is the first thing a fresh post-refresh session runs.

---

## Tier B — Persist the Phase 1 plan (do alongside A)

The driving problems and planned subareas must be durable **before any fan-out**,
so a fresh session dispatches the *same* discovery/reader workers rather than
re-deriving scope (which could silently change the survey).

- Storage: `run.json` (`driving_problems`, `planned_subareas`) is the primary home
  — written by `run-init` at Phase 1. **Additionally** mirror the scope statement
  into `corpus.json` via the existing `corpus_manifest.py init` so the two never
  drift (the survey doc's top-of-file scope already comes from there).
- Update the intake workflow so **Phase 1 always calls `run-init` immediately after
  `new_topic.py`**, before Phase 2 dispatch. This is the checkpoint that makes
  everything downstream resumable.

---

## Tier C — Section-level checkpointing for Phases 6 & 7

The token-heaviest phases with **zero** intra-phase resume today. Fix by writing
the survey as **per-part fragments**, each flushed the moment it's drafted.

### C1. Fragment layout

`<dir>/.pipeline/sections/` holds one markdown fragment per structural part of the
Phase 7 document, numbered to sort into final order:

```
00-scope.md              # Phase 1 statement, verbatim
10-taxonomy.md           # axes + justifications + taxonomy figure
20-method-<node-slug>.md # ONE per taxonomy node (Phase 7 part 3) — the big fan-out
30-evolution.md          # Phase 6 narrative + timeline figure
40-comparison.md         # cross-cutting table(s)
50-limitations.md        # limitations + future directions
90-references.md         # generated by corpus_manifest.py refs
```

The `20-method-*` fragments are the heaviest and most numerous — treat them as a
**per-item fan-out exactly like notes**: one file per taxonomy node, written
immediately, dispatched to background workers (see C3).

### C2. `sections-status <dir>` + assembly

- New subcommand `survey_pipeline.py sections-status <dir>`:
  - Derives the **expected** fragment set: the 6 fixed parts + one `20-method-<slug>`
    per distinct taxonomy node found in `corpus.json` (`taxonomy_node` field,
    split on `;`, deduped).
  - Reports each expected fragment as `present` / `missing` / `stub`. A fragment is
    a **stub** if it's under a minimum length or contains a TODO marker — reuse
    validate.py's existing TODO/placeholder check so the bar matches the `done` gate.
  - Exit 0 iff every expected fragment is present and non-stub; else 2. Print the
    missing/stub list (this is the "next work" set for a resuming session).
- New subcommand `survey_pipeline.py assemble-sections <dir>`: concatenate all
  fragments in filename order into `survey.md`, splicing the generated references.
  Idempotent — safe to re-run after any fragment changes. Assembly is the last step
  of Phase 7 and is cheap, so it never needs its own checkpoint.

### C3. Dispatch the heavy fan-out as background per-item workers

- Add a worker template `prompts/workers/section-worker.md` (mirror
  `reader-worker.md`): fill in one taxonomy node, its member papers (from
  `corpus.json` + their notes), and the house depth requirement; the worker writes
  exactly `<dir>/.pipeline/sections/20-method-<slug>.md` and nothing else.
- Drive it with the **same converge loop** as Phases 2–3: dispatch one round of
  background workers over the `missing`/`stub` set from `sections-status`, wait for
  completion notifications, re-check, dispatch a new round for whatever's still
  missing, stop after two zero-progress rounds. Keeping this work in background
  workers (not the coordinator's context) is what keeps the **coordinator** lean
  and least likely to be the session that dies.

---

## Tier D — Figure-status + critique-resolution tracking

### D1. `figures-status <dir>`

New subcommand. For each corpus paper, "attempted" iff **either** a `figures.json`
entry references its key **or** a marker file `<dir>/.pipeline/figures-attempted/<key>`
exists (worker writes this when it tried and found nothing embeddable — restricted
license, vector-only, etc.). Report per-paper `has-figure` / `attempted-none` /
`not-attempted`; exit 2 while any paper is `not-attempted`, else 0. This is what
lets a resuming session skip papers already handled instead of re-scanning all PDFs.
Update the figure step of the workflow to drop the marker on a no-figure outcome.

### D2. Critique-resolution checklist

- When the critic writes `content/critiques/<f>__<t>.md` with `verdict: revise`,
  require REQUIRED findings to be an explicit checklist (`- [ ] R1: ...`).
- The builder marks each `- [x]` as it resolves it and appends a one-line note.
- Add `survey_pipeline.py critique-status <f>/<t>` (or extend `decide.py`): report
  count of open vs resolved REQUIRED findings; exit 2 while any REQUIRED box is
  unchecked. A mid-resolution death then resumes at the first open box.
- Keep it append-only — never rewrite prior critic text (matches the existing
  `content/critiques` rule in CLAUDE.md).

---

## Tier E — Documentation (required to make A–D usable)

### E1. New CLAUDE.md section: "Resuming an interrupted build after a token refresh"

Placed right after "Autonomous build doctrine." Content, as a deterministic
procedure a fresh session follows **before touching anything**:

1. Run `python3 scripts/survey_pipeline.py scan`. If it lists any interrupted
   build, that's the resume target (ask the user if more than one).
2. Run `python3 scripts/survey_pipeline.py status <dir>`. It prints the current
   phase and the exact next command, having re-derived state from disk.
3. Do **not** re-derive scope, driving problems, or subareas — read them from
   `run.json`. Re-deriving risks building a different survey than the one on disk.
4. Resume the printed phase using its normal converge loop / next command. For
   Phases 2, 3, and 7-methods, that means dispatching only the `missing`/`invalid`/
   `stub` set — completed per-item work is never redone.
5. After each phase boundary and each per-item unit, update `run.json`
   (`run-set`) and flush any in-context draft to disk — never batch.

### E2. New by-hand verb

Add to CLAUDE.md's "By-hand verbs":
> **"resume" / "resume `<field>/<topic>`"** — run `survey_pipeline.py scan`, then
> `status <dir>` on the (chosen) interrupted build, and continue from the printed
> next command per the resume procedure above.

### E3. Checkpoint discipline line

Add to the Autonomous build doctrine: *checkpoint at every phase boundary and after
every per-item unit — update `run.json` and flush drafts to disk. The coordinator's
context is the one thing that does not survive a token-death; never let unflushed
progress accumulate in it.*

### E4. Update `survey_pipeline.py` module docstring

Extend the `.pipeline/` layout comment to document `run.json`, `sections/`,
`figures-attempted/`, and the new subcommands.

---

## Suggested implementation order

1. **A1 + A2 + A3** — ledger, `status`, `scan`. (Everything else plugs into `status`.)
2. **B** — wire `run-init` into the Phase 1 intake step.
3. **E** — docs, so the entrypoint is actually reachable by a fresh session.
4. **C** — section fragments, `sections-status`, `assemble-sections`, worker template.
5. **D** — figure-status marker + critique checklist.

After each tier: `npm run check` must stay green (validate + tests + build + gates).
The existing done survey (`ai/llm-benchmarks-evals`) has no `.pipeline/`, so `scan`
must treat a missing `.pipeline/` as "not interrupted" and skip it cleanly — add a
test fixture for that.

## Testing checklist

- `status` on a dir with **no** `run.json` self-heals and reports the correct phase
  purely from disk.
- `status` reconciles a **stale** `run.json` (claims Phase 5 while `notes-status`
  fails) down to the real phase.
- `scan` ignores `done` topics and topics without `.pipeline/`.
- `sections-status` flags a TODO-containing fragment as `stub`, and its expected
  node set tracks `corpus.json`'s `taxonomy_node` values.
- `figures-status` counts an `attempted-none` marker as attempted.
- Idempotency: every new subcommand run twice in a row is a no-op the second time.
- Kill-and-resume smoke test: interrupt a build mid-Phase-3 and mid-Phase-7, start
  fresh, follow only `scan` → `status` → next command, confirm no completed per-item
  work is redone.
