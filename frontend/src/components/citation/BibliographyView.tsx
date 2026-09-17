"use client";

import { Check, Clipboard } from "lucide-react";
import { useState } from "react";

type BibliographyViewProps = {
  citations: string[];
  style: "apa7" | "ieee" | "bgddt";
};

export function BibliographyView({ citations, style }: BibliographyViewProps) {
  const [copied, setCopied] = useState(false);

  const copyBibliography = async () => {
    await navigator.clipboard.writeText(citations.join("\n"));
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1600);
  };

  return (
    <section className="rounded-lg border border-gray-200 bg-white p-3">
      <div className="mb-2 flex items-center justify-between gap-2">
        <div>
          <h4 className="text-xs font-bold text-gray-900">Tài liệu tham khảo</h4>
          <p className="text-[11px] text-gray-500">Chuẩn {style.toUpperCase()}</p>
        </div>
        <button
          type="button"
          onClick={copyBibliography}
          disabled={citations.length === 0}
          className="inline-flex items-center gap-1 rounded border border-gray-300 px-2 py-1 text-[11px] font-medium text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40"
          title="Sao chép danh mục tài liệu"
        >
          {copied ? <Check className="h-3.5 w-3.5 text-emerald-600" /> : <Clipboard className="h-3.5 w-3.5" />}
          {copied ? "Đã sao chép" : "Sao chép"}
        </button>
      </div>
      {citations.length === 0 ? (
        <p className="rounded border border-dashed border-gray-300 p-3 text-center text-[11px] text-gray-500">
          Chưa có tài liệu tham khảo phù hợp.
        </p>
      ) : (
        <ol className="list-decimal space-y-2 pl-5 text-[11px] leading-5 text-gray-700">
          {citations.map((citation, index) => <li key={`${citation}-${index}`}>{citation}</li>)}
        </ol>
      )}
    </section>
  );
}
