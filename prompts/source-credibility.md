# Source credibility model — broad-mode surveys

This is the single source of truth for how `broad`-mode surveys (topics outside
science — see `CLAUDE.md`'s intake workflow for the scientific/broad classification
test) select and verify sources. `scientific`-mode surveys ignore this file entirely
and keep reading scientific papers exactly as the `survey-and-taxonomy-research`
skill's own Phase 2/3 describe.

Both `prompts/workers/discovery-worker-broad.md` and
`prompts/workers/reader-worker-broad.md` reference this file rather than
re-stating it — if the tier definitions ever change, change them here once.

## The tiers

Every `broad`-mode source gets exactly one tier, recorded via
`corpus_manifest.py add --tier <1|2|3>`.

- **Tier 1 — Primary / canonical.** The foundational thing itself: the primary text
  of a tradition or its originator's own writing (e.g. Marcus Aurelius' *Meditations*,
  Seneca's *Letters*, Epictetus' *Enchiridion* for a survey of Stoicism); a primary
  empirical study; an official position or report from the authoritative body in the
  domain (e.g. WHO / ILO / APA for work–life balance); the seminal book by a field's
  originator. If the field has an origin text, it belongs here.
- **Tier 2 — Authoritative secondary.** Peer-reviewed papers, university-press and
  established-publisher scholarly books, reference works with editorial authority
  (Stanford Encyclopedia of Philosophy, Encyclopædia Britannica), meta-analyses,
  expert monographs, government or major-NGO reports, recognized-expert textbooks.
- **Tier 3 — Reputable general-interest.** Established outlets with visible
  authorship and sourcing (e.g. The Atlantic, Harvard Business Review, a reputable
  domain-specific publication), recognized-expert long-form journalism, recorded
  lectures or talks by a credentialed practitioner.
- **Excluded — never add to the corpus.** SEO/content-farm blogs, anonymous or
  unsourced listicles, self-published self-help with no visible credentials,
  marketing copy, AI-generated filler, and forum/social-media threads — with one
  narrow exception: when the survey is explicitly *about* an online community or
  discourse and the thread is itself the primary artifact being studied, in which
  case include it as Tier 1 and label it as such in `inclusion_reason`.

## The balance rule

The corpus must be **majority Tier 1–2**, with **Tier 3 capped at roughly 30%**.
This is what keeps a survey of Stoicism anchored in Epictetus and the SEP rather
than in ten thinkpieces that cite each other. `corpus_manifest.py coverage
--source-mode broad` reports the tier breakdown and warns (exit 2 under `--strict`)
when the majority or cap is violated, or when any source has no tier set. The
critique rubric's broad-mode REQUIRED section (`prompts/critique-rubric.md`) treats
this as a hard gate, not a suggestion.

Scientific papers are always welcome in a `broad`-mode corpus — they simply are not
the *only* thing it draws on. A primary empirical study on a `broad` topic is Tier 1
or 2 like any other rigorously sourced work.

## Verifying provenance (replaces the Semantic Scholar / arXiv check)

For each candidate source, before recording it, confirm:

1. **Real, identifiable authorship or attribution.** A named person, or the
   specific issuing body (WHO, APA, a named publisher's editorial board) — never
   an anonymous byline.
2. **The outlet or publisher**, recorded in the manifest's `venue` field (e.g.
   "Harvard Business Review", "Stanford Encyclopedia of Philosophy", "Penguin
   Classics", "self-published" only for a genuinely primary self-authored text
   like a diary or manifesto that earns Tier 1 on its own authority).
3. **A publication or composition year.** For undated/ancient works, use the
   **original composition or first-publication year as a plain integer** (e.g.
   `180` for Marcus Aurelius' *Meditations*, written c. 170–180 CE — use the
   commonly cited single year, not a range; a modern critical edition's year is a
   fallback only when no original date is meaningful). A negative integer is
   acceptable for a genuine BCE case — if one comes up, verify the timeline SVG and
   `corpus_manifest.py refs` still render sanely with it before relying on it.
4. **A stable, resolving URL.** Prefer canonical or archival editions over an
   arbitrary reprint: Project Gutenberg or a named university's classics archive for
   public-domain primary texts, the Stanford Encyclopedia of Philosophy's own page,
   a DOI link, the publisher's or outlet's own page. A bare title with no resolvable
   URL fails the same Phase 8 HTTP-200 gate that governs scientific references —
   there is no separate leniency for `broad` mode here.

Never invent any of the four items above. If a source's authorship, year, or a
resolving URL cannot be verified, leave it out rather than guess — the same rule
`discovery-worker.md` already applies to scientific papers.

## `source_type` (optional, for auditability)

A free-text label recorded via `corpus_manifest.py add --source-type <label>` —
e.g. `book`, `primary-text`, `essay`, `report`, `paper`, `lecture`. It has no gate
of its own; it exists so a reviewer scanning `corpus.json` can see at a glance what
kind of thing each entry is, alongside its tier.
