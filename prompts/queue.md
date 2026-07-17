# Survey Queue

Build order, top to bottom. The **next** item is the first `PENDING` row whose
registry status is `pending`. A `PENDING` row whose registry status is `draft`
is already built and is waiting on the critic, not the builder. Statuses:
`PENDING`, `DONE`, `SKIPPED`. Update the status cell after each run. Reorder by
moving rows (and mirroring the order in `content/registry.json`).

This queue starts empty. Rows are added by `python3 scripts/new_topic.py`,
normally run as part of the intake workflow: describe a survey topic in plain
language and Claude Code deduces the field and topic slug, stamps both files,
builds with the `survey-and-taxonomy-research` skill, and runs the critic loop.
See `CLAUDE.md` for the exact workflow.

| field     | topic                            | title                                                      | status |
|-----------|----------------------------------|------------------------------------------------------------|--------|
| ai        | llm-benchmarks-evals             | LLM & Agent Benchmarks and Evaluations                     | DONE   |
| ai        | rl-in-llms                       | Reinforcement Learning for Large Language Models           | DONE   |
| pathology | flow-cytometry-immunophenotyping | Immunophenotyping of Hematopoietic Cells by Flow Cytometry | DONE   |

<!--
Row shape once populated:

| field | topic                | title                                   | status  |
|-------|-----------------------|-----------------------------------------|---------|
| ai    | llm-benchmarks-evals  | LLM & Agent Benchmarks and Evaluations  | PENDING |

Build notes for a topic are optional: a run looks for
prompts/notes/<field>__<topic>.md first, then derives scope from the title and
description given at intake. Extra columns are fine as long as every row has
them (validate.py checks the column count is consistent).
-->
