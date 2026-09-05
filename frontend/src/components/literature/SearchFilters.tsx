"use client";

import { Search, SlidersHorizontal } from "lucide-react";

import { Button } from "@/components/ui/button";
import type { LiteratureFilters } from "./types";

type SearchFiltersProps = {
  query: string;
  filters: LiteratureFilters;
  onQueryChange: (value: string) => void;
  onFiltersChange: (filters: LiteratureFilters) => void;
  onSearch: () => void;
  loading?: boolean;
  hasSearched?: boolean;
  hasResults?: boolean;
};

export function SearchFilters({
  query,
  filters,
  onQueryChange,
  onFiltersChange,
  onSearch,
  loading = false,
  hasSearched = false,
  hasResults = true,
}: SearchFiltersProps) {
  const updateFilter = (key: keyof LiteratureFilters, value: string) => {
    onFiltersChange({ ...filters, [key]: value });
  };

  return (
    <div className="space-y-3 border-b border-gray-200 bg-white p-3">
      <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
        <SlidersHorizontal className="h-3.5 w-3.5" />
        Tìm tài liệu
      </div>
      <div className="flex gap-2">
        <input
          value={query}
          onChange={(event) => onQueryChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") onSearch();
          }}
          placeholder="Từ khóa, chủ đề..."
          aria-label="Từ khóa tìm kiếm tài liệu"
          className="min-w-0 flex-1 rounded-lg border border-gray-300 px-3 py-2 text-xs text-gray-800 outline-none transition focus:border-purple-500 focus:ring-2 focus:ring-purple-100"
        />
        <Button type="button" size="sm" onClick={onSearch} disabled={loading} aria-label="Search" title="Search">
          <Search className="h-3.5 w-3.5" />
          {loading ? "Đang tìm" : "Search"}
        </Button>
      </div>
      <div className="grid grid-cols-1 gap-2">
        <select
          value={filters.year}
          onChange={(event) => updateFilter("year", event.target.value)}
          aria-label="Năm xuất bản"
          className="rounded-lg border border-gray-300 bg-white px-2 py-2 text-xs text-gray-600 outline-none focus:border-purple-500"
        >
          <option value="">Mọi năm</option>
          <option value="2020s">2020 - nay</option>
          <option value="2010s">2010 - 2019</option>
        </select>
        <select
          value={filters.publicationType}
          onChange={(event) => updateFilter("publicationType", event.target.value)}
          aria-label="Loại tài liệu"
          className="rounded-lg border border-gray-300 bg-white px-2 py-2 text-xs text-gray-600 outline-none focus:border-purple-500"
        >
          <option value="">Mọi loại tài liệu</option>
          <option value="Journal article">Journal article</option>
          <option value="Review article">Review article</option>
          <option value="Conference paper">Conference paper</option>
          <option value="Report">Report</option>
        </select>
        <select
          value={filters.source}
          onChange={(event) => updateFilter("source", event.target.value)}
          aria-label="Nguồn tài liệu"
          className="rounded-lg border border-gray-300 bg-white px-2 py-2 text-xs text-gray-600 outline-none focus:border-purple-500"
        >
          <option value="">Mọi nguồn</option>
          <option value="semantic_scholar">Semantic Scholar</option>
          <option value="openalex">OpenAlex</option>
          <option value="arxiv">arXiv</option>
        </select>
      </div>
      {hasSearched && !loading && !hasResults ? (
        <p className="text-xs text-gray-500">Không tìm thấy tài liệu phù hợp.</p>
      ) : null}
    </div>
  );
}
