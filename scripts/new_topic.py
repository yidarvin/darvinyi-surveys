#!/usr/bin/env python3
"""Stamp a new topic's registry entry, queue row, and (empty) survey directory.

Deterministic scaffolding so every topic starts correctly wired, whether or not
its field already exists. The intake workflow (a Claude Code session) then runs
the survey-and-taxonomy-research skill to fill content/surveys/<field>/<topic>/.

Usage:

    python3 scripts/new_topic.py \\
        --field ai --topic llm-benchmarks-evals \\
        --title "LLM & Agent Benchmarks and Evaluations" \\
        --blurb "How the field measures capability, and what the numbers miss." \\
        [--field-name "Artificial Intelligence" --field-blurb "..."]

If --field names a field slug that does not exist yet in the registry, a new
field entry is created (requires --field-name) and an original SVG emblem is
generated at public/fields/<field>.svg. New topics and new fields are always
appended (to the end of their field's topics, or the end of the fields list) --
there is no numeric ordering to preserve, unlike a linear book. Reordering is a
separate, explicit "reprioritize" operation on the two files by hand.

Idempotent: a field or topic that already exists is left alone (its registry
entry, queue row, and directory are all checked independently, and only the
missing pieces are added).

Run from the repo root.
"""
from __future__ import annotations

import argparse
import os
import sys

import validate as V

MOTIFS = ("arcs", "grid", "rays", "dots")

PALETTE = {
    "bg": "#0a0e0f",
    "surface": "#10171a",
    "border": "#1e2a30",
    "accent": "#2dd4bf",
    "comment": "#55707b",
}


def _stable_hash(s: str) -> int:
    """A hash that is stable across processes and Python versions, unlike the
    builtin hash() (randomized per-process for str, by design, for security)."""
    h = 0
    for ch in s:
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
    return h


def _motif_svg(motif: str) -> str:
    b = PALETTE["border"]
    a = PALETTE["accent"]
    if motif == "arcs":
        return (
            f'<circle cx="160" cy="100" r="150" fill="none" stroke="{b}" stroke-width="1.5"/>'
            f'<circle cx="160" cy="100" r="105" fill="none" stroke="{b}" stroke-width="1.5"/>'
            f'<circle cx="160" cy="100" r="60" fill="none" stroke="{a}" stroke-width="1.5" '
            f'stroke-dasharray="2 4"/>'
        )
    if motif == "grid":
        lines = []
        for x in range(-40, 360, 36):
            lines.append(f'<line x1="{x}" y1="0" x2="{x + 90}" y2="200" stroke="{b}" stroke-width="1"/>')
        return "".join(lines)
    if motif == "rays":
        import math

        lines = []
        for i in range(12):
            ang = i * math.pi / 6
            x2 = 160 + 135 * math.cos(ang)
            y2 = 100 + 135 * math.sin(ang)
            lines.append(f'<line x1="160" y1="100" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{b}" stroke-width="1"/>')
        return "".join(lines)
    dots = []
    for x in range(20, 320, 32):
        for y in range(20, 180, 32):
            dots.append(f'<circle cx="{x}" cy="{y}" r="2" fill="{b}"/>')
    return "".join(dots)


def generate_field_emblem(slug: str, name: str) -> str:
    """An original SVG emblem for a field's card: a deterministic-but-varied
    geometric motif (picked from the field slug, not randomly, so regenerating
    is a no-op) behind a mono monogram in the house accent color. No extracted
    paper figures ever belong on a field card -- see the licensing rule in the
    scaffold plan; this is always originally authored art."""
    motif = MOTIFS[_stable_hash(slug) % len(MOTIFS)]
    words = [w for w in name.split() if w]
    initials = "".join(w[0] for w in words[:2]).upper() or slug[:2].upper()
    body = _motif_svg(motif)
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 200">'
        f'<rect width="320" height="200" fill="{PALETTE["surface"]}"/>'
        f"{body}"
        f'<text x="160" y="114" text-anchor="middle" font-family="ui-monospace, monospace" '
        f'font-size="52" font-weight="700" fill="{PALETTE["accent"]}">{initials}</text>'
        "</svg>\n"
    )


def ensure_field(repo: str, data: dict, slug: str, name: str, blurb: str) -> dict:
    for f in data.setdefault("fields", []):
        if f.get("slug") == slug:
            return f
    if not name:
        print(f"error: field '{slug}' does not exist yet; pass --field-name to create it.")
        raise SystemExit(1)
    graphic = f"{slug}.svg"
    field = {"slug": slug, "name": name}
    if blurb:
        field["blurb"] = blurb
    field["graphic"] = graphic
    field["topics"] = []
    data["fields"].append(field)

    emblem_path = os.path.join(repo, "public", "fields", graphic)
    if not os.path.exists(emblem_path):
        os.makedirs(os.path.dirname(emblem_path), exist_ok=True)
        with open(emblem_path, "w", encoding="utf-8") as fh:
            fh.write(generate_field_emblem(slug, name))
        print(f"  wrote: public/fields/{graphic}")
    print(f"  registry: created field '{slug}' ({name})")
    return field


def ensure_topic(field: dict, slug: str, title: str, blurb: str) -> tuple[dict, bool]:
    for t in field.get("topics", []):
        if t.get("slug") == slug:
            return t, False
    topic = {"slug": slug, "title": title}
    if blurb:
        topic["blurb"] = blurb
    topic["hero"] = "taxonomy.svg"
    topic["status"] = "pending"
    topic["corpusSize"] = None
    field["topics"].append(topic)
    return topic, True


def ensure_queue_row(repo: str, field_slug: str, topic_slug: str, title: str) -> bool:
    q = V.parse_queue(repo)
    header = q["header"]
    field_i = V._col_index(header, "field")
    topic_i = V._col_index(header, "topic")
    title_i = V._col_index(header, "title")
    status_i = V._col_index(header, "status")
    for r in q["rows"]:
        if len(r) > max(field_i, topic_i) and r[field_i] == field_slug and r[topic_i] == topic_slug:
            return False
    new_row = [""] * len(header)
    if field_i != -1:
        new_row[field_i] = field_slug
    if topic_i != -1:
        new_row[topic_i] = topic_slug
    if title_i != -1:
        new_row[title_i] = title
    if status_i != -1:
        new_row[status_i] = "PENDING"
    rows = [list(r) for r in q["rows"]]
    rows.append(new_row)
    V.write_queue(repo, q, rows)
    return True


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Stamp a new survey topic.")
    ap.add_argument("--field", required=True, help="field slug, e.g. ai")
    ap.add_argument("--topic", required=True, help="topic slug, e.g. llm-benchmarks-evals")
    ap.add_argument("--title", required=True)
    ap.add_argument("--blurb", default="")
    ap.add_argument("--field-name", default="", help="required if --field does not exist yet")
    ap.add_argument("--field-blurb", default="")
    ap.add_argument("--repo", default=os.getcwd(), help="repo root (default: cwd)")
    args = ap.parse_args(argv[1:])

    field_slug = args.field.strip()
    topic_slug = args.topic.strip()
    repo = os.path.abspath(args.repo)

    if not V.SLUG_RE.match(field_slug):
        print(f"error: '{field_slug}' is not a valid slug (lowercase, hyphen-separated).")
        return 1
    if not V.SLUG_RE.match(topic_slug):
        print(f"error: '{topic_slug}' is not a valid slug (lowercase, hyphen-separated).")
        return 1
    if not os.path.exists(V.registry_path(repo)):
        print(f"error: {repo} does not look like a surveys repo (no content/registry.json).")
        return 1

    print(f"stamping topic '{field_slug}/{topic_slug}':")
    data = V.load_registry(repo)
    field = ensure_field(repo, data, field_slug, args.field_name, args.field_blurb)
    topic, created = ensure_topic(field, topic_slug, args.title, args.blurb)
    V.write_registry(repo, data)
    if created:
        print(f"  registry: inserted pending topic '{topic_slug}' under '{field_slug}'")
    else:
        print("  registry: topic already present; left alone")

    if ensure_queue_row(repo, field_slug, topic_slug, args.title):
        print(f"  queue: inserted PENDING row for '{field_slug}/{topic_slug}'")
    else:
        print("  queue: row already present; left alone")

    survey_dir = V.survey_dir(repo, field_slug, topic_slug)
    os.makedirs(survey_dir, exist_ok=True)
    gitkeep = os.path.join(survey_dir, ".gitkeep")
    if not os.listdir(survey_dir):
        open(gitkeep, "w", encoding="utf-8").close()
        print(f"  wrote: content/surveys/{field_slug}/{topic_slug}/.gitkeep")

    print("\nnext steps:")
    print("  1. run the survey-and-taxonomy-research skill into that directory (100+ papers).")
    print("  2. run 'npm run check'.")
    print(f"  3. run 'python3 scripts/mark.py {field_slug}/{topic_slug} draft'.")
    print("  4. critique the topic; only the critic runs 'mark.py ... done'.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
