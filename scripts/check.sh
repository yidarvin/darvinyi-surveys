#!/usr/bin/env bash
# The definition of mechanical done. Run from the repo root. Sections run in order
# and fail fast: an item is not done until every hard section passes. Lint is
# advisory and never blocks the gate. Build already runs tsc --noEmit, so there is
# no separate typecheck section.
#
# Section 4 re-runs the survey-and-taxonomy-research skill's own gates
# (corpus_manifest.py coverage, figure_manifest.py check) against every 'done'
# topic, using this repo's vendored copies of those scripts (scripts/corpus_manifest.py,
# scripts/figure_manifest.py) so the check works in CI without the user's global
# ~/.claude/skills/ directory. Coverage uses its default 25-paper floor and
# --strict subarea balance; the house target of 100+ papers (or an explicit
# smaller-field justification) is a critic judgment call, not a mechanical gate --
# see prompts/critique-rubric.md.
set -uo pipefail

echo "== 1/4 validate (queue + registry + content) =="
if ! python3 scripts/validate.py; then
  echo "VALIDATE FAILED"
  exit 1
fi

echo ""
echo "== 2/4 test =="
if ! npm run test; then
  echo "TESTS FAILED"
  exit 1
fi

echo ""
echo "== 3/4 build (tsc --noEmit + vite build) =="
if ! npm run build; then
  echo "BUILD FAILED"
  exit 1
fi

echo ""
echo "== 4/4 per-topic survey gates (done topics only) =="
DONE_TOPICS=$(python3 - <<'PY'
import json
with open("content/registry.json") as fh:
    data = json.load(fh)
for f in data.get("fields", []):
    for t in f.get("topics", []):
        if t.get("status") == "done":
            print(f"{f['slug']}/{t['slug']}")
PY
)
FAILED=0
if [ -z "$DONE_TOPICS" ]; then
  echo "  (no done topics yet)"
else
  while IFS= read -r key; do
    dir="content/surveys/$key"
    echo "  checking $key"
    if ! python3 scripts/figure_manifest.py check "$dir/figures.json" --document "$dir/survey.md"; then
      echo "  FIGURE CHECK FAILED: $key"
      FAILED=1
    fi
    if ! python3 scripts/corpus_manifest.py coverage "$dir/corpus.json" --strict; then
      echo "  COVERAGE CHECK FAILED: $key"
      FAILED=1
    fi
  done <<< "$DONE_TOPICS"
fi
if [ "$FAILED" -ne 0 ]; then
  echo "SURVEY GATES FAILED"
  exit 1
fi

echo ""
echo "== lint (advisory) =="
if ! npm run lint; then
  echo "lint reported issues (advisory, not blocking the gate)"
fi

echo ""
echo "CHECK OK"
