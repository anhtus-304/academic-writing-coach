export type LiteraturePaper = {
  id: string;
  title: string;
  authors: string[] | string;
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

export function formatAuthors(authors: unknown): string {
  if (!authors) return "Tác giả";
  if (Array.isArray(authors)) {
    if (authors.length === 0) return "Tác giả";
    return authors
      .map((a) => {
        if (typeof a === "object" && a !== null) {
          const item = a as Record<string, unknown>;
          return String(item.name || item.full_name || item.family || JSON.stringify(a));
        }
        return String(a);
      })
      .join(", ");
  }
  if (typeof authors === "string" && authors.trim()) return authors.trim();
  return String(authors);
}


export type LiteratureFilters = {
  year: string;
  publicationType: string;
  source: string;
};

export interface SelectedPaperItem {
  id: string;
  project_id: string;
  cached_paper_id: string;
  relevant_sections?: string[];
  citation_formatted?: string;
  used_in_draft?: boolean;
  notes?: string;
  selected_at?: string;
  paper?: LiteraturePaper;
}

