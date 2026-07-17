import { useMemo } from "react";
import { extractHeadings, type Heading } from "../lib/headings";

/** The in-page table of contents for a survey. Two renderings share one heading
 *  extraction: `SurveyToc` is the sticky desktop sidebar, `MobileToc` is a
 *  collapsible block for narrow viewports where there is no room for a sidebar. */
export function SurveyToc({ markdown }: { markdown: string }) {
  const headings = useMemo(() => extractHeadings(markdown), [markdown]);
  if (headings.length === 0) return null;

  return (
    <nav className="hidden lg:sticky lg:top-6 lg:block lg:max-h-[calc(100vh-3rem)] lg:overflow-y-auto">
      <p className="eyebrow mb-3">contents</p>
      <TocList headings={headings} />
    </nav>
  );
}

export function MobileToc({ markdown }: { markdown: string }) {
  const headings = useMemo(() => extractHeadings(markdown), [markdown]);
  if (headings.length === 0) return null;

  return (
    <details className="mb-8 rounded-md border border-border bg-surface p-4 lg:hidden">
      <summary className="cursor-pointer font-mono text-xs uppercase tracking-wider text-comment">
        contents
      </summary>
      <div className="mt-3">
        <TocList headings={headings} />
      </div>
    </details>
  );
}

function TocList({ headings }: { headings: Heading[] }) {
  return (
    <ol className="space-y-1.5 border-l border-border pl-4">
      {headings.map((h) => (
        <li key={h.id} className={h.depth === 3 ? "pl-3" : ""}>
          <a href={`#${h.id}`} className="block text-sm text-muted no-underline hover:text-accent">
            {h.text}
          </a>
        </li>
      ))}
    </ol>
  );
}
