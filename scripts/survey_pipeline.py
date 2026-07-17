#!/usr/bin/env python3
"""Resumability spine for an autonomous survey build (all 8 phases of the
survey-and-taxonomy-research skill: scope, discovery, reading, figures,
taxonomy, narrative, assembly, verification).

Problem this solves: a build that hands work off to parallel sub-agents via
messages is fragile -- a reply can misroute, a worker can stall with no
output, a worker can die on a transient error, and the coordinator has no way
to tell "still working" from "silently lost" except by waiting and guessing.
A build can also simply run out of tokens mid-phase and need to resume in a
fresh session that has no memory of what happened.

The fix is to make every handoff a FILE, not a message, and to make "what
phase are we on" a question answered by reading the filesystem, never by
recalling conversation history. Workers write one output file per unit of
work to a deterministic path under <survey-dir>/.pipeline/ (already covered
by .gitignore's ".pipeline/" entry at any depth -- these are working
artifacts, never deliverables). The coordinator discovers what's done by
reading the filesystem. Re-running any command is always safe: it only
reports or acts on what is actually missing or invalid, and `status` always
trusts the disk over any ledger when the two disagree.

Layout under <survey-dir>/.pipeline/:

    run.json                    resumability ledger: scope, driving problems,
                                 planned subareas, and a per-phase status map
                                 (Phases 1-8). Advisory -- `status` recomputes
                                 the truth from disk and overwrites this to
                                 match every time it runs, so a missing or
                                 stale run.json always self-heals.
    candidates/<subarea>.json   one array of candidate papers per discovery
                                 worker (Phase 2)
    corrections.json            array of bibliographic fixes flagged by
                                 readers (e.g. a misattributed author),
                                 applied idempotently to corpus.json
    notes/<key>.json             one structured note per corpus paper,
                                 keyed to corpus.json's paper "key" (Phase 3)
    claims/<key>.claim          empty marker file; its mtime is the claim
                                 time. Lets a coordinator avoid re-dispatching
                                 a key a live worker is already covering,
                                 without any message-passing.
    figures-attempted/<key>     empty marker file. A figure-extraction worker
                                 touches this when it tried a paper and found
                                 nothing embeddable (restricted license,
                                 vector-only art) -- lets a resuming session
                                 tell "not attempted" from "attempted, no
                                 figure" instead of re-scanning every PDF.
    sections/<NN>-<slug>.md     one markdown fragment per structural part of
                                 the final document (Phases 6-7), flushed the
                                 moment it's drafted. `assemble-sections`
                                 concatenates them into survey.md. A build
                                 that never adopts fragments (writes survey.md
                                 directly) is still resumable via `status`'s
                                 whole-file fallback -- see cmd_status.

Everything under .pipeline/ is safe to delete once a topic reaches `done`:
it is either already folded into corpus.json/figures.json/survey.md, or was
scratch work.

Python 3 stdlib only. Exit codes: 0 = success / gate passed, 1 = usage or
data error, 2 = gate not yet satisfied (mirrors corpus_manifest.py's
--strict convention: 2 means "keep working", not "something is broken").

Every command that touches content/registry.json, prompts/queue.md, or
content/critiques/ assumes it is run from the repo root (same convention as
mark.py and decide.py).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import validate as V

NOTE_FIELDS = ("problem", "contribution", "method", "results", "limitations", "relationships")
MIN_FIELD_CHARS = 25
MIN_NOTE_CHARS = 250
MIN_SECTION_CHARS = 80
DEFAULT_STALE_SECONDS = 900  # 15 min: generous for a single-paper read+write

PHASES = tuple(range(1, 9))
PHASE_NAMES = {
    1: "scope", 2: "corpus", 3: "reading", 4: "figures",
    5: "taxonomy", 6: "narrative", 7: "assemble", 8: "verify",
}
PHASE_STATUSES = ("not_started", "in_progress", "gate_passed")

FIXED_SECTIONS_PRE = ("00-scope", "10-taxonomy")
FIXED_SECTIONS_POST = ("30-evolution", "40-comparison", "50-limitations", "90-references")


# ---- shared helpers -----------------------------------------------------

def pipeline_dir(survey_dir: Path) -> Path:
    return survey_dir / ".pipeline"


def notes_dir(survey_dir: Path) -> Path:
    return pipeline_dir(survey_dir) / "notes"


def candidates_dir(survey_dir: Path) -> Path:
    return pipeline_dir(survey_dir) / "candidates"


def claims_dir(survey_dir: Path) -> Path:
    return pipeline_dir(survey_dir) / "claims"


def figures_attempted_dir(survey_dir: Path) -> Path:
    return pipeline_dir(survey_dir) / "figures-attempted"


def sections_dir(survey_dir: Path) -> Path:
    return pipeline_dir(survey_dir) / "sections"


def corrections_path(survey_dir: Path) -> Path:
    return pipeline_dir(survey_dir) / "corrections.json"


def run_json_path(survey_dir: Path) -> Path:
    return pipeline_dir(survey_dir) / "run.json"


def corpus_path(survey_dir: Path) -> Path:
    return survey_dir / "corpus.json"


def figures_json_path(survey_dir: Path) -> Path:
    return survey_dir / "figures.json"


def scripts_dir() -> Path:
    return Path(__file__).resolve().parent


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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


def _load_corpus_keys_safe(survey_dir: Path) -> list[str] | None:
    """Like load_corpus_keys, but returns None instead of exiting -- for
    internal status/scan use, where one survey's missing corpus.json must
    not kill a loop over many surveys."""
    p = corpus_path(survey_dir)
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text())
    except json.JSONDecodeError:
        return None
    papers = data.get("papers", [])
    if not papers:
        return None
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


def slugify_node(node: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", node.lower()).strip("-")


def _run_gate(cmd: list[str], timeout: int = 60) -> tuple[bool, str]:
    """Run an external gate script and report pass/fail + its last output line.
    Reuses the existing manifest tools as the single source of truth for their
    own gates, rather than re-implementing their logic here."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, f"could not run {' '.join(cmd)}: {e}"
    out = (result.stdout + result.stderr).strip()
    last_line = out.splitlines()[-1] if out else ""
    return result.returncode == 0, last_line


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


def _notes_status_for_keys(survey_dir: Path, keys: list[str]) -> dict:
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
    return {"keys": keys, "missing": missing, "invalid": invalid, "valid": valid}


def cmd_notes_status(args):
    survey_dir = Path(args.survey_dir)
    keys = load_corpus_keys(survey_dir)
    st = _notes_status_for_keys(survey_dir, keys)
    missing, invalid, valid = st["missing"], st["invalid"], st["valid"]

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


# ---- figures-status / mark-figure-attempted (Phase 4: figures) ----------

def _figures_status_for_keys(survey_dir: Path, keys: list[str]) -> dict:
    fig_path = figures_json_path(survey_dir)
    fig_keys: set[str] = set()
    if fig_path.exists():
        figs = load_json(fig_path).get("figures", [])
        fig_keys = {f.get("paper_key") for f in figs if f.get("paper_key")}
    adir = figures_attempted_dir(survey_dir)
    attempted_markers = {p.name for p in adir.glob("*")} if adir.exists() else set()

    has_figure, attempted_none, not_attempted = [], [], []
    for key in keys:
        if key in fig_keys:
            has_figure.append(key)
        elif key in attempted_markers:
            attempted_none.append(key)
        else:
            not_attempted.append(key)
    return {
        "keys": keys, "has_figure": has_figure,
        "attempted_none": attempted_none, "not_attempted": not_attempted,
    }


def cmd_figures_status(args):
    survey_dir = Path(args.survey_dir)
    keys = load_corpus_keys(survey_dir)
    st = _figures_status_for_keys(survey_dir, keys)

    print(f"Figures status for {survey_dir.name}: {len(keys)} papers in corpus")
    print(f"  has-figure:     {len(st['has_figure'])}")
    print(f"  attempted-none: {len(st['attempted_none'])}")
    print(f"  not-attempted:  {len(st['not_attempted'])}")
    if st["not_attempted"]:
        print(f"\nNot attempted ({len(st['not_attempted'])}): " + ", ".join(st["not_attempted"]))
        print(f"\nNOT DONE: {len(st['not_attempted'])} of {len(keys)} papers still need a figure attempt.")
        return 2
    print("\nALL ATTEMPTED: every corpus paper has a figure or a recorded no-figure attempt.")
    return 0


def cmd_mark_figure_attempted(args):
    survey_dir = Path(args.survey_dir)
    fdir = figures_attempted_dir(survey_dir)
    fdir.mkdir(parents=True, exist_ok=True)
    marked = []
    for key in args.keys.split(","):
        key = key.strip()
        if not key:
            continue
        (fdir / key).touch()
        marked.append(key)
    print(f"Marked {len(marked)} paper(s) as figure-attempted (no embeddable figure): "
          + ", ".join(marked))
    return 0


# ---- sections-status / assemble-sections (Phases 6-7: writing) ----------

def _sections_expected(survey_dir: Path) -> list[str]:
    """Fixed structural parts plus one method-treatment fragment per distinct
    taxonomy node found in corpus.json (set-node's own contract: one full
    axis/node path per axis, joined by '; '; 'root' papers get no fragment of
    their own -- they're cross-cutting, covered in the taxonomy/comparison
    sections instead)."""
    cpath = corpus_path(survey_dir)
    nodes: set[str] = set()
    if cpath.exists():
        data = load_json(cpath)
        for paper in data.get("papers", []):
            node_field = paper.get("taxonomy_node", "") or ""
            for piece in node_field.split(";"):
                piece = piece.strip()
                if piece and piece.lower() != "root":
                    nodes.add(piece)
    method_slugs = sorted({slugify_node(n) for n in nodes} - {""})
    method_sections = [f"20-method-{slug}" for slug in method_slugs]
    return list(FIXED_SECTIONS_PRE) + method_sections + list(FIXED_SECTIONS_POST)


def _sections_status(survey_dir: Path) -> dict:
    expected = _sections_expected(survey_dir)
    sdir = sections_dir(survey_dir)
    missing, stub, present = [], [], []
    for name in expected:
        fpath = sdir / f"{name}.md"
        if not fpath.exists():
            missing.append(name)
            continue
        text = fpath.read_text()
        if V.TODO_MARKER in text or len(text.strip()) < MIN_SECTION_CHARS:
            stub.append(name)
        else:
            present.append(name)
    return {"expected": expected, "missing": missing, "stub": stub, "present": present}


def cmd_sections_status(args):
    survey_dir = Path(args.survey_dir)
    st = _sections_status(survey_dir)

    print(f"Sections status for {survey_dir.name}: {len(st['expected'])} fragment(s) expected")
    print(f"  present: {len(st['present'])}")
    print(f"  missing: {len(st['missing'])}")
    print(f"  stub:    {len(st['stub'])}")
    if st["missing"]:
        print(f"\nMissing ({len(st['missing'])}): " + ", ".join(st["missing"]))
    if st["stub"]:
        print(f"\nStub / TODO / too short ({len(st['stub'])}): " + ", ".join(st["stub"]))

    if st["missing"] or st["stub"]:
        print(f"\nNOT DONE: {len(st['missing']) + len(st['stub'])} of {len(st['expected'])} "
              f"fragment(s) still need work.")
        return 2
    print("\nALL DONE: every expected fragment is present and non-stub.")
    return 0


def cmd_assemble_sections(args):
    survey_dir = Path(args.survey_dir)
    st = _sections_status(survey_dir)
    if (st["missing"] or st["stub"]) and not args.allow_incomplete:
        print(f"REFUSING to assemble: {len(st['missing'])} missing, {len(st['stub'])} stub "
              f"fragment(s). Pass --allow-incomplete to assemble a partial preview anyway.")
        for name in st["missing"]:
            print(f"  missing: {name}")
        for name in st["stub"]:
            print(f"  stub:    {name}")
        return 2

    sdir = sections_dir(survey_dir)
    parts = []
    used = []
    for name in st["expected"]:
        fpath = sdir / f"{name}.md"
        if fpath.exists():
            parts.append(fpath.read_text().rstrip() + "\n")
            used.append(name)
    out_path = Path(args.out) if args.out else survey_dir / "survey.md"
    out_path.write_text("\n".join(parts) if parts else "")
    print(f"Assembled {len(used)} fragment(s) into {out_path} "
          f"({sum(len(p) for p in parts)} chars).")
    if st["missing"] or st["stub"]:
        print(f"NOTE: partial assembly -- {len(st['missing'])} missing, "
              f"{len(st['stub'])} stub fragment(s) were skipped.")
    return 0


# ---- critique-status (Phase 5 of the intake workflow: critique loop) ----

CHECKLIST_RE = re.compile(r"^- \[([ xX])\]\s*(\S.*)$", re.MULTILINE)


def _critique_path_for(field: str, topic: str) -> Path:
    return Path("content/critiques") / f"{field}__{topic}.md"


def cmd_critique_status(args):
    survey_dir = Path(args.survey_dir)
    field, topic = survey_dir.parts[-2], survey_dir.parts[-1]
    cpath = _critique_path_for(field, topic)

    if not cpath.exists():
        print(f"No critique on file yet for {field}/{topic} ({cpath} does not exist).")
        return 0

    lines = cpath.read_text().splitlines()
    verdict_line = lines[0] if lines else ""
    body = "\n".join(lines[1:])
    items = CHECKLIST_RE.findall(body)
    open_items = [desc for mark, desc in items if mark == " "]
    resolved_items = [desc for mark, desc in items if mark.lower() == "x"]

    print(f"Critique status for {field}/{topic}: {verdict_line or '(no verdict line)'}")
    print(f"  REQUIRED checklist items: {len(items)} total, "
          f"{len(resolved_items)} resolved, {len(open_items)} open")
    if not items:
        print("  (no checkbox-formatted findings found -- either none recorded yet, "
              "or this critique predates the checklist convention; cannot verify "
              "resolution progress mechanically)")
    if open_items:
        print("\n  Open:")
        for d in open_items:
            print(f"    - {d}")
        return 2
    return 0


# ---- run.json ledger (Tier A: run-init / run-set) ------------------------

def load_run(survey_dir: Path) -> dict | None:
    p = run_json_path(survey_dir)
    if not p.exists():
        return None
    return load_json(p)


def save_run(survey_dir: Path, data: dict) -> None:
    p = run_json_path(survey_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def cmd_run_init(args):
    survey_dir = Path(args.survey_dir)
    p = run_json_path(survey_dir)
    if p.exists() and not args.force:
        sys.exit(f"ERROR: {p} already exists (use --force to overwrite, or "
                  f"'run-set' to update a single phase)")

    driving_problems = ([s.strip() for s in args.driving_problems.split("|") if s.strip()]
                         if args.driving_problems else [])
    planned_subareas = ([s.strip() for s in args.planned_subareas.split("|") if s.strip()]
                         if args.planned_subareas else [])

    data = {
        "field": args.field,
        "topic": args.topic,
        "title": args.title,
        "slug": f"{args.field}/{args.topic}",
        "scope": args.scope,
        "driving_problems": driving_problems,
        "planned_subareas": planned_subareas,
        "phase": 1,
        "phase_status": {"1": "gate_passed", **{str(n): "not_started" for n in range(2, 9)}},
        "updated_at": _now_iso(),
        "next_action": f"python3 scripts/survey_pipeline.py candidates-status {survey_dir} "
                        f"--expected {','.join(planned_subareas)}",
    }
    save_run(survey_dir, data)
    print(f"Initialized {p} for {args.field}/{args.topic} -- Phase 1 recorded.")
    if driving_problems:
        print(f"  driving problems: {'; '.join(driving_problems)}")
    if planned_subareas:
        print(f"  planned subareas: {', '.join(planned_subareas)}")
    return 0


def cmd_run_set(args):
    survey_dir = Path(args.survey_dir)
    data = load_run(survey_dir)
    if data is None:
        sys.exit(f"ERROR: {run_json_path(survey_dir)} not found -- run 'run-init' first")

    data["phase"] = args.phase
    data.setdefault("phase_status", {})[str(args.phase)] = args.status
    data["updated_at"] = _now_iso()
    if args.next_action:
        data["next_action"] = args.next_action
    save_run(survey_dir, data)
    print(f"{survey_dir}: Phase {args.phase} ({PHASE_NAMES.get(args.phase, '?')}) = {args.status}")
    return 0


# ---- status / scan (Tier A: the resume entrypoint) -----------------------

NEXT_ACTION_TEMPLATES = {
    1: "python3 scripts/survey_pipeline.py run-init {dir} --field <f> --topic <t> "
       "--title \"<T>\" --scope \"<one-line scope>\" --driving-problems \"a|b|c\" "
       "--planned-subareas \"x|y|z\"  (then corpus_manifest.py init {dir}/corpus.json)",
    # 2 is built dynamically in _compute_status from run.json's planned_subareas, if recorded.
    3: "python3 scripts/survey_pipeline.py next-keys {dir} --exclude-inflight",
    4: "python3 scripts/survey_pipeline.py figures-status {dir}",
    5: "derive taxonomy axes from corpus.json + notes, then "
       "corpus_manifest.py set-node {dir}/corpus.json <key> \"<axis>/<node>\" for unplaced papers",
    6: "python3 scripts/survey_pipeline.py sections-status {dir}  # write .pipeline/sections/30-evolution.md",
    7: "python3 scripts/survey_pipeline.py sections-status {dir}  # write missing/stub fragments, "
       "then assemble-sections {dir}",
    8: "python3 scripts/figure_manifest.py check {dir}/figures.json --document {dir}/survey.md; "
       "then curl-check every reference URL (or re-run status --verify-refs)",
}


def _tri(ok: bool, partial: bool) -> str:
    if ok:
        return "gate_passed"
    return "in_progress" if partial else "not_started"


def _phase1(survey_dir: Path) -> tuple[str, str]:
    cpath = corpus_path(survey_dir)
    if not cpath.exists():
        return "not_started", "corpus.json not initialized"
    data = load_json(cpath)
    ok = bool(data.get("topic", "").strip()) and bool(data.get("scope", "").strip())
    return _tri(ok, True), ("scope recorded" if ok else "corpus.json exists but topic/scope is empty")


def _phase2(survey_dir: Path) -> tuple[str, str]:
    cpath = corpus_path(survey_dir)
    if not cpath.exists():
        return "not_started", "corpus.json not initialized"
    data = load_json(cpath)
    n = len(data.get("papers", []))
    if n == 0:
        return "not_started", "corpus.json has zero papers"
    ok, detail = _run_gate([sys.executable, str(scripts_dir() / "corpus_manifest.py"),
                             "coverage", str(cpath), "--strict"])
    return _tri(ok, True), (detail or f"{n} papers")


def _phase3(survey_dir: Path) -> tuple[str, str]:
    keys = _load_corpus_keys_safe(survey_dir)
    if keys is None:
        return "not_started", "corpus.json not initialized or empty"
    st = _notes_status_for_keys(survey_dir, keys)
    n_valid, n_total = len(st["valid"]), len(keys)
    ok = n_valid == n_total
    partial = n_valid > 0 or notes_dir(survey_dir).exists()
    return _tri(ok, partial), f"{n_valid}/{n_total} valid notes"


def _phase4(survey_dir: Path) -> tuple[str, str]:
    keys = _load_corpus_keys_safe(survey_dir)
    if keys is None:
        return "not_started", "corpus.json not initialized or empty"
    st = _figures_status_for_keys(survey_dir, keys)
    n_done = len(st["has_figure"]) + len(st["attempted_none"])
    n_total = len(keys)
    ok = n_done == n_total
    partial = n_done > 0
    return _tri(ok, partial), f"{n_done}/{n_total} attempted ({len(st['has_figure'])} with a figure)"


def _phase5(survey_dir: Path) -> tuple[str, str]:
    cpath = corpus_path(survey_dir)
    if not cpath.exists():
        return "not_started", "corpus.json not initialized"
    data = load_json(cpath)
    papers = data.get("papers", [])
    if not papers:
        return "not_started", "corpus.json has zero papers"
    placed = [p for p in papers if (p.get("taxonomy_node") or "").strip()]
    fig_path = figures_json_path(survey_dir)
    has_taxonomy_fig = False
    if fig_path.exists():
        figs = load_json(fig_path).get("figures", [])
        has_taxonomy_fig = any("taxonomy" in Path(f.get("path", "")).name.lower() for f in figs)
    ok = len(placed) == len(papers) and has_taxonomy_fig
    partial = bool(placed) or has_taxonomy_fig
    detail = f"{len(placed)}/{len(papers)} papers placed, taxonomy figure {'registered' if has_taxonomy_fig else 'missing'}"
    return _tri(ok, partial), detail


def _whole_file_fallback(survey_dir: Path, label: str) -> tuple[str, str]:
    md = survey_dir / "survey.md"
    if not md.exists():
        return "not_started", f"{label}: no .pipeline/sections/ and no survey.md"
    text = md.read_text()
    if not text.strip():
        return "not_started", f"{label}: survey.md is empty"
    if V.TODO_MARKER in text:
        return "in_progress", f"{label}: survey.md has unresolved TODO markers"
    return "gate_passed", f"{label}: survey.md present, no TODO markers (whole-file build)"


def _phase6(survey_dir: Path) -> tuple[str, str]:
    sdir = sections_dir(survey_dir)
    if sdir.exists():
        st = _sections_status(survey_dir)
        missing_or_stub = "30-evolution" in st["missing"] or "30-evolution" in st["stub"]
        ok = not missing_or_stub
        partial = "30-evolution" not in st["missing"]
        return _tri(ok, partial), ("evolution fragment present" if ok else "evolution fragment missing/stub")
    return _whole_file_fallback(survey_dir, "narrative")


def _phase7(survey_dir: Path) -> tuple[str, str]:
    sdir = sections_dir(survey_dir)
    if sdir.exists():
        st = _sections_status(survey_dir)
        ok = not st["missing"] and not st["stub"]
        partial = bool(st["present"]) or bool(st["stub"])
        detail = ("all fragments present" if ok else
                  f"{len(st['present'])}/{len(st['expected'])} present, "
                  f"{len(st['missing'])} missing, {len(st['stub'])} stub")
        return _tri(ok, partial), detail
    return _whole_file_fallback(survey_dir, "assembled document")


def _phase8(survey_dir: Path, verify_refs: bool) -> tuple[str, str]:
    md = survey_dir / "survey.md"
    figs = figures_json_path(survey_dir)
    if not md.exists() or not figs.exists():
        return "not_started", "survey.md or figures.json missing"
    ok, detail = _run_gate([sys.executable, str(scripts_dir() / "figure_manifest.py"),
                             "check", str(figs), "--document", str(md)])
    if not ok:
        return "in_progress", detail
    if not verify_refs:
        return "gate_passed", detail + " (reference URLs NOT re-checked -- pass --verify-refs to curl-check them)"

    cpath = corpus_path(survey_dir)
    data = load_json(cpath) if cpath.exists() else {"papers": []}
    bad = []
    for paper in data.get("papers", []):
        url = paper.get("url", "")
        try:
            r = subprocess.run(
                ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "-L", "--max-time", "15", url],
                capture_output=True, text=True, timeout=20,
            )
            if r.stdout.strip() != "200":
                bad.append(f"{paper.get('key', '?')} -> {r.stdout.strip() or 'no response'}")
        except (OSError, subprocess.TimeoutExpired) as e:
            bad.append(f"{paper.get('key', '?')} -> error: {e}")
    if bad:
        return "in_progress", f"{len(bad)} reference URL(s) did not resolve: {'; '.join(bad[:5])}"
    return "gate_passed", "figure check passed and all reference URLs resolve (200)"


PHASE_CHECKS = {1: _phase1, 2: _phase2, 3: _phase3, 4: _phase4, 5: _phase5, 6: _phase6, 7: _phase7}


def _compute_status(survey_dir: Path, verify_refs: bool = False, reg_status: str | None = None) -> dict:
    if reg_status == "done":
        # A 'done' registry entry already passed mark.py's post-write validate.py gate
        # (approved critique, no TODO markers, all files present) -- that IS the
        # completion record. .pipeline/ working artifacts (notes/, figures-attempted/)
        # are explicitly safe to delete once done (see CLAUDE.md), so their absence
        # here must not be read as "phase not done" -- trust the committed registry
        # over ephemeral working state that outlived its purpose.
        phase_status = {n: "gate_passed" for n in PHASES}
        phase_detail = {n: "registry status is 'done' -- trusting the approved-critique "
                            "completion record over any .pipeline/ artifacts, which are "
                            "safe to have been cleaned up" for n in PHASES}
        return {"phase_status": phase_status, "phase_detail": phase_detail,
                "current_phase": None, "next_action": "none -- topic is done"}

    phase_status: dict[int, str] = {}
    phase_detail: dict[int, str] = {}
    for n in range(1, 8):
        phase_status[n], phase_detail[n] = PHASE_CHECKS[n](survey_dir)
    phase_status[8], phase_detail[8] = _phase8(survey_dir, verify_refs)

    current_phase = next((n for n in PHASES if phase_status[n] != "gate_passed"), None)
    if current_phase is None:
        next_action = "none -- all phase gates pass on disk"
    elif current_phase == 2:
        existing = load_run(survey_dir) or {}
        subareas = existing.get("planned_subareas") or []
        expected = ",".join(subareas) if subareas else "<planned-subareas -- none recorded in run.json>"
        next_action = (f"python3 scripts/survey_pipeline.py candidates-status {survey_dir} "
                        f"--expected {expected}, then apply-candidates once discovery "
                        f"workers have written candidates/")
    else:
        next_action = NEXT_ACTION_TEMPLATES[current_phase].format(dir=str(survey_dir))

    return {
        "phase_status": phase_status,
        "phase_detail": phase_detail,
        "current_phase": current_phase,
        "next_action": next_action,
    }


def _registry_status(field: str, topic: str) -> str | None:
    try:
        data = V.load_registry(os.getcwd())
    except (OSError, json.JSONDecodeError):
        return None
    for f in data.get("fields", []):
        if f.get("slug") != field:
            continue
        for t in f.get("topics", []):
            if t.get("slug") == topic:
                return t.get("status")
    return None


def _write_run_from_status(survey_dir: Path, field: str, topic: str, st: dict) -> None:
    existing = load_run(survey_dir) or {}
    if not existing:
        print(f"\nNOTE: no {run_json_path(survey_dir)} found -- creating one from disk state. "
              f"driving_problems/planned_subareas were never recorded for this build (it "
              f"predates Tier B, or Phase 1 skipped run-init). A resuming session should "
              f"re-derive them carefully from corpus.json's scope and existing papers' "
              f"subareas -- do not re-derive scope from scratch, which risks a different survey.")
    data = {
        "field": field,
        "topic": topic,
        "title": existing.get("title", ""),
        "slug": f"{field}/{topic}",
        "scope": existing.get("scope", ""),
        "driving_problems": existing.get("driving_problems", []),
        "planned_subareas": existing.get("planned_subareas", []),
        "phase": st["current_phase"] if st["current_phase"] is not None else 8,
        "phase_status": {str(n): st["phase_status"][n] for n in PHASES},
        "updated_at": _now_iso(),
        "next_action": st["next_action"],
    }
    save_run(survey_dir, data)


def cmd_status(args):
    survey_dir = Path(args.survey_dir)
    field, topic = survey_dir.parts[-2], survey_dir.parts[-1]
    reg_status = _registry_status(field, topic)
    st = _compute_status(survey_dir, verify_refs=args.verify_refs, reg_status=reg_status)

    print(f"Build status for {field}/{topic}")
    if reg_status is not None:
        print(f"  registry status: {reg_status}")
    print()
    for n in PHASES:
        status, detail = st["phase_status"][n], st["phase_detail"][n]
        print(f"  Phase {n} ({PHASE_NAMES[n]:<10}): {status:<12} -- {detail}")

    print()
    if st["current_phase"] is None:
        print("ALL PHASES PASSED. This build is complete on disk.")
    else:
        print(f"CURRENT PHASE: {st['current_phase']} ({PHASE_NAMES[st['current_phase']]})")
        print(f"NEXT ACTION: {st['next_action']}")

    if reg_status != "done":
        # A done topic's .pipeline/ is expected to be gone -- don't resurrect a
        # run.json ledger for working state that has already served its purpose.
        _write_run_from_status(survey_dir, field, topic, st)

    return 0 if st["current_phase"] is None else 2


def cmd_scan(args):
    root = Path("content/surveys")
    if not root.is_dir():
        print("content/surveys not found -- run this from the repo root.")
        return 1

    found = []
    for fdir in sorted(p for p in root.iterdir() if p.is_dir()):
        if fdir.name in V.RESERVED_FIELD_SLUGS:
            continue
        for tdir in sorted(p for p in fdir.iterdir() if p.is_dir()):
            if not pipeline_dir(tdir).is_dir():
                continue  # never started fan-out, or already cleaned up post-done -- not interrupted
            reg_status = _registry_status(fdir.name, tdir.name)
            if reg_status == "done":
                continue
            st = _compute_status(tdir, reg_status=reg_status)
            phase = st["current_phase"] if st["current_phase"] is not None else 8
            key = f"{fdir.name}/{tdir.name}"
            print(f"{key} -- Phase {phase} ({PHASE_NAMES[phase]}), registry: {reg_status or 'unknown'}")
            found.append(key)

    if not found:
        print("No interrupted builds found.")
    else:
        print(f"\n{len(found)} interrupted build(s). Run "
              f"'python3 scripts/survey_pipeline.py status content/surveys/<field>/<topic>' "
              f"on one to get the exact next command.")
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

    p = sub.add_parser("figures-status", help="check Phase 4 figure-attempt completeness")
    p.add_argument("survey_dir")
    p.set_defaults(func=cmd_figures_status)

    p = sub.add_parser("mark-figure-attempted",
                        help="record that a paper was attempted for a figure and had none embeddable")
    p.add_argument("survey_dir")
    p.add_argument("--keys", required=True, help="comma-separated paper keys")
    p.set_defaults(func=cmd_mark_figure_attempted)

    p = sub.add_parser("sections-status",
                        help="check Phases 6-7 document-fragment completeness "
                             "(.pipeline/sections/, one per structural part + taxonomy node)")
    p.add_argument("survey_dir")
    p.set_defaults(func=cmd_sections_status)

    p = sub.add_parser("assemble-sections",
                        help="concatenate .pipeline/sections/*.md into survey.md in order")
    p.add_argument("survey_dir")
    p.add_argument("--out", help="output path (default: <survey_dir>/survey.md)")
    p.add_argument("--allow-incomplete", action="store_true",
                    help="assemble even if fragments are missing or stub (partial preview)")
    p.set_defaults(func=cmd_assemble_sections)

    p = sub.add_parser("critique-status",
                        help="check REQUIRED-finding checklist resolution in "
                             "content/critiques/<field>__<topic>.md")
    p.add_argument("survey_dir")
    p.set_defaults(func=cmd_critique_status)

    p = sub.add_parser("run-init", help="create .pipeline/run.json recording the Phase 1 plan")
    p.add_argument("survey_dir")
    p.add_argument("--field", required=True)
    p.add_argument("--topic", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--scope", required=True, help="one-line operating scope statement")
    p.add_argument("--driving-problems", default="",
                    help="'|'-separated list, e.g. 'image quality|sample diversity|training stability'")
    p.add_argument("--planned-subareas", default="",
                    help="'|'-separated list of subareas dispatched to Phase 2 discovery workers")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_run_init)

    p = sub.add_parser("run-set", help="update one phase's status in .pipeline/run.json")
    p.add_argument("survey_dir")
    p.add_argument("--phase", type=int, required=True, choices=PHASES)
    p.add_argument("--status", required=True, choices=PHASE_STATUSES)
    p.add_argument("--next-action", default="")
    p.set_defaults(func=cmd_run_set)

    p = sub.add_parser("status",
                        help="recompute the true build phase from disk (ignores run.json's own "
                             "claims), print the exact next command, and self-heal run.json")
    p.add_argument("survey_dir")
    p.add_argument("--verify-refs", action="store_true",
                    help="also curl-check every reference URL for Phase 8 (slow, network-dependent)")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("scan",
                        help="list every non-done topic with a .pipeline/ dir (i.e. an "
                             "interrupted build) and its current phase -- run this first "
                             "after a token-limit refresh")
    p.set_defaults(func=cmd_scan)

    args = ap.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
