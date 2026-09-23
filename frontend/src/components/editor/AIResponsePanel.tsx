"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import {
  Loader2,
  Sparkles,
  Wand2,
  X,
  Send,
  BookOpen,
  FileText,
  GraduationCap,
  Lightbulb,
  AlertCircle,
  Zap,
  CheckCircle2,
  XCircle,
  ShieldCheck,
  Layers,
  Copy,
  Check,
  RotateCcw,
  BookMarked,
  Quote,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  agentApi,
  creditApi,
  type SuggestionItem,
  type PipelineEstimateResponse,
  type PipelineRunResponseData,
} from "@/lib/api";
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
  onApplySuggestion?: (suggestion: SuggestionItem) => void;
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
  onApplySuggestion,
}: AIResponsePanelProps) {
  // Mode selection: "ask" | "auto"
  const [panelMode, setPanelMode] = useState<"ask" | "auto">("ask");

  // Ask Mode State
  const [customQuestion, setCustomQuestion] = useState("");
  const [activeAction, setActiveAction] = useState<string | null>(null);
  const [isAsking, setIsAsking] = useState(false);
  const [aiResponse, setAiResponse] = useState<string | null>(null);
  const [askError, setAskError] = useState<string | null>(initialError);

  // Auto Mode State
  const [isEstimating, setIsEstimating] = useState(false);
  const [estimate, setEstimate] = useState<PipelineEstimateResponse | null>(null);
  const [disclaimerAccepted, setDisclaimerAccepted] = useState(false);
  const [isRunningPipeline, setIsRunningPipeline] = useState(false);
  const [pipelineCurrentStep, setPipelineCurrentStep] = useState<string>("");
  const [pipelineResult, setPipelineResult] = useState<PipelineRunResponseData | null>(null);
  const [pipelineError, setPipelineError] = useState<string | null>(null);
  const [suggestions, setSuggestions] = useState<SuggestionItem[]>([]);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // Fetch estimate when entering Auto mode
  const loadEstimate = async () => {
    if (!projectId) return;
    setIsEstimating(true);
    try {
      const res = await agentApi.estimatePipeline({ project_id: projectId });
      setEstimate(res);
    } catch (err: unknown) {
      console.error("Estimate pipeline error:", err);
    } finally {
      setIsEstimating(false);
    }
  };

  useEffect(() => {
    if (panelMode === "auto" && !estimate && projectId) {
      loadEstimate();
    }
  }, [panelMode, projectId]);

  // Handle Ask Mode submission
  const handleAsk = async (action: string, promptText?: string) => {
    const textToAnalyze = selectedText?.trim() || promptText?.trim() || "";
    if (!textToAnalyze) return;

    setActiveAction(action);
    setIsAsking(true);
    setAskError(null);

    try {
      const res = await agentApi.askAI({
        selected_text: textToAnalyze,
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

  // Handle Auto Mode pipeline execution
  const handleRunPipeline = async () => {
    if (!disclaimerAccepted) {
      setPipelineError("Vui lòng xác nhận đồng ý với Tuyên bố Liêm chính Học thuật.");
      return;
    }
    setIsRunningPipeline(true);
    setPipelineError(null);
    setPipelineCurrentStep("Đang chuẩn bị khởi chạy quy trình...");

    try {
      setPipelineCurrentStep("Phân tích dàn ý, tìm kiếm tài liệu & thẩm định trích dẫn...");
      const res = await agentApi.runPipeline({
        project_id: projectId,
        disclaimer_accepted: true,
        draft_content: selectedText && selectedText.length > 30 ? selectedText : undefined,
      });

      setPipelineResult(res);
      setSuggestions(res.suggestions || []);
      if (onCreditDeducted) {
        onCreditDeducted();
      }
      if (res.status === "failed") {
        setPipelineError(res.error || "Quy trình gặp lỗi ở một số bước.");
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Khởi chạy quy trình Auto thất bại.";
      setPipelineError(message);
    } finally {
      setIsRunningPipeline(false);
      setPipelineCurrentStep("");
    }
  };

  const handleAcceptSuggestion = (sug: SuggestionItem) => {
    setSuggestions((prev) =>
      prev.map((item) => (item.id === sug.id ? { ...item, status: "accepted" as const } : item))
    );
    if (onApplySuggestion) {
      onApplySuggestion(sug);
    }
  };

  const handleRejectSuggestion = (sugId: string) => {
    setSuggestions((prev) =>
      prev.map((item) => (item.id === sugId ? { ...item, status: "rejected" as const } : item))
    );
  };

  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const isOutOfCredits = askError?.toLowerCase().includes("credit") || askError?.includes("402") || pipelineError?.includes("402");

  return (
    <aside className="flex h-full flex-col border-l border-border bg-card p-4 shadow-sm overflow-y-auto">
      {/* Top Header & Close Button */}
      <div className="mb-3 flex items-start justify-between gap-3 shrink-0">
        <div>
          <h3 className="text-sm font-bold text-foreground flex items-center gap-1.5">
            <Sparkles className="h-4 w-4 text-purple-600" />
            AI Academic Coach
          </h3>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Cố vấn phương pháp & kiểm định học thuật
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

      {/* Dual-Mode Segmented Tabs (Ask vs Auto) */}
      <div className="mb-4 flex items-center rounded-lg bg-muted/70 p-1 text-xs shrink-0 border border-border/50">
        <button
          type="button"
          onClick={() => setPanelMode("ask")}
          className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-md font-medium transition ${
            panelMode === "ask"
              ? "bg-background text-purple-700 font-semibold shadow-xs"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          <BookOpen className="h-3.5 w-3.5" />
          <span>Hỏi đáp (Ask)</span>
        </button>
        <button
          type="button"
          onClick={() => setPanelMode("auto")}
          className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-md font-medium transition ${
            panelMode === "auto"
              ? "bg-background text-purple-700 font-semibold shadow-xs"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          <Zap className="h-3.5 w-3.5 text-amber-500 fill-amber-500" />
          <span>Tự động (Auto)</span>
        </button>
      </div>

      {/* ========================================================================= */}
      {/* MODE 1: ASK MODE (Interactive Socratic Questioning & Quick Tasks)         */}
      {/* ========================================================================= */}
      {panelMode === "ask" && (
        <div className="flex flex-col flex-1">
          {/* Selected Quote Card if text is selected */}
          {selectedText && selectedText.length > 0 ? (
            <div className="rounded-xl border border-border bg-muted/30 p-3 shrink-0">
              <div className="flex justify-between items-center mb-1.5">
                <span className="text-[10px] font-bold uppercase tracking-wider text-purple-700">
                  Đoạn văn bản được chọn
                </span>
                <span className="text-[10px] text-muted-foreground">
                  {selectedText.length} ký tự
                </span>
              </div>
              <blockquote className="border-l-2 border-purple-600 pl-2.5 text-xs leading-5 text-foreground max-h-28 overflow-y-auto italic">
                &quot;{selectedText}&quot;
              </blockquote>
            </div>
          ) : (
            <div className="rounded-xl border border-dashed border-border bg-muted/10 p-3.5 text-center text-xs text-muted-foreground mb-2">
              <Lightbulb className="h-4 w-4 mx-auto mb-1 text-amber-500" />
              Mẹo: Bôi đen một đoạn văn trong Editor để nhận phân tích chuyên sâu, hoặc đặt câu hỏi trực tiếp bên dưới.
            </div>
          )}

          {/* Quick Actions (4 Buttons) */}
          <div className="mt-3 shrink-0">
            <div className="text-xs font-semibold text-foreground mb-2 flex justify-between items-center">
              <span>Tác vụ cố vấn nhanh</span>
              <span className="text-[10px] font-medium text-purple-600 bg-purple-50 px-1.5 py-0.5 rounded">
                🪙 1 Credit / lần
              </span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => handleAsk("explain")}
                disabled={isAsking || (!selectedText && !customQuestion)}
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
                disabled={isAsking || (!selectedText && !customQuestion)}
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
                disabled={isAsking || (!selectedText && !customQuestion)}
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
                disabled={isAsking || (!selectedText && !customQuestion)}
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
              Hoặc đặt câu hỏi tùy chỉnh cho AI:
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
                placeholder="Ví dụ: Cần bổ sung luận điểm gì ở đoạn này?..."
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
              <p className="text-xs font-semibold text-purple-900">AI Coach đang phân tích luận cứ...</p>
              <p className="text-[11px] text-muted-foreground mt-0.5">
                Áp dụng chuẩn mực phương pháp luận khoa học
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
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODE 2: AUTO MODE (Human-in-the-Loop Multi-Agent Pipeline)               */}
      {/* ========================================================================= */}
      {panelMode === "auto" && (
        <div className="flex flex-col flex-1 space-y-4">
          {/* Overview Banner */}
          <div className="rounded-xl border border-purple-200 bg-purple-50/50 p-3 text-xs text-purple-900">
            <div className="flex items-start gap-2">
              <Zap className="h-4 w-4 text-purple-600 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold text-purple-950">Quy trình Tự động Đa tác nhân</p>
                <p className="text-[11px] text-purple-700 mt-0.5 leading-relaxed">
                  Tự động điều phối 3 tác tử: Dàn ý → Tổng quan tài liệu → Đối soát trích dẫn. Các điều chỉnh sẽ hiển thị dưới dạng Thẻ đề xuất để bạn tự phê duyệt.
                </p>
              </div>
            </div>
          </div>

          {/* Credit Estimation & Metering Card */}
          <div className="rounded-xl border border-border bg-card p-3 shadow-2xs">
            <div className="flex items-center justify-between mb-2 pb-1.5 border-b border-border/60">
              <span className="text-xs font-bold text-foreground flex items-center gap-1">
                <Layers className="h-3.5 w-3.5 text-purple-600" /> Dự toán Chi phí (Pre-authorization)
              </span>
              {isEstimating ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin text-purple-600" />
              ) : (
                <span className="text-[11px] font-semibold text-purple-700">
                  Tổng: {estimate?.estimated_cost ?? 6} Credits
                </span>
              )}
            </div>

            <div className="space-y-1.5 text-xs">
              <div className="flex items-center justify-between text-muted-foreground py-0.5">
                <span>1. Dàn ý nghiên cứu:</span>
                <span className="font-medium text-foreground">
                  {estimate?.stages?.find((s) => s.name === "outline")?.skip_available
                    ? "Bảo lưu dàn ý (0 Credit)"
                    : "2 Credits"}
                </span>
              </div>
              <div className="flex items-center justify-between text-muted-foreground py-0.5">
                <span>2. Tổng quan tài liệu (Semantic/ArXiv):</span>
                <span className="font-medium text-foreground">2 Credits</span>
              </div>
              <div className="flex items-center justify-between text-muted-foreground py-0.5">
                <span>3. Kiểm định trích dẫn & Missing Claims:</span>
                <span className="font-medium text-foreground">2 Credits</span>
              </div>
            </div>

            <div className="mt-2.5 pt-2 border-t border-border/60 flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Số dư hiện tại:</span>
              <span className={`font-bold ${estimate && !estimate.sufficient_balance ? "text-red-600" : "text-emerald-600"}`}>
                🪙 {estimate?.user_balance ?? 0} Credits
              </span>
            </div>
          </div>

          {/* Academic Integrity Disclaimer Card */}
          <div className="rounded-xl border border-amber-200 bg-amber-50/70 p-3 text-xs text-amber-900">
            <div className="flex items-start gap-2">
              <ShieldCheck className="h-4 w-4 text-amber-600 shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="font-bold text-amber-950">Cam kết Liêm chính Học thuật</p>
                <p className="text-[11px] text-amber-800 mt-1 leading-relaxed">
                  Hệ thống tuân thủ nguyên tắc <strong>Human-in-the-loop</strong>. AI đóng vai trò cố vấn, không viết thay và không tự ý thay đổi văn bản nếu bạn chưa bấm [Chấp nhận].
                </p>
                <label className="mt-2.5 flex items-center gap-2 cursor-pointer select-none font-medium text-amber-950">
                  <input
                    type="checkbox"
                    checked={disclaimerAccepted}
                    onChange={(e) => setDisclaimerAccepted(e.target.checked)}
                    className="h-3.5 w-3.5 rounded border-amber-300 text-purple-600 focus:ring-purple-500"
                  />
                  <span>Tôi đã đọc và cam kết tự chịu trách nhiệm về nội dung học thuật.</span>
                </label>
              </div>
            </div>
          </div>

          {/* Error Banner */}
          {pipelineError ? (
            <div className="rounded-lg border border-red-200 bg-red-50 p-2.5 text-xs text-red-700">
              <div className="flex items-start gap-1.5">
                <AlertCircle className="h-4 w-4 text-red-600 shrink-0 mt-0.5" />
                <span>{pipelineError}</span>
              </div>
            </div>
          ) : null}

          {/* Action Button: Run Pipeline */}
          <div className="shrink-0">
            <Button
              type="button"
              onClick={handleRunPipeline}
              disabled={isRunningPipeline || !disclaimerAccepted || (estimate !== null && !estimate.sufficient_balance)}
              className="w-full bg-purple-600 hover:bg-purple-700 text-white text-xs font-semibold py-2.5 flex items-center justify-center gap-2 rounded-xl transition shadow-sm disabled:opacity-50"
            >
              {isRunningPipeline ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Đang xử lý quy trình Auto...</span>
                </>
              ) : (
                <>
                  <Zap className="h-4 w-4 fill-current" />
                  <span>Khởi chạy quy trình Auto ({estimate?.estimated_cost ?? 6} Credits)</span>
                </>
              )}
            </Button>
          </div>

          {/* Real-time Timeline Stepper when Running */}
          {isRunningPipeline ? (
            <div className="rounded-xl border border-purple-100 bg-purple-50/40 p-3.5 text-xs">
              <div className="flex items-center gap-2 text-purple-800 font-semibold mb-2">
                <Loader2 className="h-4 w-4 animate-spin text-purple-600" />
                <span>{pipelineCurrentStep}</span>
              </div>
              <div className="space-y-1.5 text-[11px] text-muted-foreground pl-6">
                <div>• Bước 1: Khởi tạo/Bảo lưu dàn ý chuẩn học thuật</div>
                <div>• Bước 2: Tìm kiếm bài báo khoa học liên quan</div>
                <div>• Bước 3: Thẩm định ngữ nghĩa câu & Missing Claims</div>
              </div>
            </div>
          ) : null}

          {/* Results: Human-in-the-Loop Suggestion Cards */}
          {pipelineResult ? (
            <div className="space-y-3 pt-2">
              <div className="flex items-center justify-between pb-1 border-b border-border">
                <span className="text-xs font-bold text-foreground flex items-center gap-1.5">
                  <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                  Kết quả phân tích ({suggestions.length} đề xuất)
                </span>
                <span className="text-[10px] text-muted-foreground">
                  Đã trừ {pipelineResult.total_credits_charged} Credits
                </span>
              </div>

              {suggestions.length === 0 ? (
                <div className="rounded-xl border border-dashed border-border p-4 text-center text-xs text-muted-foreground">
                  Không phát hiện câu văn thiếu trích dẫn hay lỗi học thuật nào. Văn bản của bạn rất chuẩn mực!
                </div>
              ) : (
                <div className="space-y-2.5">
                  {suggestions.map((sug) => (
                    <div
                      key={sug.id}
                      className={`rounded-xl border p-3 text-xs transition ${
                        sug.status === "accepted"
                          ? "border-emerald-200 bg-emerald-50/40"
                          : sug.status === "rejected"
                          ? "border-muted bg-muted/20 opacity-60"
                          : "border-border bg-card shadow-2xs hover:border-purple-200"
                      }`}
                    >
                      {/* Suggestion Header */}
                      <div className="flex items-center justify-between mb-1.5">
                        <span
                          className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                            sug.type === "citation"
                              ? "bg-amber-100 text-amber-800"
                              : "bg-blue-100 text-blue-800"
                          }`}
                        >
                          {sug.type === "citation" ? "Thiếu trích dẫn" : "Gợi ý tài liệu"}
                        </span>
                        {sug.status === "accepted" ? (
                          <span className="text-[11px] font-semibold text-emerald-700 flex items-center gap-1">
                            <Check className="h-3 w-3" /> Đã chấp nhận
                          </span>
                        ) : sug.status === "rejected" ? (
                          <span className="text-[11px] text-muted-foreground flex items-center gap-1">
                            <X className="h-3 w-3" /> Đã bỏ qua
                          </span>
                        ) : null}
                      </div>

                      {/* Claim Sentence Context */}
                      {sug.sentence ? (
                        <div className="mb-2 rounded bg-muted/40 p-2 text-[11px] italic text-foreground border-l-2 border-amber-500">
                          &quot;{sug.sentence}&quot;
                        </div>
                      ) : null}

                      {/* Reason & Action */}
                      <p className="font-semibold text-foreground mb-1">{sug.title}</p>
                      {sug.reason ? (
                        <p className="text-[11px] text-muted-foreground mb-2 leading-relaxed">
                          Lý do: {sug.reason}
                        </p>
                      ) : null}

                      {/* In-text Code Snippet if available */}
                      {sug.in_text_suggestion ? (
                        <div className="mb-2.5 flex items-center justify-between rounded-md bg-purple-50 px-2.5 py-1 text-purple-900 border border-purple-100">
                          <code className="font-mono text-xs font-bold">{sug.in_text_suggestion}</code>
                          <button
                            type="button"
                            onClick={() => handleCopy(sug.in_text_suggestion || "", sug.id)}
                            className="text-[11px] text-purple-600 hover:text-purple-800 flex items-center gap-1"
                            title="Sao chép mã trích dẫn"
                          >
                            {copiedId === sug.id ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                            <span>{copiedId === sug.id ? "Đã chép" : "Sao chép"}</span>
                          </button>
                        </div>
                      ) : null}

                      {/* Human-in-the-loop Action Buttons */}
                      {sug.status === "pending" ? (
                        <div className="flex items-center gap-2 pt-1 border-t border-border/50">
                          <Button
                            type="button"
                            size="sm"
                            onClick={() => handleAcceptSuggestion(sug)}
                            className="flex-1 bg-purple-600 hover:bg-purple-700 text-white text-[11px] h-7 font-medium"
                          >
                            <Check className="h-3 w-3 mr-1" /> Chấp nhận
                          </Button>
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            onClick={() => handleRejectSuggestion(sug.id)}
                            className="h-7 text-[11px] text-muted-foreground hover:text-foreground"
                          >
                            <X className="h-3 w-3 mr-1" /> Bỏ qua
                          </Button>
                        </div>
                      ) : null}
                    </div>
                  ))}
                </div>
              )}

              <div className="pt-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleRunPipeline}
                  className="w-full text-xs text-muted-foreground hover:text-foreground flex items-center justify-center gap-1.5 h-8"
                >
                  <RotateCcw className="h-3 w-3" />
                  <span>Chạy lại quy trình</span>
                </Button>
              </div>
            </div>
          ) : null}
        </div>
      )}
    </aside>
  );
}
