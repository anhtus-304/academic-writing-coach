const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

import type { LiteraturePaper } from "@/components/literature/types";

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
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
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
  chapters: any;
  suggestions?: any;
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
  update: (projectId: string, chapters: any, suggestions?: any) =>
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
  total_results: number;
  papers: LiteraturePaper[];
}

export interface LiteratureSummaryResponse {
  paper_id: string;
  summary_vi: string;
}

export const literatureApi = {
  search: (query: string, filters?: { year?: string; publicationType?: string; source?: string; limit?: number }) => {
    const params = new URLSearchParams({ query });
    if (filters?.year) params.set("year", filters.year);
    if (filters?.publicationType) params.set("publication_type", filters.publicationType);
    if (filters?.source) params.set("source", filters.source);
    if (filters?.limit) params.set("limit", String(filters.limit));
    return apiFetch<LiteratureSearchResponse>(`/api/v1/literature/search?${params.toString()}`);
  },
  summarize: (paper: LiteraturePaper) =>
    apiFetch<LiteratureSummaryResponse>("/api/v1/literature/summarize", {
      method: "POST",
      body: JSON.stringify({ paper }),
    }),
};
