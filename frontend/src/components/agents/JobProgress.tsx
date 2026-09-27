"use client";

import React from "react";
import {
  Search,
  BookOpen,
  FileSearch,
  Quote,
  PenTool,
  ShieldCheck,
  GitPullRequest,
  CheckCircle2,
  XCircle,
  Loader2,
  Clock,
  Sparkles,
  Zap,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { StageProgressItem, StagePlanItem } from "@/lib/api";

interface JobProgressProps {
  stages: StageProgressItem[];
  plan?: StagePlanItem[] | null;
  currentStatus: string;
  estimatedCredits?: number;
  actualCredits?: number;
  className?: string;
}

const STAGE_CONFIG: Record<
  string,
  { label: string; description: string; icon: React.ComponentType<{ className?: string }> }
> = {
  inspect_context: {
    label: "Phân tích ngữ cảnh",
    description: "Đọc tài liệu hiện tại, dàn ý và yêu cầu",
    icon: Search,
  },
  build_outline: {
    label: "Định hình dàn ý",
    description: "Kiểm tra hoặc bổ sung cấu trúc đề mục",
    icon: BookOpen,
  },
  research: {
    label: "Tìm kiếm học thuật",
    description: "Khám phá bài báo và nghiên cứu tương quan",
    icon: FileSearch,
  },
  extract_evidence: {
    label: "Trích xuất bằng chứng",
    description: "Tổng hợp dữ liệu, luận điểm và tác giả",
    icon: Quote,
  },
  compose: {
    label: "Soạn thảo văn bản",
    description: "Viết đoạn văn theo văn phong học thuật chuẩn mực",
    icon: PenTool,
  },
  validate: {
    label: "Thẩm định học thuật",
    description: "Kiểm tra độ tin cậy, trích dẫn và liêm chính",
    icon: ShieldCheck,
  },
  build_proposal: {
    label: "Tạo đề xuất thay đổi",
    description: "Biên soạn bản so sánh Diff để người dùng duyệt",
    icon: GitPullRequest,
  },
};

export function JobProgress({
  stages,
  plan,
  currentStatus,
  estimatedCredits = 0,
  actualCredits = 0,
  className,
}: JobProgressProps) {
  // If stages array is empty but we have a plan, create skeleton items
  const displayStages: Array<{
    stage_id: string;
    stage_type: string;
    order: number;
    status: string;
    tokens_used?: number;
    credits_charged?: number;
    error?: string | null;
  }> =
    stages.length > 0
      ? stages
      : (plan || []).map((p, idx) => ({
          stage_id: p.stage_id,
          stage_type: p.stage_type,
          order: idx,
          status: "pending",
        }));

  return (
    <div
      className={cn(
        "rounded-2xl border border-purple-100 bg-linear-to-b from-purple-50/40 via-white to-white p-4 shadow-xs",
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between pb-3 mb-3 border-b border-purple-100/80">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-purple-600 text-white shadow-2xs">
            {currentStatus === "running" || currentStatus === "queued" ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : currentStatus === "completed" || currentStatus === "awaiting_approval" ? (
              <CheckCircle2 className="h-4 w-4" />
            ) : currentStatus === "failed" ? (
              <XCircle className="h-4 w-4" />
            ) : (
              <Sparkles className="h-4 w-4" />
            )}
          </div>
          <div>
            <h4 className="text-xs font-bold text-gray-900">Tiến trình thực thi Multi-Agent</h4>
            <p className="text-[11px] text-muted-foreground">
              {currentStatus === "running"
                ? "Các Agent chuyên biệt đang phối hợp thực hiện..."
                : currentStatus === "awaiting_approval"
                ? "Đã hoàn thành các bước, đang chờ bạn duyệt đề xuất"
                : currentStatus === "completed"
                ? "Quy trình đã hoàn tất thành công"
                : currentStatus === "failed"
                ? "Quy trình gặp sự cố"
                : "Đang xếp hàng chờ xử lý..."}
            </p>
          </div>
        </div>

        <div className="text-right">
          <div className="inline-flex items-center gap-1 text-[11px] font-semibold text-purple-700 bg-purple-100/70 px-2 py-0.5 rounded-full">
            <Zap className="h-3 w-3 fill-current" />
            <span>
              {actualCredits > 0 ? actualCredits : estimatedCredits} Credits
            </span>
          </div>
        </div>
      </div>

      {/* Stage Stepper List */}
      <div className="space-y-2">
        {displayStages.map((stage, idx) => {
          const config = STAGE_CONFIG[stage.stage_type] || {
            label: stage.stage_type,
            description: "",
            icon: Sparkles,
          };
          const Icon = config.icon;

          const isCompleted = stage.status === "completed";
          const isRunning = stage.status === "running";
          const isFailed = stage.status === "failed";
          const isPending = stage.status === "pending";

          return (
            <div
              key={stage.stage_id || `${stage.stage_type}-${idx}`}
              className={cn(
                "group relative flex items-start gap-3 rounded-xl p-2.5 transition-all duration-200",
                isRunning && "bg-purple-50/80 ring-1 ring-purple-200 shadow-xs",
                isCompleted && "bg-emerald-50/30",
                isFailed && "bg-red-50/50",
                isPending && "opacity-60"
              )}
            >
              {/* Step indicator */}
              <div
                className={cn(
                  "flex h-6 w-6 shrink-0 items-center justify-center rounded-lg transition-all",
                  isCompleted && "bg-emerald-600 text-white shadow-2xs",
                  isRunning && "bg-purple-600 text-white shadow-2xs animate-pulse",
                  isFailed && "bg-red-600 text-white",
                  isPending && "bg-gray-100 text-gray-400 border border-gray-200"
                )}
              >
                {isCompleted ? (
                  <CheckCircle2 className="h-3.5 w-3.5 stroke-[2.5]" />
                ) : isRunning ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin stroke-[2.5]" />
                ) : isFailed ? (
                  <XCircle className="h-3.5 w-3.5" />
                ) : (
                  <span className="text-[10px] font-bold">{idx + 1}</span>
                )}
              </div>

              {/* Stage content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <Icon
                      className={cn(
                        "h-3.5 w-3.5",
                        isRunning && "text-purple-600",
                        isCompleted && "text-emerald-600",
                        isFailed && "text-red-500",
                        isPending && "text-gray-400"
                      )}
                    />
                    <span
                      className={cn(
                        "text-xs font-semibold",
                        isRunning && "text-purple-900 font-bold",
                        isCompleted && "text-emerald-950",
                        isFailed && "text-red-800",
                        isPending && "text-gray-600"
                      )}
                    >
                      {config.label}
                    </span>
                  </div>

                  <span
                    className={cn(
                      "text-[10px] font-medium px-1.5 py-0.2 rounded",
                      isCompleted && "text-emerald-700 bg-emerald-100/60",
                      isRunning && "text-purple-700 bg-purple-100 animate-pulse",
                      isFailed && "text-red-700 bg-red-100",
                      isPending && "text-gray-400 bg-gray-50"
                    )}
                  >
                    {isCompleted
                      ? "Hoàn tất"
                      : isRunning
                      ? "Đang chạy..."
                      : isFailed
                      ? "Lỗi"
                      : "Chờ thực hiện"}
                  </span>
                </div>

                <p className="text-[11px] text-muted-foreground mt-0.5 leading-snug">
                  {config.description}
                </p>

                {/* Error message if any */}
                {isFailed && stage.error && (
                  <p className="text-[10px] text-red-600 mt-1 bg-red-100/50 p-1.5 rounded">
                    {stage.error}
                  </p>
                )}

                {/* Tokens and credits info */}
                {isCompleted && (stage.tokens_used || 0) > 0 && (
                  <div className="flex items-center gap-2 mt-1 text-[10px] text-muted-foreground">
                    <span>{stage.tokens_used} tokens</span>
                    {stage.credits_charged ? (
                      <span>• {stage.credits_charged} credits</span>
                    ) : null}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default JobProgress;
