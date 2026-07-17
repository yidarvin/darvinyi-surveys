#!/usr/bin/env python3
"""Validate that the registry, the queue, and the survey files all agree.

This is the load-bearing gate. It parses BOTH state files (content/registry.json
and prompts/queue.md), cross-checks them against each other, and scans every
survey directory on disk under content/surveys for missing pieces and unfinished
markers. It also doubles as the data source for "queue status": it prints the
counts and the next pending topic.

The registry is two levels: an ordered list of fields, each holding an ordered
list of topics. Every cross-check below keys on the composite "<field>/<topic>"
slug, never the topic slug alone, since two different fields may reuse a topic
slug (e.g. "overview") and the URL space is field-scoped.

Run from the repo root:

    python3 scripts/validate.py

Exit code is 1 on any error, 0 otherwise (warnings never fail the gate). The
other repo scripts (mark.py, new_topic.py) import the helpers here, so the queue
and registry are parsed and rewritten in exactly one place.
"""
from __future__ import annotations

import json
import os
import re
import sys

VALID_REGISTRY_STATUS = {"pending", "draft", "done"}
VALID_QUEUE_STATUS = {"PENDING", "DONE", "SKIPPED"}
VALID_VERDICTS = {"approve", "revise", "resolved"}
VERDICT_RE = re.compile(r"^verdict:\s*([a-z]+)\s*$")
SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

# A shared key pairs a registry status with a queue status. Any pair not in this
# set is a mismatch. DONE matches done, PENDING matches pending or draft, SKIPPED
# matches pending.
ALLOWED_STATUS_PAIRS = {
    ("done", "DONE"),
    ("draft", "PENDING"),
    ("pending", "PENDING"),
    ("pending", "SKIPPED"),
}

REGISTRY_TOP_ORDER = ("title", "subtitle", "url", "fields")
FIELD_KEY_ORDER = ("slug", "name", "blurb", "graphic", "topics")
TOPIC_KEY_ORDER = ("slug", "title", "blurb", "hero", "status", "corpusSize")

TODO_MARKER = "TODO:"

# Reserved on disk under content/surveys/ for the test suite only (src/test/).
# Never appears in the registry and is exempt from the registry-membership and
# content-hygiene checks below.
RESERVED_FIELD_SLUGS = {"__fixtures__"}


class QueueError(Exception):
    """Raised when prompts/queue.md cannot be parsed as a table."""


# ---- paths -------------------------------------------------------------

def registry_path(repo: str) -> str:
    return os.path.join(repo, "content", "registry.json")


def queue_path(repo: str) -> str:
    return os.path.join(repo, "prompts", "queue.md")


def surveys_dir(repo: str) -> str:
    return os.path.join(repo, "content", "surveys")


def survey_dir(repo: str, field: str, topic: str) -> str:
    return os.path.join(surveys_dir(repo), field, topic)


def critiques_dir(repo: str) -> str:
    return os.path.join(repo, "content", "critiques")


def critique_path(repo: str, field: str, topic: str) -> str:
    return os.path.join(critiques_dir(repo), f"{field}__{topic}.md")


def read_verdict(repo: str, field: str, topic: str) -> str | None:
    """Return the verdict token from a critique file's first line.

    None means the file does not exist. "" means it exists but the first line
    does not match the verdict grammar.
    """
    path = critique_path(repo, field, topic)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            first = fh.readline()
    except OSError:
        return ""
    m = VERDICT_RE.match(first.rstrip("\n"))
    return m.group(1) if m else ""


# ---- registry ------------------------------------------------------------

def load_registry(repo: str) -> dict:
    with open(registry_path(repo), "r", encoding="utf-8") as fh:
        return json.load(fh)


def _canonical(d: dict, order: tuple[str, ...]) -> dict:
    out: dict = {}
    for key in order:
        if key in d:
            out[key] = d[key]
    for key in d:
        if key not in out:
            out[key] = d[key]
    return out


def canonical_topic(t: dict) -> dict:
    return _canonical(t, TOPIC_KEY_ORDER)


def canonical_field(f: dict) -> dict:
    out = _canonical(f, FIELD_KEY_ORDER)
    out["topics"] = [canonical_topic(t) for t in out.get("topics", [])]
    return out


def write_registry(repo: str, data: dict) -> None:
    """Write registry.json with canonical field/topic key order and a newline."""
    out = _canonical(data, REGISTRY_TOP_ORDER)
    out["fields"] = [canonical_field(f) for f in data.get("fields", [])]
    with open(registry_path(repo), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def iter_topics(data: dict):
    """Yield (field_slug, field_dict, topic_dict) for every topic, in order."""
    for f in data.get("fields", []):
        fslug = f.get("slug")
        for t in f.get("topics", []):
            yield fslug, f, t


# ---- queue table -----------------------------------------------------------

def _split_row(line: str) -> list[str]:
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def _is_separator(line: str) -> bool:
    s = line.strip()
    return bool(s) and "-" in s and re.fullmatch(r"\|?[\s:|-]+\|?", s) is not None


def _col_index(header: list[str], name: str) -> int:
    for i, cell in enumerate(header):
        if cell.strip().lower() == name:
            return i
    return -1


def parse_queue(repo: str) -> dict:
    """Locate the run-list table and return its structure.

    Everything outside the table (the intro prose, the trailing comment) is kept
    in `lines` so a rewrite can splice the table back in place.
    """
    with open(queue_path(repo), "r", encoding="utf-8") as fh:
        content = fh.read()
    lines = content.split("\n")
    header_idx = None
    for i in range(len(lines) - 1):
        if lines[i].strip().startswith("|") and _is_separator(lines[i + 1]):
            header_idx = i
            break
    if header_idx is None:
        raise QueueError("prompts/queue.md has no markdown table")
    sep_idx = header_idx + 1
    header = _split_row(lines[header_idx])
    rows: list[list[str]] = []
    j = sep_idx + 1
    while j < len(lines) and lines[j].strip().startswith("|"):
        rows.append(_split_row(lines[j]))
        j += 1
    return {
        "lines": lines,
        "header_idx": header_idx,
        "sep_idx": sep_idx,
        "end_idx": j,
        "header": header,
        "rows": rows,
    }


def render_queue_table(header: list[str], rows: list[list[str]]) -> list[str]:
    """Render an aligned markdown table. All rows are padded to the column count."""
    ncols = len(header)
    norm = [list(r) + [""] * (ncols - len(r)) for r in rows]
    widths = [len(header[c]) for c in range(ncols)]
    for r in norm:
        for c in range(ncols):
            widths[c] = max(widths[c], len(r[c]))

    def fmt(cells: list[str]) -> str:
        return "| " + " | ".join(cells[c].ljust(widths[c]) for c in range(ncols)) + " |"

    out = [fmt(header)]
    out.append("|" + "|".join("-" * (widths[c] + 2) for c in range(ncols)) + "|")
    for r in norm:
        out.append(fmt(r))
    return out


def write_queue(repo: str, parsed: dict, rows: list[list[str]]) -> None:
    """Rewrite prompts/queue.md with a new set of rows, table region only."""
    lines = list(parsed["lines"])
    table = render_queue_table(parsed["header"], rows)
    new_lines = lines[: parsed["header_idx"]] + table + lines[parsed["end_idx"]:]
    with open(queue_path(repo), "w", encoding="utf-8") as fh:
        fh.write("\n".join(new_lines))


# ---- validation --------------------------------------------------------

def validate(repo: str) -> tuple[list[str], list[str]]:
    """Return (errors, warnings). Errors fail the gate; warnings are advisory."""
    errors: list[str] = []
    warnings: list[str] = []

    # registry --------------------------------------------------------------
    if not os.path.exists(registry_path(repo)):
        return (["content/registry.json not found (is this a surveys repo?)"], [])
    try:
        data = load_registry(repo)
    except json.JSONDecodeError as exc:
        return ([f"registry.json is not valid JSON: {exc}"], [])

    for field_name in ("title", "subtitle", "fields"):
        if field_name not in data:
            errors.append(f"registry.json is missing top-level '{field_name}'")

    fields = data.get("fields")
    if not isinstance(fields, list):
        errors.append("registry.json 'fields' is not an array")
        fields = []

    reg_status: dict[str, str] = {}
    reg_order: list[str] = []
    seen_field_slugs: set[str] = set()

    for fi, f in enumerate(fields):
        flabel = f.get("slug", f"index {fi}")
        for req in ("slug", "name", "topics"):
            if req not in f:
                errors.append(f"registry field '{flabel}' is missing required field '{req}'")
        fslug = f.get("slug")
        if fslug:
            if not SLUG_RE.match(fslug):
                errors.append(f"registry field '{flabel}' has an invalid slug '{fslug}'")
            if fslug in seen_field_slugs:
                errors.append(f"registry has a duplicate field slug '{fslug}'")
            seen_field_slugs.add(fslug)

        topics = f.get("topics")
        if not isinstance(topics, list):
            if "topics" in f:
                errors.append(f"registry field '{flabel}' 'topics' is not an array")
            topics = []

        seen_topic_slugs: set[str] = set()
        for ti, t in enumerate(topics):
            tlabel = t.get("slug", f"index {ti}")
            label = f"{flabel}/{tlabel}"
            for req in ("slug", "title", "status"):
                if req not in t:
                    errors.append(f"registry topic '{label}' is missing required field '{req}'")
            status = t.get("status")
            if status is not None and status not in VALID_REGISTRY_STATUS:
                errors.append(f"registry topic '{label}' has invalid status '{status}'")
            tslug = t.get("slug")
            if not tslug or not fslug:
                continue
            if not SLUG_RE.match(tslug):
                errors.append(f"registry topic '{label}' has an invalid slug '{tslug}'")
            if tslug in seen_topic_slugs:
                errors.append(f"registry field '{fslug}' has a duplicate topic slug '{tslug}'")
            seen_topic_slugs.add(tslug)

            key = f"{fslug}/{tslug}"
            reg_status[key] = status
            reg_order.append(key)

            sdir = survey_dir(repo, fslug, tslug)
            md = os.path.join(sdir, "survey.md")
            corpus = os.path.join(sdir, "corpus.json")
            figs = os.path.join(sdir, "figures")
            built = os.path.exists(md) and os.path.exists(corpus)
            if status in ("draft", "done"):
                if not os.path.exists(md):
                    errors.append(f"registry topic '{key}' is '{status}' but survey.md is missing")
                if not os.path.exists(corpus):
                    errors.append(f"registry topic '{key}' is '{status}' but corpus.json is missing")
                if not os.path.isdir(figs) or not os.listdir(figs):
                    errors.append(f"registry topic '{key}' is '{status}' but figures/ is missing or empty")
            if status == "pending" and built:
                warnings.append(
                    f"content/surveys/{key}/ has survey files but '{key}' is still pending "
                    "(possible interrupted run: finish it or reset the topic)"
                )
    reg_keys = set(reg_order)

    # every survey dir on disk must have a registry entry -----------------
    # __fixtures__ is reserved for the test suite (src/test/) -- it is deliberately
    # never in the registry so it never appears on the live site, and is exempt
    # from every check below that assumes a real, registered topic.
    sroot = surveys_dir(repo)
    if os.path.isdir(sroot):
        for fname in sorted(os.listdir(sroot)):
            if fname in RESERVED_FIELD_SLUGS:
                continue
            fpath = os.path.join(sroot, fname)
            if not os.path.isdir(fpath):
                continue
            for tname in sorted(os.listdir(fpath)):
                tpath = os.path.join(fpath, tname)
                if not os.path.isdir(tpath):
                    continue
                key = f"{fname}/{tname}"
                if key not in reg_keys:
                    errors.append(f"content/surveys/{key}/ has no registry entry")

    # critiques ---------------------------------------------------------------
    # The build-critique loop: a topic's registry status moves pending -> draft
    # -> done, and only the critic may grant done, by writing an approving
    # verdict to content/critiques/<field>__<topic>.md. mark.py re-runs this
    # validation after every write and rolls back on any error, so this is what
    # makes `mark.py <field>/<topic> done` physically refuse without an
    # approved critique on file. Do not duplicate that enforcement in mark.py.
    if os.path.isdir(critiques_dir(repo)):
        for name in sorted(os.listdir(critiques_dir(repo))):
            if not name.endswith(".md"):
                continue
            base = name[: -len(".md")]
            if "__" not in base:
                errors.append(f"content/critiques/{name} is not named <field>__<topic>.md")
                continue
            fslug, _, tslug = base.partition("__")
            key = f"{fslug}/{tslug}"
            if key not in reg_keys:
                errors.append(f"content/critiques/{name} has no registry entry")
                continue
            verdict = read_verdict(repo, fslug, tslug)
            if verdict == "":
                errors.append(
                    f"content/critiques/{name} first line must be exactly "
                    "'verdict: approve|revise|resolved'"
                )
            elif verdict is not None and verdict not in VALID_VERDICTS:
                errors.append(f"content/critiques/{name} has invalid verdict '{verdict}'")

    for key in reg_order:
        fslug, tslug = key.split("/", 1)
        status = reg_status.get(key)
        verdict = read_verdict(repo, fslug, tslug)
        if status == "done" and verdict != "approve":
            if verdict is None:
                errors.append(
                    f"registry topic '{key}' is 'done' but content/critiques/{fslug}__{tslug}.md "
                    "is missing (done requires an approved critique)"
                )
            elif verdict in VALID_VERDICTS:
                errors.append(
                    f"registry topic '{key}' is 'done' but content/critiques/{fslug}__{tslug}.md "
                    f"has verdict '{verdict}' (done requires an approved critique)"
                )
        elif status == "draft" and verdict == "approve":
            warnings.append(
                f"'{key}' has an approved critique but is still 'draft' "
                f"(run: python3 scripts/mark.py {key} done)"
            )
        elif status == "pending" and verdict is not None:
            warnings.append(
                f"content/critiques/{fslug}__{tslug}.md exists but '{key}' is 'pending' "
                "(stale critique from a reset topic?)"
            )

    # queue ---------------------------------------------------------------
    q = None
    if not os.path.exists(queue_path(repo)):
        errors.append("prompts/queue.md not found (is this a surveys repo?)")
    else:
        try:
            q = parse_queue(repo)
        except QueueError as exc:
            errors.append(str(exc))
            q = None

    q_status: dict[str, str] = {}
    q_order: list[str] = []
    if q is not None:
        header = q["header"]
        ncols = len(header)
        field_i = _col_index(header, "field")
        topic_i = _col_index(header, "topic")
        status_i = _col_index(header, "status")
        if field_i == -1 or topic_i == -1 or status_i == -1:
            errors.append("prompts/queue.md table needs 'field', 'topic', and 'status' columns")
        else:
            q_seen: set[str] = set()
            for r in q["rows"]:
                if len(r) != ncols:
                    errors.append(
                        f"queue row has {len(r)} columns but the header has {ncols}: {' | '.join(r)}"
                    )
                    continue
                key = f"{r[field_i]}/{r[topic_i]}"
                st = r[status_i]
                if st not in VALID_QUEUE_STATUS:
                    errors.append(f"queue row '{key}' has invalid status '{st}'")
                if key in q_seen:
                    errors.append(f"queue has a duplicate row '{key}'")
                q_seen.add(key)
                q_status[key] = st
                q_order.append(key)

    # cross-checks (only when both files parsed) ---------------------------
    if q is not None:
        q_set = set(q_order)
        for key in reg_order:
            if key not in q_set:
                errors.append(f"'{key}' is in the registry but not in prompts/queue.md")
        for key in q_order:
            if key not in reg_keys:
                errors.append(f"'{key}' is in prompts/queue.md but not in the registry")
        for key in reg_order:
            if key in q_status:
                pair = (reg_status.get(key), q_status.get(key))
                if pair not in ALLOWED_STATUS_PAIRS:
                    errors.append(
                        f"status mismatch for '{key}': registry '{pair[0]}' vs queue '{pair[1]}'"
                    )
        shared_reg = [k for k in reg_order if k in q_set]
        shared_q = [k for k in q_order if k in reg_keys]
        if shared_reg != shared_q:
            errors.append(
                "queue and registry disagree on order: "
                f"registry {shared_reg} vs queue {shared_q}"
            )

    # content scan: every survey.md on disk, not keyed to status -----------
    if os.path.isdir(sroot):
        for fname in sorted(os.listdir(sroot)):
            if fname in RESERVED_FIELD_SLUGS:
                continue
            fpath = os.path.join(sroot, fname)
            if not os.path.isdir(fpath):
                continue
            for tname in sorted(os.listdir(fpath)):
                md = os.path.join(fpath, tname, "survey.md")
                if not os.path.exists(md):
                    continue
                rel = os.path.relpath(md, repo)
                try:
                    with open(md, "r", encoding="utf-8") as fh:
                        for lineno, line in enumerate(fh, 1):
                            if TODO_MARKER in line:
                                errors.append(f"{rel}:{lineno}: unfinished marker '{TODO_MARKER}'")
                except OSError as exc:
                    errors.append(f"could not read {rel}: {exc}")

    return (errors, warnings)


# ---- report --------------------------------------------------------------

def _summary_lines(repo: str) -> list[str]:
    try:
        data = load_registry(repo)
    except (OSError, json.JSONDecodeError):
        return []
    topics = [t for _, _, t in iter_topics(data)]
    done = sum(1 for t in topics if t.get("status") == "done")
    draft = sum(1 for t in topics if t.get("status") == "draft")
    pending = sum(1 for t in topics if t.get("status") == "pending")
    lines = [
        f"registry: {len(data.get('fields', []))} field(s), {len(topics)} topic(s) "
        f"({done} done, {draft} draft, {pending} pending)"
    ]
    nxt = next(((f, t) for f, _, t in iter_topics(data) if t.get("status") == "pending"), None)
    if nxt:
        f, t = nxt
        lines.append(f"next pending: {f}/{t.get('slug')} ({t.get('title')})")
    else:
        lines.append("next pending: none, the queue is drained")

    approved = revise = resolved = unreviewed = 0
    for fslug, _, t in iter_topics(data):
        if t.get("status") not in ("draft", "done"):
            continue
        tslug = t.get("slug")
        if not tslug:
            continue
        verdict = read_verdict(repo, fslug, tslug)
        if verdict == "approve":
            approved += 1
        elif verdict == "revise":
            revise += 1
        elif verdict == "resolved":
            resolved += 1
        elif verdict is None:
            unreviewed += 1
    lines.append(
        f"critiques: {approved} approved, {revise} revise, {resolved} resolved, {unreviewed} unreviewed"
    )
    return lines


def main(argv: list[str]) -> int:
    repo = os.path.abspath(argv[1]) if len(argv) > 1 else os.getcwd()
    errors, warnings = validate(repo)
    for line in _summary_lines(repo):
        print(line)
    for w in warnings:
        print(f"  warn: {w}")
    for e in errors:
        print(f"  error: {e}")
    if errors:
        print(f"\nFAIL: {len(errors)} error(s).")
        return 1
    print("\nOK: queue, registry, and survey files agree.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
