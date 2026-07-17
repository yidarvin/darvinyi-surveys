#!/usr/bin/env python3
"""Corpus manifest helper for survey-and-taxonomy-research.

Tracks the paper corpus as a JSON manifest, emits the markdown reference list,
and reports coverage (papers per subarea / per year) so a lopsided or
undersized corpus is caught before any writing happens.

Python 3 stdlib only (argparse, json, pathlib, collections). No third-party
imports. Exit codes: 0 = success, 1 = usage/validation error, 2 = coverage
gate failed under --strict.
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

MIN_TOTAL = 25
PAPER_FIELDS = ("key", "title", "authors", "year", "venue", "url",
                "inclusion_reason", "subarea", "taxonomy_node")


def load(manifest_path):
    p = Path(manifest_path)
    if not p.exists():
        sys.exit(f"ERROR: manifest not found: {p} (run 'init' first)")
    try:
        data = json.loads(p.read_text())
    except json.JSONDecodeError as e:
        sys.exit(f"ERROR: manifest is not valid JSON: {e}")
    if "papers" not in data:
        sys.exit("ERROR: manifest has no 'papers' list")
    return p, data


def save(path, data):
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def cmd_init(args):
    p = Path(args.manifest)
    if p.exists() and not args.force:
        sys.exit(f"ERROR: {p} already exists (use --force to overwrite)")
    save(p, {"topic": args.topic, "scope": args.scope, "papers": []})
    print(f"Initialized corpus manifest: {p} (topic: {args.topic})")


def cmd_add(args):
    p, data = load(args.manifest)
    if any(paper["key"] == args.key for paper in data["papers"]):
        sys.exit(f"ERROR: duplicate key '{args.key}' — keys must be unique")
    for name, value in (("title", args.title), ("authors", args.authors),
                        ("inclusion-reason", args.inclusion_reason),
                        ("subarea", args.subarea)):
        if not value.strip():
            sys.exit(f"ERROR: --{name} must be nonempty")
    data["papers"].append({
        "key": args.key, "title": args.title, "authors": args.authors,
        "year": args.year, "venue": args.venue, "url": args.url,
        "inclusion_reason": args.inclusion_reason, "subarea": args.subarea,
        "taxonomy_node": args.taxonomy_node,
    })
    save(p, data)
    print(f"Added [{args.key}] {args.title} ({args.year}) — "
          f"{len(data['papers'])} papers in corpus")


def cmd_set_node(args):
    p, data = load(args.manifest)
    for paper in data["papers"]:
        if paper["key"] == args.key:
            paper["taxonomy_node"] = args.node
            save(p, data)
            print(f"[{args.key}] taxonomy_node = {args.node}")
            return
    sys.exit(f"ERROR: no paper with key '{args.key}'")


def cmd_refs(args):
    _, data = load(args.manifest)
    papers = sorted(data["papers"], key=lambda x: (x["year"], x["key"]))
    lines = ["## References", ""]
    for i, paper in enumerate(papers, 1):
        lines.append(f"{i}. {paper['authors']} ({paper['year']}). "
                     f"*{paper['title']}*. {paper['venue']}. {paper['url']}")
    text = "\n".join(lines) + "\n"
    if args.out:
        Path(args.out).write_text(text)
        print(f"Wrote {len(papers)} references to {args.out}")
    else:
        print(text, end="")


def cmd_coverage(args):
    _, data = load(args.manifest)
    papers = data["papers"]
    total = len(papers)
    by_subarea = Counter(paper["subarea"] for paper in papers)
    by_year = Counter(paper["year"] for paper in papers)
    unplaced = [paper["key"] for paper in papers if not paper["taxonomy_node"]]

    print(f"Corpus coverage — topic: {data.get('topic', '?')}")
    print(f"Total papers: {total}")
    print("\nPapers per subarea:")
    for sub, n in by_subarea.most_common():
        print(f"  {sub}: {n}")
    print("\nPapers per year:")
    for year in sorted(by_year):
        print(f"  {year}: {by_year[year]}")
    if unplaced:
        print(f"\nNot yet placed in taxonomy ({len(unplaced)}): "
              + ", ".join(unplaced))

    warnings = []
    if total < args.min_total:
        warnings.append(
            f"CORPUS TOO SMALL: {total} papers < required minimum "
            f"{args.min_total}. Keep collecting before you write.")
    for sub, n in by_subarea.items():
        if n < 2:
            warnings.append(
                f"THIN SUBAREA: '{sub}' has only {n} paper(s) — a subarea "
                f"needs >=2 papers or it is not a subarea.")
    for sub, n in by_subarea.items():
        if total and n > total / 2:
            warnings.append(
                f"LOPSIDED CORPUS: '{sub}' holds {n}/{total} papers (more "
                f"than half). Broaden the other subareas.")
    if warnings:
        print("\n" + "\n".join("!! WARNING: " + w for w in warnings))
        if args.strict:
            sys.exit(2)
    else:
        print("\nCoverage OK: size and subarea checks passed. This does NOT "
              "check temporal spread — review the per-year table against the "
              "Phase 2 heuristics (origin paper present? recent SOTA present?) "
              "yourself.")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="create an empty manifest")
    p_init.add_argument("manifest")
    p_init.add_argument("--topic", required=True)
    p_init.add_argument("--scope", default="",
                        help="one-line operating scope statement")
    p_init.add_argument("--force", action="store_true")
    p_init.set_defaults(func=cmd_init)

    p_add = sub.add_parser("add", help="add one paper")
    p_add.add_argument("manifest")
    p_add.add_argument("--key", required=True,
                       help="unique citation key, e.g. han2015-pruning")
    p_add.add_argument("--title", required=True)
    p_add.add_argument("--authors", required=True,
                       help="e.g. 'Han, S., Pool, J., Tran, J., Dally, W.'")
    p_add.add_argument("--year", required=True, type=int)
    p_add.add_argument("--venue", required=True,
                       help="venue, or 'arXiv' for preprint-only")
    p_add.add_argument("--url", required=True,
                       help="resolvable URL, e.g. https://arxiv.org/abs/1506.02626 "
                            "— bare identifiers like 'arXiv:1506.02626' fail the "
                            "Phase 8 reference-resolution gate")
    p_add.add_argument("--inclusion-reason", required=True,
                       help="one line: why this paper is in the corpus")
    p_add.add_argument("--subarea", required=True)
    p_add.add_argument("--taxonomy-node", default="",
                       help="leave empty until Phase 5; set via set-node")
    p_add.set_defaults(func=cmd_add)

    p_node = sub.add_parser("set-node", help="assign a paper to a taxonomy node")
    p_node.add_argument("manifest")
    p_node.add_argument("key")
    p_node.add_argument("node")
    p_node.set_defaults(func=cmd_set_node)

    p_refs = sub.add_parser("refs", help="emit markdown reference list")
    p_refs.add_argument("manifest")
    p_refs.add_argument("--out", help="write to file instead of stdout")
    p_refs.set_defaults(func=cmd_refs)

    p_cov = sub.add_parser("coverage", help="coverage report with warnings")
    p_cov.add_argument("manifest")
    p_cov.add_argument("--min-total", type=int, default=MIN_TOTAL)
    p_cov.add_argument("--strict", action="store_true",
                       help="exit 2 if any warning fires (use as the Phase 2 gate)")
    p_cov.set_defaults(func=cmd_coverage)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
