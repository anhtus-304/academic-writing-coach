"use client";

import React, { useState, useEffect, useRef } from "react";
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
  Quote,
  Terminal,
  ChevronDown,
  ArrowRight,
  GitPullRequest,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  agentApi,
  creditApi,
  type SuggestionItem,
  type PipelineEstimateResponse,
  type ProposalData,
  type ApplyProposalResponse,
  type UndoResponse,
} from "@/lib/api";
import type { OutlineNode } from "@/components/outline/OutlineEditor";
import { useAgentJob } from "@/hooks/useAgentJob";
import { JobProgress } from "@/components/agents/JobProgress";
import { DiffViewer } from "@/components/editor/DiffViewer";
import { ChatMessage, type ChatMessageProps } from "@/components/agents/ChatMessage";

export type AIResponsePanelProps = {
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
  onApplyProposal?: (proposal: ProposalData, result: ApplyProposalResponse) => void;
  onUndoProposal?: (proposal: ProposalData, result: UndoResponse) => void;
  onInsertAtCursor?: (text: string) => void;
  onReplaceSelection?: (text: string) => void;
  onProposalReady?: (proposal: ProposalData) => void;
};

export function AIResponsePanel({
  isLoading: initialLoading = false,
  error: initialError = null,
  title = "AI Academic Coach",
  description = "Cố vấn phương pháp & kiểm định học thuật",
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
  onApplyProposal,
  onUndoProposal,
  onInsertAtCursor,
  onReplaceSelection,
  onProposalReady,
}: AIResponsePanelProps) {
  // Mode: "ask" (Quick chat/advice) | "auto" (Multi-Agent Workspace Job)
  const [panelMode, setPanelMode] = useState<"ask" | "auto">("auto");

  // ── Ask Mode State ──────────────────────────────────────────────────
  const [customQuestion, setCustomQuestion] = useState("");
  const [activeAction, setActiveAction] = useState<string | null>(null);
  const [isAsking, setIsAsking] = useState(false);
  const [chatMessages, setChatMessages] = useState<ChatMessageProps[]>([]);
  const [askError, setAskError] = useState<string | null>(initialError);

  // ── Auto Mode State ─────────────────────────────────────────────────
  const [autoGoalPrompt, setAutoGoalPrompt] = useState("");
  const [disclaimerAccepted, setDisclaimerAccepted] = useState(false);
  const [isEstimating, setIsEstimating] = useState(false);
  const [estimate, setEstimate] = useState<PipelineEstimateResponse | null>(null);

  const handleJobCompleted = React.useCallback((completedJob: any) => {
    onCreditDeducted?.();
  }, [onCreditDeducted]);

  const handleProposalApplied = React.useCallback((res: any, proposal: any) => {
    onCreditDeducted?.();
    onApplyProposal?.(proposal, res);
  }, [onCreditDeducted, onApplyProposal]);

  const handleProposalUndone = React.useCallback((res: any, proposal: any) => {
    onUndoProposal?.(proposal, res);
  }, [onUndoProposal]);

  // Hook for Multi-Agent Workspace Jobs
  const {
    job,
    activeProposal,
    isLoading: isJobCreating,
    isPolling: isJobRunning,
    isApplying,
    isUndoing,
    isDeciding,
    error: jobError,
    createJob,
    cancelJob,
    decideOperation,
    acceptAll,
    rejectAll,
    applyProposal,
    undoProposal,
    resetJob,
  } = useAgentJob({
    projectId,
    onJobCompleted: handleJobCompleted,
    onProposalApplied: handleProposalApplied,
    onProposalUndone: handleProposalUndone,
  });

  // Notify parent component when activeProposal is ready with tracked_html
  useEffect(() => {
    if (activeProposal && activeProposal.status !== "applied" && activeProposal.status !== "rejected") {
      onProposalReady?.(activeProposal);
    }
  }, [activeProposal, onProposalReady]);

  // Load estimate when switching to Auto mode
  useEffect(() => {
    if (panelMode === "auto" && !estimate && projectId) {
      setIsEstimating(true);
      agentApi
        .estimatePipeline({ project_id: projectId })
        .then((res) => setEstimate(res))
        .catch((err) => console.error("Estimate pipeline error:", err))
        .finally(() => setIsEstimating(false));
    }
  }, [panelMode, projectId, estimate]);

  // Handle Ask submission
  const handleAsk = async (action: string, promptText?: string) => {
    const textToAnalyze = selectedText?.trim() || promptText?.trim() || customQuestion.trim();
    if (!textToAnalyze) return;

    setActiveAction(action);
    setIsAsking(true);
    setAskError(null);

    // Append user message
    const userMsg: ChatMessageProps = {
      role: "user",
      content: promptText || (action !== "custom" ? `[${action}] ${textToAnalyze}` : textToAnalyze),
      timestamp: new Date().toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" }),
      actionType: action,
    };
    setChatMessages((prev) => [...prev, userMsg]);
    if (promptText || customQuestion) {
      setCustomQuestion("");
    }

    try {
      const res = await agentApi.askAI({
        selected_text: textToAnalyze,
        action,
        custom_prompt: promptText || customQuestion,
        project_id: projectId,
      });

      const assistantMsg: ChatMessageProps = {
        role: "assistant",
        content: res.response,
        timestamp: new Date().toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" }),
        creditsCharged: 1,
        tokensUsed: res.tokens_used,
      };
      setChatMessages((prev) => [...prev, assistantMsg]);
      onCreditDeducted?.();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Không thể kết nối với AI Assistant.";
      setAskError(message);
    } finally {
      setIsAsking(false);
      setActiveAction(null);
    }
  };

  // Handle starting Auto Agent Job
  const handleStartAutoJob = async (templatePrompt?: string) => {
    const finalPrompt = templatePrompt || autoGoalPrompt.trim() || selectedText?.trim();
    if (!finalPrompt) {
      return;
    }
    if (!disclaimerAccepted) {
      alert("Vui lòng đồng ý với Tuyên bố Liêm chính Học thuật trước khi khởi chạy Auto.");
      return;
    }

    await createJob({
      prompt: finalPrompt,
      mode: "auto",
      selection: selectedText || undefined,
      disclaimerAccepted: true,
    });
  };

  // Goal templates for quick selection in Auto mode
  const goalTemplates = [
    {
      title: "Soạn thảo Tổng quan nghiên cứu",
      prompt: "Soạn thảo mục Tổng quan nghiên cứu (Literature Review) tích hợp các nguồn bài báo đã chọn trong thư viện theo chuẩn APA 7.",
      icon: BookOpen,
    },
    {
      title: "Thẩm định & Bổ sung trích dẫn",
      prompt: "Quét toàn bộ bản thảo, phát hiện các luận điểm thiếu trích dẫn và đề xuất bổ sung trích dẫn học thuật thích hợp.",
      icon: ShieldCheck,
    },
    {
      title: "Mở rộng & Nâng cấp học thuật",
      prompt: "Nâng cấp phong cách diễn đạt cho đoạn văn bản đã chọn theo văn phong bài báo khoa học quốc tế, làm rõ luận cứ.",
      icon: GraduationCap,
    },
    {
      title: "Hoàn thiện Dàn ý & Đề mục",
      prompt: "Phân tích dàn ý hiện tại, bổ sung các tiểu mục còn thiếu và đảm bảo logic phân cấp theo quy chuẩn luận văn.",
      icon: Layers,
    },
  ];

  const isOutOfCredits =
    askError?.toLowerCase().includes("credit") ||
    jobError?.toLowerCase().includes("credit") ||
    askError?.includes("402") ||
    jobError?.includes("402");

  return (
    <aside className="flex h-full flex-col border-l border-border bg-card p-4 shadow-sm overflow-y-auto">
      {/* Top Header & Close Button */}
      <div className="mb-3 flex items-start justify-between gap-3 shrink-0">
        <div>
          <h3 className="text-sm font-bold text-foreground flex items-center gap-1.5">
            <Sparkles className="h-4 w-4 text-purple-600" />
            {title}
          </h3>
          <p className="mt-0.5 text-xs text-muted-foreground">{description}</p>
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
      <div className="mb-3 flex items-center rounded-xl bg-muted/70 p-1 text-xs shrink-0 border border-border/50">
        <button
          type="button"
          onClick={() => setPanelMode("auto")}
          className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-lg font-medium transition ${
            panelMode === "auto"
              ? "bg-white text-purple-700 font-bold shadow-xs border border-purple-200"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          <Zap className="h-3.5 w-3.5 text-amber-500 fill-amber-500" />
          <span>Quy trình Auto (Workspace)</span>
        </button>
        <button
          type="button"
          onClick={() => setPanelMode("ask")}
          className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-lg font-medium transition ${
            panelMode === "ask"
              ? "bg-white text-purple-700 font-bold shadow-xs border border-purple-200"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          <BookOpen className="h-3.5 w-3.5" />
          <span>Hỏi đáp (Ask)</span>
        </button>
      </div>

      {/* Credit Warning Banner */}
      {isOutOfCredits && (
        <div className="mb-3 rounded-xl border border-amber-300 bg-amber-50 p-2.5 text-xs text-amber-800 shrink-0">
          <div className="flex items-center justify-between">
            <span className="font-semibold">⚠️ Bạn đã hết Credits học thuật</span>
            <Link
              href="/pricing"
              className="text-purple-700 underline font-bold hover:text-purple-900"
            >
              Nạp thêm
            </Link>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODE 1: AUTO MULTI-AGENT WORKSPACE JOB                                    */}
      {/* ========================================================================= */}
      {panelMode === "auto" && (
        <div className="flex flex-col flex-1 space-y-3.5">
          {/* Active Job Running / Progress Stepper */}
          {job && (job.status === "running" || job.status === "queued") && (
            <div className="space-y-2">
              <JobProgress
                stages={job.stages}
                plan={job.plan}
                currentStatus={job.status}
                estimatedCredits={job.estimated_credits}
                actualCredits={job.actual_credits}
              />
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={cancelJob}
                className="w-full text-xs text-red-600 hover:text-red-700 hover:bg-red-50 border-red-200 h-8"
              >
                Hủy tác vụ này
              </Button>
            </div>
          )}

          {/* Executive Summary & Track Changes Master Controls */}
          {activeProposal && (
            <div className="space-y-3.5">
              {/* Status Header Card */}
              <div className="rounded-2xl border border-purple-200/80 bg-gradient-to-br from-purple-50/90 via-indigo-50/40 to-white p-3.5 shadow-xs">
                <div className="flex items-center justify-between gap-2 mb-2">
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-purple-100 text-purple-800 border border-purple-200">
                    <Sparkles className="h-3 w-3 text-purple-600" />
                    {activeProposal.status === "applied"
                      ? "Đã áp dụng vào bài viết"
                      : activeProposal.status === "rejected"
                      ? "Đã từ chối đề xuất"
                      : "Đã đánh dấu Track Changes"}
                  </span>
                  <span className="text-[10px] text-muted-foreground font-mono">
                    v{activeProposal.base_version}
                  </span>
                </div>

                <h4 className="text-xs font-bold text-gray-950 mb-1">
                  Bản thảo đã được cập nhật trực tiếp vào Editor
                </h4>
                <p className="text-[11px] text-muted-foreground leading-relaxed">
                  Toàn bộ các đề mục và nội dung theo Dàn ý học thuật đã được tích hợp trực quan trên trình soạn thảo bên trái.
                </p>

                {/* Metrics Row */}
                <div className="grid grid-cols-2 gap-2 mt-3 pt-2.5 border-t border-purple-100/80">
                  <div className="bg-white/80 rounded-xl p-2 border border-purple-100 flex items-center gap-2">
                    <div className="h-7 w-7 rounded-lg bg-emerald-50 flex items-center justify-center shrink-0 border border-emerald-100">
                      <FileText className="h-3.5 w-3.5 text-emerald-600" />
                    </div>
                    <div>
                      <div className="text-[10px] text-muted-foreground font-medium">Từ ngữ soạn thảo</div>
                      <div className="text-xs font-bold text-gray-900">
                        ~{activeProposal.summary?.composed_words ?? "Đầy đủ"} từ
                      </div>
                    </div>
                  </div>

                  <div className="bg-white/80 rounded-xl p-2 border border-purple-100 flex items-center gap-2">
                    <div className="h-7 w-7 rounded-lg bg-blue-50 flex items-center justify-center shrink-0 border border-blue-100">
                      <BookOpen className="h-3.5 w-3.5 text-blue-600" />
                    </div>
                    <div>
                      <div className="text-[10px] text-muted-foreground font-medium">Tài liệu trích dẫn</div>
                      <div className="text-xs font-bold text-gray-900">
                        {activeProposal.summary?.sources_count ?? (activeProposal.summary?.source_refs?.length ?? 0)} nguồn
                      </div>
                    </div>
                  </div>
                </div>

                {/* Source References Pills */}
                {activeProposal.summary?.source_refs && activeProposal.summary.source_refs.length > 0 && (
                  <div className="mt-2.5">
                    <div className="text-[10px] font-semibold text-muted-foreground mb-1">
                      Nguồn trích dẫn học thuật đã tích hợp:
                    </div>
                    <div className="flex flex-wrap gap-1">
                      {activeProposal.summary.source_refs.map((ref, idx) => (
                        <span
                          key={idx}
                          className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md bg-white border border-gray-200 text-[10px] text-gray-700 font-mono"
                        >
                          <Quote className="h-2.5 w-2.5 text-blue-500" />
                          {ref}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Visual Guide Box */}
                {activeProposal.status !== "applied" && activeProposal.status !== "rejected" && (
                  <div className="mt-3 rounded-xl bg-amber-50/70 border border-amber-200/80 p-2.5 text-[11px] text-amber-900 space-y-1.5">
                    <div className="font-semibold flex items-center gap-1.5 text-amber-950">
                      <Lightbulb className="h-3.5 w-3.5 text-amber-600 shrink-0" />
                      Hướng dẫn xem & duyệt trực quan:
                    </div>
                    <div className="flex items-center gap-2 text-[10.5px]">
                      <span className="inline-block px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-800 font-semibold border border-emerald-300">
                        + Chữ xanh lục
                      </span>
                      <span>Nội dung mới do Agent viết</span>
                    </div>
                    <div className="flex items-center gap-2 text-[10.5px]">
                      <span className="inline-block px-1.5 py-0.5 rounded bg-red-100 text-red-800 line-through font-semibold border border-red-300">
                        - Chữ đỏ gạch
                      </span>
                      <span>Nội dung cũ được thay thế</span>
                    </div>
                    <p className="text-[10px] text-amber-800/90 pt-0.5 italic">
                      * Bạn có thể bấm vào từng đoạn trong bài viết để Chấp nhận/Bỏ qua, hoặc duyệt toàn bài bằng 2 nút bên dưới.
                    </p>
                  </div>
                )}
              </div>

              {/* Master Action Buttons */}
              {activeProposal.status !== "applied" && activeProposal.status !== "rejected" ? (
                <div className="space-y-2">
                  <Button
                    type="button"
                    onClick={() => applyProposal(activeProposal.proposal_id, { action: "accept_all" })}
                    disabled={isApplying}
                    className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-semibold py-2.5 rounded-xl text-xs flex items-center justify-center gap-2 shadow-sm transition"
                  >
                    {isApplying ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        <span>Đang lưu bản thảo hoàn chỉnh...</span>
                      </>
                    ) : (
                      <>
                        <CheckCircle2 className="h-4 w-4" />
                        <span>Chấp nhận tất cả vào bài viết</span>
                      </>
                    )}
                  </Button>

                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => applyProposal(activeProposal.proposal_id, { action: "reject_all" })}
                    disabled={isApplying}
                    className="w-full border-red-200 text-red-600 hover:bg-red-50 hover:text-red-700 font-medium py-2 rounded-xl text-xs flex items-center justify-center gap-1.5 transition"
                  >
                    <XCircle className="h-4 w-4" />
                    <span>Từ chối & Khôi phục bản gốc</span>
                  </Button>
                </div>
              ) : activeProposal.status === "applied" ? (
                <div className="space-y-2">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => undoProposal(activeProposal.proposal_id)}
                    disabled={isUndoing}
                    className="w-full border-gray-300 text-gray-700 hover:bg-gray-100 font-medium py-2 rounded-xl text-xs flex items-center justify-center gap-1.5 transition"
                  >
                    {isUndoing ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <RotateCcw className="h-3.5 w-3.5" />
                    )}
                    <span>Hoàn tác thay đổi này</span>
                  </Button>
                </div>
              ) : null}

              {/* Reset button to start new task */}
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={resetJob}
                className="w-full text-xs text-muted-foreground hover:text-foreground h-8"
              >
                <RotateCcw className="h-3 w-3 mr-1" /> Tạo yêu cầu Auto mới
              </Button>
            </div>
          )}

          {/* Job Error Display */}
          {jobError && (
            <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-xs text-red-700 flex items-start gap-2">
              <AlertCircle className="h-4 w-4 text-red-600 shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="font-semibold">Thông báo quy trình</p>
                <p className="mt-0.5 leading-relaxed">{jobError}</p>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={resetJob}
                  className="mt-2 h-7 text-xs border-red-300 text-red-700 hover:bg-red-100"
                >
                  Thử lại
                </Button>
              </div>
            </div>
          )}

          {/* New Job Setup Form (Shown when no active job or proposal) */}
          {!isJobRunning && !activeProposal && (
            <div className="space-y-3.5">
              {/* Selected Text context card if available */}
              {selectedText && (
                <div className="rounded-xl border border-border bg-muted/20 p-2.5 text-xs">
                  <div className="flex justify-between items-center mb-1 text-[10px] font-bold uppercase tracking-wider text-purple-700">
                    <span>Đoạn văn bản trọng tâm</span>
                    <span className="text-muted-foreground">{selectedText.length} ký tự</span>
                  </div>
                  <p className="line-clamp-3 italic text-[11px] text-foreground border-l-2 border-purple-500 pl-2">
                    &quot;{selectedText}&quot;
                  </p>
                </div>
              )}

              {/* Goal Input Area */}
              <div>
                <label className="text-xs font-semibold text-foreground mb-1 block">
                  Mục tiêu công việc bạn muốn Agent thực hiện:
                </label>
                <textarea
                  value={autoGoalPrompt}
                  onChange={(e) => setAutoGoalPrompt(e.target.value)}
                  placeholder="Ví dụ: Soạn thảo phần Tổng quan nghiên cứu dựa trên 5 bài báo đã chọn, bổ sung trích dẫn chuẩn APA 7..."
                  rows={3}
                  className="w-full rounded-xl border border-input bg-background p-2.5 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-purple-500 transition"
                />
              </div>

              {/* Quick Goal Templates */}
              <div>
                <span className="text-[11px] font-medium text-muted-foreground mb-1.5 block">
                  Hoặc chọn mẫu nhiệm vụ học thuật:
                </span>
                <div className="space-y-1.5">
                  {goalTemplates.map((tpl, idx) => {
                    const Icon = tpl.icon;
                    return (
                      <button
                        key={idx}
                        type="button"
                        onClick={() => {
                          setAutoGoalPrompt(tpl.prompt);
                        }}
                        className="w-full text-left p-2 rounded-xl border border-border bg-white hover:border-purple-300 hover:bg-purple-50/40 text-xs transition flex items-center justify-between group"
                      >
                        <div className="flex items-center gap-2">
                          <Icon className="h-3.5 w-3.5 text-purple-600 shrink-0" />
                          <span className="font-medium text-gray-900 group-hover:text-purple-700">
                            {tpl.title}
                          </span>
                        </div>
                        <ArrowRight className="h-3 w-3 text-gray-300 group-hover:text-purple-600 shrink-0 transition" />
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Integrity Disclaimer */}
              <div className="rounded-xl border border-amber-200 bg-amber-50/60 p-3 text-xs">
                <label className="flex items-start gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={disclaimerAccepted}
                    onChange={(e) => setDisclaimerAccepted(e.target.checked)}
                    className="h-3.5 w-3.5 rounded border-amber-400 text-purple-600 focus:ring-purple-500 mt-0.5"
                  />
                  <span className="text-[11px] text-amber-900 leading-snug">
                    Tôi cam kết kiểm tra lại toàn bộ dẫn chứng, nguồn tài liệu và chịu trách nhiệm liêm chính về nội dung học thuật trước khi áp dụng.
                  </span>
                </label>
              </div>

              {/* Run Button */}
              <Button
                type="button"
                onClick={() => handleStartAutoJob()}
                disabled={
                  isJobCreating ||
                  !disclaimerAccepted ||
                  (!autoGoalPrompt.trim() && !selectedText?.trim())
                }
                className="w-full bg-purple-600 hover:bg-purple-700 text-white font-semibold py-2.5 rounded-xl text-xs flex items-center justify-center gap-2 shadow-sm disabled:opacity-50 transition"
              >
                {isJobCreating ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span>Đang lập kế hoạch & khởi chạy...</span>
                  </>
                ) : (
                  <>
                    <Zap className="h-4 w-4 fill-current text-amber-300" />
                    <span>Khởi chạy quy trình Auto ({estimate?.estimated_cost ?? 6} Credits)</span>
                  </>
                )}
              </Button>
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODE 2: ASK MODE (Interactive Chat & Quick Socratic Tools)                */}
      {/* ========================================================================= */}
      {panelMode === "ask" && (
        <div className="flex flex-col flex-1">
          {/* Selected Quote Card if text is selected */}
          {selectedText && (
            <div className="rounded-xl border border-border bg-muted/30 p-2.5 shrink-0 mb-3">
              <div className="flex justify-between items-center mb-1 text-[10px] font-bold uppercase tracking-wider text-purple-700">
                <span>Đoạn văn bản được chọn</span>
                <span className="text-muted-foreground">{selectedText.length} ký tự</span>
              </div>
              <blockquote className="border-l-2 border-purple-600 pl-2.5 text-[11px] leading-relaxed text-foreground max-h-24 overflow-y-auto italic">
                &quot;{selectedText}&quot;
              </blockquote>
            </div>
          )}

          {/* Quick Action Pills (4 Buttons) */}
          <div className="mb-3 shrink-0">
            <div className="text-xs font-semibold text-foreground mb-1.5 flex justify-between items-center">
              <span>Tác vụ cố vấn nhanh</span>
              <span className="text-[10px] font-medium text-purple-600 bg-purple-50 px-1.5 py-0.5 rounded">
                🪙 1 Credit / lần
              </span>
            </div>
            <div className="grid grid-cols-2 gap-1.5">
              <button
                type="button"
                onClick={() => handleAsk("explain")}
                disabled={isAsking || (!selectedText && !customQuestion)}
                className={`flex items-center gap-1.5 rounded-lg border p-2 text-left text-xs font-medium transition ${
                  activeAction === "explain" && isAsking
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
                  activeAction === "summarize" && isAsking
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
                  activeAction === "academic_rewrite" && isAsking
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
                  activeAction === "critique" && isAsking
                    ? "border-purple-600 bg-purple-50 text-purple-700"
                    : "border-border bg-background hover:border-purple-300 hover:bg-purple-50/50 text-foreground"
                } disabled:opacity-50`}
              >
                <Lightbulb className="h-3.5 w-3.5 text-amber-600 shrink-0" />
                <span className="truncate">Phản biện luận cứ</span>
              </button>
            </div>
          </div>

          {/* Chat Messages Stream */}
          <div className="flex-1 space-y-3 overflow-y-auto mb-3 pr-1">
            {chatMessages.length === 0 ? (
              <div className="rounded-xl border border-dashed border-border bg-muted/10 p-4 text-center text-xs text-muted-foreground">
                <Lightbulb className="h-4 w-4 mx-auto mb-1 text-amber-500" />
                Chọn đoạn văn trong editor hoặc đặt câu hỏi học thuật trực tiếp dưới đây để nhận hướng dẫn.
              </div>
            ) : (
              chatMessages.map((msg, idx) => (
                <ChatMessage
                  key={idx}
                  {...msg}
                  onInsertAtCursor={onInsertAtCursor}
                  onReplaceSelection={onReplaceSelection}
                />
              ))
            )}
            {isAsking && (
              <div className="flex items-center gap-2 p-3 bg-purple-50/60 rounded-xl text-xs text-purple-800 border border-purple-100">
                <Loader2 className="h-3.5 w-3.5 animate-spin text-purple-600" />
                <span>AI Coach đang suy nghĩ và tra cứu...</span>
              </div>
            )}
          </div>

          {/* Ask Error */}
          {askError && (
            <div className="mb-2 rounded-lg border border-red-200 bg-red-50 p-2 text-xs text-red-700">
              {askError}
            </div>
          )}

          {/* Input Box */}
          <div className="shrink-0 flex gap-2">
            <input
              type="text"
              value={customQuestion}
              onChange={(e) => setCustomQuestion(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && customQuestion.trim() && !isAsking) {
                  handleAsk("custom", customQuestion);
                }
              }}
              placeholder="Hỏi AI Coach về văn phong, trích dẫn..."
              className="flex-1 rounded-xl border border-input bg-background px-3 py-2 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-purple-500"
            />
            <Button
              type="button"
              size="icon"
              onClick={() => handleAsk("custom", customQuestion)}
              disabled={isAsking || !customQuestion.trim()}
              className="h-8 w-8 rounded-xl bg-purple-600 hover:bg-purple-700 text-white shrink-0"
            >
              <Send className="h-3.5 w-3.5" />
            </Button>
          </div>
        </div>
      )}
    </aside>
  );
}

export default AIResponsePanel;
