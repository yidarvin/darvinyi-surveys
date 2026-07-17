verdict: approve

## Critique round 1 -- 2026-07-17

Fresh-eyes review of `content/surveys/ai/llm-benchmarks-evals/` (survey.md, corpus.json,
figures.json, figures/, refs.md), graded against `prompts/critique-rubric.md`. No memory of
the build; all findings are from the artifacts on disk plus external verification.

**Verdict: approve.** This is a genuinely strong survey. It clears every REQUIRED bar,
including the one that matters most (higher-level insight). Zero REQUIRED findings; three
minor ADVISORY notes recorded below, none blocking.

### REQUIRED checklist — all pass

1. **Corpus adequacy — PASS.** `corpus_manifest.py coverage ... --strict` exits 0. 189 papers.
   Subarea balance is healthy: largest node is agentic-benchmarks at 24/189 (~13%, far under
   the half-corpus ceiling); smallest is efficiency-evaluation at 10 (well over the 2-paper
   floor). Year spread is sensible (origin papers 2017-2018 present through 2026 SOTA).

2. **Grounding — PASS.** Spot-checked well beyond the required 8-10 method/results claims
   against the real papers via web verification; every specific number I sampled is accurate:
   - SWE-bench Verified filters **68.3%** of instances; GPT-4o resolve rate roughly doubles
     (16% -> 33.2%). Confirmed exact against OpenAI's announcement.
   - GSM-Symbolic / GSM-NoOp: single irrelevant clause drops accuracy **up to 65%** across
     SOTA models. Confirmed against arXiv:2410.05229 abstract.
   - Length-Controlled AlpacaEval: length-controlling raises Spearman correlation with Chatbot
     Arena from **0.94 to 0.98**. Confirmed exact against arXiv:2404.04475.
   - Sclar prompt-format spread (0.036–0.804), MMLU-Redux (6.49% avg error, 57% Virology),
     Schaeffer emergent-mirage (>92% of BIG-bench instances from two metric choices),
     Leaderboard Illusion (61.4%/8.9%, 23.5%->49.9%), Turpin CoT-bias, DecodingTrust — all
     consistent with the papers and with the corpus entries. Nothing reads as invented,
     misattributed, or unsupported. Claims carry inline `[n]` reference numbers throughout.

3. **Taxonomy quality — PASS.** The two axes are genuinely corpus-derived, not a template.
   Axis 1 (target of measurement: static-knowledge/code, reasoning-process-depth,
   agentic-behavior, safety/robustness, meta-evaluation-process) is justified by *what
   evaluation format each target forces* — a real, non-obvious organizing insight. Axis 2
   (construction vs. audit-or-critique) is orthogonal and load-bearing (it drives the
   evolution narrative's "critique-and-repair era"). `corpus_manifest.py coverage` (non-strict)
   emits no "not yet placed" warnings — every paper carries a `taxonomy_node`.

4. **Higher-level insight — PASS (the strongest part of the document).** This is real
   field-level synthesis, not stitched per-paper summaries. The evolution narrative (§4) is
   built on an explicit **construct-saturate-critique-repair** cycle with genuine causal
   claims (GPT-3's few-shot paradigm *created* the prompt-sensitivity blind spot; MMLU
   saturation *drove* both harder variants and the audit turn; the 2023 "three crises"
   framing). §5's cross-cutting table synthesizes two non-trivial patterns that hold across
   every row: cost trades off directly against contamination-resistance, and every subarea's
   "biggest gap" is a *validity* gap rather than a capability gap. A competent reader finishes
   this able to explain the field's shape in their own words. §6 (limitations / honest
   negative results) is unusually candid and further evidences real synthesis.

5. **Consistent depth — PASS.** No fan-page imbalance. The five Axis-1 nodes get treatment
   proportional to their size, and within each, sibling leaf subareas get comparably dense,
   evidence-packed paragraphs. Even the smallest node (efficiency-evaluation, 10 papers) gets
   a full, well-developed treatment rather than a stub.

6. **Figures — PASS.** `figure_manifest.py check ... --document survey.md` exits 0. 15 figures,
   each with a caption and verbatim attribution. The 13 paper-extracted figures are all
   analytical diagrams (pipelines, taxonomy trees, result plots) embedded with scholarly
   commentary in body prose, consistent with the licensing rule; the two landing-relevant
   originals (taxonomy.svg, timeline.svg) are correctly marked "Original figure, this survey"
   with `paper_key: this-survey`. No paper figure is promoted to card art.

7. **References resolve — PASS.** Curl-checked 20 URLs weighted toward the highest-risk ones
   (non-arXiv, GitHub, web.archive, Berkeley leaderboard, and every 2025/2026 paper). All
   return HTTP 200 except **[127] Zenodo (10829972)**, which returns 403 to curl even with a
   browser UA — this is Cloudflare anti-bot blocking, not a dead link. Verified via WebFetch
   that the record is genuine (EleutherAI/lm-evaluation-harness v0.4.2, published 2024-03-18).
   The 2026 arXiv IDs (2601.11868, 2605.17273, 2601.20251) resolve cleanly, as do all recent
   2025 entries.

8. **Gate passes — PASS.** `npm run check` is green: validate + eslint (0 warnings) + build +
   sitemap + per-topic gates all succeed. Output ends `CHECK OK`.

### Specifically-scrutinized: the Picard -> Bethard correction — fully consistent

Verified the mid-build author correction propagated everywhere. `grep -rin "picard"` over the
survey directory returns **zero** hits. arXiv:2210.13393 appears with author **Steven Bethard**
and key **bethard2022-random-seeds** consistently across all three files: corpus.json
(key + authors + url), refs.md [41], and survey.md (reference list [41] and the in-body
citation "Biderman et al. [118] and Bethard [41]" in §3.5). No stray old key or old author
name anywhere.

### ADVISORY (does not block approval)

- **§3.2 GSM-NoOp phrasing.** "drops accuracy by up to 65 points, including on o1-preview" —
  the 65-point figure is the maximum across all SOTA models; o1-preview's own drop is smaller.
  The intended reading ("even o1-preview is affected") is defensible, but the sentence could be
  misread as o1-preview itself dropping 65 points. Consider tightening to "up to 65 points
  across models, and o1-preview is not immune."
- **Reference [127] robustness.** The Zenodo URL is genuine but 403s to automated HTTP checkers
  behind Cloudflare. If the reference-resolution gate is ever run strictly against live HTTP,
  this row will trip a false negative. A stable DOI form (10.5281/zenodo.10829972) or a note in
  the ref would make the automated check more robust. Not a correctness issue.
- **Uncited-in-prose corpus papers.** A handful of corpus entries (e.g., PIQA [8], GSM8K [23],
  MATH [27], CodeXGLUE [34], Surface Form Competition [29], InterCode [110]) are placed on the
  taxonomy and appear in the reference list but are not individually discussed in body prose.
  This is acceptable under the rubric (placement + grounding are what's required), but a couple
  could be woven into their subarea paragraphs for completeness if a future revision touches
  those sections.
