verdict: approve

## Critique round 1 — 2026-07-17

Source mode: **scientific** (from `run.json`). Judged against the REQUIRED
(scientific mode) list in `prompts/critique-rubric.md`.

This is a strong survey. The synthesis quality — the single most important bar —
is clearly met: the two-axis taxonomy (reward source × optimization mechanism)
is genuinely derived from the papers' *methods* rather than the discovery-time
keyword buckets, and the survey says so explicitly and justifies each axis in a
sentence. Every corpus paper is placed (85 on the grid + 33 cross-cutting root =
118). The evolution narrative is causal, not chronological ("GRPO … roughly
halved the cost of an RL step and made large-scale task RL practical",
"R1-Zero was the branch point that turned task-specific RL from a specialist
craft into a commodity recipe"). There are two cross-cutting comparison tables
(reward sources on cost/hackability/density; the recipe across domains). The
limitations section is honest and load-bearing — the teach-vs-elicit debate is
presented with both sides (Yue/Shao vs. ProRL/Wen), plus reward hacking,
forgetting laws, and diversity collapse, each grounded in corpus papers. Method
claims trace to citations throughout, and depth is consistent across taxonomy
nodes (no fan-page imbalance). The survey is genuinely distinct from the sibling
`ai/rl-in-llms`: the scope section differentiates it explicitly (no DPO node,
foregrounds reward *construction* and search-guided training, domain case
studies). Figures all carry captions and verbatim per-paper attributions;
`figure_manifest.py check` passes (20 verified). Reference URLs spot-checked
resolve HTTP 200, including the future-looking 2026 arXiv IDs (2603–2607),
which WebFetch confirms are real papers matching the reference entries exactly.
`npm run check` is green.

One REQUIRED item blocks approval — a mechanical corpus-balance gate the rubric
names explicitly, which the build never cleared (the pipeline itself still
reports Phase 2 as `in_progress` for this reason).

REQUIRED:
- [ ] R1: The `--strict` coverage gate fails. `python3
  scripts/corpus_manifest.py coverage content/surveys/ai/task-specific-rl/corpus.json
  --strict` exits non-zero: the subarea `execution-grounded-rewards` has only
  **1 paper** (`jiang2025coderlplus`, CodeRL+), and the rubric's Corpus-adequacy
  bar requires "none under 2 papers." (`npm run check` passes only because its
  coverage check is non-strict; `survey_pipeline.py status` still shows
  "CURRENT PHASE: 2" with a THIN SUBAREA warning.) This is a discovery-bucket
  labeling artifact, not a genuine gap in coverage — the survey has a full
  execution-grounded method node spanning ~15 papers, all of which are tagged
  into domain buckets (`domain-code`, `domain-sql-extraction`,
  `domain-agents-search`) instead. Fix by re-tagging: either move CodeRL+ to
  `domain-code` and retire the one-paper `execution-grounded-rewards` subarea,
  or move a second genuinely execution-grounded paper into it so it reaches ≥2.
  Re-run `... coverage ... --strict` (exit 0) and `survey_pipeline.py status`
  (Phase 2 gate_passed) to confirm before re-review.

ADVISORY (does not block approval):
- The Tulu 3 figure caption (survey.md, "Overview of the Tulu 3 post-training
  pipeline") attributes to "Lambert et al. (**2025**)", while reference #19 and
  every in-text citation use **2024**. Make the year consistent.
- The `verifiable-task-rewards` subarea (3 papers) clears the ≥2 floor, but its
  three members (Lv 2025, Wen 2025, Wu 2025) are all teach-vs-elicit / analysis
  papers rather than verifiable-reward *methods* — the actual RLVR method papers
  live under the domain buckets. Cosmetic, since these are discovery buckets and
  not the survey's taxonomy, but worth tidying if the subareas are re-touched
  for R1.

## Critique round 2 — 2026-07-17

Re-review of the round-1 resolution. Source mode still **scientific**; judged
against the same REQUIRED (scientific mode) list. I re-verified round 1's sole
REQUIRED finding and confirmed nothing regressed.

REQUIRED:
- [x] R1: **RESOLVED.** `python3 scripts/corpus_manifest.py coverage
  content/surveys/ai/task-specific-rl/corpus.json --strict` now exits **0**. The
  one-paper `execution-grounded-rewards` subarea is retired — CodeRL+
  (`jiang2025coderlplus`) is re-tagged into `domain-code` (now 14). Every
  subarea sits between 8 (`rft-frameworks-recipes`) and 14, all ≥2 and none over
  half the 118-paper corpus. `survey_pipeline.py status` now reports Phase 2
  `gate_passed` and **ALL PHASES PASSED**.

Verified no regression:
- The advisory Tulu 3 year is now consistent — every mention (figure caption
  line 348, references #19, and all in-text citations) reads **Lambert et al.
  (2024)**, and the caption matches `figures.json` verbatim ("Figure from
  Lambert et al. (2024), Tulu 3, arXiv:2411.15124"). `figure_manifest.py check`
  passes (20 verified).
- The re-tagging is discovery bookkeeping only: the **Execution-grounded reward**
  METHOD node in the survey (section at "### Execution-grounded reward") and the
  taxonomy grid are unchanged. The moved analysis papers (out of the retired
  `verifiable-task-rewards` into `specialization-dynamics`, now 12) likewise did
  not disturb any taxonomy placement or synthesis.
- `npm run check` is green (CHECK OK). Document still reads coherently on
  spot-check.

All round-1 quality findings (synthesis, taxonomy, grounding, figures,
references) stand as accepted. Approving. Marked done and set `corpusSize: 118`.
