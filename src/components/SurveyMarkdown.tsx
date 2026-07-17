import ReactMarkdown, { defaultUrlTransform } from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeSlug from "rehype-slug";

/** Renders a survey.md document with the house style. Two survey-specific
 *  concerns beyond stock react-markdown:
 *
 *  1. Heading ids: rehypeSlug assigns them at render time; lib/headings.ts
 *     mirrors the exact same algorithm from raw text so SurveyToc's links resolve.
 *  2. Figure paths: survey.md references its figures relatively
 *     ("figures/taxonomy.svg"), which resolves against the route, not the file.
 *     Rewrite that one prefix to the topic's public figures base; everything else
 *     (http(s) links, data: URIs) goes through react-markdown's own sanitizer. */
export function SurveyMarkdown({
  markdown,
  figuresBase,
}: {
  markdown: string;
  figuresBase: string;
}) {
  const urlTransform = (url: string) => {
    if (url.startsWith("figures/")) return figuresBase + url.slice("figures/".length);
    return defaultUrlTransform(url);
  };

  return (
    <div className="survey-prose">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeSlug]}
        urlTransform={urlTransform}
        components={{
          // id comes from rehypeSlug (via hast properties -> react props) --
          // forward it, or SurveyToc's anchor links have nothing to land on.
          h1: ({ id, children }) => (
            <h1 id={id} className="mt-14 scroll-mt-24 font-mono text-2xl font-bold text-fg first:mt-0">
              {children}
            </h1>
          ),
          h2: ({ id, children }) => (
            <h2 id={id} className="mt-12 scroll-mt-24 font-mono text-xl font-bold text-fg">
              {children}
            </h2>
          ),
          h3: ({ id, children }) => (
            <h3 id={id} className="mt-8 scroll-mt-24 font-mono text-base font-bold text-fg">
              {children}
            </h3>
          ),
          p: ({ children }) => <p className="mt-4 leading-relaxed text-fg">{children}</p>,
          ul: ({ children }) => <ul className="mt-4 list-disc space-y-1.5 pl-6 text-fg">{children}</ul>,
          ol: ({ children }) => <ol className="mt-4 list-decimal space-y-1.5 pl-6 text-fg">{children}</ol>,
          li: ({ children }) => <li className="leading-relaxed">{children}</li>,
          blockquote: ({ children }) => (
            <blockquote className="mt-4 border-l-2 border-accent-dim pl-4 text-muted">
              {children}
            </blockquote>
          ),
          code: ({ className, children }) => {
            const isBlock = /language-/.test(className ?? "");
            if (isBlock) {
              return <code className={`font-mono text-sm ${className ?? ""}`}>{children}</code>;
            }
            return (
              <code className="rounded bg-surface px-1.5 py-0.5 font-mono text-sm text-fg">
                {children}
              </code>
            );
          },
          pre: ({ children }) => (
            <pre className="mt-4 overflow-x-auto rounded-md border border-border bg-surface p-4">
              {children}
            </pre>
          ),
          // max-h + object-contain: a figure's aspect ratio is whatever the source
          // paper's diagram happens to be -- an unconstrained w-full would let a
          // near-square or portrait figure dominate the reading column.
          img: ({ src, alt }) => (
            <div className="mt-4 flex justify-center rounded-md border border-border bg-surface p-4">
              <img
                src={typeof src === "string" ? src : undefined}
                alt={alt ?? ""}
                className="max-h-[480px] max-w-full object-contain"
                loading="lazy"
              />
            </div>
          ),
          table: ({ children }) => (
            <div className="mt-4 overflow-x-auto rounded-md border border-border">
              <table className="w-full border-collapse text-sm">{children}</table>
            </div>
          ),
          thead: ({ children }) => <thead className="bg-surface">{children}</thead>,
          th: ({ children }) => (
            <th className="border-b border-border px-3 py-2 text-left font-mono text-xs uppercase tracking-wider text-comment">
              {children}
            </th>
          ),
          td: ({ children }) => <td className="border-b border-border px-3 py-2 text-fg">{children}</td>,
          hr: () => <hr className="my-10 border-border" />,
        }}
      >
        {markdown}
      </ReactMarkdown>
    </div>
  );
}
