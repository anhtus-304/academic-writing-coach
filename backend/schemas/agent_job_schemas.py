"""Pydantic schemas for Agent Job API endpoints.

Defines request/response models for the canonical /agent-jobs/* API.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ── Shared sub-schemas ────────────────────────────────────────────────

class StagePlanItem(BaseModel):
    """A single stage in the execution plan returned by the Planner."""
    stage_id: str
    stage_type: str  # inspect_context | build_outline | research | extract_evidence | compose | validate | build_proposal
    description: str
    depends_on: List[str] = []
    estimated_credits: int = 0


class StageProgressItem(BaseModel):
    """Progress info for a single stage during/after execution."""
    stage_id: str
    stage_type: str
    order: int
    status: str  # pending | running | completed | failed | skipped
    tokens_used: int = 0
    credits_charged: int = 0
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class ProposalOperation(BaseModel):
    """A single diff operation within a proposal."""
    operation_id: str
    type: str  # replace | insert | delete | outline_patch | select_source
    start: Optional[int] = None
    end: Optional[int] = None
    before: Optional[str] = None
    after: Optional[str] = None
    source_refs: List[str] = []
    status: str = "pending"  # pending | accepted | rejected


class ProposalData(BaseModel):
    """Proposal with diff operations for human review."""
    proposal_id: str
    base_version: int
    base_hash: str
    target_type: str = "document"  # document | outline | selected_papers
    target_section_id: Optional[str] = None
    operations: List[ProposalOperation] = []
    warnings: List[str] = []
    status: str = "pending"
    tracked_html: Optional[str] = None
    summary: Optional[Dict[str, Any]] = None


class OperationDecision(BaseModel):
    """A single accept/reject decision on an operation."""
    operation_id: Optional[str] = None  # null = whole-proposal decision
    decision: str  # "accept" | "reject"
    reason: Optional[str] = None


# ── Create Job ────────────────────────────────────────────────────────

class CreateJobRequest(BaseModel):
    """POST /api/v1/agent-jobs"""
    project_id: str
    mode: str = Field(default="auto", pattern="^(ask|auto)$")
    prompt: str = Field(..., min_length=1, max_length=5000)

    # Optional context overrides
    target_section: Optional[str] = None
    requested_action: Optional[str] = None
    language: Optional[str] = "vi"
    citation_style: Optional[str] = None
    selection: Optional[str] = None  # Selected text in editor
    client_context_version: Optional[int] = None  # Client-side doc version for conflict check

    disclaimer_accepted: bool = False
    idempotency_key: Optional[str] = None


class CreateJobResponse(BaseModel):
    """Response for POST /api/v1/agent-jobs"""
    job_id: str
    status: str
    mode: str
    estimated_credits: int = 0
    plan: Optional[List[StagePlanItem]] = None
    result: Optional[Dict[str, Any]] = None  # Populated for ask mode (inline result)
    error: Optional[str] = None


# ── Get Job ───────────────────────────────────────────────────────────

class GetJobResponse(BaseModel):
    """Response for GET /api/v1/agent-jobs/{job_id}"""
    job_id: str
    project_id: str
    mode: str
    status: str
    prompt_summary: Optional[str] = None
    plan: Optional[List[StagePlanItem]] = None
    stages: List[StageProgressItem] = []
    proposals: List[ProposalData] = []
    estimated_credits: int = 0
    actual_credits: int = 0
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


# ── Cancel Job ────────────────────────────────────────────────────────

class CancelJobResponse(BaseModel):
    """Response for POST /api/v1/agent-jobs/{job_id}/cancel"""
    job_id: str
    status: str
    credits_refunded: int = 0


# ── Proposal Decisions ────────────────────────────────────────────────

class ProposalDecisionRequest(BaseModel):
    """POST /api/v1/agent-jobs/{job_id}/proposals/{proposal_id}/decisions"""
    decisions: List[OperationDecision] = []
    accept_all: bool = False
    reject_all: bool = False


class ProposalDecisionResponse(BaseModel):
    """Response for proposal decision endpoint."""
    proposal_id: str
    status: str
    operations: List[ProposalOperation] = []


# ── Apply Proposal ────────────────────────────────────────────────────

class ApplyProposalRequest(BaseModel):
    """POST /api/v1/agent-jobs/{job_id}/apply"""
    proposal_id: str
    accepted_operation_ids: List[str] = []  # Empty = apply all accepted
    base_version: int
    base_hash: str
    action: Optional[str] = "accept_all"  # "accept_all" | "reject_all" | "resolve_chunk" | "apply"
    target_operation_id: Optional[str] = None


class ApplyProposalResponse(BaseModel):
    """Response for apply endpoint."""
    success: bool
    new_version: int
    applied_operations: List[str] = []
    conflicts: List[Dict[str, Any]] = []
    undo_token: Optional[str] = None
    content: Optional[str] = None


# ── Undo ──────────────────────────────────────────────────────────────

class UndoRequest(BaseModel):
    """POST /api/v1/agent-jobs/{job_id}/undo"""
    proposal_id: str
    undo_token: Optional[str] = None


class UndoResponse(BaseModel):
    """Response for undo endpoint."""
    success: bool
    restored_version: int
    message: str = ""
