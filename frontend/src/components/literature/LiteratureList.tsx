"use client";

import { Loader2, SearchX } from "lucide-react";

import type { LiteraturePaper } from "./types";
import { PaperCard } from "./PaperCard";

type LiteratureListProps = {
  papers: LiteraturePaper[];
  loading?: boolean;
  error?: string | null;
  selectedPaperId?: string;
  onSelectPaper: (paper: LiteraturePaper) => void;
};

export function LiteratureList({
  papers,
  loading = false,
  error = null,
  selectedPaperId,
  onSelectPaper,
}: LiteratureListProps) {
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center gap-2 py-12 text-xs text-gray-500">
        <Loader2 className="h-5 w-5 animate-spin text-purple-600" />
        Đang tải tài liệu...
      </div>
    );
  }

  if (error) {
    return <div className="m-3 rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-700">{error}</div>;
  }

  if (papers.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-2 px-4 py-12 text-center text-xs text-gray-500">
        <SearchX className="h-6 w-6 text-gray-400" />
        Chưa có kết quả tài liệu.
      </div>
    );
  }

  return (
    <div className="space-y-3 p-3">
      {papers.map((paper) => (
        <PaperCard
          key={paper.id}
          paper={paper}
          selected={paper.id === selectedPaperId}
          onSelect={onSelectPaper}
        />
      ))}
    </div>
  );
}
