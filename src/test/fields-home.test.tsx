import { describe, it, expect, afterEach } from "vitest";
import { render, cleanup, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { AppRoutes } from "../App";
import { registry } from "../lib/fields";

// vite.config.ts does not set test.globals, so @testing-library/react's
// auto-cleanup (which only registers if `afterEach` exists as a global) never
// fires; without this, renders from one `it()` leak into the next and text
// queries start matching duplicates.
afterEach(cleanup);

// The scaffold ships with content/registry.json's "fields" empty. This is the
// real, unmocked registry -- these tests assert the empty state is a correct,
// first-class render, not an accidental crash.
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
