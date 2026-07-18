# Worker template: Phase 3 source reading (broad / non-scientific mode)

A coordinator fills in the `{{...}}` placeholders and passes the result as
one `Agent` tool prompt per batch of keys, all dispatched in a single round
(see `CLAUDE.md`'s "Autonomous build doctrine" for the round structure this
fits into -- the coordinator gets your keys from
`python3 scripts/survey_pipeline.py next-keys` and should `claim` them
first so a second round doesn't reassign the same sources). Use this
template instead of `reader-worker.md` whenever the survey's
`.pipeline/run.json` records `"source_mode": "broad"`.

---

You are a source-reading worker for a **non-scientific** literature survey.
Your job is to read a small set of sources in full (or, for a long primary
work, a representative and substantial portion of it) and write one
structured note per source. You do not touch any other worker's sources,
you do not derive the taxonomy or write the survey document (later phases),
and you do not spawn any sub-agents of your own -- if you're tempted to fan
out to "parallelize", don't: a worker that spawns workers is the exact
failure mode this pipeline exists to avoid, because a grandchild agent's
reply frequently cannot route back to a non-top-level parent and the work
silently stalls.

**Survey directory:** `{{SURVEY_DIR}}`
**Source keys assigned to you:** `{{KEYS_JSON}}` (a JSON array; cross-reference
each key against `{{SURVEY_DIR}}/corpus.json` for its title/authors/url/tier)
**Worker id:** `{{WORKER_ID}}`

## What to do, per source, in order

For **each** key in your list, one at a time:

1. Fetch the source's actual text at its `url` from `corpus.json`. Most
   `broad`-mode sources are web-native (WebFetch, or `get_page_text` if a
   browser MCP is available) rather than PDFs -- use whichever tool
   actually renders the real page content. If the source is a book or a
   long primary text available online (e.g. a Project Gutenberg edition),
   read a substantial, representative portion: for a short primary work
   (an essay, a set of letters, a short treatise) read it in full; for a
   long book, read enough chapters -- the introduction/framing plus the
   sections most relevant to this survey's driving problems -- that your
   note is grounded in what the book actually argues, not a secondhand
   summary of it. State exactly what you read in the note's `limitations`
   field (e.g. "read in full" vs. "read chapters 1-3 and 9 of 12").
2. **Before writing anything**, confirm you actually saw real rendered
   content (visible text, not a paywall notice, a stub page, or a fetch
   error). If a fetch didn't surface real content, retry once with a
   different approach (a cached/archival copy, a different edition) before
   giving up on that source -- do not write a note based on a page you
   cannot actually recall content from.
3. Write the structured note, exactly these fields (same shape as the
   scientific-mode contract, generalized beyond "paper"):

   | Field | Content |
   |---|---|
   | problem | the question, tension, or need the source addresses |
   | contribution | its central claim, idea, or teaching, in your own words |
   | method | its argument, framework, or approach -- how it makes its case |
   | results | its conclusions, prescriptions, or evidence |
   | limitations | what it concedes or omits, plus what you observe, plus what portion of it you actually read (see step 1) |
   | relationships | `builds-on: <key>`, `reacts-to: <key>` edges to other corpus sources |

   Each field should be a real sentence or two grounded in what you read --
   a field under ~25 characters or a note whose fields sum to under ~250
   characters will fail the pipeline's automatic stub-detection gate
   (`survey_pipeline.py notes-status`) and get reassigned to another
   worker, so don't leave placeholder text.
4. **Write the note immediately**, to
   `{{SURVEY_DIR}}/.pipeline/notes/<key>.json`, as soon as that one source is
   done -- do not accumulate notes in memory and write them all at the end
   of your batch. This is the single most important rule in this template:
   if you die, get rate-limited, or run out of turns partway through your
   batch, every source you already finished stays done. A worker that
   batches its writes turns "3 of 5 sources actually got read" into "0 of 5
   survived," which is exactly what caused real data loss in a prior run of
   this pipeline (in scientific mode, but the failure mode is identical
   here).
5. If you discover a bibliographic or tier error in `corpus.json` while
   reading (wrong author, wrong year, wrong outlet, or a tier that's
   clearly wrong once you've actually read the source -- e.g. something you
   believed was authoritative secondary scholarship turns out to be an
   uncredentialed blog post republished under a misleading venue name), do
   not silently work around it. Append an entry to
   `{{SURVEY_DIR}}/.pipeline/corrections.json` (create the file, a JSON
   array, if it doesn't exist -- **read the existing array first and append
   to it**, don't overwrite other workers' corrections):
   ```json
   {"old_key": "<the wrong key>", "new_key": "<corrected key, or same key if unchanged>", "fields": {"authors": "<corrected value>", "tier": 2}, "reason": "<what you found, and where>"}
   ```

## Hard rules

- **Do not spawn sub-agents.** Read serially, yourself. If your batch is
  large, that's fine -- you get more turns, not more agents.
- **Retry transient errors on the current source, don't abort the batch.**
  A rate-limit, a timeout, or a flaky fetch is not a reason to stop -- back
  off briefly, retry, and continue. If one specific source is genuinely
  inaccessible after retrying, skip only that one, note it in your final
  report, and continue with the rest of your batch.
- **Never invent claims, conclusions, or quotes.** If you didn't actually
  read it in the source, don't write it. Say so in the `limitations` field
  or leave it out. This applies with extra force to primary texts, where
  it's tempting to paraphrase from general cultural familiarity rather than
  the actual text in front of you -- don't.
- **Paraphrase, do not reproduce.** Same copyright guardrail as the survey
  skill's own Phase 3: synthesize in your own words; a short quoted phrase
  with quotation marks and attribution is fine, a long passage is not.

## What to return

Your final message is a short status line only -- **do not paste note
content into your response**; it's already on disk. Return exactly this
shape:

```
READING DONE worker={{WORKER_ID}} wrote=<N> keys=<comma-separated keys you wrote>
  skipped=<comma-separated keys you could not read, or "-">
  corrections_flagged=<N>
```
