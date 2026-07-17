import { describe, it, expect } from "vitest";
import {
  corpusLoader,
  corpusStats,
  figuresBase,
  surveyMarkdownLoader,
} from "../lib/surveys";
import { extractHeadings } from "../lib/headings";

// Exercises the real import.meta.glob loaders against the on-disk fixture at
// content/surveys/__fixtures__/example/ -- reserved for the test suite,
// excluded from content/registry.json (see scripts/validate.py), and never
// linked from the live site.
describe("survey data loaders", () => {
  it("finds the fixture survey markdown and loads it", async () => {
    const loader = surveyMarkdownLoader("__fixtures__", "example");
    expect(loader).toBeDefined();
    const md = await loader!();
    expect(md).toContain("# Fixture survey");
    expect(md).toContain("figures/taxonomy.svg");
  });

  it("finds the fixture corpus and loads it", async () => {
    const loader = corpusLoader("__fixtures__", "example");
    expect(loader).toBeDefined();
    const corpus = await loader!();
    expect(corpus.papers).toHaveLength(1);
    expect(corpus.papers[0].key).toBe("fixture2024");
  });

  it("returns undefined for an unknown field/topic", () => {
    expect(surveyMarkdownLoader("nope", "nope")).toBeUndefined();
    expect(corpusLoader("nope", "nope")).toBeUndefined();
  });

  it("computes corpus stats", async () => {
    const corpus = await corpusLoader("__fixtures__", "example")!();
    const stats = corpusStats(corpus);
    expect(stats.paperCount).toBe(1);
    expect(stats.subareaCount).toBe(1);
    expect(stats.yearMin).toBe(2024);
    expect(stats.yearMax).toBe(2024);
  });

  it("builds the public figures base path", () => {
    expect(figuresBase("ai", "some-topic")).toBe("/surveys/ai/some-topic/figures/");
  });
});

describe("extractHeadings", () => {
  it("extracts ##/### headings with stable ids, skipping h1 and fenced code", () => {
    const md = [
      "# Title",
      "",
      "## Scope and driving problems",
      "",
      "```",
      "## not a heading",
      "```",
      "",
      "### A subsection",
      "",
      "## Scope and driving problems",
    ].join("\n");
    const headings = extractHeadings(md);
    expect(headings.map((h) => h.text)).toEqual([
      "Scope and driving problems",
      "A subsection",
      "Scope and driving problems",
    ]);
    expect(headings[0].depth).toBe(2);
    expect(headings[1].depth).toBe(3);
    // duplicate heading text gets a distinct, deterministic id
    expect(headings[0].id).not.toBe(headings[2].id);
  });

  it("strips inline markdown from heading text", () => {
    const headings = extractHeadings("## **Bold** and `code` and [a link](https://x.test)");
    expect(headings[0].text).toBe("Bold and code and a link");
  });
});
