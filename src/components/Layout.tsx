import type { ReactNode } from "react";
import { Link } from "react-router";
import { registry } from "../lib/fields";

export interface Crumb {
  label: string;
  to?: string;
}

/** The shell: a quiet mono header with an optional breadcrumb trail, a centered
 *  reading column, a thin footer. `wide` widens the column for pages that need
 *  room for a sidebar (the survey page's in-page TOC); every other page stays a
 *  narrow reading column. */
export function Layout({
  children,
  crumbs,
  wide = false,
}: {
  children: ReactNode;
  crumbs?: Crumb[];
  wide?: boolean;
}) {
  const widthClass = wide ? "max-w-6xl" : "max-w-3xl";
  return (
    <div className="min-h-screen bg-bg text-fg">
      <header className="border-b border-border">
        <div className={`mx-auto flex ${widthClass} items-center justify-between px-5 py-4`}>
          <Link to="/" className="font-mono text-sm text-fg no-underline hover:no-underline">
            <span className="text-comment">/* </span>
            {registry.title}
            <span className="text-comment"> */</span>
          </Link>
          <a
            href="https://github.com/yidarvin"
            className="font-mono text-xs text-muted hover:text-accent"
          >
            source
          </a>
        </div>
        {crumbs && crumbs.length > 0 && (
          <div className={`mx-auto ${widthClass} px-5 pb-3 font-mono text-xs text-muted`}>
            {crumbs.map((c, i) => (
              <span key={i}>
                {i > 0 && <span className="text-comment"> / </span>}
                {c.to ? (
                  <Link to={c.to} className="text-muted hover:text-accent">
                    {c.label}
                  </Link>
                ) : (
                  <span className="text-fg">{c.label}</span>
                )}
              </span>
            ))}
          </div>
        )}
      </header>
      <main className={`mx-auto ${widthClass} px-5 py-10`}>{children}</main>
      <footer className="border-t border-border">
        <div className={`mx-auto ${widthClass} px-5 py-6 font-mono text-xs text-comment`}>
          {"// built with claude code --- one survey at a time"}
        </div>
      </footer>
    </div>
  );
}
