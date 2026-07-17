import { describe, it, expect, vi, afterEach } from "vitest";
import { render, cleanup, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router";

// vite.config.ts does not set test.globals, so @testing-library/react's
// auto-cleanup (which only registers if `afterEach` exists as a global) never
// fires; without this, renders from one `it()` leak into the next.
afterEach(cleanup);

// Mocks only the registry layer (lib/fields), pointing a fake field/topic at
// the SAME slugs as the real on-disk fixture (content/surveys/__fixtures__/example/,
// reserved for the test suite -- see scripts/validate.py). lib/surveys itself is
// left unmocked, so its real import.meta.glob loaders load the real fixture
// files: this exercises the full registry -> loader -> render pipeline, not a
// synthetic shortcut.
const doneTopic = {
  slug: "example",
  title: "Fixture Example",
  blurb: "a fixture topic for tests",
  hero: "taxonomy.svg",
  status: "done" as const,
  corpusSize: 1,
};
const pendingTopic = {
  slug: "planned",
  title: "Planned Fixture Topic",
  blurb: "not built yet",
  status: "pending" as const,
  corpusSize: null,
};
const fixtureField = {
  slug: "__fixtures__",
  name: "Fixtures",
  blurb: "a fixture field for tests",
  graphic: undefined,
  topics: [doneTopic, pendingTopic],
};

vi.mock("../lib/fields", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/fields")>();
  return {
    ...actual,
    registry: { ...actual.registry, fields: [fixtureField] },
    fields: [fixtureField],
    fieldBySlug: (slug: string) => (slug === fixtureField.slug ? fixtureField : undefined),
    topicBySlug: (f: string, t: string) =>
      f === fixtureField.slug ? fixtureField.topics.find((x) => x.slug === t) : undefined,
    publishedTopics: (field: typeof fixtureField) =>
      field.topics.filter((t) => t.status !== "pending"),
  };
});

// Import AFTER the mock is registered (vi.mock is hoisted, so this is safe at
// module scope, but keep the imports below the mock for readability).
const { AppRoutes } = await import("../App");

describe("FieldPage", () => {
  it("lists a done topic as a link and a pending topic dimmed/unlinked", async () => {
    render(
      <MemoryRouter initialEntries={["/__fixtures__"]}>
        <AppRoutes />
      </MemoryRouter>,
    );
    expect(await screen.findByRole("heading", { name: "Fixtures" })).toBeTruthy();
    const doneLink = screen.getByRole("link", { name: /Fixture Example/i });
    expect(doneLink.getAttribute("href")).toBe("/__fixtures__/example");
    expect(screen.getByText("Planned Fixture Topic")).toBeTruthy();
    expect(screen.queryByRole("link", { name: /Planned Fixture Topic/i })).toBeNull();
  });
});

describe("SurveyPage", () => {
  it("renders the fixture survey: title, taxonomy figure, prose, TOC, paper table", async () => {
    render(
      <MemoryRouter initialEntries={["/__fixtures__/example"]}>
        <AppRoutes />
      </MemoryRouter>,
    );
    await waitFor(() => expect(screen.queryByText("// loading...")).toBeNull());

    expect(screen.getAllByText("Fixture Example").length).toBeGreaterThan(0);
    // taxonomy figure, resolved through the public figures base
    const taxonomyImg = screen.getByAltText(/Taxonomy for Fixture Example/i);
    expect(taxonomyImg.getAttribute("src")).toBe("/surveys/__fixtures__/example/figures/taxonomy.svg");
    // markdown body rendered with a heading id from rehype-slug
    const heading = screen.getByRole("heading", { name: "Scope and driving problems" });
    expect(heading.id).toBe("scope-and-driving-problems");
    // both the desktop sidebar TOC and the mobile collapsible TOC link to it
    const tocLinks = screen.getAllByRole("link", { name: "Scope and driving problems" });
    expect(tocLinks.length).toBeGreaterThan(0);
    for (const link of tocLinks) {
      expect(link.getAttribute("href")).toBe("#scope-and-driving-problems");
    }
    // paper table lists the one fixture paper
    const paperLink = screen.getByRole("link", { name: "Fixture Paper" });
    expect(paperLink.getAttribute("href")).toBe("https://example.com/fixture-paper");
  });

  it("404s a topic that is not status=done (pending/draft are not public)", () => {
    render(
      <MemoryRouter initialEntries={["/__fixtures__/planned"]}>
        <AppRoutes />
      </MemoryRouter>,
    );
    expect(screen.getByText(/page not found/i)).toBeTruthy();
  });
});
