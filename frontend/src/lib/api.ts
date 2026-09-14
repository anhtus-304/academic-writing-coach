const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

import type { LiteraturePaper, SelectedPaperItem } from "@/components/literature/types";

export function getAuthToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("token") || localStorage.getItem("access_token");
}

export function setAuthToken(token: string) {
  if (typeof window === "undefined") return;
  localStorage.setItem("token", token);
  localStorage.setItem("access_token", token);
}

export function clearAuthToken() {
  if (typeof window === "undefined") return;
  localStorage.removeItem("token");
  localStorage.removeItem("access_token");
}

export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getAuthToken();
  const isFormData = typeof FormData !== "undefined" && options.body instanceof FormData;
  const headers: Record<string, string> = {
    ...(isFormData ? {} : { "Content-Type": "application/json" }),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...((options.headers as Record<string, string>) ?? {}),
  };

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
    credentials: "include", // Automatically send and receive HttpOnly Cookies
  });

  if (!response.ok) {
    const errorText = await response.text();
    let errorMessage = "Request failed";
    try {
      const errorJson = JSON.parse(errorText);
      errorMessage = errorJson.detail || errorJson.message || errorText;
    } catch {
      errorMessage = errorText || `Error ${response.status}: ${response.statusText}`;
    }
    throw new Error(errorMessage);
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return {} as T;
  }

  return (await response.json()) as T;
}

export function getApiBaseUrl() {
  return API_BASE_URL;
}

export interface UserProfile {
  id: string;
  email: string;
  name: string;
  avatar_url?: string;
  credits: number;
}

export interface ProjectData {
  id: string;
  user_id: string;
  topic: string;
  document_type: "tieu_luan" | "khoa_luan" | "luan_van";
  field?: string;
  university?: string;
  citation_style: "apa7" | "ieee" | "bgddt";
  additional_requirements?: string;
  status: "draft" | "in_progress" | "completed";
  created_at: string;
  updated_at?: string;
}

export interface OutlineData {
  id: string;
  project_id: string;
  title: string;
  chapters: unknown;
  suggestions?: Record<string, unknown>;
  template_source?: string;
  version: number;
  generated_at?: string;
  updated_at?: string;
}

export const authApi = {
  getGoogleLoginUrl: () => `${API_BASE_URL}/api/v1/auth/google/login`,
  devLogin: (email?: string, name?: string) =>
    apiFetch<{ access_token: string; token_type: string; user: UserProfile }>(
      "/api/v1/auth/dev-login",
      {
        method: "POST",
        body: JSON.stringify({ email: email || "demo@student.edu.vn", name: name || "Thúy Vi" }),
      }
    ),
  logout: () =>
    apiFetch<{ message: string }>("/api/v1/auth/logout", {
      method: "POST",
    }).finally(() => {
      clearAuthToken();
    }),
  getMe: () => apiFetch<UserProfile>("/api/v1/auth/me"),
};

export const projectApi = {
  list: () => apiFetch<ProjectData[]>("/api/v1/projects/"),
  get: (id: string) => apiFetch<ProjectData>(`/api/v1/projects/${id}`),
  create: (data: Partial<ProjectData>) =>
    apiFetch<ProjectData>("/api/v1/projects/", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  update: (id: string, data: Partial<ProjectData>) =>
    apiFetch<ProjectData>(`/api/v1/projects/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  delete: (id: string) =>
    apiFetch<void>(`/api/v1/projects/${id}`, {
      method: "DELETE",
    }),
};

export const outlineApi = {
  get: (projectId: string) =>
    apiFetch<{ success: boolean; outline: OutlineData | null }>(`/api/v1/projects/${projectId}/outline`),
  generate: (projectId: string, templateId?: string, userRequirements?: string) =>
    apiFetch<{ success: boolean; outline: OutlineData }>(`/api/v1/projects/${projectId}/outline/generate`, {
      method: "POST",
      body: JSON.stringify({
        template_id: templateId,
        user_requirements: userRequirements,
      }),
    }),
  update: (projectId: string, chapters: unknown, suggestions?: Record<string, unknown>) =>
    apiFetch<{ success: boolean; outline: OutlineData }>(`/api/v1/projects/${projectId}/outline`, {
      method: "PUT",
      body: JSON.stringify({
        chapters,
        suggestions,
      }),
    }),
};

export interface LiteratureSearchResponse {
  query: string;
  expanded_queries?: string[];
  total_results: number;
  papers: LiteraturePaper[];
}

export interface ProjectLiteratureSearchResponse {
  search_session_id: string;
  cached: boolean;
  total_results: number;
  expanded_queries?: string[];
  papers: LiteraturePaper[];
}

export interface ProjectSelectedPapersResponse {
  total: number;
  selected_papers: SelectedPaperItem[];
}

export interface RecentSearchResponse {
  has_recent: boolean;
  search_session_id?: string;
  query?: string;
  total_results?: number;
  expires_at?: string;
  papers: LiteraturePaper[];
}

export interface LiteratureSummaryResponse {
  paper_id: string;
  summary_vi: string;
}

export const literatureApi = {
  search: (
    query: string,
    filters?: {
      year?: string;
      publicationType?: string;
      source?: string;
      limit?: number;
      enableSemanticExpansion?: boolean;
    }
  ) => {
    const params = new URLSearchParams({ query });
    if (filters?.year) params.set("year", filters.year);
    if (filters?.publicationType) params.set("publication_type", filters.publicationType);
    if (filters?.source) params.set("source", filters.source);
    if (filters?.limit) params.set("limit", String(filters.limit));
    if (filters?.enableSemanticExpansion !== undefined) {
      params.set("enable_semantic_expansion", String(filters.enableSemanticExpansion));
    }
    return apiFetch<LiteratureSearchResponse>(`/api/v1/literature/search?${params.toString()}`);
  },
  searchInProject: (
    projectId: string,
    query: string,
    filters?: {
      year?: string;
      publicationType?: string;
      source?: string;
    }
  ) =>
    apiFetch<ProjectLiteratureSearchResponse>(`/api/v1/projects/${projectId}/literature/search`, {
      method: "POST",
      body: JSON.stringify({ query, filters }),
    }),
  selectPaper: (
    projectId: string,
    payload: {
      paper?: LiteraturePaper;
      cached_paper_id?: string;
      relevant_sections?: string[];
      notes?: string;
    }
  ) =>
    apiFetch<SelectedPaperItem>(`/api/v1/projects/${projectId}/literature/select`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getSelectedPapers: (projectId: string) =>
    apiFetch<ProjectSelectedPapersResponse>(`/api/v1/projects/${projectId}/literature/selected`),
  removeSelectedPaper: (projectId: string, selectedPaperId: string) =>
    apiFetch<{ message: string }>(`/api/v1/projects/${projectId}/literature/selected/${selectedPaperId}`, {
      method: "DELETE",
    }),
  getRecentSearch: (projectId: string) =>
    apiFetch<RecentSearchResponse>(`/api/v1/projects/${projectId}/literature/recent-search`),
  summarize: (paper: LiteraturePaper) =>
    apiFetch<LiteratureSummaryResponse>("/api/v1/literature/summarize", {
      method: "POST",
      body: JSON.stringify({ paper }),
    }),
};

export interface MissingCitationClaim {
  sentence: string;
  reason: string;
  suggested_action: string;
  recommended_paper_id?: string | null;
  recommended_paper_title?: string | null;
  in_text_suggestion?: string | null;
}

export interface UncitedPaperItem {
  id?: string;
  title: string;
  authors: string[];
  year?: number;
  in_text_code?: string;
  suggested_action: string;
}

export interface CitationCheckResponse {
  total_issues: number;
  missing_claims: MissingCitationClaim[];
  invalid_citations: string[];
  citation_warnings: string[];
  uncited_papers: UncitedPaperItem[];
  verified_count: number;
  credits_charged: number;
}

export const citationApi = {
  checkCitations: (projectId: string, content: string, citationStyle = "apa7") =>
    apiFetch<CitationCheckResponse>(`/api/v1/projects/${projectId}/citation/check`, {
      method: "POST",
      body: JSON.stringify({ content, citation_style: citationStyle }),
    }),
  formatCitation: (metadata: Record<string, unknown>, style = "apa7", index = 1) =>
    apiFetch<{ in_text_citation: string; full_citation: string; style: string }>("/api/v1/citation/format", {
      method: "POST",
      body: JSON.stringify({ metadata, style, index }),
    }),
  getProjectBibliography: (projectId: string, style?: string) =>
    apiFetch<{
      project_id: string;
      style: string;
      total_references: number;
      bibliography: string[];
      html_formatted: string;
    }>(`/api/v1/projects/${projectId}/citation/bibliography${style ? `?style=${encodeURIComponent(style)}` : ""}`, {
      method: "POST",
    }),
};


export interface CreditBalanceResponse {
  balance: number;
}

export interface AIUseLogItem {
  id: string;
  agent_name: string;
  tokens_used: number;
  credits_charged: number;
  duration_ms?: number;
  project_id?: string;
  created_at?: string;
}

export interface CreditTransactionItem {
  id: string;
  type: string;
  amount: number;
  balance_after: number;
  description: string;
  created_at?: string;
}

export const creditApi = {
  getBalance: () => apiFetch<CreditBalanceResponse>("/api/v1/credits/balance"),
  getLogs: (limit = 20) => apiFetch<AIUseLogItem[]>(`/api/v1/credits/logs?limit=${limit}`),
  getTransactions: (limit = 20) => apiFetch<CreditTransactionItem[]>(`/api/v1/credits/transactions?limit=${limit}`),
};

export interface AskAIRequestPayload {
  selected_text: string;
  action: "explain" | "summarize" | "academic_rewrite" | "critique" | "custom" | string;
  custom_prompt?: string;
  project_id?: string;
}

export interface AskAIResponseData {
  action: string;
  selected_text: string;
  response: string;
  tokens_used: number;
  credits_charged: number;
}

export const agentApi = {
  askAI: (payload: AskAIRequestPayload) =>
    apiFetch<AskAIResponseData>("/api/v1/agents/ask", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};

export async function apiDownload(path: string, body: unknown, defaultFilename: string) {
  const token = getAuthToken();
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
    credentials: "include",
  });
  if (!res.ok) {
    const errorText = await res.text();
    let errorMessage = "Download failed";
    try {
      const errJson = JSON.parse(errorText);
      errorMessage = errJson.detail || errJson.message || errorText;
    } catch {
      errorMessage = errorText;
    }
    throw new Error(errorMessage);
  }
  const blob = await res.blob();
  const disposition = res.headers.get("Content-Disposition");
  let filename = defaultFilename;
  if (disposition && disposition.includes("filename=")) {
    const match = disposition.match(/filename="?([^"]+)"?/);
    if (match && match[1]) filename = match[1];
  }
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  document.body.removeChild(a);
}

export interface DocumentDraftData {
  id: string;
  project_id: string;
  content: unknown;
  html: string;
  chapter_ref?: string | null;
  word_count: number;
  version: number;
  updated_at?: string | null;
}

export const documentApi = {
  get: (projectId: string) =>
    apiFetch<{ success: boolean; document: DocumentDraftData | null }>(
      `/api/v1/projects/${projectId}/document`
    ),
  save: (projectId: string, content: string | Record<string, unknown>, wordCount = 0) =>
    apiFetch<{ success: boolean; document: DocumentDraftData }>(
      `/api/v1/projects/${projectId}/document`,
      {
        method: "PUT",
        body: JSON.stringify({ content, word_count: wordCount }),
      }
    ),
};

export const exportApi = {
  exportDocx: (projectId: string, htmlContent: string, topic?: string) =>
    apiDownload(
      `/api/v1/projects/${projectId}/export/docx`,
      { html_content: htmlContent, topic },
      `${topic || "Bao_Cao_Hoc_Thuat"}.docx`
    ),
  exportMarkdown: (projectId: string, htmlContent: string, topic?: string) =>
    apiDownload(
      `/api/v1/projects/${projectId}/export/markdown`,
      { html_content: htmlContent, topic },
      `${topic || "Bao_Cao_Hoc_Thuat"}.md`
    ),
};

export const importApi = {
  importOutline: (projectId: string, file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return apiFetch<{ success: boolean; nodes: any[]; filename: string }>(
      `/api/v1/projects/${projectId}/import/outline`,
      {
        method: "POST",
        body: formData,
      }
    );
  },
  importDocument: (projectId: string, file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return apiFetch<{ success: boolean; html_content: string; filename: string }>(
      `/api/v1/projects/${projectId}/import/document`,
      {
        method: "POST",
        body: formData,
      }
    );
  },
};

