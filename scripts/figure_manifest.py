#!/usr/bin/env python3
"""Figure manifest helper for survey-and-taxonomy-research.

Tracks every extracted figure (source paper, local path, caption, attribution)
and verifies, before the survey document is finalized, that (a) every manifest
figure exists on disk with a nonempty caption and attribution, (b) the set
of images referenced by the document exactly matches the manifest, and (c)
every figure's attribution text appears verbatim in the document. Original
figures authored by the survey itself use the reserved paper key
'this-survey'. `remove` deletes an entry (extracted candidates that end up
unembedded are expected — remove them before the final check).

Python 3 stdlib only (argparse, json, pathlib, re). No third-party imports.
Paths in the manifest are resolved relative to the manifest file's directory;
image paths in the document are resolved relative to the document's directory.
Exit codes: 0 = all checks pass, 1 = any check failed or usage error.
"""

import argparse
import json
import re
import sys
from pathlib import Path

IMG_MD = re.compile(r"!\[[^\]]*\]\(\s*([^)\s]+)")           # ![alt](path)
IMG_HTML = re.compile(r"<img[^>]+src=[\"']([^\"']+)[\"']")  # <img src="path">


def load(manifest_path):
    p = Path(manifest_path)
    if p.exists():
        try:
            data = json.loads(p.read_text())
        except json.JSONDecodeError as e:
            sys.exit(f"ERROR: manifest is not valid JSON: {e}")
    else:
        data = {"figures": []}
    data.setdefault("figures", [])
    return p, data


def cmd_add(args):
    p, data = load(args.manifest)
    if any(f["id"] == args.id for f in data["figures"]):
        sys.exit(f"ERROR: duplicate figure id '{args.id}'")
    for name, value in (("caption", args.caption),
                        ("attribution", args.attribution),
                        ("paper-key", args.paper_key)):
        if not value.strip():
            sys.exit(f"ERROR: --{name} must be nonempty — every figure "
                     f"carries a caption, an attribution, and a paper key "
                     f"(use 'this-survey' for original figures)")
    data["figures"].append({
        "id": args.id, "paper_key": args.paper_key, "path": args.path,
        "caption": args.caption, "attribution": args.attribution,
    })
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(f"Added figure [{args.id}] {args.path} "
          f"({len(data['figures'])} figures in manifest)")


def cmd_remove(args):
    p, data = load(args.manifest)
    kept = [f for f in data["figures"] if f["id"] != args.id]
    if len(kept) == len(data["figures"]):
        sys.exit(f"ERROR: no figure with id '{args.id}'")
    data["figures"] = kept
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(f"Removed figure [{args.id}] "
          f"({len(kept)} figures remain in manifest)")


def doc_image_paths(doc_path):
    text = Path(doc_path).read_text()
    raw = IMG_MD.findall(text) + IMG_HTML.findall(text)
    local = [r for r in raw if not r.startswith(("http://", "https://",
                                                 "data:"))]
    remote = [r for r in raw if r.startswith(("http://", "https://"))]
    return local, remote


def cmd_check(args):
    p, data = load(args.manifest)
    base = p.parent
    failures = []

    if not data["figures"]:
        failures.append("manifest has no figures")

    resolved = {}
    for fig in data["figures"]:
        fid = fig.get("id", "?")
        path = base / fig.get("path", "")
        if not path.is_file():
            failures.append(f"figure [{fid}]: file missing on disk: {path}")
        else:
            resolved[path.resolve()] = fid
        if not fig.get("caption", "").strip():
            failures.append(f"figure [{fid}]: empty caption")
        if not fig.get("attribution", "").strip():
            failures.append(f"figure [{fid}]: empty attribution")
        if not fig.get("paper_key", "").strip():
            failures.append(f"figure [{fid}]: empty paper_key")

    if args.document:
        doc = Path(args.document)
        if not doc.is_file():
            sys.exit(f"ERROR: document not found: {doc}")
        doc_text = doc.read_text()
        for fig in data["figures"]:
            attribution = fig.get("attribution", "").strip()
            if attribution and attribution not in doc_text:
                failures.append(
                    f"figure [{fig.get('id', '?')}]: attribution text not "
                    f"found in document — every embedded figure's caption "
                    f"must carry its attribution verbatim: '{attribution}'")
        local, remote = doc_image_paths(doc)
        for r in remote:
            failures.append(f"document embeds a REMOTE image ({r}) — "
                            f"figures must be local files beside the document")
        used = set()
        for rel in local:
            ap = (doc.parent / rel).resolve()
            used.add(ap)
            if ap not in resolved:
                failures.append(f"document references image not in manifest: "
                                f"{rel}")
        for ap, fid in resolved.items():
            if ap not in used:
                failures.append(f"manifest figure [{fid}] ({ap.name}) is "
                                f"never referenced by the document")

    if failures:
        print(f"FIGURE CHECK FAILED ({len(failures)} problem(s)):")
        for f in failures:
            print(f"  !! {f}")
        sys.exit(1)
    n = len(data["figures"])
    scope = f" and document {args.document}" if args.document else ""
    print(f"Figure check OK: {n} figure(s) verified{scope}.")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_add = sub.add_parser("add", help="record one extracted figure")
    p_add.add_argument("manifest")
    p_add.add_argument("--id", required=True,
                       help="unique figure id, e.g. fig-han2015-sparsity")
    p_add.add_argument("--paper-key", required=True,
                       help="corpus-manifest key of the source paper, or "
                            "'this-survey' for original figures you authored")
    p_add.add_argument("--path", required=True,
                       help="figure file path relative to the manifest's directory")
    p_add.add_argument("--caption", required=True)
    p_add.add_argument("--attribution", required=True,
                       help='e.g. "Figure from Han et al. (2015), arXiv:1506.02626"')
    p_add.set_defaults(func=cmd_add)

    p_rm = sub.add_parser("remove",
                          help="delete a figure entry (e.g. an extracted "
                               "candidate you decided not to embed)")
    p_rm.add_argument("manifest")
    p_rm.add_argument("id", help="figure id to remove")
    p_rm.set_defaults(func=cmd_remove)

    p_chk = sub.add_parser("check",
                           help="verify files, captions, attributions; with "
                                "--document, cross-check embedded images and "
                                "attribution text")
    p_chk.add_argument("manifest")
    p_chk.add_argument("--document",
                       help="path to the survey document (markdown)")
    p_chk.set_defaults(func=cmd_check)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
