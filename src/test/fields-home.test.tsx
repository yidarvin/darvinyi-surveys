import { describe, it, expect, vi, afterEach } from "vitest";
import { render, cleanup, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";

// vite.config.ts does not set test.globals, so @testing-library/react's
// auto-cleanup (which only registers if `afterEach` exists as a global) never
// fires; without this, renders from one `it()` leak into the next and text
// queries start matching duplicates.
afterEach(cleanup);

// The scaffold ships with content/registry.json's "fields" empty, and the
// empty state must remain a correct, first-class render (not an accidental
// crash) even after real fields/topics are built. Mock the registry layer
// (same pattern as field-and-survey-pages.test.tsx) rather than depending on
// content/registry.json actually being empty, since the intake workflow's
// whole point is to fill it in over time.
vi.mock("../lib/fields", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/fields")>();
  return { ...actual, registry: { ...actual.registry, fields: [] }, fields: [] };
});

const { AppRoutes } = await import("../App");
const { registry } = await import("../lib/fields");

describe("FieldsHome with an empty registry", () => {
  it("renders the site title and subtitle", () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <AppRoutes />
      </MemoryRouter>,
    );
    expect(screen.getAllByText(registry.title).length).toBeGreaterThan(0);
    expect(screen.getByText(registry.subtitle)).toBeTruthy();
  });

  it("shows the no-fields-yet empty state", () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <AppRoutes />
      </MemoryRouter>,
    );
    expect(screen.getByText(/no fields yet/i)).toBeTruthy();
  });

  it("404s an unknown field", () => {
    render(
      <MemoryRouter initialEntries={["/nonexistent-field"]}>
        <AppRoutes />
      </MemoryRouter>,
    );
    expect(screen.getByText(/page not found/i)).toBeTruthy();
  });
});
