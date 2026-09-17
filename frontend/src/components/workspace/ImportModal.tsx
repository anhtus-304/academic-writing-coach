"use client";

import React, { useState, useRef } from "react";
import { UploadCloud, FileText, X, Loader2, CheckCircle2, AlertCircle } from "lucide-react";
import { importApi } from "@/lib/api";
import type { OutlineNode } from "@/components/outline/OutlineEditor";

interface ImportModalProps {
  isOpen: boolean;
  onClose: () => void;
  projectId: string;
  onImportOutline: (nodes: OutlineNode[], mode: "replace" | "append") => void;
  onImportDocument: (html: string, mode: "replace" | "insert") => void;
}

export function ImportModal({
  isOpen,
  onClose,
  projectId,
  onImportOutline,
  onImportDocument,
}: ImportModalProps) {
  const [target, setTarget] = useState<"outline" | "document">("document");
  const [mode, setMode] = useState<"replace" | "append_or_insert">("replace");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      const ext = file.name.toLowerCase().split(".").pop();
      if (!["docx", "doc", "md", "markdown", "txt"].includes(ext || "")) {
        setError("Vui lòng chỉ chọn tệp tin Word (.docx) hoặc Markdown (.md, .txt)");
        return;
      }
      setSelectedFile(file);
      setError(null);
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      const ext = file.name.toLowerCase().split(".").pop();
      if (!["docx", "doc", "md", "markdown", "txt"].includes(ext || "")) {
        setError("Vui lòng chỉ chọn tệp tin Word (.docx) hoặc Markdown (.md, .txt)");
        return;
      }
      setSelectedFile(file);
      setError(null);
    }
  };

  const handleImport = async () => {
    if (!selectedFile) {
      setError("Vui lòng chọn một tệp tin để nhập.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      if (target === "outline") {
        const res = await importApi.importOutline(projectId, selectedFile);
        if (res.success && res.nodes) {
          onImportOutline(res.nodes as unknown as OutlineNode[], mode === "replace" ? "replace" : "append");
          onClose();
        } else {
          throw new Error("Không thể bóc tách dàn ý từ tệp tin.");
        }
      } else {
        const res = await importApi.importDocument(projectId, selectedFile);
        if (res.success && res.html_content) {
          onImportDocument(res.html_content, mode === "replace" ? "replace" : "insert");
          onClose();
        } else {
          throw new Error("Không thể đọc nội dung văn bản từ tệp tin.");
        }
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Đã có lỗi xảy ra khi nhập tệp tin.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4">
      <div className="bg-white rounded-2xl shadow-xl max-w-lg w-full overflow-hidden border border-gray-200 animate-in fade-in zoom-in-95 duration-150">
        <div className="p-4 border-b border-gray-100 flex items-center justify-between bg-purple-50/50">
          <div className="flex items-center gap-2">
            <UploadCloud className="w-5 h-5 text-purple-600" />
            <h3 className="font-bold text-gray-900 text-sm">Nhập Tệp Tin Học Thuật (Import)</h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-gray-400 hover:text-gray-700 text-sm font-semibold p-1"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-5 space-y-4">
          {/* Mục tiêu nhập */}
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1.5">
              1. Bạn muốn nhập nội dung này vào đâu?
            </label>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setTarget("document")}
                className={`py-2 px-3 rounded-lg border text-xs font-medium transition text-left flex items-start gap-2 ${
                  target === "document"
                    ? "border-purple-600 bg-purple-50 text-purple-900"
                    : "border-gray-200 hover:bg-gray-50 text-gray-700"
                }`}
              >
                <FileText className="w-4 h-4 mt-0.5 shrink-0 text-purple-600" />
                <div>
                  <div className="font-semibold">Văn bản soạn thảo</div>
                  <div className="text-[10px] text-gray-500">Nhập vào Tiptap Editor</div>
                </div>
              </button>

              <button
                type="button"
                onClick={() => setTarget("outline")}
                className={`py-2 px-3 rounded-lg border text-xs font-medium transition text-left flex items-start gap-2 ${
                  target === "outline"
                    ? "border-purple-600 bg-purple-50 text-purple-900"
                    : "border-gray-200 hover:bg-gray-50 text-gray-700"
                }`}
              >
                <span className="text-base leading-none">📑</span>
                <div>
                  <div className="font-semibold">Cấu trúc Dàn ý</div>
                  <div className="text-[10px] text-gray-500">Nhập vào Outline Editor</div>
                </div>
              </button>
            </div>
          </div>

          {/* Chế độ nhập */}
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1.5">
              2. Phương thức nhập:
            </label>
            <div className="flex gap-4 text-xs">
              <label className="flex items-center gap-1.5 cursor-pointer">
                <input
                  type="radio"
                  name="importMode"
                  checked={mode === "replace"}
                  onChange={() => setMode("replace")}
                  className="text-purple-600 focus:ring-purple-500"
                />
                <span>{target === "document" ? "Thay thế toàn bộ bài viết" : "Ghi đè dàn ý hiện tại"}</span>
              </label>
              <label className="flex items-center gap-1.5 cursor-pointer">
                <input
                  type="radio"
                  name="importMode"
                  checked={mode === "append_or_insert"}
                  onChange={() => setMode("append_or_insert")}
                  className="text-purple-600 focus:ring-purple-500"
                />
                <span>{target === "document" ? "Chèn vào con trỏ chuột" : "Nối tiếp vào sau"}</span>
              </label>
            </div>
          </div>

          {/* Vùng kéo thả tệp tin */}
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1.5">
              3. Chọn tệp tin (.docx hoặc .md):
            </label>
            <div
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className="border-2 border-dashed border-gray-300 hover:border-purple-400 rounded-xl p-6 text-center cursor-pointer bg-gray-50/50 hover:bg-purple-50/30 transition group"
            >
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileChange}
                accept=".docx,.doc,.md,.markdown,.txt"
                className="hidden"
              />
              <UploadCloud className="w-8 h-8 text-gray-400 group-hover:text-purple-600 mx-auto mb-2 transition" />
              {selectedFile ? (
                <div className="flex items-center justify-center gap-1.5 text-xs font-semibold text-purple-800">
                  <CheckCircle2 className="w-4 h-4 text-purple-600" />
                  <span>{selectedFile.name}</span>
                  <span className="text-gray-400 text-[10px]">
                    ({(selectedFile.size / 1024).toFixed(1)} KB)
                  </span>
                </div>
              ) : (
                <>
                  <p className="text-xs font-medium text-gray-700">
                    Kéo thả tệp tin vào đây hoặc <span className="text-purple-600 underline">chọn tệp</span>
                  </p>
                  <p className="text-[10px] text-gray-400 mt-1">
                    Hỗ trợ file Microsoft Word (.docx) và Markdown (.md)
                  </p>
                </>
              )}
            </div>
          </div>

          {error && (
            <div className="flex items-start gap-2 bg-red-50 border border-red-200 text-red-700 text-xs p-2.5 rounded-lg">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-red-500" />
              <span>{error}</span>
            </div>
          )}
        </div>

        <div className="p-4 border-t border-gray-100 flex items-center justify-end gap-2 bg-gray-50/60">
          <button
            type="button"
            onClick={onClose}
            disabled={loading}
            className="px-3.5 py-1.5 text-xs text-gray-600 hover:bg-gray-200/70 rounded-lg transition font-medium"
          >
            Hủy
          </button>
          <button
            type="button"
            onClick={handleImport}
            disabled={loading || !selectedFile}
            className="px-4 py-1.5 text-xs font-medium text-white bg-purple-600 hover:bg-purple-700 rounded-lg transition shadow-sm disabled:opacity-50 flex items-center gap-1.5"
          >
            {loading ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Đang xử lý...</span>
              </>
            ) : (
              <span>Xác nhận nhập tệp</span>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
