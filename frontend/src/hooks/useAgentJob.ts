"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import {
  agentJobApi,
  type CreateJobPayload,
  type CreateJobResponse,
  type GetJobResponse,
  type ProposalData,
  type ProposalOperation,
  type ApplyProposalResponse,
  type UndoResponse,
} from "@/lib/api";

export interface UseAgentJobOptions {
  projectId?: string;
  onJobCompleted?: (job: GetJobResponse) => void;
  onProposalApplied?: (result: ApplyProposalResponse, proposal: ProposalData) => void;
  onProposalUndone?: (result: UndoResponse, proposal: ProposalData) => void;
}

export function useAgentJob({
  projectId,
  onJobCompleted,
  onProposalApplied,
  onProposalUndone,
}: UseAgentJobOptions = {}) {
  const [job, setJob] = useState<GetJobResponse | null>(null);
  const [activeProposal, setActiveProposal] = useState<ProposalData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isPolling, setIsPolling] = useState(false);
  const [isApplying, setIsApplying] = useState(false);
  const [isUndoing, setIsUndoing] = useState(false);
  const [isDeciding, setIsDeciding] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUndoToken, setLastUndoToken] = useState<string | null>(null);

  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const onJobCompletedRef = useRef(onJobCompleted);
  const onProposalAppliedRef = useRef(onProposalApplied);
  const onProposalUndoneRef = useRef(onProposalUndone);

  useEffect(() => {
    onJobCompletedRef.current = onJobCompleted;
    onProposalAppliedRef.current = onProposalApplied;
    onProposalUndoneRef.current = onProposalUndone;
  }, [onJobCompleted, onProposalApplied, onProposalUndone]);

  // Clear polling on unmount
  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    };
  }, []);

  // Update active proposal when job changes
  useEffect(() => {
    if (job && job.proposals && job.proposals.length > 0) {
      // Pick first pending or applying proposal, or the first one
      const pending = job.proposals.find((p) => p.status === "pending" || p.status === "partially_accepted");
      setActiveProposal(pending || job.proposals[0]);
    } else {
      setActiveProposal(null);
    }
  }, [job]);

  // Polling loop (stable reference with useRef callbacks)
  const startPolling = useCallback((jobId: string) => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
    setIsPolling(true);

    const checkJob = async () => {
      try {
        const jobData = await agentJobApi.getJob(jobId);
        setJob(jobData);

        // Terminal statuses
        if (
          jobData.status === "awaiting_approval" ||
          jobData.status === "completed" ||
          jobData.status === "failed" ||
          jobData.status === "cancelled"
        ) {
          if (pollIntervalRef.current) {
            clearInterval(pollIntervalRef.current);
            pollIntervalRef.current = null;
          }
          setIsPolling(false);

          if (jobData.status === "completed" || jobData.status === "awaiting_approval") {
            onJobCompletedRef.current?.(jobData);
          }
          if (jobData.error) {
            setError(jobData.error);
          }
        }
      } catch (err: unknown) {
        console.error("Polling job error:", err);
      }
    };

    checkJob();
    pollIntervalRef.current = setInterval(checkJob, 2000);
  }, []);

  // Job recovery on page refresh / project load
  useEffect(() => {
    if (!projectId) return;

    let isMounted = true;
    agentJobApi
      .getActiveJob(projectId)
      .then((activeJob) => {
        if (!isMounted || !activeJob) return;
        setJob(activeJob);
        if (activeJob.status === "running" || activeJob.status === "queued") {
          startPolling(activeJob.job_id);
        }
      })
      .catch((err) => {
        console.debug("No active agent job recovered:", err);
      });

    return () => {
      isMounted = false;
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    };
  }, [projectId, startPolling]);

  // Create Job
  const createJob = useCallback(
    async (params: {
      prompt: string;
      mode?: "ask" | "auto";
      selection?: string;
      targetSection?: string;
      requestedAction?: string;
      disclaimerAccepted?: boolean;
      clientContextVersion?: number;
    }): Promise<CreateJobResponse | null> => {
      if (!projectId) {
        setError("Chưa chọn đề tài nghiên cứu (Project ID thiếu).");
        return null;
      }

      setIsLoading(true);
      setError(null);

      try {
        const payload: CreateJobPayload = {
          project_id: projectId,
          mode: params.mode || "auto",
          prompt: params.prompt,
          selection: params.selection,
          target_section: params.targetSection,
          requested_action: params.requestedAction,
          disclaimer_accepted: params.disclaimerAccepted ?? false,
          client_context_version: params.clientContextVersion,
        };

        const res = await agentJobApi.createJob(payload);

        if (res.mode === "ask") {
          // Inline response already in res
          // Fetch full job data once to hydrate
          const fullJob = await agentJobApi.getJob(res.job_id);
          setJob(fullJob);
          setIsLoading(false);
          return res;
        }

        // Auto mode -> start polling
        startPolling(res.job_id);
        setIsLoading(false);
        return res;
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : "Không thể khởi tạo Agent Job.";
        setError(message);
        setIsLoading(false);
        return null;
      }
    },
    [projectId, startPolling]
  );

  // Cancel Job
  const cancelJob = useCallback(async () => {
    if (!job?.job_id) return;
    try {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
      setIsPolling(false);
      const res = await agentJobApi.cancelJob(job.job_id);
      setJob((prev) => (prev ? { ...prev, status: "cancelled" } : null));
      return res;
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Lỗi khi hủy Job.";
      setError(message);
    }
  }, [job?.job_id]);

  // Submit decisions on individual operations
  const decideOperation = useCallback(
    async (proposalId: string, operationId: string, decision: "accept" | "reject", reason?: string) => {
      if (!job?.job_id) return;
      setIsDeciding(true);
      try {
        const res = await agentJobApi.submitDecisions(job.job_id, proposalId, {
          decisions: [{ operation_id: operationId, decision, reason }],
        });

        // Update local activeProposal and job proposals
        setActiveProposal((prev) =>
          prev && prev.proposal_id === proposalId
            ? { ...prev, status: res.status as ProposalData["status"], operations: res.operations }
            : prev
        );
        setJob((prev) => {
          if (!prev) return null;
          return {
            ...prev,
            proposals: prev.proposals.map((p) =>
              p.proposal_id === proposalId
                ? { ...p, status: res.status as ProposalData["status"], operations: res.operations }
                : p
            ),
          };
        });
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : "Lỗi khi lưu quyết định.";
        setError(message);
      } finally {
        setIsDeciding(false);
      }
    },
    [job?.job_id]
  );

  // Accept all operations in proposal
  const acceptAll = useCallback(
    async (proposalId: string) => {
      if (!job?.job_id) return;
      setIsDeciding(true);
      try {
        const res = await agentJobApi.submitDecisions(job.job_id, proposalId, {
          accept_all: true,
        });
        setActiveProposal((prev) =>
          prev && prev.proposal_id === proposalId
            ? { ...prev, status: res.status as ProposalData["status"], operations: res.operations }
            : prev
        );
        setJob((prev) => {
          if (!prev) return null;
          return {
            ...prev,
            proposals: prev.proposals.map((p) =>
              p.proposal_id === proposalId
                ? { ...p, status: res.status as ProposalData["status"], operations: res.operations }
                : p
            ),
          };
        });
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : "Lỗi khi chấp nhận toàn bộ.";
        setError(message);
      } finally {
        setIsDeciding(false);
      }
    },
    [job?.job_id]
  );

  // Reject all operations in proposal
  const rejectAll = useCallback(
    async (proposalId: string) => {
      if (!job?.job_id) return;
      setIsDeciding(true);
      try {
        const res = await agentJobApi.submitDecisions(job.job_id, proposalId, {
          reject_all: true,
        });
        setActiveProposal((prev) =>
          prev && prev.proposal_id === proposalId
            ? { ...prev, status: res.status as ProposalData["status"], operations: res.operations }
            : prev
        );
        setJob((prev) => {
          if (!prev) return null;
          return {
            ...prev,
            proposals: prev.proposals.map((p) =>
              p.proposal_id === proposalId
                ? { ...p, status: res.status as ProposalData["status"], operations: res.operations }
                : p
            ),
          };
        });
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : "Lỗi khi bỏ qua toàn bộ.";
        setError(message);
      } finally {
        setIsDeciding(false);
      }
    },
    [job?.job_id]
  );

  // Apply proposal
  const applyProposal = useCallback(
    async (
      proposalId: string,
      optionsOrIds?: string[] | {
        acceptedOperationIds?: string[];
        action?: "accept_all" | "reject_all" | "resolve_chunk" | "apply";
        targetOperationId?: string;
      }
    ) => {
      if (!job?.job_id) return;
      const targetProposal = job.proposals.find((p) => p.proposal_id === proposalId) || activeProposal;
      if (!targetProposal) {
        setError("Không tìm thấy đề xuất (Proposal).");
        return;
      }

      setIsApplying(true);
      setError(null);

      try {
        let acceptedOperationIds: string[] | undefined;
        let action: "accept_all" | "reject_all" | "resolve_chunk" | "apply" = "apply";
        let targetOperationId: string | undefined;

        if (Array.isArray(optionsOrIds)) {
          acceptedOperationIds = optionsOrIds;
        } else if (optionsOrIds && typeof optionsOrIds === "object") {
          acceptedOperationIds = optionsOrIds.acceptedOperationIds;
          action = optionsOrIds.action || "apply";
          targetOperationId = optionsOrIds.targetOperationId;
        }

        const opsToUse = (acceptedOperationIds && acceptedOperationIds.length > 0)
          ? acceptedOperationIds
          : (targetProposal.operations || [])
              .filter((op) => op.status === "accepted")
              .map((op) => op.operation_id);

        const res = await agentJobApi.applyProposal(job.job_id, {
          proposal_id: proposalId,
          accepted_operation_ids: opsToUse,
          base_version: targetProposal.base_version,
          base_hash: targetProposal.base_hash,
          action,
          target_operation_id: targetOperationId,
        });

        if (res.success) {
          setLastUndoToken(res.undo_token || null);
          const nextStatus = action === "reject_all" ? "rejected" : "applied";
          setActiveProposal((prev) =>
            prev && prev.proposal_id === proposalId ? { ...prev, status: nextStatus } : prev
          );
          setJob((prev) => {
            if (!prev) return null;
            return {
              ...prev,
              status: "completed",
              proposals: prev.proposals.map((p) =>
                p.proposal_id === proposalId ? { ...p, status: nextStatus } : p
              ),
            };
          });
          onProposalAppliedRef.current?.(res, targetProposal);
        } else if (res.conflicts && res.conflicts.length > 0) {
          setError("Xung đột phiên bản: Nội dung tài liệu đã thay đổi kể từ khi tạo đề xuất này.");
        }
        return res;
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : "Lỗi khi áp dụng đề xuất vào tài liệu.";
        setError(message);
      } finally {
        setIsApplying(false);
      }
    },
    [job, activeProposal]
  );

  // Undo proposal
  const undoProposal = useCallback(
    async (proposalId: string) => {
      if (!job?.job_id) return;
      const targetProposal = job.proposals.find((p) => p.proposal_id === proposalId) || activeProposal;
      if (!targetProposal) return;

      setIsUndoing(true);
      setError(null);

      try {
        const res = await agentJobApi.undoProposal(job.job_id, {
          proposal_id: proposalId,
          undo_token: lastUndoToken,
        });

        if (res.success) {
          setLastUndoToken(null);
          setActiveProposal((prev) =>
            prev && prev.proposal_id === proposalId ? { ...prev, status: "pending" } : prev
          );
          setJob((prev) => {
            if (!prev) return null;
            return {
              ...prev,
              proposals: prev.proposals.map((p) =>
                p.proposal_id === proposalId ? { ...p, status: "pending" } : p
              ),
            };
          });
          onProposalUndoneRef.current?.(res, targetProposal);
        }
        return res;
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : "Lỗi khi hoàn tác đề xuất.";
        setError(message);
      } finally {
        setIsUndoing(false);
      }
    },
    [job, activeProposal, lastUndoToken]
  );

  // Reset state
  const resetJob = useCallback(() => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
    setJob(null);
    setActiveProposal(null);
    setError(null);
    setIsLoading(false);
    setIsPolling(false);
    setLastUndoToken(null);
  }, []);

  return {
    job,
    activeProposal,
    isLoading,
    isPolling,
    isApplying,
    isUndoing,
    isDeciding,
    error,
    lastUndoToken,
    createJob,
    cancelJob,
    decideOperation,
    acceptAll,
    rejectAll,
    applyProposal,
    undoProposal,
    resetJob,
    setActiveProposal,
  };
}
