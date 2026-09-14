"use client";

import React, { useState, useRef, useEffect } from "react";
import { Download, FileText, FileDown, Printer, ChevronDown, Loader2 } from "lucide-react";
import { exportApi } from "@/lib/api";

interface ExportDropdownProps {
  projectId: string;
  topic?: string;
  editorContent: string;
}

export function ExportDropdown({ projectId, topic, editorContent }: ExportDropdownProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [exportingType, setExportingType] = useState<"docx" | "md" | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleExportDocx = async () => {
    if (!editorContent || editorContent.trim().length === 0) {
      alert("Văn bản chưa có nội dung để xuất file.");
      return;
    }
    setExportingType("docx");
    setIsOpen(false);
    try {
      await exportApi.exportDocx(projectId, editorContent, topic);
    } catch (err: unknown) {
      alert("Xuất file Word thất bại: " + (err instanceof Error ? err.message : "Đã có lỗi xảy ra"));
    } finally {
      setExportingType(null);
    }
  };

  const handleExportMarkdown = async () => {
    if (!editorContent || editorContent.trim().length === 0) {
      alert("Văn bản chưa có nội dung để xuất file.");
      return;
    }
    setExportingType("md");
    setIsOpen(false);
    try {
      await exportApi.exportMarkdown(projectId, editorContent, topic);
    } catch (err: unknown) {
      alert("Xuất file Markdown thất bại: " + (err instanceof Error ? err.message : "Đã có lỗi xảy ra"));
    } finally {
      setExportingType(null);
    }
  };

  const handlePrintPdf = () => {
    setIsOpen(false);
    // Kích hoạt engine in ấn của trình duyệt với CSS @media print chuyên dụng
    window.print();
  };

  return (
    <div className="relative inline-block text-left" ref={dropdownRef}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        disabled={exportingType !== null}
        className="inline-flex items-center gap-1.5 bg-white hover:bg-gray-50 text-gray-700 border border-gray-200 text-xs px-3 py-1.5 rounded-md font-medium transition shadow-2xs active:scale-95 disabled:opacity-60"
        title="Xuất văn bản ra Word, Markdown, hoặc in PDF"
      >
        {exportingType ? (
          <Loader2 className="w-3.5 h-3.5 animate-spin text-purple-600" />
        ) : (
          <Download className="w-3.5 h-3.5 text-purple-600" />
        )}
        <span>{exportingType ? "Đang xuất..." : "Xuất file"}</span>
        <ChevronDown className="w-3 h-3 text-gray-400" />
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-1.5 w-60 rounded-xl bg-white shadow-lg border border-gray-200 py-1.5 z-50 animate-in fade-in zoom-in-95 duration-100">
          <div className="px-3 py-1.5 border-b border-gray-100 text-[11px] font-semibold text-gray-500 uppercase tracking-wider">
            Chọn định dạng xuất file
          </div>

          <button
            type="button"
            onClick={handleExportDocx}
            className="w-full text-left px-3.5 py-2.5 text-xs text-gray-700 hover:bg-purple-50 hover:text-purple-700 flex items-start gap-2.5 transition"
          >
            <FileText className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
            <div>
              <div className="font-medium text-gray-900">Microsoft Word (.docx)</div>
              <div className="text-[10px] text-gray-500">Chuẩn học thuật A4, Times New Roman 13pt</div>
            </div>
          </button>

          <button
            type="button"
            onClick={handleExportMarkdown}
            className="w-full text-left px-3.5 py-2.5 text-xs text-gray-700 hover:bg-purple-50 hover:text-purple-700 flex items-start gap-2.5 transition"
          >
            <FileDown className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
            <div>
              <div className="font-medium text-gray-900">Markdown (.md)</div>
              <div className="text-[10px] text-gray-500">Chuẩn định dạng GitHub GFM thuần text</div>
            </div>
          </button>

          <button
            type="button"
            onClick={handlePrintPdf}
            className="w-full text-left px-3.5 py-2.5 text-xs text-gray-700 hover:bg-purple-50 hover:text-purple-700 flex items-start gap-2.5 transition border-t border-gray-100"
          >
            <Printer className="w-4 h-4 text-purple-600 shrink-0 mt-0.5" />
            <div>
              <div className="font-medium text-gray-900">In / Lưu PDF (.pdf)</div>
              <div className="text-[10px] text-gray-500">In trực tiếp trang chuẩn A4 không dính toolbar</div>
            </div>
          </button>
        </div>
      )}
    </div>
  );
}
