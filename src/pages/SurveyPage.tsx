import { useEffect, useState } from "react";
import { useParams } from "react-router";
import { fieldBySlug, registry, topicBySlug } from "../lib/fields";
import {
  corpusLoader,
  corpusStats,
  figuresBase,
  surveyMarkdownLoader,
  type Corpus,
} from "../lib/surveys";
import { useHead } from "../lib/useHead";
import { Layout } from "../components/Layout";
import { ErrorBoundary } from "../components/ErrorBoundary";
import { SurveyMarkdown } from "../components/SurveyMarkdown";
import { SurveyToc, MobileToc } from "../components/SurveyToc";
import { PaperTable } from "../components/PaperTable";
import { NotFound } from "./NotFound";

// SurveyPage --- "/:field/:topic", one long page: header stats, the taxonomy
// figure, the survey prose with an in-page TOC sidebar, then the full paper index.
// Only `done` topics are public; `draft` (built, awaiting critic) and `pending`
// resolve to NotFound so an unreviewed page is never link-reachable.
export function SurveyPage() {
  const { field: fieldSlug = "", topic: topicSlug = "" } = useParams();
  const field = fieldBySlug(fieldSlug);
  const topic = topicBySlug(fieldSlug, topicSlug);
  const isPublic = Boolean(field && topic && topic.status === "done");

  const [markdown, setMarkdown] = useState<string | null>(null);
  const [corpus, setCorpus] = useState<Corpus | null>(null);
  const [loadError, setLoadError] = useState(false);

  useHead(
    topic ? `${topic.title} · ${registry.title}` : `Not found · ${registry.title}`,
    topic?.blurb,
  );

  useEffect(() => {
    setMarkdown(null);
    setCorpus(null);
    setLoadError(false);
    if (!isPublic) return;
    const loadMd = surveyMarkdownLoader(fieldSlug, topicSlug);
    const loadCorpus = corpusLoader(fieldSlug, topicSlug);
    if (!loadMd || !loadCorpus) {
      setLoadError(true);
      return;
    }
    let cancelled = false;
    Promise.all([loadMd(), loadCorpus()])
      .then(([md, c]) => {
        if (cancelled) return;
        setMarkdown(md);
        setCorpus(c);
      })
      .catch(() => {
        if (!cancelled) setLoadError(true);
      });
    return () => {
      cancelled = true;
    };
  }, [isPublic, fieldSlug, topicSlug]);

  if (!field || !topic || !isPublic) return <NotFound />;

  const crumbs = [
    { label: "Home", to: "/" },
    { label: field.name, to: `/${field.slug}` },
    { label: topic.title },
  ];

  if (loadError) {
    return (
      <Layout crumbs={crumbs} wide>
        <p className="eyebrow mb-3">error</p>
        <h1 className="font-mono text-2xl font-bold text-fg">{"// survey failed to load"}</h1>
        <p className="mt-3 text-muted">
          This topic is marked done in the registry but its survey files are missing or invalid.
        </p>
      </Layout>
    );
  }

  if (!markdown || !corpus) {
    return (
      <Layout crumbs={crumbs} wide>
        <p className="font-mono text-sm text-comment">{"// loading..."}</p>
      </Layout>
    );
  }

  const stats = corpusStats(corpus);
  const base = figuresBase(field.slug, topic.slug);
  const taxonomyImg = topic.hero ? `${base}${topic.hero}` : null;

  return (
    <Layout crumbs={crumbs} wide>
      <p className="eyebrow mb-3">survey</p>
      <h1 className="font-mono text-3xl font-bold tracking-tight text-fg">{topic.title}</h1>
      {topic.blurb && <p className="mt-2 text-lg text-muted">{topic.blurb}</p>}

      <div className="mt-4 flex flex-wrap gap-x-4 gap-y-1 font-mono text-xs text-comment">
        <span>
          {stats.paperCount} {topic.sourceMode === "broad" ? "sources" : "papers"}
        </span>
        <span>{stats.subareaCount} subareas</span>
        {stats.yearMin !== null && stats.yearMax !== null && (
          <span>
            {stats.yearMin === stats.yearMax ? stats.yearMin : `${stats.yearMin}–${stats.yearMax}`}
          </span>
        )}
        {topic.sourceMode === "broad" && (
          <span title="Corpus: primary texts, authoritative books, and reputable long-form -- not scientific papers">
            broad-mode sources
          </span>
        )}
      </div>

      {taxonomyImg && (
        <div className="mt-8 flex justify-center rounded-md border border-border bg-surface p-4">
          {/* max-h + object-contain: a taxonomy.svg's aspect ratio varies survey to
              survey, and an unconstrained w-full would let a near-square or portrait
              figure blow up to full column width squared -- cap the height instead so
              it reads as a diagram, not a hero banner. */}
          <img
            src={taxonomyImg}
            alt={`Taxonomy for ${topic.title}`}
            className="max-h-[480px] max-w-full object-contain"
          />
        </div>
      )}

      <div className="mt-12 grid grid-cols-1 gap-10 lg:grid-cols-[220px_1fr]">
        <SurveyToc markdown={markdown} />
        <article className="min-w-0">
          <MobileToc markdown={markdown} />
          <ErrorBoundary key={`${fieldSlug}/${topicSlug}`}>
            <SurveyMarkdown markdown={markdown} figuresBase={base} />

            <section className="mt-16">
              <h2 className="scroll-mt-24 font-mono text-xl font-bold text-fg">Paper index</h2>
              <div className="mt-4">
                <PaperTable corpus={corpus} />
              </div>
            </section>
          </ErrorBoundary>
        </article>
      </div>
    </Layout>
  );
}
