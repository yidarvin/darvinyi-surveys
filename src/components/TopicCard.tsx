import { Link } from "react-router";
import type { Topic } from "../lib/fields";
import { figuresBase } from "../lib/surveys";

/** A topic's card within its field page: the survey's own taxonomy figure as the
 *  graphic (original art, so always safe to display), title, blurb, status. A
 *  `done` topic links out; `pending` or `draft` (built but not yet critic-approved)
 *  render dimmed and unlinked, so the field's full ambition is visible from day
 *  one without exposing an unreviewed page. */
export function TopicCard({ fieldSlug, topic }: { fieldSlug: string; topic: Topic }) {
  const published = topic.status === "done";
  const graphic =
    published && topic.hero ? `${figuresBase(fieldSlug, topic.slug)}${topic.hero}` : "/topic-placeholder.svg";

  const card = (
    <div
      className={`overflow-hidden rounded-lg border border-border bg-surface transition-colors ${
        published ? "group-hover:border-accent-dim" : "opacity-70"
      }`}
    >
      <div className="aspect-[16/10] w-full overflow-hidden border-b border-border bg-bg">
        <img src={graphic} alt="" className="h-full w-full object-cover" />
      </div>
      <div className="p-5">
        <div className="flex items-center gap-2">
          <h3
            className={`font-mono text-base font-bold ${published ? "text-fg group-hover:text-accent" : "text-muted"}`}
          >
            {topic.title}
          </h3>
          <StatusTag status={topic.status} />
        </div>
        {topic.blurb && <p className="mt-2 text-sm text-muted">{topic.blurb}</p>}
        {published && typeof topic.corpusSize === "number" && (
          <p className="mt-3 font-mono text-xs text-comment">{topic.corpusSize} papers surveyed</p>
        )}
      </div>
    </div>
  );

  if (!published) {
    return <div className="cursor-default">{card}</div>;
  }
  return (
    <Link to={`/${fieldSlug}/${topic.slug}`} className="group block no-underline">
      {card}
    </Link>
  );
}

function StatusTag({ status }: { status: Topic["status"] }) {
  if (status === "done") return null;
  const label = status === "draft" ? "in review" : "planned";
  return (
    <span className="shrink-0 rounded border border-border px-1.5 py-0.5 font-mono text-[0.65rem] uppercase tracking-wider text-comment">
      {label}
    </span>
  );
}
