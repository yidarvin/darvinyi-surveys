# Fixture survey

## Scope and driving problems

This is a fixture document used only by the test suite (`src/test/`). It is
never linked from `content/registry.json`, so it never appears on the live
site; `scripts/validate.py` treats the `__fixtures__` field as reserved and
skips it.

## Taxonomy

![Taxonomy](figures/taxonomy.svg)

Figure from this fixture.

### Axis: depth

One node, `root`, holds the single fixture paper.

## Evolution narrative

The fixture paper exists so component tests have something real to render.

## Comparison table

| method | year | note |
|---|---|---|
| Fixture Method | 2024 | test row |

## Limitations

None; this is not a real survey.

## References

- [1] A. Author, "Fixture Paper," 2024. https://example.com/fixture-paper
