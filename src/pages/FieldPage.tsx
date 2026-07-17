import { useParams } from "react-router";
import { registry, fieldBySlug } from "../lib/fields";
import { useHead } from "../lib/useHead";
import { Layout } from "../components/Layout";
import { TopicCard } from "../components/TopicCard";
import { NotFound } from "./NotFound";

// FieldPage --- "/:field", a grid of topic cards for one field. Pending and draft
// topics render dimmed and unlinked (see TopicCard) so the field's planned scope
// is visible even before a topic is critic-approved.
export function FieldPage() {
  const { field: fieldSlug = "" } = useParams();
  const field = fieldBySlug(fieldSlug);

  useHead(
    field ? `${field.name} · ${registry.title}` : `Not found · ${registry.title}`,
    field?.blurb,
  );

  if (!field) return <NotFound />;

  return (
    <Layout crumbs={[{ label: "Home", to: "/" }, { label: field.name }]}>
      <p className="eyebrow mb-3">field</p>
      <h1 className="font-mono text-3xl font-bold tracking-tight text-fg">{field.name}</h1>
      {field.blurb && <p className="mt-2 text-muted">{field.blurb}</p>}

      {field.topics.length === 0 ? (
        <div className="mt-12 rounded-lg border border-dashed border-border p-8 text-center">
          <p className="font-mono text-sm text-comment">{"// no topics yet"}</p>
          <p className="mt-2 text-sm text-muted">
            No surveys have been started in this field yet.
          </p>
        </div>
      ) : (
        <div className="mt-12 grid grid-cols-1 gap-6 sm:grid-cols-2">
          {field.topics.map((topic) => (
            <TopicCard key={topic.slug} fieldSlug={field.slug} topic={topic} />
          ))}
        </div>
      )}
    </Layout>
  );
}
