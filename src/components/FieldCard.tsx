import { Link } from "react-router";
import type { Field } from "../lib/fields";
import { publishedTopics } from "../lib/fields";

/** A field's landing-page card: its original emblem, name, blurb, and a count of
 *  published topics. Always links -- a field with zero built topics still shows,
 *  with its topics visible (dimmed) one level down. */
export function FieldCard({ field }: { field: Field }) {
  const published = publishedTopics(field).length;
  const graphic = field.graphic ? `/fields/${field.graphic}` : "/topic-placeholder.svg";

  return (
    <Link
      to={`/${field.slug}`}
      className="group block overflow-hidden rounded-lg border border-border bg-surface no-underline transition-colors hover:border-accent-dim"
    >
      <div className="aspect-[16/10] w-full overflow-hidden border-b border-border bg-bg">
        <img src={graphic} alt="" className="h-full w-full object-cover" />
      </div>
      <div className="p-5">
        <h2 className="font-mono text-lg font-bold text-fg group-hover:text-accent">
          {field.name}
        </h2>
        {field.blurb && <p className="mt-2 text-sm text-muted">{field.blurb}</p>}
        <p className="mt-3 font-mono text-xs text-comment">
          {published === 0
            ? "no surveys published yet"
            : `${published} survey${published === 1 ? "" : "s"}`}
        </p>
      </div>
    </Link>
  );
}
