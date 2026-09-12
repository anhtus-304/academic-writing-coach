export type CitationStyle = "apa7" | "ieee" | "bgddt";

export interface CitationIssue {
  sentence: string;
  reason: string;
  suggested_action: string;
}

export interface CitationSuggestion {
  original_text: string;
  suggested_text: string | null;
  reason: string;
  source?: Record<string, unknown> | null;
}

export interface CitationCheckResult {
  total_issues: number;
  missing_claims: CitationIssue[];
  invalid_citations: string[];
  verified_count: number;
  credits_charged: number;
  suggestions: CitationSuggestion[];
  bibliography: string[];
}
