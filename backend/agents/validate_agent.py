"""ValidateAgent — checks quality of composed academic content.

Phase 3 implementation. Evaluates citation density, source diversity,
unverified claim flags, word budget adherence, and generates actionable warnings.
"""

import logging
import re
from typing import Any, Dict, List, Optional

try:
    from backend.agents.base_agent import BaseAgent
    from backend.services.llm_service import LLMService, llm_service
except ImportError:
    from agents.base_agent import BaseAgent
    from services.llm_service import LLMService, llm_service

logger = logging.getLogger(__name__)


class ValidateAgent(BaseAgent):
    """Agent responsible for validating composed content quality and academic integrity."""

    def __init__(self, llm_service_instance: Optional[LLMService] = None):
        super().__init__(llm_service_instance=llm_service_instance)

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run content validation.

        Input: composed_content, outline, evidence_bundle, citation_style, word_budget
        Output: validation_report with issues, warnings, scores, and passed status
        """
        return await self.validate_content(
            content=input_data.get("composed_content", ""),
            outline=input_data.get("outline", {}),
            evidence=input_data.get("evidence_bundle", []),
            citation_style=input_data.get("citation_style", "apa7"),
            word_budget=input_data.get("word_budget", 400),
            unverified_claims=input_data.get("unverified_claims", []),
        )

    async def validate_content(
        self,
        content: str,
        outline: Dict[str, Any],
        evidence: List[Dict[str, Any]],
        citation_style: str = "apa7",
        word_budget: int = 400,
        unverified_claims: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Validate composed content across academic criteria."""
        issues: List[Dict[str, Any]] = []
        warnings: List[str] = []
        scores: Dict[str, float] = {}

        if not content or not content.strip():
            return {
                "validation_report": {
                    "word_count": 0,
                    "issues": [{"type": "empty_content", "severity": "error", "message": "Nội dung văn bản trống."}],
                    "warnings": ["Không có nội dung để kiểm định."],
                    "scores": {"overall": 0.0},
                    "passed": False,
                },
                "status": "failed",
                "current_step": "content_validated",
            }

        words = content.split()
        word_count = len(words)

        # 1. Word budget adherence
        if word_budget > 0:
            ratio = word_count / word_budget
            if ratio < 0.5:
                msg = f"Nội dung hơi ngắn ({word_count}/{word_budget} từ dự kiến). Cân nhắc mở rộng luận điểm."
                issues.append({"type": "length", "severity": "warning", "message": msg})
                warnings.append(msg)
                scores["word_budget_adherence"] = max(0.2, ratio)
            elif ratio > 1.8:
                msg = f"Nội dung khá dài ({word_count}/{word_budget} từ dự kiến). Cân nhắc cô đọng lại."
                issues.append({"type": "length", "severity": "info", "message": msg})
                scores["word_budget_adherence"] = 0.7
            else:
                scores["word_budget_adherence"] = 1.0
        else:
            scores["word_budget_adherence"] = 1.0

        # 2. Check for [UNVERIFIED] markers
        unverified_in_text = content.count("[UNVERIFIED]")
        total_unverified = max(unverified_in_text, len(unverified_claims or []))
        if total_unverified > 0:
            msg = f"Phát hiện {total_unverified} luận điểm mang tính suy luận chưa được đối chiếu trực tiếp với tài liệu ([UNVERIFIED])."
            issues.append({"type": "unverified_claims", "severity": "warning", "message": msg})
            warnings.append(msg)
            scores["fact_grounding"] = max(0.4, 1.0 - (total_unverified * 0.15))
        else:
            scores["fact_grounding"] = 1.0

        # 3. Citation presence & density
        # Patterns for APA: (Author, Year) or IEEE: [1]
        apa_pattern = r"\([A-ZÀ-Ỹa-zà-ỹ\s&]+,\s*\d{4}\)"
        ieee_pattern = r"\[\d+\]"
        has_apa = bool(re.search(apa_pattern, content))
        has_ieee = bool(re.search(ieee_pattern, content))
        has_citations = has_apa or has_ieee or ("et al." in content) or ("cộng sự" in content)

        if not has_citations and evidence:
            msg = "Đoạn văn bản chưa xuất hiện trích dẫn nguồn học thuật rõ ràng."
            issues.append({"type": "missing_citations", "severity": "warning", "message": msg})
            warnings.append(msg)
            scores["citation_density"] = 0.3
        else:
            # Approximate citation density
            citation_count = len(re.findall(apa_pattern, content)) + len(re.findall(ieee_pattern, content))
            scores["citation_density"] = min(1.0, max(0.6, citation_count / max(1, word_count / 120)))

        # 4. Source diversity / ledger
        used_sources_count = 0
        source_ledger = []
        for ev in evidence:
            p_title = str(ev.get("title", ""))
            authors = ev.get("authors", [])
            first_author = str(authors[0]) if authors else ""
            year_str = str(ev.get("year", ""))

            is_used = False
            if p_title and (p_title[:25].lower() in content.lower()):
                is_used = True
            elif first_author and (first_author.lower() in content.lower()):
                is_used = True
            elif year_str and (year_str in content):
                is_used = True

            if is_used:
                used_sources_count += 1

            source_ledger.append({
                "paper_id": ev.get("paper_id"),
                "title": p_title,
                "cited": is_used,
            })

        if evidence and len(evidence) >= 2 and used_sources_count < 2:
            msg = f"Mới chỉ tích hợp dẫn chứng từ {used_sources_count}/{len(evidence)} bài báo đã chọn. Nên tăng tính đa nguồn."
            issues.append({"type": "source_diversity", "severity": "info", "message": msg})
            warnings.append(msg)
            scores["source_diversity"] = 0.5
        else:
            scores["source_diversity"] = 1.0

        # 5. Overall quality score
        penalty = len([i for i in issues if i["severity"] == "warning"]) * 0.15
        scores["overall"] = max(0.4, round(1.0 - penalty, 2))

        # Has critical errors?
        has_error = any(i["severity"] == "error" for i in issues)

        return {
            "validation_report": {
                "word_count": word_count,
                "issues": issues,
                "warnings": warnings,
                "scores": scores,
                "source_ledger": source_ledger,
                "passed": not has_error,
            },
            "warnings": warnings,
            "status": "success",
            "current_step": "content_validated",
        }


validate_agent = ValidateAgent()
