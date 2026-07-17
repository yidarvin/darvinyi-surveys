import GithubSlugger from "github-slugger";

export interface Heading {
  depth: 2 | 3;
  text: string;
  id: string;
}

/** Strip common inline markdown so extracted heading text matches what a reader
 *  (and rehype-slug, operating on rendered text) actually sees. Covers the cases
 *  survey headings realistically use: emphasis, code spans, and links. */
function stripInlineMarkdown(text: string): string {
  return text
    .replace(/`([^`]+)`/g, "$1")
    .replace(/\*\*([^*]+)\*\*/g, "$1")
    .replace(/__([^_]+)__/g, "$1")
    .replace(/\*([^*]+)\*/g, "$1")
    .replace(/_([^_]+)_/g, "$1")
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
    .trim();
}

const HEADING_RE = /^(#{1,6})\s+(.+?)\s*#*$/;
const FENCE_RE = /^\s*(```|~~~)/;

/** Extract every ## / ### heading from a survey.md source, in document order,
 *  with the same ids SurveyMarkdown's rehype-slug pass will assign to the
 *  rendered headings -- both walk headings top to bottom through a fresh
 *  GithubSlugger (the same package rehype-slug uses internally), so SurveyToc's
 *  anchor links always match the rendered ids. All heading levels advance the
 *  slugger (matching rehype-slug's own traversal), but only ##/### are returned
 *  since those are the only levels the TOC shows. Lines inside fenced code blocks
 *  are skipped so a commented "## foo" in an example never counts as a heading. */
export function extractHeadings(markdown: string): Heading[] {
  const slugger = new GithubSlugger();
  const headings: Heading[] = [];
  let inFence = false;
  for (const line of markdown.split("\n")) {
    if (FENCE_RE.test(line)) {
      inFence = !inFence;
      continue;
    }
    if (inFence) continue;
    const m = HEADING_RE.exec(line);
    if (!m) continue;
    const depth = m[1].length;
    const text = stripInlineMarkdown(m[2]);
    if (!text) continue;
    const id = slugger.slug(text);
    if (depth === 2 || depth === 3) {
      headings.push({ depth, text, id });
    }
  }
  return headings;
}
