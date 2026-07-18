# Critique rubric

The bar a survey topic must clear to go from `draft` to `done`. Adapted from the
`refsite-runner` skill's build-critique doctrine (separated builder/critic
roles, an append-only verdict file, `REQUIRED` blocks approval, `ADVISORY` does
not), specialized for a survey-and-taxonomy document rather than a book
chapter.

## Roles and models

Builder and critic are different roles and should run as different agents so
the critique is a genuine fresh-eyes review, not the builder grading its own
work:

- **Builder** (research, corpus assembly, writing `survey.md`, deriving the
  taxonomy, fixing REQUIRED findings during resolve) -- **Sonnet**, effort
  **high**. This is execution: following the `survey-and-taxonomy-research`
  skill's phases and gates precisely.
- **Critic** (judging corpus adequacy, taxonomy validity, and above all
  synthesis quality) -- **Opus**, effort **high**. Judgment and higher-level
  insight assessment is exactly the kind of work that benefits from the
  stronger model; spawn the critic as its own subagent (e.g. via the Agent
  tool with `model: "opus"`) so it has no memory of the build and reviews only
  the artifacts on disk.

Any other agentic step in the intake workflow (deducing field placement, corpus
discovery fan-out, resolve-round fixes) defaults to Sonnet at effort high
unless it is specifically a judgment/critique step, in which case it is Opus.

## Source mode

Every survey has a `source_mode` recorded in `.pipeline/run.json` (self-healed by
`python3 scripts/survey_pipeline.py status <survey_dir>` if missing, which defaults
it to `scientific`). **The critic reads this before reviewing** and applies the
matching REQUIRED list below: `scientific` surveys are judged against "REQUIRED
(scientific mode)", `broad` surveys against "REQUIRED (broad / non-scientific
mode)". Everything outside those two lists — the roles above, the verdict-file
mechanics, ADVISORY, and Anti-oscillation — applies identically to both.

## Verdict file

`content/critiques/<field>__<topic>.md`, append-only. Line 1 is the only
machine-read verdict: `verdict: approve | revise | resolved`. Each critic round
and each builder resolution is appended below as a dated section, forming the
audit trail. `scripts/validate.py` enforces that a `done` topic has line 1
`verdict: approve`.

On `verdict: revise`, list every REQUIRED finding as a markdown checkbox,
labeled, one per line:

```
REQUIRED:
- [ ] R1: <finding>
- [ ] R2: <finding>
```

The builder toggles `- [ ]` to `- [x]` in place as each finding is resolved
(a narrow exception to append-only, scoped to checkbox state within the
still-open round -- never rewrite the surrounding prose, and never re-open a
box a prior round already closed unless a later edit visibly regressed it,
per Anti-oscillation below). This is what makes resolution progress durable
across a token-limit death: `python3 scripts/survey_pipeline.py
critique-status <survey_dir>` reads the checkboxes directly and reports
exactly which findings are still open, so a resuming session never has to
recall which fixes it already made. A critique predating this convention (no
checkboxes) is not retroactively broken -- `critique-status` reports it
can't verify resolution mechanically and defers to the text.

## REQUIRED (scientific mode)

- **Corpus adequacy.** 100+ papers, or a smaller N with an explicit, convincing
  written justification (in the survey's scope section or the corpus notes)
  that the subfield is genuinely small. `python3 scripts/corpus_manifest.py
  coverage corpus.json --strict` passes: no subarea over half the corpus, none
  under 2 papers.
- **Grounding.** Every method claim in `survey.md` traces to a corpus paper (by
  key or reference number). Nothing ungroundable is left unlabeled.
- **Taxonomy quality.** The axes are derived from the corpus, not a template,
  each justified in one sentence. Every corpus paper is placed on the taxonomy
  (or explicitly at `root` for cross-cutting papers).
- **Higher-level insight.** This is the single most important bar. A survey
  that is only per-paper summaries strung together, with no field-level
  synthesis, fails here regardless of how many papers it read. The document
  must deliver: a taxonomy that actually clarifies the field's shape, an
  evolution narrative with causes ("X made Y possible", "Z reacted to the
  failure of W"), and at least one cross-cutting comparison. If a competent
  reader finishes the document and cannot explain the field's structure in
  their own words, this is a REQUIRED finding.
- **Consistent depth.** No taxonomy node gets three paragraphs while its
  sibling gets one line (the "fan page" failure mode).
- **Figures.** Every figure has a caption and a verbatim attribution;
  `python3 scripts/figure_manifest.py check figures.json --document survey.md`
  passes. Licensing was checked per paper (the skill's own guardrail) before
  any paper figure was embedded.
- **References resolve.** Every reference URL returns HTTP 200 (curl-checked).
- **Gate passes.** `npm run check` is green on the current artifacts. A
  failing gate on a draft is itself a REQUIRED finding, not something to work
  around.

## REQUIRED (broad / non-scientific mode)

Applies when `run.json` records `"source_mode": "broad"` — see
`prompts/source-credibility.md` for the tier model this section enforces.

- **Corpus adequacy.** 100+ sources, or a smaller N with an explicit, convincing
  written justification that the topic is genuinely narrow. `python3
  scripts/corpus_manifest.py coverage corpus.json --strict --source-mode broad`
  passes: no subarea over half the corpus, none under 2 sources.
- **Source credibility (replaces scientific mode's per-figure licensing check).**
  The corpus is **majority Tier 1-2** (primary/canonical + authoritative
  secondary) with **Tier 3 capped at ~30%**, per the coverage report's tier
  breakdown. Every source is tiered — none left blank. Spot-check a sample of
  entries directly (not just trust the discovery worker's self-report): real
  authorship/attribution, a credible outlet or publisher, and a resolving
  canonical URL. A corpus that leans on blog thinkpieces rather than primary
  texts and authoritative scholarship fails here regardless of count — this is
  the broad-mode equivalent of the scientific bar's grounding requirement.
- **Grounding.** Every claim in `survey.md` traces to a corpus source (by key or
  reference number). Nothing ungroundable is left unlabeled.
- **Taxonomy quality.** The axes are derived from the corpus, not a template,
  each justified in one sentence. Every corpus source is placed on the taxonomy
  (or explicitly at `root` for cross-cutting sources).
- **Higher-level insight.** Identical bar to scientific mode, word for word: a
  survey of per-source summaries strung together with no field-level synthesis
  fails here regardless of how many sources it read. The document must deliver
  a taxonomy that actually clarifies the field's shape, an evolution narrative
  with causes, and at least one cross-cutting comparison.
- **Consistent depth.** No taxonomy node gets three paragraphs while its sibling
  gets one line.
- **Figures.** Non-scientific surveys carry only original figures (the taxonomy
  SVG, optionally a timeline SVG) — there is no paper-figure extraction or
  per-figure licensing question. `python3 scripts/figure_manifest.py check
  figures.json --document survey.md` passes; every figure's attribution reads
  "Original figure, this survey".
- **References resolve.** Every reference URL returns HTTP 200 (curl-checked) —
  same gate as scientific mode, no leniency for non-paper sources.
- **Gate passes.** `npm run check` is green on the current artifacts.

## ADVISORY (does not block approval, either mode)

- Prose polish, minor rephrasing, additional cross-links between related
  topics once more than one exists in the same field.
- A thin subarea that technically clears the coverage gate but could use one
  or two more papers/sources.
- Additional comparison tables beyond the required one.
- (Broad mode) A corpus that clears the Tier 1-2 majority by a comfortable
  margin but could still use one or two more Tier 1 primary sources.

Only fix an advisory item during resolve if it is cheap and clearly correct,
and never at the cost of regressing a required fix.

## Anti-oscillation

Do not re-litigate a finding a prior round already accepted as resolved unless
a later edit visibly regressed it. A resolve round must name which prior
rounds it re-verified.
