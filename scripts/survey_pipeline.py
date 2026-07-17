#!/usr/bin/env python3
"""Resumability spine for an autonomous survey build (Phases 2-3 of the
survey-and-taxonomy-research skill: corpus discovery and paper reading).

Problem this solves: a build that hands work off to parallel sub-agents via
messages is fragile -- a reply can misroute, a worker can stall with no
output, a worker can die on a transient error, and the coordinator has no way
to tell "still working" from "silently lost" except by waiting and guessing.

The fix is to make every handoff a FILE, not a message. Workers write one
output file per unit of work to a deterministic path under
<survey-dir>/.pipeline/ (already covered by .gitignore's ".pipeline/" entry
at any depth -- these are working artifacts, never deliverables). The
coordinator discovers what's done by reading the filesystem, never by
waiting on a reply. Re-running any command is always safe: it only reports
or acts on what is actually missing or invalid.

Layout under <survey-dir>/.pipeline/:

    candidates/<subarea>.json   one array of candidate papers per discovery
                                 worker (Phase 2)
    corrections.json            array of bibliographic fixes flagged by
                                 readers (e.g. a misattributed author),
                                 applied idempotently to corpus.json
    notes/<key>.json             one structured note per corpus paper,
                                 keyed to corpus.json's paper "key" (Phase 3)
    claims/<key>.claim           empty marker file; its mtime is the claim
                                 time. Lets a coordinator avoid re-dispatching
                                 a key a live worker is already covering,
                                 without any message-passing.

Python 3 stdlib only. Exit codes: 0 = success / gate passed, 1 = usage or
data error, 2 = gate not yet satisfied (mirrors corpus_manifest.py's
--strict convention: 2 means "keep working", not "something is broken").
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

NOTE_FIELDS = ("problem", "contribution", "method", "results", "limitations", "relationships")
MIN_FIELD_CHARS = 25
MIN_NOTE_CHARS = 250
DEFAULT_STALE_SECONDS = 900  # 15 min: generous for a single-paper read+write


# ---- shared helpers -----------------------------------------------------

def pipeline_dir(survey_dir: Path) -> Path:
    return survey_dir / ".pipeline"


def notes_dir(survey_dir: Path) -> Path:
    return pipeline_dir(survey_dir) / "notes"


def candidates_dir(survey_dir: Path) -> Path:
    return pipeline_dir(survey_dir) / "candidates"


def claims_dir(survey_dir: Path) -> Path:
    return pipeline_dir(survey_dir) / "claims"


def corrections_path(survey_dir: Path) -> Path:
    return pipeline_dir(survey_dir) / "corrections.json"


def corpus_path(survey_dir: Path) -> Path:
    return survey_dir / "corpus.json"


def load_json(path: Path):
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as e:
        sys.exit(f"ERROR: {path} is not valid JSON: {e}")


def load_corpus_keys(survey_dir: Path) -> list[str]:
    p = corpus_path(survey_dir)
    if not p.exists():
        sys.exit(f"ERROR: {p} not found -- assemble the corpus (apply-candidates) first")
    data = load_json(p)
    papers = data.get("papers", [])
    if not papers:
        sys.exit(f"ERROR: {p} has zero papers -- nothing to read yet")
    return [paper["key"] for paper in papers]


def normalize_url_id(url: str) -> str | None:
    """Extract a stable identifier from a URL for dedup, e.g. an arXiv id.
    Returns None if no recognizable id pattern is found (caller falls back
    to normalized title)."""
    m = re.search(r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})", url, re.IGNORECASE)
    if m:
        return f"arxiv:{m.group(1)}"
    m = re.search(r"aclanthology\.org/([A-Za-z0-9.\-]+)", url, re.IGNORECASE)
    if m:
        return f"acl:{m.group(1).rstrip('.pdf').lower()}"
    return None


def normalize_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", title.lower())


def dedup_id_for(paper: dict) -> str:
    url_id = normalize_url_id(paper.get("url", ""))
    if url_id:
        return url_id
    return "title:" + normalize_title(paper.get("title", ""))


# ---- notes-status / next-keys (Phase 3: reading) -------------------------

def validate_note(note: dict) -> list[str]:
    """Return a list of problems with a note; empty list means valid.
    Catches missing fields AND the silent-truncation failure mode (a Read
    call that returns a confirmation but no rendered content, which some
    workers this pipeline replaced produced without noticing) by requiring
    a minimum length per field and in total."""
    problems = []
    if not isinstance(note, dict):
        return ["not a JSON object"]
    for field in NOTE_FIELDS:
        val = note.get(field)
        if val is None:
            problems.append(f"missing field '{field}'")
            continue
        text = val if isinstance(val, str) else json.dumps(val)
        if len(text.strip()) < MIN_FIELD_CHARS:
            problems.append(
                f"field '{field}' is only {len(text.strip())} chars "
                f"(< {MIN_FIELD_CHARS}) -- looks like a stub, not a real read"
            )
    total_chars = sum(
        len(note[f] if isinstance(note[f], str) else json.dumps(note[f]))
        for f in NOTE_FIELDS if f in note
    )
    if total_chars < MIN_NOTE_CHARS:
        problems.append(
            f"total note content is only {total_chars} chars (< {MIN_NOTE_CHARS}) "
            f"-- looks truncated"
        )
    return problems


def cmd_notes_status(args):
    survey_dir = Path(args.survey_dir)
    keys = load_corpus_keys(survey_dir)
    ndir = notes_dir(survey_dir)

    missing, invalid, valid = [], [], []
    for key in keys:
        note_path = ndir / f"{key}.json"
        if not note_path.exists():
            missing.append(key)
            continue
        note = load_json(note_path)
        problems = validate_note(note)
        if problems:
            invalid.append((key, problems))
        else:
            valid.append(key)

    print(f"Notes status for {survey_dir.name}: {len(keys)} papers in corpus")
    print(f"  valid:   {len(valid)}")
    print(f"  missing: {len(missing)}")
    print(f"  invalid: {len(invalid)}")
    if missing:
        print(f"\nMissing ({len(missing)}): " + ", ".join(missing))
    if invalid:
        print(f"\nInvalid ({len(invalid)}):")
        for key, problems in invalid:
            print(f"  {key}:")
            for p in problems:
                print(f"    - {p}")

    if missing or invalid:
        print(f"\nNOT DONE: {len(missing) + len(invalid)} of {len(keys)} papers still need work.")
        return 2
    print("\nALL DONE: every corpus paper has a valid note.")
    return 0


def _stale_cutoff(stale_after_seconds: int) -> float:
    return time.time() - stale_after_seconds


def _inflight_keys(survey_dir: Path, stale_after_seconds: int) -> set[str]:
    cdir = claims_dir(survey_dir)
    if not cdir.exists():
        return set()
    cutoff = _stale_cutoff(stale_after_seconds)
    live = set()
    for claim_file in cdir.glob("*.claim"):
        if claim_file.stat().st_mtime >= cutoff:
            live.add(claim_file.stem)
    return live


def cmd_next_keys(args):
    survey_dir = Path(args.survey_dir)
    keys = load_corpus_keys(survey_dir)
    ndir = notes_dir(survey_dir)

    outstanding = []
    for key in keys:
        note_path = ndir / f"{key}.json"
        if not note_path.exists():
            outstanding.append(key)
            continue
        if validate_note(load_json(note_path)):
            outstanding.append(key)

    if args.exclude_inflight:
        inflight = _inflight_keys(survey_dir, args.stale_after_seconds)
        outstanding = [k for k in outstanding if k not in inflight]

    result = outstanding[: args.limit] if args.limit else outstanding
    print(json.dumps(result))
    return 0


def cmd_claim(args):
    survey_dir = Path(args.survey_dir)
    cdir = claims_dir(survey_dir)
    cdir.mkdir(parents=True, exist_ok=True)
    cutoff = _stale_cutoff(args.stale_after_seconds)

    claimed, refused = [], []
    for key in args.keys.split(","):
        key = key.strip()
        if not key:
            continue
        claim_file = cdir / f"{key}.claim"
        owner_file = cdir / f"{key}.owner"
        if claim_file.exists() and claim_file.stat().st_mtime >= cutoff:
            owner = owner_file.read_text().strip() if owner_file.exists() else "?"
            if owner != args.worker_id:
                refused.append(key)
                continue
        claim_file.touch()
        owner_file.write_text(args.worker_id)
        claimed.append(key)

    print(json.dumps({"claimed": claimed, "refused_live_elsewhere": refused}))
    return 0 if not refused else 2


# ---- candidates-status / apply-candidates (Phase 2: discovery) ----------

CANDIDATE_FIELDS = ("suggested_key", "title", "authors", "year", "venue", "url",
                     "inclusion_reason", "subarea")


def validate_candidate(c: dict) -> list[str]:
    problems = []
    for field in CANDIDATE_FIELDS:
        if not str(c.get(field, "")).strip():
            problems.append(f"missing/empty field '{field}'")
    return problems


def cmd_candidates_status(args):
    survey_dir = Path(args.survey_dir)
    cdir = candidates_dir(survey_dir)
    present = sorted(p.stem for p in cdir.glob("*.json")) if cdir.exists() else []

    expected = [s.strip() for s in args.expected.split(",") if s.strip()] if args.expected else None
    missing_subareas = [s for s in expected if s not in present] if expected else []

    total_candidates = 0
    invalid_files = []
    for subarea in present:
        data = load_json(cdir / f"{subarea}.json")
        if not isinstance(data, list):
            invalid_files.append((subarea, "not a JSON array"))
            continue
        bad = [validate_candidate(c) for c in data]
        bad = [b for b in bad if b]
        if bad:
            invalid_files.append((subarea, f"{len(bad)} of {len(data)} candidates invalid"))
        total_candidates += len(data)

    print(f"Candidates status for {survey_dir.name}:")
    print(f"  subarea files present: {len(present)} ({', '.join(present) or '-'})")
    print(f"  total candidates: {total_candidates}")
    if expected:
        print(f"  expected subareas: {', '.join(expected)}")
        print(f"  missing subareas: {', '.join(missing_subareas) or '-'}")
    if invalid_files:
        print("  invalid files:")
        for subarea, reason in invalid_files:
            print(f"    {subarea}: {reason}")

    if missing_subareas or invalid_files:
        return 2
    return 0


def cmd_apply_candidates(args):
    survey_dir = Path(args.survey_dir)
    cdir = candidates_dir(survey_dir)
    if not cdir.exists():
        sys.exit(f"ERROR: {cdir} does not exist -- no discovery workers have written candidates yet")

    cpath = corpus_path(survey_dir)
    if cpath.exists():
        corpus = load_json(cpath)
    else:
        if not args.topic:
            sys.exit(f"ERROR: {cpath} does not exist and --topic not given to initialize it")
        corpus = {"topic": args.topic, "scope": args.scope or "", "papers": []}

    seen_ids = {dedup_id_for(p) for p in corpus["papers"]}
    seen_keys = {p["key"] for p in corpus["papers"]}

    added, skipped_dupe, skipped_key_collision = [], [], []
    for subarea_file in sorted(cdir.glob("*.json")):
        candidates = load_json(subarea_file)
        for c in candidates:
            problems = validate_candidate(c)
            if problems:
                print(f"  skip (invalid): {c.get('suggested_key', '?')} -- {'; '.join(problems)}")
                continue
            dedup_id = dedup_id_for({"url": c["url"], "title": c["title"]})
            if dedup_id in seen_ids:
                skipped_dupe.append(c["suggested_key"])
                continue
            key = c["suggested_key"]
            if key in seen_keys:
                # same URL/title not yet seen under this exact key -- suffix to avoid collision
                suffix = 2
                new_key = f"{key}-{suffix}"
                while new_key in seen_keys:
                    suffix += 1
                    new_key = f"{key}-{suffix}"
                skipped_key_collision.append((key, new_key))
                key = new_key
            corpus["papers"].append({
                "key": key, "title": c["title"], "authors": c["authors"],
                "year": int(c["year"]), "venue": c["venue"], "url": c["url"],
                "inclusion_reason": c["inclusion_reason"], "subarea": c["subarea"],
                "taxonomy_node": "",
            })
            seen_ids.add(dedup_id)
            seen_keys.add(key)
            added.append(key)

    cpath.write_text(json.dumps(corpus, indent=2, ensure_ascii=False) + "\n")
    print(f"Added {len(added)} papers to {cpath} ({len(corpus['papers'])} total).")
    print(f"Skipped {len(skipped_dupe)} exact duplicates (same arXiv id / normalized title).")
    if skipped_key_collision:
        print(f"Renamed {len(skipped_key_collision)} key collisions (different paper, same suggested key):")
        for old, new in skipped_key_collision:
            print(f"  {old} -> {new}")
    return 0


# ---- apply-corrections ----------------------------------------------------

def cmd_apply_corrections(args):
    survey_dir = Path(args.survey_dir)
    corr_path = corrections_path(survey_dir)
    if not corr_path.exists():
        print("No corrections.json -- nothing to apply.")
        return 0

    corrections = load_json(corr_path)
    cpath = corpus_path(survey_dir)
    corpus = load_json(cpath)
    by_key = {p["key"]: p for p in corpus["papers"]}

    applied, already, errors = [], [], []
    for i, corr in enumerate(corrections):
        if corr.get("applied"):
            already.append(corr.get("old_key", f"#{i}"))
            continue
        old_key = corr.get("old_key")
        new_key = corr.get("new_key", old_key)
        fields = corr.get("fields", {})
        if old_key not in by_key:
            errors.append(f"correction #{i}: old_key '{old_key}' not found in corpus (already renamed?)")
            corr["applied"] = True
            corr["apply_note"] = "skipped: old_key not found"
            continue

        paper = by_key.pop(old_key)
        paper["key"] = new_key
        for field, value in fields.items():
            paper[field] = value
        by_key[new_key] = paper

        # keep the note file in sync so Phase 3 output doesn't cite a dead key
        old_note = notes_dir(survey_dir) / f"{old_key}.json"
        if old_note.exists() and new_key != old_key:
            new_note = notes_dir(survey_dir) / f"{new_key}.json"
            old_note.rename(new_note)
            text = new_note.read_text()
            if old_key in text:
                new_note.write_text(text.replace(old_key, new_key))

        corr["applied"] = True
        applied.append(f"{old_key} -> {new_key}")

    corpus["papers"] = list(by_key.values())
    cpath.write_text(json.dumps(corpus, indent=2, ensure_ascii=False) + "\n")
    corr_path.write_text(json.dumps(corrections, indent=2, ensure_ascii=False) + "\n")

    print(f"Applied {len(applied)} correction(s):")
    for a in applied:
        print(f"  {a}")
    if already:
        print(f"Already applied (skipped): {len(already)}")
    if errors:
        print("Errors:")
        for e in errors:
            print(f"  {e}")
        return 1
    return 0


# ---- CLI ------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("notes-status", help="check Phase 3 reading completeness against corpus.json")
    p.add_argument("survey_dir")
    p.set_defaults(func=cmd_notes_status)

    p = sub.add_parser("next-keys", help="list paper keys still missing/invalid notes")
    p.add_argument("survey_dir")
    p.add_argument("--limit", type=int, default=0, help="0 = no limit")
    p.add_argument("--exclude-inflight", action="store_true",
                    help="exclude keys with a live (non-stale) claim")
    p.add_argument("--stale-after-seconds", type=int, default=DEFAULT_STALE_SECONDS)
    p.set_defaults(func=cmd_next_keys)

    p = sub.add_parser("claim", help="mark keys as being worked on, so next-keys can skip them")
    p.add_argument("survey_dir")
    p.add_argument("--keys", required=True, help="comma-separated paper keys")
    p.add_argument("--worker-id", required=True)
    p.add_argument("--stale-after-seconds", type=int, default=DEFAULT_STALE_SECONDS)
    p.set_defaults(func=cmd_claim)

    p = sub.add_parser("candidates-status", help="check Phase 2 discovery-file completeness")
    p.add_argument("survey_dir")
    p.add_argument("--expected", default="",
                    help="comma-separated subarea names the coordinator dispatched")
    p.set_defaults(func=cmd_candidates_status)

    p = sub.add_parser("apply-candidates",
                        help="dedup all candidates/*.json and merge into corpus.json")
    p.add_argument("survey_dir")
    p.add_argument("--topic", help="required if corpus.json does not exist yet")
    p.add_argument("--scope", default="")
    p.set_defaults(func=cmd_apply_candidates)

    p = sub.add_parser("apply-corrections",
                        help="apply corrections.json fixes to corpus.json + notes/, idempotently")
    p.add_argument("survey_dir")
    p.set_defaults(func=cmd_apply_corrections)

    args = ap.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
