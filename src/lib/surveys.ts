// surveys.ts --- maps a "<field>/<topic>" key to its lazily-loaded survey document
// and corpus data. import.meta.glob keeps each survey in its own chunk so a reader
// only downloads the one they open. The shapes below match the survey-and-taxonomy-
// research skill's own manifest scripts (corpus_manifest.py / figure_manifest.py)
// exactly -- this file does not invent a schema, it reads the skill's native output.

export interface Paper {
  key: string;
  title: string;
  authors: string;
  year: number;
  venue: string;
  url: string;
  inclusion_reason: string;
  subarea: string;
  taxonomy_node: string;
}

export interface Corpus {
  topic: string;
  scope: string;
  papers: Paper[];
}

export interface SurveyFigure {
  id: string;
  paper_key: string;
  path: string;
  caption: string;
  attribution: string;
}

export interface FigureManifest {
  figures: SurveyFigure[];
}

type RawLoader = () => Promise<string>;
type CorpusLoader = () => Promise<Corpus>;

// Note: this also picks up content/surveys/__fixtures__/ (reserved for the test
// suite in src/test/, exempted from scripts/validate.py's registry-membership
// check). It is never linked from any route, so it ends up as one small unused
// chunk in a production build -- not worth a build-vs-test conditional glob to
// avoid.
const mdModules = import.meta.glob("../../content/surveys/*/*/survey.md", {
  query: "?raw",
  import: "default",
}) as Record<string, RawLoader>;

const corpusModules = import.meta.glob("../../content/surveys/*/*/corpus.json", {
  import: "default",
}) as Record<string, CorpusLoader>;

/** Path looks like ".../content/surveys/<field>/<topic>/survey.md"; key on the last
 *  two segments so field and topic slugs join the same way the URL does. */
function parseKey(path: string): string {
  const parts = path.split("/");
  const topic = parts[parts.length - 2];
  const field = parts[parts.length - 3];
  return `${field}/${topic}`;
}

const mdByKey: Record<string, RawLoader> = {};
for (const path in mdModules) mdByKey[parseKey(path)] = mdModules[path];

const corpusByKey: Record<string, CorpusLoader> = {};
for (const path in corpusModules) corpusByKey[parseKey(path)] = corpusModules[path];

export function surveyMarkdownLoader(field: string, topic: string): RawLoader | undefined {
  return mdByKey[`${field}/${topic}`];
}

export function corpusLoader(field: string, topic: string): CorpusLoader | undefined {
  return corpusByKey[`${field}/${topic}`];
}

/** Public base a survey's relative figure paths (e.g. "figures/taxonomy.svg") resolve
 *  against, once scripts/sync_figures.mjs has copied them under public/. */
export function figuresBase(field: string, topic: string): string {
  return `/surveys/${field}/${topic}/figures/`;
}

export interface CorpusStats {
  paperCount: number;
  subareaCount: number;
  yearMin: number | null;
  yearMax: number | null;
}

export function corpusStats(corpus: Corpus): CorpusStats {
  const papers = corpus.papers ?? [];
  const subareas = new Set(papers.map((p) => p.subarea).filter(Boolean));
  const years = papers.map((p) => p.year).filter((y): y is number => typeof y === "number");
  return {
    paperCount: papers.length,
    subareaCount: subareas.size,
    yearMin: years.length ? Math.min(...years) : null,
    yearMax: years.length ? Math.max(...years) : null,
  };
}
