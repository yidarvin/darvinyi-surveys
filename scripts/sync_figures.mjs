// Copy every survey's figures/ directory into public/surveys/<field>/<topic>/figures/
// so an <img> in the rendered markdown (and a topic card's taxonomy hero) resolves at
// runtime -- Vite only serves what's under public/, not content/. Runs as predev and
// prebuild; plain Node, no dependencies, so this stays out of the TypeScript build.
import { cpSync, existsSync, readdirSync, statSync } from "node:fs";
import { join, resolve } from "node:path";

const root = process.cwd();
const surveysDir = resolve(root, "content/surveys");
const publicDir = resolve(root, "public/surveys");

if (!existsSync(surveysDir)) {
  console.log("sync_figures: no content/surveys/, nothing to do.");
  process.exit(0);
}

let copied = 0;
for (const field of readdirSync(surveysDir)) {
  const fieldDir = join(surveysDir, field);
  if (!statSync(fieldDir).isDirectory()) continue;
  for (const topic of readdirSync(fieldDir)) {
    const figuresDir = join(fieldDir, topic, "figures");
    if (!existsSync(figuresDir)) continue;
    const dest = join(publicDir, field, topic, "figures");
    cpSync(figuresDir, dest, { recursive: true });
    copied++;
  }
}
console.log(`sync_figures: synced figures for ${copied} topic(s).`);
