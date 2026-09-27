"""ProposalService — build diff proposals and handle apply/undo logic.

Computes text diffs between current document and composed content,
manages version tracking, conflict detection via content hash,
and apply/undo operations on document versions.
"""

import asyncio
import difflib
import hashlib
import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

try:
    from backend.models.agent_proposal import AgentProposal
    from backend.models.agent_decision import AgentDecision
    from backend.models.document_version import DocumentVersion
    from backend.models.draft_document import DraftDocument
except ImportError:
    from models.agent_proposal import AgentProposal
    from models.agent_decision import AgentDecision
    from models.document_version import DocumentVersion
    from models.draft_document import DraftDocument

logger = logging.getLogger(__name__)


def _content_hash(content: Any) -> str:
    """SHA-256 hex digest of JSON-serialised content."""
    raw = json.dumps(content, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _word_count(text: str) -> int:
    """Approximate word count."""
    return len(text.split())


class ProposalService:
    """Builds diff-based proposals and handles apply/undo."""

    # ── Build proposal ────────────────────────────────────────────────

    async def build_proposal_async(
        self,
        job_id: str,
        composed_content: str,
        current_content: str,
        current_version: int,
        target_type: str = "document",
        target_section_id: Optional[str] = None,
        source_refs: Optional[List[str]] = None,
        warnings: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Compute diff operations and proposal structure in a worker thread to prevent event loop blocking."""
        return await asyncio.to_thread(
            self.build_proposal,
            job_id=job_id,
            composed_content=composed_content,
            current_content=current_content,
            current_version=current_version,
            target_type=target_type,
            target_section_id=target_section_id,
            source_refs=source_refs,
            warnings=warnings,
        )

    def build_proposal(
        self,
        job_id: str,
        composed_content: str,
        current_content: str,
        current_version: int,
        target_type: str = "document",
        target_section_id: Optional[str] = None,
        source_refs: Optional[List[str]] = None,
        warnings: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Create a proposal dict with diff operations and inline tracked HTML."""
        base_hash = _content_hash(current_content)
        tracked_html, operations = self.generate_tracked_html(
            before=current_content,
            after=composed_content,
            source_refs=source_refs or [],
        )

        # Summary metadata for executive summary card
        summary = {
            "composed_words": _word_count(composed_content),
            "operations_count": len(operations),
            "sources_count": len(source_refs or []),
            "source_refs": source_refs or [],
            "warnings_count": len(warnings or []),
        }

        return {
            "proposal_id": str(uuid.uuid4()),
            "job_id": job_id,
            "base_version": current_version,
            "base_hash": base_hash,
            "target_type": target_type,
            "target_section_id": target_section_id,
            "operations": operations,
            "tracked_html": tracked_html,
            "summary": summary,
            "warnings": warnings or [],
            "status": "pending",
        }

    def _split_html_into_blocks(self, html: str) -> List[str]:
        """Split HTML string into structural blocks (headings, paragraphs, lists, etc)."""
        if not html:
            return []
        pattern = r"(<h[1-6][^>]*>.*?</h[1-6]>|<p[^>]*>.*?</p>|<ul[^>]*>.*?</ul>|<ol[^>]*>.*?</ol>|<blockquote[^>]*>.*?</blockquote>|<table[^>]*>.*?</table>)"
        raw = re.split(pattern, html, flags=re.DOTALL | re.IGNORECASE)
        blocks = [b.strip() for b in raw if b.strip()]
        if not blocks:
            blocks = [b.strip() for b in html.split("\n\n") if b.strip()]
        return blocks

    def _wrap_in_ins(self, block: str, op_id: str) -> str:
        """Wrap inner content in <ins> track-changes tag."""
        m = re.match(r"^(<(h[1-6]|p|li|blockquote)[^>]*>)(.*?)(</\2>)$", block, re.DOTALL | re.IGNORECASE)
        if m:
            open_tag, tag_name, inner, close_tag = m.groups()
            return f'{open_tag}<ins class="diff-ins bg-emerald-50 text-emerald-950 border-b-2 border-emerald-500 rounded-xs px-0.5" data-op-id="{op_id}">{inner}</ins>{close_tag}'
        return f'<p><ins class="diff-ins bg-emerald-50 text-emerald-950 border-b-2 border-emerald-500 rounded-xs px-0.5" data-op-id="{op_id}">{block}</ins></p>'

    def _wrap_in_del(self, block: str, op_id: str) -> str:
        """Wrap inner content in <del> track-changes tag."""
        m = re.match(r"^(<(h[1-6]|p|li|blockquote)[^>]*>)(.*?)(</\2>)$", block, re.DOTALL | re.IGNORECASE)
        if m:
            open_tag, tag_name, inner, close_tag = m.groups()
            return f'{open_tag}<del class="diff-del bg-red-50 text-red-900 line-through opacity-75 border-b-2 border-red-500 rounded-xs px-0.5" data-op-id="{op_id}">{inner}</del>{close_tag}'
        return f'<p><del class="diff-del bg-red-50 text-red-900 line-through opacity-75 border-b-2 border-red-500 rounded-xs px-0.5" data-op-id="{op_id}">{block}</del></p>'

    def generate_tracked_html(
        self,
        before: str,
        after: str,
        source_refs: Optional[List[str]] = None,
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """Generate tracked HTML with <ins> and <del> tags and return list of diff operations."""
        if not before and not after:
            return "", []

        before_blocks = self._split_html_into_blocks(before)
        after_blocks = self._split_html_into_blocks(after)

        if not before_blocks and after_blocks:
            # Pure insert: all blocks are newly added
            tracked_parts = []
            operations = []
            for blk in after_blocks:
                op_id = str(uuid.uuid4())
                tracked_parts.append(self._wrap_in_ins(blk, op_id))
                operations.append({
                    "operation_id": op_id,
                    "type": "insert",
                    "start": 0,
                    "end": 0,
                    "before": "",
                    "after": blk,
                    "source_refs": source_refs or [],
                    "status": "pending",
                })
            return "".join(tracked_parts), operations

        if before_blocks and not after_blocks:
            # Pure delete
            tracked_parts = []
            operations = []
            for blk in before_blocks:
                op_id = str(uuid.uuid4())
                tracked_parts.append(self._wrap_in_del(blk, op_id))
                operations.append({
                    "operation_id": op_id,
                    "type": "delete",
                    "start": 0,
                    "end": len(blk),
                    "before": blk,
                    "after": "",
                    "source_refs": [],
                    "status": "pending",
                })
            return "".join(tracked_parts), operations

        matcher = difflib.SequenceMatcher(None, before_blocks, after_blocks)
        tracked_parts = []
        operations = []

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                for k in range(i1, i2):
                    tracked_parts.append(before_blocks[k])
            elif tag == "delete":
                for k in range(i1, i2):
                    op_id = str(uuid.uuid4())
                    b_blk = before_blocks[k]
                    tracked_parts.append(self._wrap_in_del(b_blk, op_id))
                    operations.append({
                        "operation_id": op_id,
                        "type": "delete",
                        "start": 0,
                        "end": len(b_blk),
                        "before": b_blk,
                        "after": "",
                        "source_refs": [],
                        "status": "pending",
                    })
            elif tag == "insert":
                for k in range(j1, j2):
                    op_id = str(uuid.uuid4())
                    a_blk = after_blocks[k]
                    tracked_parts.append(self._wrap_in_ins(a_blk, op_id))
                    operations.append({
                        "operation_id": op_id,
                        "type": "insert",
                        "start": 0,
                        "end": 0,
                        "before": "",
                        "after": a_blk,
                        "source_refs": source_refs or [],
                        "status": "pending",
                    })
            elif tag == "replace":
                for k in range(i1, i2):
                    op_id = str(uuid.uuid4())
                    b_blk = before_blocks[k]
                    tracked_parts.append(self._wrap_in_del(b_blk, op_id))
                    operations.append({
                        "operation_id": op_id,
                        "type": "delete",
                        "start": 0,
                        "end": len(b_blk),
                        "before": b_blk,
                        "after": "",
                        "source_refs": [],
                        "status": "pending",
                    })
                for k in range(j1, j2):
                    op_id = str(uuid.uuid4())
                    a_blk = after_blocks[k]
                    tracked_parts.append(self._wrap_in_ins(a_blk, op_id))
                    operations.append({
                        "operation_id": op_id,
                        "type": "insert",
                        "start": 0,
                        "end": 0,
                        "before": "",
                        "after": a_blk,
                        "source_refs": source_refs or [],
                        "status": "pending",
                    })

        return "".join(tracked_parts), operations

    def clean_tracked_html(
        self,
        html: str,
        action: str = "accept_all",
        op_id: Optional[str] = None,
    ) -> str:
        """Clean tracked HTML:
        - accept_all: remove <del> tags, unwrap <ins> tags to clean text.
        - reject_all: remove <ins> tags, unwrap <del> tags to restore original.
        - resolve_chunk: accept or reject a specific op_id.
        """
        if not html:
            return ""

        if action == "accept_all":
            cleaned = re.sub(r"<del\b[^>]*>.*?</del>", "", html, flags=re.DOTALL | re.IGNORECASE)
            cleaned = re.sub(r"</?ins\b[^>]*>", "", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"<p\b[^>]*>\s*</p>", "", cleaned, flags=re.IGNORECASE)
            return cleaned.strip()

        elif action == "reject_all":
            cleaned = re.sub(r"<ins\b[^>]*>.*?</ins>", "", html, flags=re.DOTALL | re.IGNORECASE)
            cleaned = re.sub(r"</?del\b[^>]*>", "", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"<p\b[^>]*>\s*</p>", "", cleaned, flags=re.IGNORECASE)
            return cleaned.strip()

        elif op_id:
            if action == "accept":
                cleaned = re.sub(rf'<del\b[^>]*data-op-id="{re.escape(op_id)}"[^>]*>.*?</del>', "", html, flags=re.DOTALL | re.IGNORECASE)
                cleaned = re.sub(rf'<ins\b[^>]*data-op-id="{re.escape(op_id)}"[^>]*>(.*?)</ins>', r"\1", html, flags=re.DOTALL | re.IGNORECASE)
                return cleaned.strip()
            elif action == "reject":
                cleaned = re.sub(rf'<ins\b[^>]*data-op-id="{re.escape(op_id)}"[^>]*>.*?</ins>', "", html, flags=re.DOTALL | re.IGNORECASE)
                cleaned = re.sub(rf'<del\b[^>]*data-op-id="{re.escape(op_id)}"[^>]*>(.*?)</del>', r"\1", html, flags=re.DOTALL | re.IGNORECASE)
                return cleaned.strip()

        return html.strip()

    def _apply_single_op(self, content: str, op: Dict[str, Any]) -> str:
        """Apply a single diff operation to content string."""
        op_type = op.get("type", "replace")
        start = op.get("start", 0)
        end = op.get("end", 0)
        after = op.get("after", "")
        before = op.get("before", "")

        if op_type == "insert":
            if not content:
                return after
            return content + "\n\n" + after
        elif op_type == "delete":
            if before and before in content:
                return content.replace(before, "", 1)
            return content[:start] + content[end:]
        elif op_type == "replace":
            if before and before in content:
                return content.replace(before, after, 1)
            return content[:start] + after + content[end:]
        return content

    # ── Persist proposal ──────────────────────────────────────────────

    async def save_proposal(
        self,
        db: AsyncSession,
        proposal_data: Dict[str, Any],
    ) -> AgentProposal:
        """Persist a proposal to the database."""
        proposal = AgentProposal(
            id=proposal_data.get("proposal_id") or str(uuid.uuid4()),
            job_id=proposal_data["job_id"],
            base_version=proposal_data["base_version"],
            base_hash=proposal_data["base_hash"],
            target_type=proposal_data["target_type"],
            target_section_id=proposal_data.get("target_section_id"),
            operations=proposal_data["operations"],
            tracked_html=proposal_data.get("tracked_html"),
            summary=proposal_data.get("summary"),
            warnings=proposal_data.get("warnings"),
            status="pending",
        )
        db.add(proposal)
        await db.commit()
        await db.refresh(proposal)
        return proposal

    # ── Record decisions ──────────────────────────────────────────────

    async def record_decisions(
        self,
        db: AsyncSession,
        proposal_id: str,
        user_id: str,
        decisions: List[Dict[str, Any]],
        accept_all: bool = False,
        reject_all: bool = False,
    ) -> AgentProposal:
        """Record user decisions on proposal operations."""
        proposal = await db.get(AgentProposal, proposal_id)
        if not proposal:
            raise ValueError(f"Proposal {proposal_id} not found")

        operations = list(proposal.operations)

        if accept_all:
            for op in operations:
                op["status"] = "accepted"
            decision_record = AgentDecision(
                proposal_id=proposal_id,
                operation_id=None,
                decision="accept",
                actor_user_id=user_id,
            )
            db.add(decision_record)
        elif reject_all:
            for op in operations:
                op["status"] = "rejected"
            decision_record = AgentDecision(
                proposal_id=proposal_id,
                operation_id=None,
                decision="reject",
                actor_user_id=user_id,
            )
            db.add(decision_record)
        else:
            for d in decisions:
                op_id = d.get("operation_id")
                decision_val = d.get("decision", "reject")
                for op in operations:
                    if op.get("operation_id") == op_id:
                        op["status"] = "accepted" if decision_val == "accept" else "rejected"
                        break
                decision_record = AgentDecision(
                    proposal_id=proposal_id,
                    operation_id=op_id,
                    decision=decision_val,
                    actor_user_id=user_id,
                    reason=d.get("reason"),
                )
                db.add(decision_record)

        proposal.operations = operations
        flag_modified(proposal, "operations")
        proposal.decided_at = datetime.now(timezone.utc)

        # Determine overall status
        statuses = {op["status"] for op in operations}
        if statuses == {"accepted"}:
            proposal.status = "accepted"
        elif statuses == {"rejected"}:
            proposal.status = "rejected"
        elif "accepted" in statuses:
            proposal.status = "partially_accepted"

        await db.commit()
        await db.refresh(proposal)
        return proposal

    # ── Apply proposal ────────────────────────────────────────────────

    async def apply_proposal(
        self,
        db: AsyncSession,
        project_id: str,
        proposal_id: str,
        accepted_operation_ids: Optional[List[str]] = None,
        base_version: int = 0,
        base_hash: str = "",
        action: str = "accept_all",
        target_operation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Apply accepted operations or resolve inline track-changes.

        Supports:
        - action="accept_all": removes <del> and unwraps <ins> into clean text
        - action="reject_all": removes <ins> and restores <del> back to original
        - action="resolve_chunk": resolves a specific op_id
        """
        proposal = await db.get(AgentProposal, proposal_id)
        if not proposal:
            raise ValueError(f"Proposal {proposal_id} not found")

        # Get current document
        stmt = (
            select(DraftDocument)
            .where(DraftDocument.project_id == project_id)
            .order_by(desc(DraftDocument.version))
            .limit(1)
        )
        result = await db.execute(stmt)
        draft = result.scalar_one_or_none()

        current_content = ""
        current_version = 0
        if draft:
            if isinstance(draft.content, dict):
                current_content = str(draft.content.get("html") or draft.content.get("text") or "")
            else:
                current_content = str(draft.content) if draft.content else ""
            current_version = draft.version or 1

        # Check if document currently contains inline track changes
        is_tracked_markup = bool(re.search(r"<(?:ins|del)\b[^>]*class=[\"'][^\"']*diff-(?:ins|del)", current_content, re.IGNORECASE))

        # Handle Action: Reject All
        if action == "reject_all":
            if is_tracked_markup:
                restored_content = self.clean_tracked_html(current_content, action="reject_all")
            else:
                restored_content = current_content

            if draft:
                draft.content = {"html": restored_content}
                draft.word_count = _word_count(restored_content)

            proposal.status = "rejected"
            proposal.applied_at = datetime.now(timezone.utc)
            for op in (proposal.operations or []):
                op["status"] = "rejected"
            flag_modified(proposal, "operations")
            await db.commit()

            return {
                "success": True,
                "new_version": current_version,
                "applied_operations": [],
                "conflicts": [],
                "undo_token": None,
                "content": restored_content,
                "status": "rejected",
            }

        # Handle Action: Accept All (only if no specific operations are filtered)
        if (action == "accept_all" and not accepted_operation_ids) or (is_tracked_markup and not accepted_operation_ids and action != "reject_all"):
            if is_tracked_markup:
                clean_content = self.clean_tracked_html(current_content, action="accept_all")
            else:
                # Fallback to standard diff merge if not already markup
                ops = proposal.operations or []
                clean_content = current_content
                for op in ops:
                    clean_content = self._apply_single_op(clean_content, op)

            new_version = current_version + 1
            new_hash = _content_hash(clean_content)
            undo_token = str(uuid.uuid4())

            doc_version = DocumentVersion(
                project_id=project_id,
                version=new_version,
                content={"html": clean_content},
                content_hash=new_hash,
                word_count=_word_count(clean_content),
                source_job_id=proposal.job_id,
                source_proposal_id=proposal_id,
                created_by="agent",
            )
            db.add(doc_version)

            if draft:
                draft.content = {"html": clean_content}
                draft.word_count = _word_count(clean_content)
                draft.version = new_version
            else:
                draft = DraftDocument(
                    project_id=project_id,
                    content={"html": clean_content},
                    word_count=_word_count(clean_content),
                    version=new_version,
                )
                db.add(draft)

            proposal.status = "applied"
            proposal.applied_at = datetime.now(timezone.utc)
            for op in (proposal.operations or []):
                op["status"] = "accepted"
            flag_modified(proposal, "operations")
            await db.commit()

            applied_ids = [op.get("operation_id") for op in (proposal.operations or []) if op.get("operation_id")]

            return {
                "success": True,
                "new_version": new_version,
                "applied_operations": applied_ids,
                "conflicts": [],
                "undo_token": undo_token,
                "content": clean_content,
                "status": "applied",
            }

        # Handle Single Chunk Resolve or Partial Operations Apply
        if action == "resolve_chunk" and target_operation_id:
            sub_action = "accept" if (not accepted_operation_ids or target_operation_id in accepted_operation_ids) else "reject"
            clean_content = self.clean_tracked_html(current_content, action=sub_action, op_id=target_operation_id)
            if draft:
                draft.content = {"html": clean_content}
                draft.word_count = _word_count(clean_content)

            for op in (proposal.operations or []):
                if op.get("operation_id") == target_operation_id:
                    op["status"] = "accepted" if sub_action == "accept" else "rejected"
            flag_modified(proposal, "operations")
            await db.commit()

            return {
                "success": True,
                "new_version": current_version,
                "applied_operations": [target_operation_id],
                "conflicts": [],
                "undo_token": None,
                "content": clean_content,
            }

        # Standard Fallback apply with ops list
        ops = proposal.operations or []
        accepted_set = set(accepted_operation_ids or [])
        ops_to_apply = [
            op for op in ops
            if (accepted_set and op.get("operation_id") in accepted_set)
            or (not accepted_set and op.get("status") == "accepted")
        ]
        if not ops_to_apply:
            ops_to_apply = list(ops)

        modified_content = current_content
        applied_ids = []
        for op in ops_to_apply:
            modified_content = self._apply_single_op(modified_content, op)
            applied_ids.append(op["operation_id"])
            op["status"] = "accepted"

        new_version = current_version + 1
        new_hash = _content_hash(modified_content)
        undo_token = str(uuid.uuid4())

        doc_version = DocumentVersion(
            project_id=project_id,
            version=new_version,
            content={"html": modified_content},
            content_hash=new_hash,
            word_count=_word_count(modified_content),
            source_job_id=proposal.job_id,
            source_proposal_id=proposal_id,
            created_by="agent",
        )
        db.add(doc_version)

        if draft:
            draft.content = {"html": modified_content}
            draft.word_count = _word_count(modified_content)
            draft.version = new_version
        else:
            draft = DraftDocument(
                project_id=project_id,
                content={"html": modified_content},
                word_count=_word_count(modified_content),
                version=new_version,
            )
            db.add(draft)

        proposal.status = "applied"
        proposal.applied_at = datetime.now(timezone.utc)
        flag_modified(proposal, "operations")
        await db.commit()

        return {
            "success": True,
            "new_version": new_version,
            "applied_operations": applied_ids,
            "conflicts": [],
            "undo_token": undo_token,
            "content": modified_content,
        }

    # ── Undo proposal ─────────────────────────────────────────────────

    async def undo_proposal(
        self,
        db: AsyncSession,
        project_id: str,
        proposal_id: str,
    ) -> Dict[str, Any]:
        """Undo an applied proposal by restoring the previous version."""
        proposal = await db.get(AgentProposal, proposal_id)
        if not proposal or proposal.status != "applied":
            raise ValueError("Proposal not found or not applied")

        # Find the version created by this proposal
        stmt = (
            select(DocumentVersion)
            .where(
                DocumentVersion.project_id == project_id,
                DocumentVersion.source_proposal_id == proposal_id,
            )
            .order_by(desc(DocumentVersion.version))
            .limit(1)
        )
        result = await db.execute(stmt)
        applied_version = result.scalar_one_or_none()
        if not applied_version:
            raise ValueError("Applied version not found")

        # Find the version just before it
        stmt = (
            select(DocumentVersion)
            .where(
                DocumentVersion.project_id == project_id,
                DocumentVersion.version < applied_version.version,
            )
            .order_by(desc(DocumentVersion.version))
            .limit(1)
        )
        result = await db.execute(stmt)
        prev_version = result.scalar_one_or_none()

        if not prev_version:
            raise ValueError("No previous version to restore")

        # Restore draft to previous version
        stmt = (
            select(DraftDocument)
            .where(DraftDocument.project_id == project_id)
            .order_by(desc(DraftDocument.version))
            .limit(1)
        )
        result = await db.execute(stmt)
        draft = result.scalar_one_or_none()

        if draft:
            draft.content = prev_version.content
            draft.word_count = prev_version.word_count
            draft.version = prev_version.version

        # Create undo version record
        undo_version = DocumentVersion(
            project_id=project_id,
            version=applied_version.version + 1,
            content=prev_version.content,
            content_hash=prev_version.content_hash,
            word_count=prev_version.word_count,
            source_job_id=proposal.job_id,
            source_proposal_id=proposal_id,
            created_by="undo",
        )
        db.add(undo_version)

        proposal.status = "pending"  # Allow re-review
        proposal.applied_at = None

        await db.commit()

        return {
            "success": True,
            "restored_version": prev_version.version,
            "message": f"Đã hoàn tác về phiên bản {prev_version.version}",
        }

    # ── Helper: get current doc info ──────────────────────────────────

    async def get_current_document(
        self,
        db: AsyncSession,
        project_id: str,
    ) -> Tuple[str, int, str]:
        """Return (content_text, version, content_hash) for current document."""
        stmt = (
            select(DraftDocument)
            .where(DraftDocument.project_id == project_id)
            .order_by(desc(DraftDocument.version))
            .limit(1)
        )
        result = await db.execute(stmt)
        draft = result.scalar_one_or_none()

        if not draft:
            return "", 0, _content_hash("")

        if isinstance(draft.content, dict):
            text = str(draft.content.get("html") or draft.content.get("text") or "")
        else:
            text = str(draft.content) if draft.content else ""

        return text, draft.version or 1, _content_hash(text)


proposal_service = ProposalService()
