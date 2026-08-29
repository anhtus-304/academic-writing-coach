"use client";

import { Check, ExternalLink, FileText } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { LiteraturePaper } from "./types";

type PaperCardProps = {
  paper: LiteraturePaper;
  selected?: boolean;
  onSelect: (paper: LiteraturePaper) => void;
};

export function PaperCard({ paper, selected = false, onSelect }: PaperCardProps) {
  return (
    <article className={cn("rounded-lg border bg-white p-3 shadow-sm transition", selected ? "border-purple-500 ring-2 ring-purple-100" : "border-gray-200")}>
      <div className="flex items-start gap-2">
        <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-purple-50 text-purple-600">
          <FileText className="h-3.5 w-3.5" />
        </div>
        <div className="min-w-0 flex-1">
          <h3 className="text-sm font-semibold leading-5 text-gray-900">{paper.title}</h3>
          <p className="mt-1 text-[11px] leading-4 text-gray-500">{paper.authors.join(", ")}</p>
        </div>
      </div>

      <div className="mt-3 flex flex-wrap gap-1.5 text-[10px] text-gray-500">
        {paper.year ? <span className="rounded bg-gray-100 px-1.5 py-0.5">{paper.year}</span> : null}
        {paper.source ? <span className="rounded bg-gray-100 px-1.5 py-0.5">{paper.source}</span> : null}
        {paper.publicationType ? <span className="rounded bg-gray-100 px-1.5 py-0.5">{paper.publicationType}</span> : null}
      </div>

      {paper.abstract ? <p className="mt-3 line-clamp-3 text-xs leading-5 text-gray-600">{paper.abstract}</p> : null}

      <div className="mt-3 flex items-center justify-between gap-2">
        {paper.doi || paper.url ? (
          <a
            href={paper.url || `https://doi.org/${paper.doi}`}
            target="_blank"
            rel="noreferrer"
            className="inline-flex min-w-0 items-center gap-1 truncate text-[11px] text-purple-600 hover:underline"
          >
            <ExternalLink className="h-3 w-3 shrink-0" />
            {paper.doi || "Open source"}
          </a>
        ) : <span />}
        <Button type="button" size="sm" variant={selected ? "secondary" : "outline"} onClick={() => onSelect(paper)}>
          {selected ? <Check className="h-3.5 w-3.5" /> : null}
          {selected ? "Đã chọn" : "Chọn tài liệu"}
        </Button>
      </div>
    </article>
  );
}
