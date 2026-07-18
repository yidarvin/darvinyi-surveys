verdict: approve

## Critique round 1 -- 2026-07-17

**Source mode:** broad (judged against `prompts/critique-rubric.md`'s broad /
non-scientific REQUIRED list and `prompts/source-credibility.md`).

**Summary.** This is a strong, unusually rigorous broad-mode survey of Stoicism
built on 101 tiered sources. Every broad-mode REQUIRED bar is met, most of them
comfortably. Ground truth was established with the tooling (`survey_pipeline.py
status`, `corpus_manifest.py coverage --strict --source-mode broad`,
`figure_manifest.py check`, `npm run check`), by curl-checking all 101 reference
URLs directly, by reconciling every node/subarea/tier count against the prose,
and by reading the full 1,146-line document. No REQUIRED findings. Two minor
ADVISORY items, neither blocking.

### REQUIRED — all satisfied

- **Corpus adequacy.** 101 sources across 8 balanced subareas (max 16, min 10;
  none over half the corpus, none under 2). `coverage --strict --source-mode
  broad` passes.
- **Source credibility.** Tier breakdown T1=40, T2=58, T3=3 — 97% Tier 1-2,
  Tier 3 at 3% (cap is ~30%). Every source is tiered; no entry missing a tier or
  URL. Spot-checked provenance across primary texts (Marcus/Epictetus/Seneca =
  T1 primary-text), scholarship (Bobzien, SEP/IEP = T2), and general-interest
  essays (The Conversation, Aeon = T3) — all correctly classified with real
  authorship, credible venues, and resolving canonical URLs.
- **Grounding.** Prose is densely cited inline by corpus key, sentence by
  sentence. Ungroundable field-shape inferences (the "20th-century split," the
  "~1,350-year dormancy," the recurrence of Hegel's charge) are each explicitly
  labeled as the survey's own inference rather than sourced claims — exactly what
  the bar requires. Claims resting on access-limited (mediated) readings are
  hedged in place.
- **Taxonomy quality.** Two axes (Period × Domain), each justified in one
  sentence and explicitly derived from recurring corpus contrasts, not a
  template. All 101 sources placed (94 on both axes, 7 at `root` — the four
  whole-system reference works plus Diogenes Laertius's three founder
  biographies, matching the prose exactly). The deliberate Period-axis imbalance
  (23 / 3 / 68) is defended as itself a finding.
- **Higher-level insight (the key bar).** Exceeds it. The taxonomy genuinely
  clarifies the field (evidentiary-distance rationale for the Period axis). The
  evolution narrative is causal throughout ("Stoicism begins as a defection";
  Zeno keeps Cynic virtue-sufficiency but rejects their contempt for
  logic/physics to compete with the Academy/Peripatos; the Roman shift toward
  ethics-as-practice; dormancy → thin early-modern node; Neostoicism as
  civil-war-pressured Christianizing rework; the independent academic-recovery
  vs. clinical-borrowing lineages converging in Modern Stoicism). Two full
  cross-cutting comparison tables (four Roman authors by production context;
  four modern therapy lineages by evidence base), plus recurring cross-node
  synthesis ("can the ethics survive dropping the physics?").
- **Consistent depth.** No fan-page failure. Domain nodes get deep,
  multi-source treatment; Period nodes are deliberately (and explicitly)
  treated as broader era-characterizations to avoid duplicating the evolution
  narrative. The thin early-modern node is justified by the history, not
  padded or starved arbitrarily.
- **Figures.** Two original figures (`taxonomy.svg`, `timeline.svg`), both
  captioned and attributed "Original figure, this survey"; `figure_manifest.py
  check` passes. Broad mode carries only original figures — satisfied.
- **References resolve.** 100 of 101 URLs return HTTP 200 to a direct curl
  check (independently reproduced here). See ADVISORY A1 for the one exception.
- **Gate passes.** `npm run check` is green (CHECK OK).

Additional strength worth recording: the Limitations section is a model of
scholarly transparency — it discloses all 23 access-limited sources (23%)
individually with the exact grounding basis for each, analyzes the concentration
(the CBT-lineage account rests more on secondhand readings than the Roman-Stoa
primary-text account does), names one source dropped entirely (Levi 1964), and
documents the single reference 403 below. This strengthens rather than weakens
the grounding bar.

### ADVISORY (non-blocking)

- **A1: One reference URL (cavanna-2019, `10.2217/fnl-2018-0046`) returns 403,
  not 200.** Reproduced independently — it 403s even with a browser user-agent,
  confirming genuine Taylor & Francis CDN bot-detection of a correctly-cited
  real DOI, not a dead or fabricated link. The survey documents this
  exhaustively (independent WebSearch verification of title/author/journal/DOI,
  every alternate URL form tried). I also searched for a resolving mirror and
  found none currently available (`futuremedicine.com/doi/...` 404s; no PMC copy
  of the 2019 article, unlike its 2023 companion). Because the reference is
  real, correctly attributed, and reachable by a human reader — the 403 being
  purely a curl-vs-CDN artifact — this does not rise to a blocking failure of
  the "references resolve" bar's purpose. If a stable open mirror ever becomes
  available, substitute it.
- **A2: Minor URL inconsistency for the Pigliucci "Stoics as activists" entry
  (`sharpe-2017-stoicism-political-virtue`).** `corpus.json` uses a Wayback
  snapshot URL while `survey.md`'s reference #87 shows the direct Aeon URL. Both
  return 200; purely cosmetic. The underlying re-attribution (Sharpe→Pigliucci,
  2021) is correctly applied in `corpus.json` and documented in the corrections
  record.

Marking done and setting `corpusSize` = 101.
