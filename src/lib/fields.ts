// fields.ts --- typed access to the "database" at content/registry.json.
// The registry is the ordered table of contents: an ordered list of fields, each
// holding an ordered list of topics. It is the one place that knows which fields
// and topics exist, their order, and their build status. The intake workflow
// (via scripts/new_topic.py and scripts/mark.py) updates it; the site reads it.
import data from "../../content/registry.json";

export type TopicStatus = "pending" | "draft" | "done";

export interface Topic {
  /** URL-safe id, unique within its field. Must match content/surveys/<field>/<slug>. */
  slug: string;
  title: string;
  blurb?: string;
  /** Filename of the topic's card graphic within its survey's figures/ dir, e.g.
   *  "taxonomy.svg". Absent or unresolvable falls back to a placeholder emblem. */
  hero?: string;
  status: TopicStatus;
  /** Paper count from corpus.json, filled in once the topic is built. */
  corpusSize?: number | null;
}

export interface Field {
  /** URL-safe id, e.g. "ai". */
  slug: string;
  name: string;
  blurb?: string;
  /** Filename of the field's emblem under public/fields/, e.g. "ai.svg". */
  graphic?: string;
  topics: Topic[];
}

export interface Registry {
  title: string;
  subtitle: string;
  /** Canonical origin, e.g. "https://surveys.darvinyi.com". When set, the build
   *  writes dist/sitemap.xml from the published topics. */
  url?: string;
  fields: Field[];
}

export const registry = data as Registry;

export const fields = registry.fields;

export function fieldBySlug(slug: string): Field | undefined {
  return fields.find((f) => f.slug === slug);
}

export function topicBySlug(fieldSlug: string, topicSlug: string): Topic | undefined {
  return fieldBySlug(fieldSlug)?.topics.find((t) => t.slug === topicSlug);
}

/** Topics that have a built page (draft or done), in field order. */
export function publishedTopics(field: Field): Topic[] {
  return field.topics.filter((t) => t.status !== "pending");
}

/** Fields that hold at least one published (draft or done) topic. */
export function fieldsWithContent(): Field[] {
  return fields.filter((f) => publishedTopics(f).length > 0);
}

export function adjacentTopics(
  fieldSlug: string,
  topicSlug: string,
): { prev?: Topic; next?: Topic } {
  const field = fieldBySlug(fieldSlug);
  if (!field) return {};
  const list = publishedTopics(field);
  const i = list.findIndex((t) => t.slug === topicSlug);
  if (i === -1) return {};
  return { prev: list[i - 1], next: list[i + 1] };
}
