# Worker template: Phase 6-7 document fragment

A coordinator fills in the `{{...}}` placeholders and passes the result as
one `Agent` tool prompt per fragment, all dispatched in a single round (see
`CLAUDE.md`'s "Autonomous build doctrine" for the round structure this fits
into -- the coordinator gets the missing/stub fragment list from
`python3 scripts/survey_pipeline.py sections-status {{SURVEY_DIR}}`).

This template covers the heaviest, most numerous fragment: one
`20-method-<node-slug>.md` per taxonomy node (Phase 7's "per-method treatment"
step). The six fixed-part fragments (`00-scope`, `10-taxonomy`, `30-evolution`,
`40-comparison`, `50-limitations`, `90-references`) are usually written
directly by the coordinator instead, since there's exactly one of each and no
fan-out benefit -- but the same per-item-immediately rule applies if the
coordinator ever dispatches one of those as its own worker too.

---

You are a section-writing worker for a literature survey. Your job is
narrow: write the method-treatment section for ONE taxonomy node, then write
it to a file. You do not touch any other node's fragment, you do not derive
the taxonomy or decide node placement (Phase 5, already done), and you do
not spawn any sub-agents of your own -- a worker that fans out further is
the exact failure mode this pipeline exists to avoid.

**Survey directory:** `{{SURVEY_DIR}}`
**Taxonomy node:** `{{NODE}}` (e.g. `architecture-variants/conditional-gans`)
**Fragment path:** `{{SURVEY_DIR}}/.pipeline/sections/20-method-{{NODE_SLUG}}.md`
**Member papers:** `{{MEMBER_KEYS_JSON}}` (a JSON array of corpus keys placed
on this node; cross-reference each against `{{SURVEY_DIR}}/corpus.json` for
bibliographic data and `{{SURVEY_DIR}}/.pipeline/notes/<key>.json` for the
structured reading notes -- read the notes, don't re-read the PDFs)

## What to write

Per the skill's Phase 7 part 3 ("per-method treatment at consistent depth"):
what problem this node targets, its key idea, and how it differs from
sibling nodes. Ground every claim in the member papers' notes -- cite by key.
Match the depth of other `20-method-*.md` fragments already on disk (skim
one if any exist) so no node gets three paragraphs while its sibling gets
one line -- the "fan page" failure mode the critique rubric explicitly
checks for.

## Hard rules

- **Do not spawn sub-agents.** Write serially, yourself.
- **Write the fragment immediately** to
  `{{SURVEY_DIR}}/.pipeline/sections/20-method-{{NODE_SLUG}}.md` as soon as
  it's done -- this is one file, so there's no partial-batch risk the way
  Phase 3 reading has, but write it directly to that path rather than
  returning the text in your final message; the coordinator reads the
  filesystem, not your reply.
- **No TODO markers, no placeholder text.** A fragment under ~80 characters
  or containing the literal string `TODO:` fails the pipeline's automatic
  stub-detection gate (`survey_pipeline.py sections-status`) and gets
  reassigned to another worker.
- **Never invent claims.** If a member paper's note doesn't support a claim
  you want to make, don't make it -- ground everything in the notes.

## What to return

Your final message is a short status line only -- **do not paste the
fragment content into your response**; it's already on disk. Return exactly
this shape:

```
SECTION DONE node={{NODE}} file=.pipeline/sections/20-method-{{NODE_SLUG}}.md chars=<N>
```

or, if you hit a genuine blocker you could not work around:

```
SECTION BLOCKED node={{NODE}} reason=<one line>
```
