# Plan — Extend surveys beyond science (trustable non-paper sources)

**Execute this on Sonnet 5, effort high.** This plan changes the *tooling and
doctrine* of the repo so the intake workflow can build surveys on **non-scientific**
topics (e.g. "maintaining work–life balance", "Stoicism") from 100+ trustable,
high-quality sources — books, primary texts, authoritative secondary works, and
reputable long-form — while **scientific** surveys keep reading scientific papers
exactly as they do today. It is an infrastructure change, not a single survey build.

Do **not** commit, push, or deploy unless the user asks (House rules). End with a
summary and let the user review.

---

## The core idea (decisions already made — do not re-derive)

- **Source mode is a per-survey property**, decided at intake and recorded durably
  in `.pipeline/run.json` so it survives a token-limit death and resume. Two values:
  - **`scientific`** — *default; today's behavior, unchanged.* Corpus = scientific
    papers, verified via Semantic Scholar / arXiv, read as PDFs, figures extracted
    from PDFs. Everything in `CLAUDE.md` and the survey skill applies verbatim.
  - **`broad`** — non-scientific topics. Corpus = **trustable, high-quality sources
    of any kind**, tiered by credibility (below), read from their actual text (web /
    canonical editions), with no PDF-figure extraction. Scientific papers are still
    *welcome* as the top credibility tier — `broad` simply is not *limited* to them.
- **Implement at the project layer, not the global skill.** `CLAUDE.md` already
  establishes that this repo reuses the `survey-and-taxonomy-research` skill's
  *doctrine* but overrides its content mechanics with its own tooling. We keep the
  global skill untouched (it stays the scientific engine and is shared with other
  repos) and add `broad`-mode behavior here: new worker templates, a `--source-mode`
  flag on the pipeline, a credibility rubric, and a parallel critique bar. Updating
  the global skill itself is an explicit **non-goal** of this plan (possible future
  follow-up).
- **What is reused unchanged** (verified against the code): the resumability spine
  `scripts/survey_pipeline.py` (phases, `run.json`, converge loops, `status`/`scan`),
  the manifests `scripts/corpus_manifest.py` / `figure_manifest.py` (their fields
  `key/title/authors/year/venue/url/inclusion_reason/subarea/taxonomy_node` are
  already source-agnostic — `venue` holds the outlet/publisher, `url` must resolve
  HTTP 200), and **Phases 1, 5, 6, 7, 8** of the survey doctrine (scope, taxonomy,
  evolution narrative, document assembly, grounding). These do not know or care what
  a "source" is.
- **What changes** is concentrated in exactly four places where "scientific paper"
  is baked in: **Phase 2 discovery** (arXiv/S2 → credibility-tiered discovery),
  **Phase 3 reading** (PDF download → fetch the source's real text), **Phase 4
  figures** (PDF extraction → skip; keep only the authored taxonomy/timeline SVGs),
  and the **critique rubric** (a parallel non-scientific bar). Plus a small,
  backward-compatible flag threaded through the pipeline and `CLAUDE.md`.

### The credibility model (this is the heart of `broad` mode)

Every `broad`-mode source is assigned a **tier**, recorded in the corpus manifest.
The tiers, and the balance rule the critic enforces:

- **Tier 1 — Primary / canonical.** The foundational thing itself: the primary text
  of a tradition or its originator's own writing (e.g. Marcus Aurelius' *Meditations*,
  Seneca's *Letters*, Epictetus' *Enchiridion* for Stoicism); a primary empirical
  study, or an official position of the authoritative body (e.g. WHO / ILO / APA on
  work–life balance); the seminal book by a field's originator.
- **Tier 2 — Authoritative secondary.** Peer-reviewed papers, university-press and
  established-publisher scholarly books, reference works with editorial authority
  (Stanford Encyclopedia of Philosophy, Encyclopædia Britannica), meta-analyses,
  expert monographs, government / major-NGO reports.
- **Tier 3 — Reputable general-interest.** Established outlets with visible
  authorship and sourcing (e.g. The Atlantic, Harvard Business Review, reputable
  domain publications), recognized-expert long-form and lectures.
- **Excluded — do not add to the corpus.** SEO/content-farm blogs, anonymous or
  unsourced listicles, self-published self-help with no credentials, marketing copy,
  AI-generated filler, forum/Reddit threads (allowed *only* when the survey is
  explicitly *about* an online community and the thread is a primary artifact, and
  then labeled as such).
- **Balance rule (the new gate for `broad`):** the corpus must be **majority Tier 1–2**,
  and **Tier 3 capped at ~30%**. This is what keeps a "survey of Stoicism" anchored in
  Epictetus and the SEP rather than in ten thinkpieces.

Verification for non-paper sources replaces the S2/arXiv path with a
**provenance check**: confirm a real author/attribution, the outlet/publisher, the
publication (or original composition) year, and a **stable, resolving URL** — prefer
canonical/archival editions (Project Gutenberg, SEP, DOI, the publisher's own page).
The Phase-8 HTTP-200-on-every-URL gate is unchanged and still applies.

---

## Workstreams

Do them in this order; each has explicit acceptance criteria. Steps 1–6 are the
change; Step 7 is the end-to-end proof.

### 1. Pipeline: add `source_mode` to the resumability spine
**File:** `scripts/survey_pipeline.py`

- Add `--source-mode {scientific,broad}` to the `run-init` subcommand
  (`cmd_run_init`, ~line 745). Default `scientific`. Store it in the `run.json` dict
  (alongside `scope`/`driving_problems`/`planned_subareas`, ~line 757).
- Make `status` / `_compute_status` print the mode prominently (it drives which
  worker templates a resuming session uses — a resume that picks the wrong mode
  rebuilds the wrong kind of survey, exactly the failure `run.json` exists to prevent).
- In `_reconcile`/`scan` (the self-heal path, ~line 1015–1027), default a missing
  `source_mode` to `scientific` and carry it through, so pre-existing builds and
  today's `rl-in-llms` build are unaffected.
- Optionally allow `run-set` to correct the mode. Keep it backward compatible:
  every existing invocation without `--source-mode` behaves exactly as before.

**Acceptance:** `run-init ... --source-mode broad` writes `"source_mode": "broad"`;
`status` prints it; an existing `run.json` with no `source_mode` still passes
`status`/`scan` and reports `scientific`.

### 2. Corpus manifest: record the credibility tier
**File:** `scripts/corpus_manifest.py`

- Add an optional `--tier {1,2,3}` (or `--tier {primary,secondary,general}`) field
  to `add` and store it per paper. Default null (scientific mode never sets it).
- Add an optional `--source-type` free-text label (e.g. `book`, `essay`, `primary-text`,
  `report`, `paper`, `lecture`) for auditability. Optional; null default.
- Extend `coverage` with a `--source-mode broad` check that **warns loudly** (like
  the existing thin-subarea warning) when Tier-1+2 is not a majority or Tier-3
  exceeds ~30%. Keep the existing hard gates (`>=25`, subarea balance) as the machine
  gate; the tier-balance rule is enforced by the critic (Step 5), with this warning
  as its evidence.
- **`--year`:** keep it an int. Convention for undated/ancient works: use the
  **original composition/publication year as a plain integer** (e.g. `180` for
  *Meditations*; use a modern critical edition's year only if no original date is
  meaningful). Document this convention in the worker template (Step 4). If a genuine
  BCE case appears, allow a negative int — verify the timeline SVG and `refs` output
  still render before relying on it.

**Acceptance:** `add ... --tier 1 --source-type primary-text` round-trips into
`corpus.json`; `coverage --source-mode broad` prints a tier-balance line; every
existing scientific invocation is unchanged (new flags are optional).

### 3. Critique rubric: a parallel non-scientific bar
**File:** `prompts/critique-rubric.md`

Add a **"REQUIRED (broad / non-scientific mode)"** section beside the existing
REQUIRED list. It mirrors the scientific bar but swaps the source-specific items:

- **Corpus adequacy** — 100+ sources (same floor / same small-N escape hatch),
  `coverage --strict` passes.
- **Source credibility (new, replaces "licensing per paper figure")** — corpus is
  **majority Tier 1–2**, Tier 3 ≤ ~30%, **zero excluded sources** (spot-check a
  sample for real authorship/authenticity and a resolving canonical URL). A survey
  built on thinkpieces and blogs fails here regardless of count.
- **Grounding** — every claim in `survey.md` traces to a corpus source by key/ref;
  nothing ungroundable left unlabeled. (Unchanged in spirit.)
- **Taxonomy quality, higher-level insight, consistent depth, evolution narrative,
  references resolve, gate passes** — **identical** to the scientific bar. The
  intellectual bar (a taxonomy that clarifies the field, an evolution narrative with
  causes, at least one cross-cutting comparison) is exactly the same; this is the
  whole point of "survey-like overview with deeper insights."
- **Figures** — non-scientific surveys carry only **original** figures
  (taxonomy.svg, optional timeline.svg); `figure_manifest.py check` still passes. No
  extracted-figure licensing question arises (the repo's card-art rule already forbids
  promoting extracted figures anyway).

Note in the roles section that the critic reads `run.json`'s `source_mode` and
applies the matching REQUIRED list.

**Acceptance:** the rubric has both bars; a `broad` build is judged against the
non-scientific one.

### 4. Worker templates for `broad` mode
**Files:** `prompts/workers/discovery-worker-broad.md`,
`prompts/workers/reader-worker-broad.md` (new), and a shared
`prompts/source-credibility.md` (new).

- **`source-credibility.md`** — the single source of truth for the tier model above
  (Tier 1/2/3 + excluded + the balance rule + the provenance-verification steps +
  the `--year` convention). Both worker templates and `CLAUDE.md` reference it, so
  the definition lives in exactly one place.
- **`discovery-worker-broad.md`** — parallels `discovery-worker.md` but: searches
  for the best sources in a subarea *across types* (primary texts, scholarly
  secondary, reputable long-form), assigns each a **tier**, and verifies provenance
  the non-scientific way (author/outlet/year + a resolving canonical URL) instead of
  via Semantic Scholar. Same output contract: writes
  `.pipeline/candidates/<subarea>.json`, one object per candidate, with the existing
  fields **plus** `tier` and `source_type`. Same hard rules (one level of fan-out,
  never invent bibliographic data, retry transients).
- **`reader-worker-broad.md`** — parallels `reader-worker.md` but reads the source's
  **actual text**: WebFetch / `get_page_text` for web sources; the canonical online
  edition for books/primary texts (Project Gutenberg, SEP, etc.); a representative,
  substantial read when a work is too long to read whole — with an explicit honesty
  rule (**never write a note from memory or from a summary you didn't read**; if only
  part was accessible, say so in `limitations`). Same per-item-immediate write to
  `.pipeline/notes/<key>.json`, same structured-note fields, with generalized meanings
  stated in the template:
  - `problem` → the question / tension / need the source addresses
  - `contribution` → its central claim, idea, or teaching (your words)
  - `method` → its argument, framework, or approach
  - `results` → its conclusions / prescriptions / evidence
  - `limitations` → what it concedes or omits, plus what you observe
  - `relationships` → `builds-on` / `reacts-to` edges to other corpus sources
    (these still drive the taxonomy and evolution narrative — a note without them
    is half a note).

**Acceptance:** both templates exist, reference `source-credibility.md`, keep the
Autonomous-build doctrine's hard rules verbatim, and emit the same on-disk contracts
the coordinator's converge loops already read (so `candidates-status` / `notes-status`
work with zero pipeline changes beyond Step 1–2).

### 5. Intake workflow: teach `CLAUDE.md` the branch
**File:** `CLAUDE.md`

- In **the intake workflow**, add a classification step (between "Deduce the field"
  and "Deduce the topic"): **"Classify the survey's source mode."** Give the test:
  *does answering this topic well mean reading the scientific literature, or the
  field's best books / primary texts / authoritative writing?* Examples: LLM
  benchmarks, protein folding, flow cytometry → `scientific`; Stoicism, work–life
  balance, the history of jazz, negotiation tactics → `broad`. State the decision in
  one line ("Building this in **broad** source mode — corpus will be primary texts +
  authoritative secondary sources, not papers"), and let the user override.
- Thread `--source-mode` into the **Step 4** `run-init` command.
- Branch the build: in `broad` mode, **Phase 2 uses `discovery-worker-broad.md`**,
  **Phase 3 uses `reader-worker-broad.md`**, **Phase 4 is skipped** (produce only the
  authored taxonomy/timeline SVGs — Phase 5/6 already create these), and the critic
  applies the non-scientific REQUIRED list. Phases 1, 5, 6, 7, 8 are unchanged.
- Add one line to the **Models and effort** and **Resuming an interrupted build**
  sections: a resuming session reads `source_mode` from `run.json` and selects the
  matching worker templates — never guesses.
- Update the **"Where things live"** list to mention the new templates and
  `source-credibility.md`.

**Acceptance:** a fresh reading of `CLAUDE.md` unambiguously routes a "survey on
Stoicism" request to `broad` mode end-to-end, and a "survey on X papers" request to
`scientific` mode exactly as today.

### 6. Optional: surface the mode in the site
**Files:** `content/registry.json` schema + `src/lib/surveys.ts` + `SurveyPage`
(only if cheap).

- A per-topic `sourceMode` (optional field) enabling a small label on the survey
  page ("Sources: primary texts, books & authoritative writing"). Nice-to-have, not
  required for function. Skip if it risks touching the running house style; the
  card-art / registry rules are otherwise unchanged. **Confirm with the user before
  doing this one** — it's the only workstream that touches rendered UI.

### 7. End-to-end proof (validation)
Prove the change with a real `broad`-mode build, small but honest:

- **Mechanical first:** `npm run check` green after Steps 1–5; add/adjust any
  pipeline/script tests so the new flags are covered.
- **Live proof:** run one `broad` survey through the full intake workflow as the
  acceptance test. **Recommended topic: Stoicism** (rich primary corpus: Epictetus,
  Seneca, Marcus Aurelius, Musonius Rufus; strong secondary: SEP, university-press
  histories; a clean evolution narrative from the Greek Stoa → Roman Stoicism →
  modern revival). Target 100+ sources per the rubric, or state a convincing small-N
  justification. Take it through critique → resolve → approve like any topic.
  - Because a full 100+ source build is expensive, **confirm with the user before
    launching the live build** — they may want to validate Steps 1–6 mechanically
    first and run the live survey as a separate session. Do not silently spend a long
    build without a green light.

**Acceptance:** `scripts/validate.py` / `npm run check` green; if the live build is
run, the Stoicism survey reaches `done` with an approving critique judged against the
non-scientific rubric, majority Tier 1–2 sources, a real taxonomy and evolution
narrative.

---

## Guardrails carried over (do not weaken)

- **Read for real.** The non-negotiable that the corpus is *actually read*, not
  skimmed, is unchanged — `reader-worker-broad.md` reads source text and forbids
  notes-from-memory just as the paper reader forbids notes-from-abstract.
- **Never fabricate to close a gap.** If a canonical source is genuinely inaccessible,
  say so in the final report; never write a placeholder note or invent a citation.
- **Original artwork only** for cards and figures (existing licensing rule) — `broad`
  mode makes this easier, since it extracts no paper figures at all.
- **Honesty about maturity / grounding.** Same bar: claims trace to sources; synthesis
  is labeled as synthesis; the limitations section says what the field has not shown.
- **Backward compatibility.** Every change is additive and mode-gated. A `scientific`
  build — including the in-flight `rl-in-llms` — behaves identically to today, with no
  `source_mode` required on disk.

## Explicit non-goals
- Editing the global `~/.claude/skills/survey-and-taxonomy-research/` skill.
- Changing the house style / `tokens.css` (Step 6, if done, is a minimal additive label).
- Auto-committing, pushing, or deploying.
