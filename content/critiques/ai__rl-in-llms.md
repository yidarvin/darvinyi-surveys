verdict: approve

## Critique round 1 — 2026-07-17

Fresh-eyes critic review of `content/surveys/ai/rl-in-llms` against
`prompts/critique-rubric.md`. Reviewed only the on-disk artifacts (the full
2500-line `survey.md`, `corpus.json`, `figures.json`, the pipeline status,
and a sample of `.pipeline/notes/`), with no memory of the build.

**Verdict: approve.** This is one of the strongest surveys in the repo. Every
REQUIRED bar is cleared, most of them comfortably. No REQUIRED findings; a
small number of ADVISORY notes below, none of which block.

### REQUIRED bars — all pass

- **Corpus adequacy.** 141 papers. `corpus_manifest.py coverage --strict`
  passes: largest subarea is evaluation-theory at 23/141 (well under half),
  smallest is rlhf-foundations at 10 (well over the 2-paper floor). Temporal
  spread is excellent — origin papers present (Williams 1992 REINFORCE, Sutton
  1999 policy-gradient theorem, Christiano 2017), through to recent SOTA
  (DeepSeek-R1, GSPO, Absolute Zero, 2025 systems papers).
- **Grounding.** Every method claim traces to a corpus paper by key or
  reference number, consistently, throughout. I spot-checked three specific
  numeric/structural claims against the structured notes — DeepSeek-R1's AIME
  figures (15.6%→71.0%, 79.8%), Shao et al.'s spurious-rewards result (21–24pt
  gains, Qwen-family-specific, clipping-bias mechanism), and GSPO's
  sequence-level fix / MoE Routing-Replay elimination — all three match the
  notes exactly. Nothing ungroundable is left unlabeled.
- **Taxonomy quality.** Two orthogonal axes (reward source; optimization
  mechanism), each explicitly derived from reading across the corpus (not a
  template) and each justified by what it predicts (data requirements & hacking
  exposure vs. memory/compute footprint & on/off-policy sensitivity). All
  141 papers placed — 83 at axis intersections, 58 explicitly at `root` with
  a well-argued justification (systems, evaluation/diagnosis, and pre-LLM
  theory are cross-cutting by construction, not a placement failure).
- **Higher-level insight** (the central bar). Outstanding. The taxonomy
  genuinely clarifies the field's shape; the evolution narrative is causal
  throughout ("reward-hacking critique thread is the intellectual backdrop
  against which the RLVR branch reads as a natural response"; DPO framed as
  eliminating the RL loop that branch one merely simplified); and there are
  multiple genuine cross-cutting comparisons (Table 1 method-family matrix,
  Table 2 shared-benchmark results with explicit non-comparability caveats,
  the "elicitation vs. reshuffling" synthesis across three skeptic papers,
  and an honest "where the corpus itself is thin" section). A competent reader
  finishes this able to explain the field's structure in their own words.
- **Consistent depth.** No fan-page imbalance. Every taxonomy node gets a
  full, multi-paragraph section. The thinnest node (process/step-level reward,
  4 papers) is given a proportionate treatment and its thinness is explicitly
  flagged rather than padded.
- **Figures.** `figure_manifest.py check` passes: 40 figures, each with a
  caption and verbatim attribution, licenses noted per figure (CC BY, CC
  BY-NC-SA, CC0, etc.). Card art is the original `taxonomy.svg`.
- **References resolve.** Phase 8 with `--verify-refs`: all 141 reference URLs
  return HTTP 200.
- **Gate passes.** `npm run check` is green (CHECK OK), including lint.

### ADVISORY (do not block approval)

- Pipeline `status` reports Phase 4 (figures) as `in_progress` — 130/141
  papers attempted for figure extraction. This is figure-*attempt* tracking,
  not a gate: the figure gate (Phase 8) passes, 40 figures are embedded and
  verified, and the survey is not figure-starved. No action needed; noting it
  only so a future resume session doesn't mistake it for unfinished work.
- rlhf-foundations (10 papers) and process/step-level reward (4 as a method)
  are the corpus's thinnest slices. Both clear the gate, and the survey itself
  already discloses the process-reward thinness prominently. Optional future
  enrichment, not a defect.
- Prose is occasionally dense (some very long sentences in the taxonomy
  sections). This is a stylistic preference, not a correctness or clarity
  failure — the density carries real content.
