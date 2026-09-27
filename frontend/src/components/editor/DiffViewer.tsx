"use client";

import React, { useState } from "react";
import {
  GitPullRequest,
  Check,
  X,
  RotateCcw,
  AlertTriangle,
  FileText,
  Layers,
  BookOpen,
  ArrowRight,
  ShieldAlert,
  Sparkles,
  ExternalLink,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { ProposalData, ProposalOperation } from "@/lib/api";

interface DiffViewerProps {
  proposal: ProposalData;
  isApplying?: boolean;
  isUndoing?: boolean;
  isDeciding?: boolean;
  onAcceptOperation: (proposalId: string, operationId: string) => Promise<any> | void;
  onRejectOperation: (proposalId: string, operationId: string) => Promise<any> | void;
  onAcceptAll: (proposalId: string) => Promise<any> | void;
  onRejectAll: (proposalId: string) => Promise<any> | void;
  onApply: (proposalId: string, acceptedOperationIds?: string[]) => Promise<any> | void;
  onUndo: (proposalId: string) => Promise<any> | void;
  className?: string;
}

export function DiffViewer({
  proposal,
  isApplying = false,
  isUndoing = false,
  isDeciding = false,
  onAcceptOperation,
  onRejectOperation,
  onAcceptAll,
  onRejectAll,
  onApply,
  onUndo,
  className,
}: DiffViewerProps) {
  const [viewMode, setViewMode] = useState<"unified" | "split">("unified");
  const [expandedOps, setExpandedOps] = useState<Record<string, boolean>>({});

  const toggleExpand = (opId: string) => {
    setExpandedOps((prev) => ({ ...prev, [opId]: !prev[opId] }));
  };

  const operations = proposal.operations || [];
  const acceptedCount = operations.filter((o) => o.status === "accepted").length;
  const pendingCount = operations.filter((o) => o.status === "pending").length;
  const rejectedCount = operations.filter((o) => o.status === "rejected").length;
  const isApplied = proposal.status === "applied";
  const isConflict = proposal.status === "conflict";

  const getTargetLabel = () => {
    switch (proposal.target_type) {
      case "outline":
        return { label: "Dàn ý học thuật", icon: Layers };
      case "selected_papers":
        return { label: "Tài liệu tham khảo", icon: BookOpen };
      case "document":
      default:
        return { label: "Bản thảo tài liệu", icon: FileText };
    }
  };

  const TargetIcon = getTargetLabel().icon;

  return (
    <div
      className={cn(
        "rounded-2xl border border-gray-200 bg-white overflow-hidden shadow-xs",
        className
      )}
    >
      {/* Header */}
      <div className="bg-linear-to-r from-purple-50/70 to-indigo-50/50 p-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-purple-600 text-white shadow-2xs">
              <GitPullRequest className="h-4 w-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-xs font-bold text-gray-900">
                  Đề xuất thay đổi (Diff Proposal)
                </h3>
                <span className="inline-flex items-center gap-1 rounded-md bg-white/80 px-2 py-0.5 text-[10px] font-semibold text-purple-700 border border-purple-200">
                  <TargetIcon className="h-3 w-3" />
                  {getTargetLabel().label}
                </span>
                <span className="text-[10px] text-muted-foreground font-mono">
                  v{proposal.base_version}
                </span>
              </div>
              <p className="text-[11px] text-muted-foreground mt-0.5">
                Xem xét và quyết định chấp nhận hoặc bỏ qua từng thay đổi
              </p>
            </div>
          </div>

          {/* Quick stats pills */}
          <div className="flex items-center gap-1 text-[11px]">
            {acceptedCount > 0 && (
              <span className="rounded-full bg-emerald-100 text-emerald-800 px-2 py-0.5 font-semibold">
                +{acceptedCount} chấp nhận
              </span>
            )}
            {pendingCount > 0 && (
              <span className="rounded-full bg-amber-100 text-amber-800 px-2 py-0.5 font-semibold">
                {pendingCount} chờ duyệt
              </span>
            )}
            {rejectedCount > 0 && (
              <span className="rounded-full bg-gray-100 text-gray-600 px-2 py-0.5 font-semibold">
                {rejectedCount} bỏ qua
              </span>
            )}
          </div>
        </div>

        {/* Warnings Banner if any */}
        {proposal.warnings && proposal.warnings.length > 0 && (
          <div className="mt-3 rounded-xl border border-amber-200 bg-amber-50/80 p-2.5 text-xs text-amber-800">
            <div className="flex items-start gap-2">
              <AlertTriangle className="h-4 w-4 text-amber-600 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <span className="font-semibold text-[11px]">Lưu ý từ AI Validation:</span>
                <ul className="list-disc pl-4 text-[11px] space-y-0.5">
                  {proposal.warnings.map((w, idx) => (
                    <li key={idx}>{w}</li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        )}

        {/* Conflict Warning */}
        {isConflict && (
          <div className="mt-3 rounded-xl border border-red-200 bg-red-50 p-2.5 text-xs text-red-800">
            <div className="flex items-start gap-2">
              <ShieldAlert className="h-4 w-4 text-red-600 shrink-0 mt-0.5" />
              <div>
                <p className="font-bold text-[11px]">Phát hiện xung đột nội dung</p>
                <p className="text-[11px] mt-0.5 text-red-700">
                  Tài liệu đã được chỉnh sửa trong Editor kể từ khi đề xuất này được tạo. Vui lòng tạo lại yêu cầu để AI đồng bộ với phiên bản mới nhất.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Selected chunks ready banner */}
        {!isApplied && !isConflict && acceptedCount > 0 && (
          <div className="mt-3 rounded-xl border border-emerald-300 bg-emerald-50/90 p-2.5 flex items-center justify-between shadow-xs">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-emerald-600 shrink-0" />
              <span className="text-xs font-semibold text-emerald-900">
                Đã chọn {acceptedCount}/{operations.length} thay đổi
              </span>
            </div>
            <Button
              type="button"
              size="sm"
              onClick={() => onApply(proposal.proposal_id)}
              disabled={isApplying}
              className="h-7 text-xs bg-emerald-600 hover:bg-emerald-700 text-white font-semibold px-3 rounded-lg shadow-2xs gap-1.5 transition"
            >
              {isApplying ? (
                <div className="h-3 w-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
              ) : (
                <Sparkles className="h-3 w-3" />
              )}
              <span>Áp dụng vào văn bản ngay</span>
            </Button>
          </div>
        )}

        {/* Bulk Action Controls */}
        {!isApplied && !isConflict && operations.length > 0 && (
          <div className="flex items-center justify-between mt-3 pt-2.5 border-t border-purple-100">
            <span className="text-[11px] text-muted-foreground">
              Thao tác nhanh:
            </span>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={async () => {
                  await onAcceptAll(proposal.proposal_id);
                  await onApply(proposal.proposal_id);
                }}
                disabled={isDeciding || isApplying}
                className="text-[11px] font-semibold text-emerald-700 hover:text-emerald-800 flex items-center gap-1 bg-emerald-50 hover:bg-emerald-100/70 px-2.5 py-1 rounded-md transition disabled:opacity-50"
              >
                {isApplying ? (
                  <div className="h-3 w-3 border-2 border-emerald-600 border-t-transparent rounded-full animate-spin" />
                ) : (
                  <Check className="h-3 w-3" />
                )}
                <span>Chấp nhận & Áp dụng tất cả</span>
              </button>
              <button
                type="button"
                onClick={() => onRejectAll(proposal.proposal_id)}
                disabled={isDeciding || isApplying}
                className="text-[11px] font-semibold text-gray-600 hover:text-gray-800 flex items-center gap-1 bg-gray-100 hover:bg-gray-200/80 px-2 py-1 rounded-md transition disabled:opacity-50"
              >
                <X className="h-3 w-3" />
                <span>Bỏ qua tất cả</span>
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Operations List */}
      <div className="p-4 space-y-3 max-h-[500px] overflow-y-auto">
        {operations.length === 0 ? (
          <div className="text-center py-8 text-xs text-muted-foreground">
            Không có thay đổi nào được tạo ra trong đề xuất này.
          </div>
        ) : (
          operations.map((op, index) => {
            const isOpAccepted = op.status === "accepted";
            const isOpRejected = op.status === "rejected";
            const isOpPending = op.status === "pending";

            return (
              <div
                key={op.operation_id}
                className={cn(
                  "rounded-xl border transition-all duration-200 overflow-hidden",
                  isOpAccepted && "border-emerald-300 bg-emerald-50/20",
                  isOpRejected && "border-gray-200 bg-gray-50/50 opacity-60",
                  isOpPending && "border-gray-200 bg-white shadow-2xs hover:border-purple-200"
                )}
              >
                {/* Op Card Header */}
                <div className="flex items-center justify-between p-2.5 bg-gray-50/80 border-b border-gray-100 text-xs">
                  <div className="flex items-center gap-2">
                    <span className="flex h-5 w-5 items-center justify-center rounded-md bg-purple-100 text-purple-800 text-[10px] font-bold">
                      #{index + 1}
                    </span>
                    <span
                      className={cn(
                        "text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded",
                        op.type === "insert" && "bg-emerald-100 text-emerald-800",
                        op.type === "replace" && "bg-blue-100 text-blue-800",
                        op.type === "delete" && "bg-red-100 text-red-800",
                        op.type === "outline_patch" && "bg-purple-100 text-purple-800"
                      )}
                    >
                      {op.type === "insert"
                        ? "Thêm mới"
                        : op.type === "replace"
                        ? "Thay thế / Viết lại"
                        : op.type === "delete"
                        ? "Xóa bỏ"
                        : "Cập nhật dàn ý"}
                    </span>
                  </div>

                  {/* Operation Decision Buttons */}
                  {!isApplied && !isConflict && (
                    <div className="flex items-center gap-1.5">
                      {isOpPending ? (
                        <>
                          <Button
                            type="button"
                            size="sm"
                            onClick={() => onAcceptOperation(proposal.proposal_id, op.operation_id)}
                            disabled={isDeciding || isApplying}
                            title="Chọn đoạn này để áp dụng chung"
                            className="h-6 px-2 text-[11px] bg-emerald-600 hover:bg-emerald-700 text-white font-medium rounded-md gap-1"
                          >
                            <Check className="h-3 w-3" />
                            <span>Đồng ý</span>
                          </Button>
                          <Button
                            type="button"
                            size="sm"
                            onClick={async () => {
                              await onAcceptOperation(proposal.proposal_id, op.operation_id);
                              await onApply(proposal.proposal_id, [op.operation_id]);
                            }}
                            disabled={isDeciding || isApplying}
                            title="Áp dụng ngay riêng đoạn này vào văn bản"
                            className="h-6 px-2 text-[11px] bg-purple-600 hover:bg-purple-700 text-white font-medium rounded-md gap-1 shadow-2xs"
                          >
                            <Sparkles className="h-3 w-3" />
                            <span>Áp dụng ngay</span>
                          </Button>
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            onClick={() => onRejectOperation(proposal.proposal_id, op.operation_id)}
                            disabled={isDeciding || isApplying}
                            className="h-6 px-2 text-[11px] text-gray-500 hover:text-gray-800 rounded-md gap-1"
                          >
                            <X className="h-3 w-3" />
                            <span>Bỏ qua</span>
                          </Button>
                        </>
                      ) : isOpAccepted ? (
                        <div className="flex items-center gap-1.5">
                          <span className="text-[11px] font-semibold text-emerald-700 flex items-center gap-1 bg-emerald-100/70 px-2 py-0.5 rounded">
                            <Check className="h-3 w-3 stroke-[2.5]" /> Đã chọn
                          </span>
                          <Button
                            type="button"
                            size="sm"
                            onClick={() => onApply(proposal.proposal_id, [op.operation_id])}
                            disabled={isApplying}
                            className="h-6 px-2 text-[10px] bg-emerald-600 hover:bg-emerald-700 text-white font-medium rounded-md gap-1"
                          >
                            <Sparkles className="h-2.5 w-2.5" />
                            <span>Áp dụng</span>
                          </Button>
                          <button
                            type="button"
                            onClick={() => onRejectOperation(proposal.proposal_id, op.operation_id)}
                            disabled={isDeciding || isApplying}
                            className="text-[10px] text-gray-400 hover:text-gray-600 underline ml-1"
                          >
                            Bỏ chọn
                          </button>
                        </div>
                      ) : (
                        <div className="flex items-center gap-1">
                          <span className="text-[11px] font-medium text-gray-500 flex items-center gap-1 bg-gray-200/60 px-2 py-0.5 rounded">
                            <X className="h-3 w-3" /> Đã bỏ qua
                          </span>
                          <button
                            type="button"
                            onClick={() => onAcceptOperation(proposal.proposal_id, op.operation_id)}
                            disabled={isDeciding || isApplying}
                            className="text-[10px] text-purple-600 hover:text-purple-800 underline ml-1"
                          >
                            Chọn lại
                          </button>
                        </div>
                      )}
                    </div>
                  )}

                  {isApplied && (
                    <span className="text-[10px] font-semibold text-emerald-700 flex items-center gap-1">
                      <Check className="h-3 w-3 stroke-[2.5]" /> Đã áp dụng
                    </span>
                  )}
                </div>

                {/* Diff Visual Content */}
                <div className="p-3 text-xs space-y-2">
                  {/* Before (Deleted/Replaced) */}
                  {op.before && (
                    <div className="rounded-lg bg-red-50/70 p-2.5 border-l-2 border-red-500 text-red-950 font-sans">
                      <div className="text-[10px] font-bold text-red-700 mb-1 flex items-center gap-1">
                        <span>— Nội dung gốc (Bị xóa / Thay thế)</span>
                      </div>
                      <div className="line-through opacity-80 leading-relaxed whitespace-pre-wrap text-[11.5px]">
                        {op.before}
                      </div>
                    </div>
                  )}

                  {/* After (Added/Composed) */}
                  {op.after && (
                    <div className="rounded-lg bg-emerald-50/70 p-2.5 border-l-2 border-emerald-500 text-emerald-950 font-sans">
                      <div className="text-[10px] font-bold text-emerald-700 mb-1 flex items-center gap-1">
                        <span>+ Nội dung mới đề xuất (Sẽ thêm vào)</span>
                      </div>
                      <div className="leading-relaxed whitespace-pre-wrap text-[11.5px] font-normal">
                        {op.after}
                      </div>
                    </div>
                  )}

                  {/* Source citations reference tags */}
                  {op.source_refs && op.source_refs.length > 0 && (
                    <div className="pt-1 flex items-center gap-1.5 flex-wrap">
                      <span className="text-[10px] text-muted-foreground font-semibold">
                        Nguồn trích dẫn:
                      </span>
                      {op.source_refs.map((ref, idx) => (
                        <span
                          key={idx}
                          className="inline-flex items-center gap-1 rounded bg-purple-50 px-1.5 py-0.5 text-[10px] font-medium text-purple-700 border border-purple-200/60"
                        >
                          <BookOpen className="h-2.5 w-2.5" />
                          {ref}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Footer / Apply Controls */}
      <div className="p-4 bg-gray-50/80 border-t border-gray-200">
        {!isApplied ? (
          <div className="space-y-2">
            <Button
              type="button"
              onClick={() => onApply(proposal.proposal_id)}
              disabled={isApplying || isConflict || (acceptedCount === 0 && operations.length > 0)}
              className={cn(
                "w-full text-white font-semibold py-2.5 rounded-xl text-xs flex items-center justify-center gap-2 shadow-sm transition",
                acceptedCount > 0
                  ? "bg-gradient-to-r from-purple-600 via-indigo-600 to-purple-700 hover:from-purple-700 hover:to-indigo-700 shadow-md ring-2 ring-purple-300 ring-offset-1"
                  : "bg-purple-600 hover:bg-purple-700 disabled:opacity-50"
              )}
            >
              {isApplying ? (
                <>
                  <div className="h-4 w-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  <span>Đang áp dụng thay đổi vào tài liệu...</span>
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4" />
                  <span>
                    Áp dụng vào tài liệu ({acceptedCount > 0 ? `${acceptedCount} thay đổi đã chọn` : "Chưa chọn đoạn nào"})
                  </span>
                </>
              )}
            </Button>
            {acceptedCount === 0 && operations.length > 0 && (
              <p className="text-[10px] text-center text-muted-foreground">
                Hãy bấm &quot;Đồng ý&quot; hoặc &quot;Áp dụng ngay&quot; tại từng đoạn, hoặc &quot;Chấp nhận & Áp dụng tất cả&quot; ở trên.
              </p>
            )}
          </div>
        ) : (
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2 text-xs text-emerald-800 font-semibold">
              <Check className="h-4 w-4 stroke-[2.5] text-emerald-600" />
              <span>Đã áp dụng thành công vào văn bản!</span>
            </div>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => onUndo(proposal.proposal_id)}
              disabled={isUndoing}
              className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1.5 h-8 border-gray-300"
            >
              <RotateCcw className="h-3 w-3" />
              <span>{isUndoing ? "Đang hoàn tác..." : "Hoàn tác (Undo)"}</span>
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}

export default DiffViewer;
