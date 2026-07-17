verdict: approve

## Critique round 1 -- 2026-07-17

**Reviewer:** critic (fresh-eyes, Opus). Reviewed only on-disk artifacts:
`survey.md`, `refs.md`, `corpus.json`, `figures.json`, and `.pipeline/notes/`.

### Summary

This is a strong survey that misses approval on a single, localized but
genuine grounding defect: throughout Section 3.1 (the B-lineage node) three
papers are cited to reference numbers that resolve to unrelated papers. A
reader chasing those citations lands on the wrong article, so the affected
method claims do not trace to a corpus paper by reference number as the rubric
requires. The error is silent (each wrong number is itself a live reference to
a real but off-topic paper), mechanical to fix, and confined to one node --
every other section, including the Evolution Narrative and the Section 5
aggregate tables, uses the correct numbering. Nothing else blocks approval.

Objective checks all pass on the current artifacts:
- `corpus_manifest.py coverage --strict`: OK (67 papers, 8 subareas 6-13 each,
  none over half, none under 2).
- `figure_manifest.py check`: OK (1 figure verified against the document).
- `survey_pipeline.py status`: all 8 phases gate_passed.
- `npm run check`: CHECK OK (green).

On the merits the survey clears the hard bars. The two-axis taxonomy
(lineage x maturation stage) is genuinely derived and justified, all 67 papers
are placed with 12 cross-cutting standardization papers at root. Higher-level
insight is real: the Evolution Narrative has causal structure (EGIL ->
Bethesda -> EuroFlow; the recurring "reference-pattern -> discriminator ->
standardize" cycle named lineage by lineage), and there are multiple genuine
cross-cutting comparisons (Section 5.2 master population x marker matrices,
Section 5.3 the four named discriminator problems). Depth is consistent -- the
2-paper nodes (3.5-3.7, 3.9) each still carry full problem framing, a marker
table, and a sibling contrast; none reads as a stub. The single original
taxonomy figure is licensing-clean. The 67-paper corpus is defended with a
convincing written justification (the "clinically utilized" flow literature is
structurally concentrated around a small set of consensus/standardization
anchors plus short per-lineage landmark chains), which I accept for this
clinical subfield. The abstract-only sourcing (19/67) and the four
bot-walled-but-live reference URLs are disclosed honestly and per-item in
Section 6 rather than hidden.

REQUIRED findings: 1. ADVISORY findings: 2.

### REQUIRED (blocks approval)

- [x] R1: **Section 3.1 miscites three papers to reference numbers that
  resolve to unrelated corpus papers.** In the B-lineage node body prose and
  its marker table, the printed citation numbers do not match `refs.md`:
    - **Li et al. 2002** (surface-Ig light-chain absence as a clonality
      surrogate) is cited as **[10]**, but `refs.md` [10] is Rawstron 2002
      (plasma-cell myeloma MRD). Correct number is **[9]**.
    - **Huang et al. 2023** (four-pattern sIg-negative framework) is cited as
      **[57]**, but `refs.md` [57] is Seheult 2023 (NK-cell receptor
      restriction). Correct number is **[55]**.
    - **Velounias-Tull 2023** (mature B-cell subset review) is cited as
      **[56]**, but `refs.md` [56] is Kern 2023 (iMDS flow). Correct number is
      **[58]**.

  This is a grounding failure per the rubric: following these numbers leads a
  verifier to the wrong papers (e.g. Section 3.1's light-chain-restriction
  claim points at Rawstron's myeloma paper). I confirmed the underlying claims
  themselves ARE grounded -- `.pipeline/notes/huang-2023-...json`,
  `li-2002-...json`, and `velounias-tull-2023-...json` all exist and support
  the prose -- so this is a stale-numbering error from a corpus renumber, not
  fabrication. It is also confirmed localized: Section 4, Section 5.2.2's
  citation line (`[1][8][9][11][30][33][55][58]`), Section 5.3, and the
  Section 3.11 cross-lineage lists all already use the correct numbers, and
  [10]/[56]/[57] are used CORRECTLY (Rawstron/Kern/Seheult) everywhere OUTSIDE
  Section 3.1.

  Fix, scoped strictly to Section 3.1 (do not touch [10], [56], or [57] in any
  other section, where they are correct):
    - Replace every Li-2002 citation `[10]` -> `[9]` (appears in the
      opening problem paragraph, the "mature side" paragraph, the marker
      table's surface-light-chain row, and the abstract-only-papers sentence
      "([1], [8], [10], [11], [30])" which should read "([1], [8], [9],
      [11], [30])").
    - Replace every Huang-2023 citation `[57]` -> `[55]` (opening problem
      paragraph, "mature side" paragraph, marker table light-chain row).
    - Replace every Velounias-Tull-2023 citation `[56]` -> `[58]` (opening
      problem paragraph, "mature side" paragraph, and the CD10/CD38/CD27/IgD
      marker-table rows).
    - After the fix, re-verify that the node's stated member set is the
      intended `{1, 8, 9, 11, 30, 33, 55, 58}` and that no `[10]`, `[56]`, or
      `[57]` remains inside Section 3.1.

### ADVISORY (does not block approval)

- A1: Section 3.1's abstract-only-papers sentence currently reads "Five of the
  eight papers in this node ([1], [8], [10], [11], [30]) were accessible only
  at abstract level." Once R1 is applied this becomes [9] not [10]; while
  fixing, sanity-check that the abstract-only set named here still matches the
  per-paper access flags recorded for those papers (Loken 1987, McKenna 2001,
  Li 2002, McKenna 2004, Challagundla 2014).

- A2: Minor prose consistency -- the B-lineage node is the survey's most
  citation-dense passage and would benefit from one final read-through after
  R1 to confirm every bracketed number in its table cells resolves to the
  paper the cell's claim actually comes from (spot-check only; the systematic
  error is the three papers named in R1).

## Critique round 2 -- 2026-07-17

**Reviewer:** critic (fresh-eyes, Opus). Verdict: **approve**. Re-verified only
the R1 fix and the objective gates against on-disk artifacts, per the rubric's
anti-oscillation rule -- I did not re-audit the survey-wide numbering that round
1 already swept and confirmed localized to Section 3.1.

### R1 confirmed fixed

Read Section 3.1 directly against `refs.md`. All three miscitations are now
correct and confined to the intended member set `{1, 8, 9, 11, 30, 33, 55, 58}`:

- **Li 2002** now cites **[9]** (refs.md [9] = Li 2002) -- opening problem
  paragraph, mature-side paragraph, marker table surface-light-chain row, and
  the sibling-contrast paragraph.
- **Huang 2023** now cites **[55]** (refs.md [55] = Huang 2023) -- opening
  paragraph, mature-side paragraph, marker table light-chain row.
- **Velounias-Tull 2023** now cites **[58]** (refs.md [58] = Velounias-Tull
  2023) -- opening paragraph, mature-side paragraph, CD10/CD38/CD27/IgD marker
  rows.

Mechanical check confirmed **no `[10]`, `[56]`, or `[57]` appears anywhere in
Section 3.1** (lines 30-53), so the stale numbers that belonged to
Rawstron/Kern/Seheult no longer misroute a verifier inside this node. Those
three numbers remain correctly used in the sections outside 3.1 (untouched).

### ADVISORY items from round 1

- **A1 resolved:** the abstract-only-papers sentence now reads "Five of the
  eight papers in this node ([1], [8], [9], [11], [30]) were accessible only at
  abstract level" -- [10] correctly replaced by [9], and the named set
  (Loken 1987, McKenna 2001, Li 2002, McKenna 2004, Challagundla 2014) matches
  those five reference numbers.
- **A2 spot-check:** the marker table's bracketed citations
  ([1][33], [11], [8][11][33], [58], [33][58], [9][55], [30]) each resolve to a
  paper whose claim supports the cell. No residual mismatch found.

### Objective gates (all green on current artifacts)

- `corpus_manifest.py coverage --strict`: OK (67 papers; 8 subareas 6-13 each;
  none over half, none under 2).
- `figure_manifest.py check`: OK (1 figure verified against the document).
- `survey_pipeline.py status`: all 8 phases gate_passed.
- `npm run check`: CHECK OK (green).

REQUIRED findings this round: 0. ADVISORY: 0 open (both round-1 advisories
resolved). Approving and marking done; setting `corpusSize` to 67.
