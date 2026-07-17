import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// defineConfig comes from vitest/config (not vite) so the `test` key is typed; tsc
// includes this file, so the plain vite defineConfig would fail the typecheck. Vitest
// reuses this same config, so import.meta.glob (survey.md / corpus.json loaders) works
// in tests too.
export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
  },
});
