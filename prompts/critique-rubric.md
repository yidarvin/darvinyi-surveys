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

## Verdict file

`content/critiques/<field>__<topic>.md`, append-only. Line 1 is the only
machine-read verdict: `verdict: approve | revise | resolved`. Each critic round
and each builder resolution is appended below as a dated section, forming the
audit trail. `scripts/validate.py` enforces that a `done` topic has line 1
`verdict: approve`.

## REQUIRED (blocks approval)

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

## ADVISORY (does not block approval)

- Prose polish, minor rephrasing, additional cross-links between related
  topics once more than one exists in the same field.
- A thin subarea that technically clears the coverage gate but could use one
  or two more papers.
- Additional comparison tables beyond the required one.

Only fix an advisory item during resolve if it is cheap and clearly correct,
and never at the cost of regressing a required fix.

## Anti-oscillation

Do not re-litigate a finding a prior round already accepted as resolved unless
a later edit visibly regressed it. A resolve round must name which prior
rounds it re-verified.
