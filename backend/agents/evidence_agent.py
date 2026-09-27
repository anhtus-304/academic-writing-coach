"""EvidenceAgent — extracts claims, evidence, and key findings from papers.

Phase 3 implementation. Aggregates and extracts structured evidence from
selected academic papers and maps them to relevant outline sections.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

try:
    from backend.agents.base_agent import BaseAgent
    from backend.services.llm_service import LLMService, llm_service
except ImportError:
    from agents.base_agent import BaseAgent
    from services.llm_service import LLMService, llm_service

logger = logging.getLogger(__name__)

EVIDENCE_SYSTEM_PROMPT = """Bạn là Chuyên gia Trích xuất Dẫn chứng Học thuật (Evidence Extraction Specialist).

NHIỆM VỤ:
Từ danh sách bài báo khoa học và dàn ý nghiên cứu, hãy trích xuất:
1. Các luận điểm chính (Key Claims) mà bài báo chứng minh.
2. Các phát hiện thực nghiệm / số liệu then chốt (Key Findings / Evidence).
3. Phương pháp nghiên cứu (Methodology) nếu có.
4. Gán nhãn các đề mục dàn ý (Relevant Sections) mà tài liệu này có thể làm bằng chứng hỗ trợ.

ĐỊNH DẠNG ĐẦU RA:
Trả về JSON tuân thủ cấu trúc được yêu cầu, chính xác và khách quan.
"""


class ExtractedPaperEvidence(BaseModel):
    paper_id: str
    claims: List[str] = Field(default_factory=list)
    key_findings: List[str] = Field(default_factory=list)
    methodology: Optional[str] = None
    relevant_sections: List[str] = Field(default_factory=list)
    confidence: float = 0.85


class EvidenceBundleResponse(BaseModel):
    items: List[ExtractedPaperEvidence] = Field(default_factory=list)


class EvidenceAgent(BaseAgent):
    """Agent responsible for extracting structured evidence from papers."""

    def __init__(self, llm_service_instance: Optional[LLMService] = None):
        super().__init__(llm_service_instance=llm_service_instance)

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run evidence extraction.

        Input: selected_papers, outline, topic
        Output: evidence_bundle — list of evidence items mapped to sections
        """
        return await self.extract_evidence(
            papers=input_data.get("selected_papers", []),
            outline=input_data.get("outline", {}),
            topic=input_data.get("topic", ""),
        )

    async def extract_evidence(
        self,
        papers: List[Dict[str, Any]],
        outline: Dict[str, Any],
        topic: str = "",
    ) -> Dict[str, Any]:
        """Extract claims and evidence from papers for each outline section."""
        if not papers:
            return {
                "evidence_bundle": [],
                "status": "success",
                "current_step": "evidence_extracted",
                "_tokens_used": 0,
            }

        # Build outline context for matching
        sections_summary = []
        inner = outline.get("outline") or outline if isinstance(outline, dict) else outline
        if isinstance(inner, dict):
            sections = inner.get("sections") or inner.get("chapters") or []
        elif isinstance(inner, list):
            sections = inner
        else:
            sections = [str(inner)] if inner else []

        if isinstance(sections, dict):
            sections = list(sections.values())
        elif not isinstance(sections, list):
            sections = [sections]

        for s in sections:
            if isinstance(s, str):
                sections_summary.append(s)
            elif isinstance(s, dict):
                title = s.get("title") or s.get("heading") or ""
                if title:
                    sections_summary.append(title)
                subs = s.get("subsections", [])
                subs_list = subs if isinstance(subs, list) else (list(subs.values()) if isinstance(subs, dict) else [subs])
                for sub in subs_list:
                    sub_title = sub.get("title") if isinstance(sub, dict) else str(sub)
                    if sub_title:
                        sections_summary.append(f"  - {sub_title}")
            else:
                sections_summary.append(str(s))

        outline_text = "\n".join(sections_summary) if sections_summary else "Chưa có dàn ý chi tiết."

        # Prepare papers text for LLM
        papers_list = papers if isinstance(papers, list) else (list(papers.values()) if isinstance(papers, dict) else [])
        papers_to_process = papers_list[:8]  # Limit to top 8 to stay within token budgets
        papers_text_list = []
        for idx, paper in enumerate(papers_to_process):
            p = paper if isinstance(paper, dict) else {}
            title = p.get("title", f"Paper {idx + 1}")
            authors = p.get("authors", [])
            authors_list = authors if isinstance(authors, list) else [str(authors)] if authors else []
            year = p.get("year", "N/A")
            summary = p.get("summary_vi") or p.get("summary") or p.get("abstract") or ""
            p_id = str(p.get("id") or p.get("cached_paper_id") or f"p_{idx}")

            papers_text_list.append(
                f"[ID: {p_id}] {title} ({', '.join(str(a) for a in authors[:2])}, {year})\n"
                f"Tóm tắt: {summary[:400]}"
            )

        user_prompt = (
            f"Chủ đề nghiên cứu: {topic}\n\n"
            f"Dàn ý bài viết:\n{outline_text}\n\n"
            f"Danh sách tài liệu khoa học cần trích xuất:\n\n"
            + "\n\n".join(papers_text_list)
            + "\n\nTrích xuất các luận điểm (claims), phát hiện thực nghiệm (key_findings), "
            "phương pháp và mục dàn ý phù hợp cho từng tài liệu."
        )

        total_tokens = 0
        evidence_bundle: List[Dict[str, Any]] = []

        try:
            structured_res, usage = await self.llm_service.generate_structured_output_with_usage(
                system_prompt=EVIDENCE_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                schema=EvidenceBundleResponse,
                temperature=0.3,
            )
            total_tokens = usage.get("total_tokens", 0)

            # Map back to paper metadata
            extracted_map = {item.paper_id: item for item in structured_res.items}

            for idx, paper in enumerate(papers_to_process):
                p = paper if isinstance(paper, dict) else {}
                p_id = str(p.get("id") or p.get("cached_paper_id") or f"p_{idx}")
                extracted = extracted_map.get(p_id)

                claims = extracted.claims if extracted else []
                findings = extracted.key_findings if extracted else []
                methodology = extracted.methodology if extracted else None
                relevant_secs = extracted.relevant_sections if extracted else []
                confidence = extracted.confidence if extracted else 0.75

                # Fallback heuristics if LLM missed items
                if not claims and (p.get("summary") or p.get("summary_vi")):
                    summary_text = str(p.get("summary_vi") or p.get("summary"))
                    sentences = [s.strip() for s in re.split(r"[.!?]", summary_text) if len(s.strip()) > 15]
                    claims = sentences[:2]
                    findings = sentences[2:4] if len(sentences) > 2 else []

                evidence_bundle.append({
                    "paper_id": p_id,
                    "title": str(p.get("title", "")),
                    "authors": p.get("authors", []),
                    "year": p.get("year"),
                    "doi": p.get("doi"),
                    "claims": claims,
                    "key_findings": findings,
                    "summary": str(p.get("summary_vi") or p.get("summary") or ""),
                    "methodology": methodology,
                    "confidence": confidence,
                    "relevant_sections": relevant_secs,
                })

        except Exception as e:
            logger.warning("Evidence extraction via LLM structured output failed, falling back to heuristics: %s", e)
            for idx, paper in enumerate(papers_to_process):
                p = paper if isinstance(paper, dict) else {}
                p_id = str(p.get("id") or p.get("cached_paper_id") or f"p_{idx}")
                summary_text = str(p.get("summary_vi") or p.get("summary") or "")
                sentences = [s.strip() for s in re.split(r"[.!?]", summary_text) if len(s.strip()) > 15]

                evidence_bundle.append({
                    "paper_id": p_id,
                    "title": str(p.get("title", "")),
                    "authors": p.get("authors", []),
                    "year": p.get("year"),
                    "doi": p.get("doi"),
                    "claims": sentences[:2],
                    "key_findings": sentences[2:4],
                    "summary": summary_text,
                    "methodology": None,
                    "confidence": 0.7,
                    "relevant_sections": [],
                })

        return {
            "evidence_bundle": evidence_bundle,
            "status": "success",
            "current_step": "evidence_extracted",
            "_tokens_used": total_tokens,
        }


evidence_agent = EvidenceAgent()
