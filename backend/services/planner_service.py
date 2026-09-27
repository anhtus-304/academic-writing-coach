"""PlannerService — analyse user prompt and generate a structured execution plan.

The planner uses the LLM to classify intent and produce a list of stages
with dependencies, estimated credits, and input/output mappings.
"""

import json
import logging
from typing import Any, Dict, List, Optional

try:
    from backend.services.llm_service import llm_service
    from backend.schemas.agent_job_schemas import StagePlanItem
    from backend.config import settings
except ImportError:
    from services.llm_service import llm_service
    from schemas.agent_job_schemas import StagePlanItem
    from config import settings

logger = logging.getLogger(__name__)

# ── Stage cost lookup ─────────────────────────────────────────────────

STAGE_COSTS: Dict[str, int] = {
    "inspect_context": 0,
    "build_outline": settings.AGENT_AUTO_CHECKPOINT_COST_OUTLINE,
    "research": settings.AGENT_AUTO_CHECKPOINT_COST_LITERATURE,
    "extract_evidence": 1,
    "compose": 2,
    "validate": settings.AGENT_AUTO_CHECKPOINT_COST_CITATION,
    "build_proposal": 0,
}

# ── Default stage pipelines ──────────────────────────────────────────

AUTO_FULL_PIPELINE: List[Dict[str, Any]] = [
    {"stage_type": "inspect_context", "description": "Đọc project, outline, bản thảo, tài liệu đã chọn", "depends_on": []},
    {"stage_type": "build_outline", "description": "Tạo hoặc cập nhật dàn ý nghiên cứu", "depends_on": ["inspect_context"]},
    {"stage_type": "research", "description": "Tìm kiếm và xếp hạng tài liệu khoa học", "depends_on": ["build_outline"]},
    {"stage_type": "extract_evidence", "description": "Trích xuất bằng chứng và luận điểm từ tài liệu", "depends_on": ["research"]},
    {"stage_type": "compose", "description": "Viết nội dung cho section theo dàn ý và bằng chứng", "depends_on": ["extract_evidence"]},
    {"stage_type": "validate", "description": "Kiểm tra cấu trúc, trích dẫn và chất lượng nội dung", "depends_on": ["compose"]},
    {"stage_type": "build_proposal", "description": "Tạo proposal diff để người dùng review", "depends_on": ["validate"]},
]

ASK_PIPELINE: List[Dict[str, Any]] = [
    {"stage_type": "inspect_context", "description": "Đọc project, outline, bản thảo", "depends_on": []},
]

# ── Planner system prompt ────────────────────────────────────────────

PLANNER_SYSTEM_PROMPT = """Bạn là Planner Agent cho hệ thống Academic Writing Coach.
Nhiệm vụ: phân tích prompt của người dùng và trả về một execution plan ở dạng JSON.

Các stage types có sẵn cho Auto mode:
- inspect_context: đọc project metadata, outline, draft, selected papers
- build_outline: tạo hoặc cập nhật dàn ý
- research: tìm kiếm tài liệu khoa học
- extract_evidence: trích xuất bằng chứng từ papers
- compose: viết nội dung theo dàn ý + evidence
- validate: kiểm tra chất lượng
- build_proposal: tạo diff proposal

Cho Ask mode, chỉ dùng inspect_context + trả lời trực tiếp.

Trả về JSON với format:
{
  "intent": "string mô tả ngắn ý định",
  "stages": [{"stage_type": "...", "description": "...", "depends_on": [...]}],
  "assumptions": ["..."],
  "target_section": "section ID nếu user chỉ định, null nếu không"
}
"""


class PlannerService:
    """Analyses user prompt and context to produce an execution plan."""

    async def create_plan(
        self,
        mode: str,
        prompt: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate execution plan.

        For Auto mode, call LLM to intelligently select stages.
        For Ask mode, return a minimal read-only plan.

        Returns dict with keys: intent, stages (list of StagePlanItem dicts),
        assumptions, target_section, estimated_credits.
        """
        if mode == "ask":
            return self._build_ask_plan(prompt, context)

        return await self._build_auto_plan(prompt, context)

    def _build_ask_plan(self, prompt: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Ask mode: read-only, single stage, no LLM planning needed."""
        stages = [
            StagePlanItem(
                stage_id="stage-ask-1",
                stage_type="inspect_context",
                description="Đọc context và trả lời câu hỏi",
                depends_on=[],
                estimated_credits=1,
            ).model_dump()
        ]
        return {
            "intent": f"Trả lời câu hỏi: {prompt[:100]}",
            "stages": stages,
            "assumptions": [],
            "target_section": None,
            "estimated_credits": 1,
        }

    async def _build_auto_plan(self, prompt: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Auto mode: use LLM to decide which stages are needed.

        Falls back to full pipeline if LLM fails or returns invalid JSON.
        """
        has_outline = bool(context.get("outline"))
        has_draft = bool(context.get("draft_content"))

        try:
            user_prompt = (
                f"Prompt người dùng: \"{prompt}\"\n\n"
                f"Context hiện tại:\n"
                f"- Có outline: {'Có' if has_outline else 'Chưa có'}\n"
                f"- Có bản thảo: {'Có' if has_draft else 'Chưa có'}\n"
                f"- Số papers đã chọn: {len(context.get('selected_papers', []))}\n"
                f"- Topic: {context.get('topic', 'N/A')}\n\n"
                f"Hãy phân tích và trả về execution plan JSON."
            )

            response_text, usage = await llm_service.generate_text_with_usage(
                system_prompt=PLANNER_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.2,
            )

            # Parse LLM response
            plan_data = self._parse_plan_json(response_text)
            if plan_data and plan_data.get("stages"):
                stages = self._build_stage_items(plan_data["stages"], has_outline)
                total_credits = sum(s["estimated_credits"] for s in stages)
                return {
                    "intent": plan_data.get("intent", prompt[:100]),
                    "stages": stages,
                    "assumptions": plan_data.get("assumptions", []),
                    "target_section": plan_data.get("target_section"),
                    "estimated_credits": total_credits,
                }
        except Exception as e:
            logger.warning("Planner LLM call failed, using default pipeline: %s", e)

        # Fallback: use default full pipeline
        return self._build_default_auto_plan(prompt, has_outline)

    def _parse_plan_json(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from LLM response (handles markdown code blocks)."""
        cleaned = text.strip()
        # Strip markdown code fences if present
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            cleaned = "\n".join(lines)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # Try to find JSON object in text
            start = cleaned.find("{")
            end = cleaned.rfind("}") + 1
            if start >= 0 and end > start:
                try:
                    return json.loads(cleaned[start:end])
                except json.JSONDecodeError:
                    pass
        return None

    def _build_stage_items(
        self, raw_stages: List[Dict[str, Any]], has_outline: bool
    ) -> List[Dict[str, Any]]:
        """Convert raw stage dicts from LLM into StagePlanItem dicts."""
        items = []
        for i, s in enumerate(raw_stages):
            stage_type = s.get("stage_type", "inspect_context")
            # Skip outline if already exists
            cost = STAGE_COSTS.get(stage_type, 1)
            if stage_type == "build_outline" and has_outline:
                cost = 0

            items.append(
                StagePlanItem(
                    stage_id=f"stage-{i + 1}",
                    stage_type=stage_type,
                    description=s.get("description", stage_type),
                    depends_on=s.get("depends_on", []),
                    estimated_credits=cost,
                ).model_dump()
            )
        return items

    def _build_default_auto_plan(
        self, prompt: str, has_outline: bool
    ) -> Dict[str, Any]:
        """Fallback: full pipeline with all 7 stages."""
        stages = []
        for i, s in enumerate(AUTO_FULL_PIPELINE):
            stage_type = s["stage_type"]
            cost = STAGE_COSTS.get(stage_type, 1)
            if stage_type == "build_outline" and has_outline:
                cost = 0
            stages.append(
                StagePlanItem(
                    stage_id=f"stage-{i + 1}",
                    stage_type=stage_type,
                    description=s["description"],
                    depends_on=s.get("depends_on", []),
                    estimated_credits=cost,
                ).model_dump()
            )

        total_credits = sum(s["estimated_credits"] for s in stages)
        return {
            "intent": f"Thực hiện quy trình viết học thuật: {prompt[:100]}",
            "stages": stages,
            "assumptions": [],
            "target_section": None,
            "estimated_credits": total_credits,
        }


planner_service = PlannerService()
