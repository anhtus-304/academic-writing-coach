"""OrchestratorService — central coordinator for agent job execution.

Manages the lifecycle of an agent job: loading plan, executing stages
sequentially via sub-agents, and producing a proposal for human review.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

try:
    from backend.database import AsyncSessionLocal
    from backend.models.user import User
    from backend.models.agent_job import AgentJob
    from backend.models.agent_job_stage import AgentJobStage
    from backend.models.selected_paper import SelectedPaper
    from backend.models.cached_paper import CachedPaper
    from backend.models.draft_document import DraftDocument
    from backend.agents.graph import outline_node, literature_node, citation_node
    from backend.agents.evidence_agent import evidence_agent
    from backend.agents.compose_agent import compose_agent
    from backend.agents.validate_agent import validate_agent
    from backend.services.planner_service import planner_service
    from backend.services.proposal_service import proposal_service
    from backend.services.credit_service import (
        deduct_checkpoint,
        refund_unspent,
        get_credit_balance,
    )
    from backend.services.ai_use_logger import ai_use_logger
    from backend.services.llm_service import llm_service
    from backend.config import settings
    import backend.services.project_service as project_service
except ImportError:
    from database import AsyncSessionLocal
    from models.user import User
    from models.agent_job import AgentJob
    from models.agent_job_stage import AgentJobStage
    from models.selected_paper import SelectedPaper
    from models.cached_paper import CachedPaper
    from models.draft_document import DraftDocument
    from agents.graph import outline_node, literature_node, citation_node
    from agents.evidence_agent import evidence_agent
    from agents.compose_agent import compose_agent
    from agents.validate_agent import validate_agent
    from services.planner_service import planner_service
    from services.proposal_service import proposal_service
    from services.credit_service import (
        deduct_checkpoint,
        refund_unspent,
        get_credit_balance,
    )
    from services.ai_use_logger import ai_use_logger
    from services.llm_service import llm_service
    from config import settings
    import services.project_service as project_service

logger = logging.getLogger(__name__)


# ── Stage cost mapping ────────────────────────────────────────────────

STAGE_CREDIT_MAP = {
    "inspect_context": 0,
    "build_outline": settings.AGENT_AUTO_CHECKPOINT_COST_OUTLINE,
    "research": settings.AGENT_AUTO_CHECKPOINT_COST_LITERATURE,
    "extract_evidence": 1,
    "compose": 2,
    "validate": settings.AGENT_AUTO_CHECKPOINT_COST_CITATION,
    "build_proposal": 0,
}


class OrchestratorService:
    """Coordinates agent job execution across multiple stages."""

    def __init__(self):
        self._running_tasks: Dict[str, asyncio.Task] = {}

    # ── Background Task Runner with Independent Session ────────────────

    async def start_job(self, job_id: str, user_id: str) -> None:
        """Entry point for executing a job in an isolated background asyncio task with its own DB session."""
        task = asyncio.current_task()
        if task:
            self._running_tasks[job_id] = task

        try:
            await self._run_job_isolated(job_id, user_id)
        except asyncio.CancelledError:
            logger.info("Job %s cancelled via asyncio task cancellation", job_id)
            await self._mark_job_cancelled_on_abort(job_id, user_id)
            raise
        finally:
            self._running_tasks.pop(job_id, None)

    async def _run_job_isolated(self, job_id: str, user_id: str) -> None:
        """Execute job inside a dedicated, isolated AsyncSession."""
        try:
            async with AsyncSessionLocal() as db:
                user = await db.get(User, user_id)
                if not user:
                    logger.error("User %s not found for job %s", user_id, job_id)
                    return
                await self.execute_job(job_id, db, user)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error("Fatal error running job %s: %s", job_id, e, exc_info=True)
            try:
                async with AsyncSessionLocal() as fail_db:
                    job = await fail_db.get(AgentJob, job_id)
                    if job and job.status in ("queued", "running"):
                        job.status = "failed"
                        job.error = f"Lỗi hệ thống: {e}"
                        job.completed_at = datetime.now(timezone.utc)
                        await fail_db.commit()
            except Exception as inner_e:
                logger.error("Failed to mark job as failed: %s", inner_e)

    async def _mark_job_cancelled_on_abort(self, job_id: str, user_id: str) -> None:
        """Safety cleanup when asyncio task is cancelled."""
        try:
            async with AsyncSessionLocal() as cancel_db:
                job = await cancel_db.get(
                    AgentJob,
                    job_id,
                    options=[selectinload(AgentJob.stages)],
                )
                if not job:
                    return
                if job.status != "cancelled":
                    user = await cancel_db.get(User, user_id)
                    estimated = job.estimated_credits or 0
                    actual = job.actual_credits or 0
                    refund_amount = max(0, estimated - actual)
                    if refund_amount > 0 and user:
                        await refund_unspent(
                            cancel_db, user, refund_amount, reason=f"Job cancelled: {job_id}"
                        )
                    job.status = "cancelled"
                    job.completed_at = datetime.now(timezone.utc)
                    job.error = "Cancelled by user"
                    for s in (job.stages or []):
                        if s.status in ("pending", "running"):
                            s.status = "skipped"
                    await cancel_db.commit()
        except Exception as e:
            logger.warning("Error during cancellation DB cleanup for job %s: %s", job_id, e)

    # ── Main execution loop ───────────────────────────────────────────

    async def execute_job(
        self,
        job_id: str,
        db: AsyncSession,
        user: Any,
    ) -> None:
        """Execute all stages of a job sequentially.

        Updates job and stage statuses in the database as execution proceeds.
        On failure, marks failed stage and refunds unspent credits.
        """
        job = await db.get(
            AgentJob,
            job_id,
            options=[selectinload(AgentJob.stages), selectinload(AgentJob.proposals)],
        )
        if not job:
            logger.error("Job %s not found", job_id)
            return

        total_charged = 0

        try:
            job.status = "running"
            job.started_at = datetime.now(timezone.utc)
            await db.commit()

            # Load stages
            stages = sorted(job.stages, key=lambda s: s.order)

            # Build initial agent state from context
            agent_state = await self._build_agent_state(db, job, user)

            for stage in stages:
                # Check if job was cancelled externally before running each stage
                await db.refresh(job)
                if job.status == "cancelled":
                    logger.info("Job %s was cancelled, stopping execution loop.", job_id)
                    return

                # Check dependencies
                if not self._dependencies_met(stage, stages):
                    stage.status = "skipped"
                    await db.commit()
                    continue

                stage.status = "running"
                stage.started_at = datetime.now(timezone.utc)
                await db.commit()

                # Deduct credits for this stage
                cost = STAGE_CREDIT_MAP.get(stage.stage_type, 1)
                if cost > 0:
                    deducted = await deduct_checkpoint(
                        db, user, f"Agent stage: {stage.stage_type}", cost
                    )
                    if not deducted:
                        stage.status = "failed"
                        stage.error = "Số dư không đủ"
                        job.status = "failed"
                        job.error = f"Số dư không đủ cho stage: {stage.stage_type}"
                        job.completed_at = datetime.now(timezone.utc)
                        await db.commit()
                        return

                    stage.credits_charged = cost
                    total_charged += cost

                # Execute stage with retry
                while stage.retry_count <= stage.max_retries:
                    try:
                        stage_output = await self._execute_stage(
                            stage.stage_type, agent_state, db, job
                        )

                        # Merge output into agent_state
                        if stage_output:
                            agent_state.update(stage_output)
                            stage.output_ref = {
                                "keys": list(stage_output.keys()),
                                "status": stage_output.get("status", "success"),
                            }

                        if stage_output and stage_output.get("status") == "failed":
                            raise RuntimeError(
                                stage_output.get("error", "Stage execution failed")
                            )

                        stage.status = "completed"
                        stage.tokens_used = stage_output.get("_tokens_used", 0) if stage_output else 0
                        stage.completed_at = datetime.now(timezone.utc)
                        break

                    except asyncio.CancelledError:
                        raise
                    except Exception as e:
                        stage.retry_count += 1
                        logger.warning(
                            "Stage %s failed in job %s (attempt %d/%d): %s",
                            stage.stage_type, job_id, stage.retry_count, stage.max_retries + 1, e,
                        )
                        if stage.retry_count > stage.max_retries:
                            stage.status = "failed"
                            stage.error = str(e)
                            job.status = "failed"
                            job.error = f"Stage {stage.stage_type} failed: {e}"
                            job.completed_at = datetime.now(timezone.utc)
                            await db.commit()
                            return
                        await asyncio.sleep(1.0)

                await db.commit()

            # All stages completed — build proposal if auto mode
            await db.refresh(job)
            if job.status == "cancelled":
                logger.info("Job %s was cancelled, skipping proposal generation.", job_id)
                return

            if job.mode == "auto":
                has_proposal = await self._build_and_save_proposal(db, job, agent_state)
                job.status = "awaiting_approval" if has_proposal else "completed"
            else:
                job.result = agent_state.get("result") or agent_state.get("ai_response")
                job.status = "completed"

            job.actual_credits = total_charged
            job.completed_at = datetime.now(timezone.utc)
            await db.commit()

        except asyncio.CancelledError:
            logger.info("execute_job for %s was cancelled.", job_id)
            raise
        except Exception as exc:
            logger.error("Job %s failed: %s", job_id, exc, exc_info=True)
            job.status = "failed"
            job.error = str(exc)
            job.completed_at = datetime.now(timezone.utc)

            # Refund unspent credits
            estimated = job.estimated_credits or 0
            unspent = estimated - total_charged
            if unspent > 0:
                await refund_unspent(
                    db, user, unspent, reason=f"Job failed: {exc}"
                )
            await db.commit()

        finally:
            # Safety check to ensure session is committed
            try:
                await db.commit()
            except Exception:
                pass

    # ── Build agent state from job context ────────────────────────────

    async def _build_agent_state(
        self,
        db: AsyncSession,
        job: AgentJob,
        user: Any,
    ) -> Dict[str, Any]:
        """Collect project, outline, draft, papers into agent state dict."""
        state: Dict[str, Any] = {
            "project_id": job.project_id,
            "user_id": job.user_id,
            "prompt": job.prompt,
            "mode": job.mode,
            "current_step": "init",
            "status": "running",
            "messages": [],
            "suggestions": [],
        }

        # Load project
        project = await project_service.get_project(db, job.project_id, job.user_id)
        if project:
            state["topic"] = project.topic
            state["document_type"] = project.document_type or "tieu_luan"
            state["field"] = project.field
            state["citation_style"] = project.citation_style or "apa7"

            # Load outline
            outline_rec = await project_service.get_project_outline(
                db, project.id, job.user_id
            )
            if outline_rec and outline_rec.chapters:
                state["outline"] = {
                    "title": outline_rec.title or project.topic,
                    "sections": outline_rec.chapters,
                }

            # Load draft
            doc_rec = await project_service.get_project_document(
                db, project.id, job.user_id
            )
            if doc_rec and doc_rec.content:
                if isinstance(doc_rec.content, dict):
                    state["draft_content"] = str(
                        doc_rec.content.get("html")
                        or doc_rec.content.get("text")
                        or ""
                    )
                else:
                    state["draft_content"] = str(doc_rec.content)

            # Load selected papers
            sel_stmt = (
                select(SelectedPaper)
                .options(selectinload(SelectedPaper.cached_paper))
                .where(SelectedPaper.project_id == project.id)
            )
            sel_res = await db.execute(sel_stmt)
            papers_payload = []
            for sp in sel_res.scalars().all():
                cp = sp.cached_paper
                if not cp and sp.cached_paper_id:
                    cp = await db.get(CachedPaper, sp.cached_paper_id)
                papers_payload.append({
                    "id": sp.id,
                    "cached_paper_id": sp.cached_paper_id,
                    "title": cp.title if cp else "Tài liệu",
                    "authors": cp.authors if cp else [],
                    "year": cp.year if cp else 2024,
                    "doi": cp.doi if cp else None,
                    "url": cp.url if cp else None,
                })
            state["selected_papers"] = papers_payload

        # Save context snapshot
        job.context_snapshot = {
            "topic": state.get("topic"),
            "has_outline": bool(state.get("outline")),
            "has_draft": bool(state.get("draft_content")),
            "papers_count": len(state.get("selected_papers", [])),
        }
        await db.commit()

        return state

    # ── Execute individual stage ──────────────────────────────────────

    async def _execute_stage(
        self,
        stage_type: str,
        state: Dict[str, Any],
        db: AsyncSession,
        job: AgentJob,
    ) -> Optional[Dict[str, Any]]:
        """Dispatch to appropriate agent/logic for a stage type."""

        if stage_type == "inspect_context":
            return await self._stage_inspect_context(state)

        elif stage_type == "build_outline":
            return await self._stage_build_outline(state, db, job)

        elif stage_type == "research":
            return await self._stage_research(state)

        elif stage_type == "extract_evidence":
            return await self._stage_extract_evidence(state)

        elif stage_type == "compose":
            return await self._stage_compose(state)

        elif stage_type == "validate":
            return await self._stage_validate(state)

        elif stage_type == "build_proposal":
            # Handled separately after all stages
            return {"status": "success"}

        else:
            logger.warning("Unknown stage type: %s", stage_type)
            return {"status": "skipped"}

    # ── Stage implementations ─────────────────────────────────────────

    async def _stage_inspect_context(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Read and summarise available context."""
        context_summary = {
            "topic": state.get("topic", "N/A"),
            "has_outline": bool(state.get("outline")),
            "has_draft": bool(state.get("draft_content")),
            "papers_count": len(state.get("selected_papers", [])),
            "draft_word_count": len(state.get("draft_content", "").split()),
        }
        return {
            "context_summary": context_summary,
            "current_step": "context_inspected",
            "status": "success",
        }

    async def _stage_build_outline(
        self, state: Dict[str, Any], db: AsyncSession, job: AgentJob
    ) -> Dict[str, Any]:
        """Generate or preserve outline using OutlineAgent."""
        result = await outline_node(state)

        # Sync to DB if new outline generated
        if result.get("status") == "success" and result.get("outline"):
            project = await project_service.get_project(db, job.project_id, job.user_id)
            if project:
                inner = result["outline"].get("outline") or result["outline"]
                chapters = inner.get("sections") or inner.get("chapters") or []
                await project_service.update_project_outline(
                    db=db,
                    project_id=project.id,
                    user_id=job.user_id,
                    chapters_data=chapters,
                    suggestions_data=result["outline"].get("suggestions"),
                )

        return result

    async def _stage_research(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Search and summarise literature using LiteratureAgent."""
        return await literature_node(state)

    async def _stage_extract_evidence(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Extract structured evidence from papers using EvidenceAgent."""
        papers = state.get("selected_papers", [])
        lit_results = state.get("literature_results", {})
        lit_papers = lit_results.get("papers", []) if isinstance(lit_results, dict) else []

        combined_papers = list(lit_papers) if lit_papers else list(papers)
        seen_ids = {str(p.get("id")) for p in combined_papers if isinstance(p, dict)}
        for sp in papers:
            if isinstance(sp, dict) and str(sp.get("id")) not in seen_ids:
                combined_papers.append(sp)

        input_data = {
            "selected_papers": combined_papers,
            "outline": state.get("outline", {}),
            "topic": state.get("topic", ""),
        }
        res = await evidence_agent.run(input_data)
        if res.get("status") == "success":
            state["evidence_bundle"] = res.get("evidence_bundle", [])
        return res

    async def _stage_compose(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Compose academic content based on outline + evidence using ComposeAgent."""
        input_data = {
            "section": state.get("outline", {}),
            "evidence_bundle": state.get("evidence_bundle", []),
            "citation_style": state.get("citation_style", "apa7"),
            "word_budget": state.get("word_budget", 400),
            "topic": state.get("topic", ""),
            "language": state.get("language", "vi"),
            "prompt": state.get("prompt", ""),
            "current_draft": state.get("draft_content", ""),
        }
        res = await compose_agent.run(input_data)
        if res.get("status") == "success":
            state["composed_content"] = res.get("composed_content", "")
            state["source_refs"] = res.get("source_refs", [])
            state["unverified_claims"] = res.get("unverified_claims", [])
        return res

    async def _stage_validate(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Validate composed content using ValidateAgent."""
        composed = state.get("composed_content", "")
        if not composed:
            return {
                "validation_result": {"status": "skipped", "message": "No content to validate"},
                "current_step": "validation_skipped",
                "status": "success",
            }

        input_data = {
            "composed_content": composed,
            "outline": state.get("outline", {}),
            "evidence_bundle": state.get("evidence_bundle", []),
            "citation_style": state.get("citation_style", "apa7"),
            "word_budget": state.get("word_budget", 400),
            "unverified_claims": state.get("unverified_claims", []),
        }
        res = await validate_agent.run(input_data)
        if res.get("status") == "success":
            state["validation_result"] = res.get("validation_report", {})
            state["warnings"] = res.get("warnings", [])
        return res

    # ── Build and save proposal ───────────────────────────────────────

    async def _build_and_save_proposal(
        self,
        db: AsyncSession,
        job: AgentJob,
        state: Dict[str, Any],
    ) -> bool:
        """Build a proposal from composed content and save to DB. Returns True if created."""
        composed = state.get("composed_content", "")
        if not composed:
            logger.info("No composed content, skipping proposal for job %s", job.id)
            return False

        current_content, current_version, current_hash = (
            await proposal_service.get_current_document(db, job.project_id)
        )

        # Build sources list from evidence
        evidence = state.get("evidence_bundle", [])
        source_refs = state.get("source_refs") or [
            str(ev.get("title") or ev.get("paper_id", ""))
            for ev in evidence
            if ev.get("paper_id") or ev.get("title")
        ]

        # Build warnings from validation
        warnings = list(state.get("warnings") or [])
        validation = state.get("validation_result", {})
        if isinstance(validation, dict):
            val_warnings = validation.get("warnings") or []
            for w in val_warnings:
                if w not in warnings:
                    warnings.append(w)

        proposal_data = await proposal_service.build_proposal_async(
            job_id=job.id,
            composed_content=composed,
            current_content=current_content,
            current_version=current_version,
            target_type="document",
            source_refs=source_refs,
            warnings=warnings,
        )

        await proposal_service.save_proposal(db, proposal_data)

        # Update DraftDocument with the tracked markup so editor shows it immediately
        tracked_html = proposal_data.get("tracked_html") or composed
        stmt = (
            select(DraftDocument)
            .where(DraftDocument.project_id == job.project_id)
            .order_by(desc(DraftDocument.version))
            .limit(1)
        )
        draft_res = await db.execute(stmt)
        draft = draft_res.scalar_one_or_none()
        if draft:
            draft.content = {"html": tracked_html}
        else:
            draft = DraftDocument(
                project_id=job.project_id,
                content={"html": tracked_html},
                version=current_version or 1,
            )
            db.add(draft)
        await db.commit()

        logger.info("Proposal saved and DraftDocument updated with tracked markup for job %s", job.id)
        return True

    # ── Check stage dependencies ──────────────────────────────────────

    def _dependencies_met(
        self,
        stage: AgentJobStage,
        all_stages: List[AgentJobStage],
    ) -> bool:
        """Check if all dependencies of a stage are completed."""
        if not stage.depends_on:
            return True

        dep_set = set(stage.depends_on)
        for s in all_stages:
            if (s.id in dep_set or s.stage_type in dep_set) and s.status != "completed":
                return False
        return True

    # ── Cancel job ────────────────────────────────────────────────────

    async def cancel_job(
        self,
        db: AsyncSession,
        job_id: str,
        user: Any,
    ) -> Dict[str, Any]:
        """Cancel a running or queued job and refund unspent credits."""
        job = await db.get(
            AgentJob,
            job_id,
            options=[selectinload(AgentJob.stages)],
        )
        if not job:
            raise ValueError("Job not found")

        if job.status in ("completed", "failed", "cancelled"):
            raise ValueError(f"Job already in terminal state: {job.status}")

        # Cancel running background task immediately if present
        running_task = self._running_tasks.get(job_id)
        if running_task and not running_task.done():
            logger.info("Cancelling active asyncio background task for job %s", job_id)
            running_task.cancel()

        # Calculate refund
        estimated = job.estimated_credits or 0
        actual = job.actual_credits or 0
        refund_amount = max(0, estimated - actual)

        if refund_amount > 0:
            await refund_unspent(
                db, user, refund_amount, reason=f"Job cancelled: {job_id}"
            )

        job.status = "cancelled"
        job.completed_at = datetime.now(timezone.utc)
        job.error = "Cancelled by user"

        # Mark pending stages as skipped
        for stage in job.stages:
            if stage.status in ("pending", "running"):
                stage.status = "skipped"

        await db.commit()

        return {
            "job_id": job_id,
            "status": "cancelled",
            "credits_refunded": refund_amount,
        }


orchestrator_service = OrchestratorService()
