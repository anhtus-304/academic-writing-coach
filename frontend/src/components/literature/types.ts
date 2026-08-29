export type LiteraturePaper = {
  id: string;
  title: string;
  authors: string[];
  abstract?: string;
  year?: number;
  source?: string;
  publicationType?: string;
  doi?: string;
  url?: string;
  citationCount?: number;
  summaryVi?: string;
  raw?: Record<string, unknown>;
};

export type LiteratureFilters = {
  year: string;
  publicationType: string;
  source: string;
};
