import { useMemo, useState } from "react";
import type { Corpus, Paper } from "../lib/surveys";

type SortKey = "title" | "year" | "subarea";

/** The corpus as a sortable, filterable table -- the "summarize the papers"
 *  surface next to the survey's prose synthesis. Reads corpus.json directly, the
 *  survey skill's own paper manifest. */
export function PaperTable({ corpus }: { corpus: Corpus }) {
  const [subareaFilter, setSubareaFilter] = useState<string>("all");
  const [sortKey, setSortKey] = useState<SortKey>("year");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  const subareaCounts = useMemo(() => {
    const counts = new Map<string, number>();
    for (const p of corpus.papers) {
      if (!p.subarea) continue;
      counts.set(p.subarea, (counts.get(p.subarea) ?? 0) + 1);
    }
    return counts;
  }, [corpus.papers]);

  const rows = useMemo(() => {
    const filtered =
      subareaFilter === "all" ? corpus.papers : corpus.papers.filter((p) => p.subarea === subareaFilter);
    const dir = sortDir === "asc" ? 1 : -1;
    return [...filtered].sort((a, b) => {
      if (sortKey === "year") return (a.year - b.year) * dir;
      return (a[sortKey] || "").localeCompare(b[sortKey] || "") * dir;
    });
  }, [corpus.papers, subareaFilter, sortKey, sortDir]);

  function toggleSort(key: SortKey) {
    if (key === sortKey) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir(key === "year" ? "desc" : "asc");
    }
  }

  return (
    <div>
      <div className="flex flex-wrap items-center gap-2">
        <label htmlFor="subarea-filter" className="font-mono text-xs text-comment">
          subarea
        </label>
        <select
          id="subarea-filter"
          value={subareaFilter}
          onChange={(e) => setSubareaFilter(e.target.value)}
          className="rounded border border-border bg-surface px-2 py-1 font-mono text-xs text-fg"
        >
          <option value="all">all ({corpus.papers.length})</option>
          {[...subareaCounts.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([s, n]) => (
            <option key={s} value={s}>
              {s} ({n})
            </option>
          ))}
        </select>
      </div>

      <div className="mt-4 overflow-x-auto rounded-md border border-border">
        <table className="w-full border-collapse text-sm">
          <thead className="bg-surface">
            <tr>
              <SortHeader label="title" active={sortKey === "title"} dir={sortDir} onClick={() => toggleSort("title")} />
              <th className="border-b border-border px-3 py-2 text-left font-mono text-xs uppercase tracking-wider text-comment">
                authors
              </th>
              <SortHeader label="year" active={sortKey === "year"} dir={sortDir} onClick={() => toggleSort("year")} />
              <th className="border-b border-border px-3 py-2 text-left font-mono text-xs uppercase tracking-wider text-comment">
                venue
              </th>
              <SortHeader
                label="subarea"
                active={sortKey === "subarea"}
                dir={sortDir}
                onClick={() => toggleSort("subarea")}
              />
            </tr>
          </thead>
          <tbody>
            {rows.map((p) => (
              <PaperRow key={p.key} paper={p} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function SortHeader({
  label,
  active,
  dir,
  onClick,
}: {
  label: string;
  active: boolean;
  dir: "asc" | "desc";
  onClick: () => void;
}) {
  return (
    <th className="border-b border-border px-3 py-2 text-left font-mono text-xs uppercase tracking-wider text-comment">
      <button type="button" onClick={onClick} className="flex items-center gap-1 hover:text-accent">
        {label}
        {active && <span aria-hidden>{dir === "asc" ? "↑" : "↓"}</span>}
      </button>
    </th>
  );
}

function PaperRow({ paper }: { paper: Paper }) {
  return (
    <tr>
      <td className="border-b border-border px-3 py-2 text-fg">
        <a href={paper.url} target="_blank" rel="noreferrer" className="text-fg hover:text-accent">
          {paper.title}
        </a>
      </td>
      <td className="border-b border-border px-3 py-2 text-muted">{paper.authors}</td>
      <td className="border-b border-border px-3 py-2 text-muted">{paper.year}</td>
      <td className="border-b border-border px-3 py-2 text-muted">{paper.venue}</td>
      <td className="border-b border-border px-3 py-2 text-muted">{paper.subarea}</td>
    </tr>
  );
}
