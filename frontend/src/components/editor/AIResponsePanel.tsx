"use client";

import React, { useState } from "react";
import Link from "next/link";
import { Loader2, Sparkles, Wand2, X, Send, BookOpen, FileText, GraduationCap, Lightbulb, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { agentApi } from "@/lib/api";
import type { OutlineNode } from "@/components/outline/OutlineEditor";

type AIResponsePanelProps = {
  isLoading?: boolean;
  error?: string | null;
  title?: string;
  description?: string;
  prompt?: string;
  onPromptChange?: (value: string) => void;
  onGenerate?: () => void;
  onApply?: () => void;
  result?: OutlineNode[] | null;
  defaultActionLabel?: string;
  selectedText?: string;
  projectId?: string;
  onClose?: () => void;
  onCreditDeducted?: () => void;
};

export function AIResponsePanel({
  isLoading = false,
  error: initialError = null,
  title = "AI Assistant",
  description = "Phân tích và hướng dẫn viết học thuật",
  prompt = "",
  onPromptChange,
  onGenerate,
  onApply,
  result,
  defaultActionLabel = "Generate",
  selectedText,
  projectId,
  onClose,
  onCreditDeducted,
}: AIResponsePanelProps) {
  const [customQuestion, setCustomQuestion] = useState("");
  const [activeAction, setActiveAction] = useState<string | null>(null);
  const [isAsking, setIsAsking] = useState(false);
  const [aiResponse, setAiResponse] = useState<string | null>(null);
  const [askError, setAskError] = useState<string | null>(initialError);

  const handleAsk = async (action: string, promptText?: string) => {
    if (!selectedText || !selectedText.trim()) return;

    setActiveAction(action);
    setIsAsking(true);
    setAskError(null);

    try {
      const res = await agentApi.askAI({
        selected_text: selectedText.trim(),
        action,
        custom_prompt: promptText,
        project_id: projectId,
      });

      setAiResponse(res.response);
      if (onCreditDeducted) {
        onCreditDeducted();
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Không thể kết nối với AI Assistant. Vui lòng thử lại.";
      setAskError(message);
    } finally {
      setIsAsking(false);
    }
  };

  if (selectedText !== undefined && selectedText.length > 0) {
    const isOutOfCredits = askError?.toLowerCase().includes("credit") || askError?.includes("402");

    return (
      <aside className="flex h-full flex-col border-l border-border bg-card p-4 shadow-sm overflow-y-auto">
        {/* Header */}
        <div className="mb-4 flex items-start justify-between gap-3 shrink-0">
          <div>
            <h3 className="text-sm font-bold text-foreground flex items-center gap-1.5">
              <Sparkles className="h-4 w-4 text-purple-600" />
              AI Academic Coach
            </h3>
            <p className="mt-0.5 text-xs text-muted-foreground">
              Phân tích & định hướng tư duy học thuật
            </p>
          </div>
          {onClose ? (
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="h-7 w-7 text-muted-foreground hover:text-foreground"
              onClick={onClose}
              aria-label="Đóng"
            >
              <X className="h-4 w-4" />
            </Button>
          ) : null}
        </div>

        {/* Selected Quote Card */}
        <div className="rounded-xl border border-border bg-muted/30 p-3 shrink-0">
          <div className="flex justify-between items-center mb-1.5">
            <span className="text-[10px] font-bold uppercase tracking-wider text-purple-700">
              Đoạn văn bản được chọn
            </span>
            <span className="text-[10px] text-muted-foreground">
              {selectedText.length} ký tự
            </span>
          </div>
          <blockquote className="border-l-2 border-purple-600 pl-2.5 text-xs leading-5 text-foreground max-h-32 overflow-y-auto italic">
            &quot;{selectedText}&quot;
          </blockquote>
        </div>

        {/* Quick Actions (4 Buttons) */}
        <div className="mt-4 shrink-0">
          <div className="text-xs font-semibold text-foreground mb-2 flex justify-between items-center">
            <span>Tác vụ nhanh</span>
            <span className="text-[10px] font-medium text-purple-600 bg-purple-50 px-1.5 py-0.5 rounded">
              🪙 1 Credit / lần
            </span>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              onClick={() => handleAsk("explain")}
              disabled={isAsking}
              className={`flex items-center gap-1.5 rounded-lg border p-2 text-left text-xs font-medium transition ${
                activeAction === "explain" && !isAsking
                  ? "border-purple-600 bg-purple-50 text-purple-700"
                  : "border-border bg-background hover:border-purple-300 hover:bg-purple-50/50 text-foreground"
              } disabled:opacity-50`}
            >
              <BookOpen className="h-3.5 w-3.5 text-purple-600 shrink-0" />
              <span className="truncate">Giải thích thuật ngữ</span>
            </button>

            <button
              type="button"
              onClick={() => handleAsk("summarize")}
              disabled={isAsking}
              className={`flex items-center gap-1.5 rounded-lg border p-2 text-left text-xs font-medium transition ${
                activeAction === "summarize" && !isAsking
                  ? "border-purple-600 bg-purple-50 text-purple-700"
                  : "border-border bg-background hover:border-purple-300 hover:bg-purple-50/50 text-foreground"
              } disabled:opacity-50`}
            >
              <FileText className="h-3.5 w-3.5 text-blue-600 shrink-0" />
              <span className="truncate">Tóm tắt ý chính</span>
            </button>

            <button
              type="button"
              onClick={() => handleAsk("academic_rewrite")}
              disabled={isAsking}
              className={`flex items-center gap-1.5 rounded-lg border p-2 text-left text-xs font-medium transition ${
                activeAction === "academic_rewrite" && !isAsking
                  ? "border-purple-600 bg-purple-50 text-purple-700"
                  : "border-border bg-background hover:border-purple-300 hover:bg-purple-50/50 text-foreground"
              } disabled:opacity-50`}
            >
              <GraduationCap className="h-3.5 w-3.5 text-emerald-600 shrink-0" />
              <span className="truncate">Viết lại học thuật</span>
            </button>

            <button
              type="button"
              onClick={() => handleAsk("critique")}
              disabled={isAsking}
              className={`flex items-center gap-1.5 rounded-lg border p-2 text-left text-xs font-medium transition ${
                activeAction === "critique" && !isAsking
                  ? "border-purple-600 bg-purple-50 text-purple-700"
                  : "border-border bg-background hover:border-purple-300 hover:bg-purple-50/50 text-foreground"
              } disabled:opacity-50`}
            >
              <Lightbulb className="h-3.5 w-3.5 text-amber-600 shrink-0" />
              <span className="truncate">Phản biện luận cứ</span>
            </button>
          </div>
        </div>

        {/* Custom Question Input */}
        <div className="mt-4 shrink-0">
          <label className="text-xs font-semibold text-foreground mb-1.5 block">
            Hoặc đặt câu hỏi tùy chỉnh:
          </label>
          <div className="flex gap-2">
            <input
              type="text"
              value={customQuestion}
              onChange={(e) => setCustomQuestion(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && customQuestion.trim() && !isAsking) {
                  handleAsk("custom", customQuestion);
                }
              }}
              placeholder="Ví dụ: Đoạn này thiếu số liệu gì?..."
              className="flex-1 rounded-lg border border-border bg-background px-3 py-1.5 text-xs text-foreground outline-none transition focus:border-purple-600 focus:ring-1 focus:ring-purple-600"
            />
            <button
              type="button"
              onClick={() => handleAsk("custom", customQuestion)}
              disabled={!customQuestion.trim() || isAsking}
              className="flex items-center justify-center rounded-lg bg-purple-600 px-3 py-1.5 text-white hover:bg-purple-700 transition disabled:opacity-40"
              title="Gửi câu hỏi"
            >
              <Send className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>

        {/* Out of Credits / Error Alert */}
        {askError ? (
          <div className="mt-4 rounded-lg border border-red-200 bg-red-50/80 p-3 text-xs text-red-700 shrink-0">
            <div className="flex items-start gap-2">
              <AlertCircle className="h-4 w-4 text-red-600 shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="font-semibold">{askError}</p>
                {isOutOfCredits ? (
                  <div className="mt-2">
                    <Link
                      href="/pricing"
                      className="inline-flex items-center gap-1 rounded bg-purple-600 px-3 py-1 text-[11px] font-semibold text-white hover:bg-purple-700 transition"
                    >
                      <span>🪙 Nạp thêm Credit ngay</span>
                    </Link>
                  </div>
                ) : null}
              </div>
            </div>
          </div>
        ) : null}

        {/* AI Loading State */}
        {isAsking ? (
          <div className="mt-4 rounded-xl border border-purple-100 bg-purple-50/40 p-4 text-center">
            <Loader2 className="mx-auto h-5 w-5 animate-spin text-purple-600 mb-2" />
            <p className="text-xs font-semibold text-purple-900">AI Coach đang suy nghĩ & phân tích...</p>
            <p className="text-[11px] text-muted-foreground mt-0.5">
              Áp dụng chuẩn mực phương pháp luận học thuật
            </p>
          </div>
        ) : null}

        {/* AI Response Output */}
        {!isAsking && aiResponse ? (
          <div className="mt-4 flex-1 rounded-xl border border-border bg-muted/20 p-3.5 text-xs text-foreground">
            <div className="flex items-center justify-between mb-2 pb-2 border-b border-border/60">
              <span className="font-bold text-purple-700 flex items-center gap-1">
                <Sparkles className="h-3.5 w-3.5" /> Phản hồi từ AI Coach
              </span>
              <span className="text-[10px] text-muted-foreground">Đã trừ 1 Credit</span>
            </div>
            <div className="prose prose-xs max-w-none text-foreground leading-relaxed whitespace-pre-wrap">
              {aiResponse}
            </div>
          </div>
        ) : null}

        {!isAsking && !aiResponse && !askError ? (
          <div className="mt-4 rounded-lg border border-dashed border-border p-4 text-center text-xs text-muted-foreground">
            Chọn một tác vụ nhanh ở trên hoặc gõ câu hỏi để AI Coach phân tích đoạn văn này.
          </div>
        ) : null}
      </aside>
    );
  }

  // Fallback view for Topic Outline Generation mode
  return (
    <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <h3 className="text-base font-semibold text-foreground">{title}</h3>
          <p className="mt-1 text-sm text-muted-foreground">{description}</p>
        </div>
        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-primary/10 text-primary">
          <Sparkles className="h-4 w-4" />
        </div>
      </div>

      <label className="mb-3 block text-sm font-medium text-foreground">
        Yêu cầu của bạn
      </label>
      <textarea
        value={prompt}
        onChange={(event) => onPromptChange && onPromptChange(event.target.value)}
        rows={5}
        className="w-full resize-none rounded-xl border border-border bg-background px-3 py-2 text-sm text-foreground outline-none ring-0 transition focus:border-ring"
        placeholder="Ví dụ: Tạo dàn ý cho bài nghiên cứu về ứng dụng AI trong giáo dục..."
      />

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <Button type="button" onClick={onGenerate} disabled={isLoading}>
          {isLoading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Generating outline...
            </>
          ) : (
            <>
              <Wand2 className="mr-2 h-4 w-4" />
              {defaultActionLabel}
            </>
          )}
        </Button>

        {onApply && result && result.length > 0 ? (
          <Button type="button" variant="outline" onClick={onApply}>
            Apply outline
          </Button>
        ) : null}
      </div>

      {initialError ? (
        <div className="mt-4 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
          {initialError}
        </div>
      ) : null}
    </div>
  );
}
