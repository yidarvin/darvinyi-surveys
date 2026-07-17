import { registry, fields } from "../lib/fields";
import { useHead } from "../lib/useHead";
import { Layout } from "../components/Layout";
import { FieldCard } from "../components/FieldCard";

// FieldsHome --- the top-level index, generated from content/registry.json.
// Renders a grid of field cards. A brand-new site has zero fields; that empty
// state is a first-class render, not an error, since the intake workflow adds
// fields one at a time as surveys get built.
export function FieldsHome() {
  useHead(registry.title, registry.subtitle);

  return (
    <Layout>
      <p className="eyebrow mb-3">index</p>
      <h1 className="font-mono text-3xl font-bold tracking-tight text-fg">{registry.title}</h1>
      <p className="mt-2 text-muted">{registry.subtitle}</p>

      {fields.length === 0 ? (
        <div className="mt-12 rounded-lg border border-dashed border-border p-8 text-center">
          <p className="font-mono text-sm text-comment">{"// no fields yet"}</p>
          <p className="mt-2 text-sm text-muted">
            Fields appear here as surveys get built. Describe a survey topic to start one.
          </p>
        </div>
      ) : (
        <div className="mt-12 grid grid-cols-1 gap-6 sm:grid-cols-2">
          {fields.map((field) => (
            <FieldCard key={field.slug} field={field} />
          ))}
        </div>
      )}
    </Layout>
  );
}
