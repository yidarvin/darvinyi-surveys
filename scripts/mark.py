#!/usr/bin/env python3
"""Set a topic's status in the registry and the queue in one atomic operation.

Usage:

    python3 scripts/mark.py <field>/<topic> <done|draft|skipped|pending>

Full status mapping (registry, queue):

    done     registry 'done',    queue 'DONE'
    draft    registry 'draft',   queue 'PENDING'
    pending  registry 'pending', queue 'PENDING'
    skipped  registry 'pending', queue 'SKIPPED'   (skipped is a queue-only idea)

Refuses up front, with no write, if the key is missing from either file. After
writing, it runs the full validate.py suite in-process; on any error it restores
both files untouched and exits 1. So marking a topic done while its survey.md
still holds a TODO marker is refused: the content gate cannot be skipped by
marking. The same mechanism means `done` additionally requires
content/critiques/<field>__<topic>.md on disk with first line `verdict: approve`
(see validate.py); a topic is only ever marked done by the critic, once it has
approved.
"""
from __future__ import annotations

import json
import os
import sys

import validate as V

MAPPING = {
    "done": ("done", "DONE"),
    "draft": ("draft", "PENDING"),
    "pending": ("pending", "PENDING"),
    "skipped": ("pending", "SKIPPED"),
}


def main(argv: list[str]) -> int:
    if len(argv) != 3 or argv[2] not in MAPPING or "/" not in argv[1]:
        print("usage: python3 scripts/mark.py <field>/<topic> <done|draft|skipped|pending>")
        return 2

    key = argv[1].strip()
    fslug, tslug = key.split("/", 1)
    target = argv[2]
    reg_status, queue_status = MAPPING[target]
    repo = os.getcwd()

    reg_file = V.registry_path(repo)
    q_file = V.queue_path(repo)
    with open(reg_file, "r", encoding="utf-8") as fh:
        reg_original = fh.read()
    with open(q_file, "r", encoding="utf-8") as fh:
        q_original = fh.read()

    data = json.loads(reg_original)
    target_topic = None
    for f in data.get("fields", []):
        if f.get("slug") != fslug:
            continue
        for t in f.get("topics", []):
            if t.get("slug") == tslug:
                target_topic = t
    in_reg = target_topic is not None

    q = V.parse_queue(repo)
    field_i = V._col_index(q["header"], "field")
    topic_i = V._col_index(q["header"], "topic")
    status_i = V._col_index(q["header"], "status")
    in_queue = field_i != -1 and topic_i != -1 and any(
        len(r) > max(field_i, topic_i) and r[field_i] == fslug and r[topic_i] == tslug
        for r in q["rows"]
    )

    if not in_reg or not in_queue:
        missing = [name for name, present in (("registry", in_reg), ("queue", in_queue)) if not present]
        print(f"refusing: '{key}' is missing from the {', '.join(missing)}. Nothing written.")
        return 1

    # apply the change to both files
    target_topic["status"] = reg_status
    V.write_registry(repo, data)

    new_rows = []
    for r in q["rows"]:
        r = list(r)
        if len(r) > max(field_i, topic_i) and r[field_i] == fslug and r[topic_i] == tslug:
            r[status_i] = queue_status
        new_rows.append(r)
    V.write_queue(repo, q, new_rows)

    # post-write gate: any validation error rolls both files back
    errors, warnings = V.validate(repo)
    if errors:
        with open(reg_file, "w", encoding="utf-8") as fh:
            fh.write(reg_original)
        with open(q_file, "w", encoding="utf-8") as fh:
            fh.write(q_original)
        print(f"refusing to mark '{key}' {target}: validation failed, reverted both files.")
        for e in errors:
            print(f"  error: {e}")
        return 1

    print(f"marked '{key}': registry '{reg_status}', queue '{queue_status}'.")
    for w in warnings:
        print(f"  warn: {w}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
