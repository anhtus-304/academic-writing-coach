"""ComposeAgent — writes academic content based on outline + evidence.

Phase 3 implementation. Synthesises evidence from multiple papers into
academically rigorous sections with proper in-text citations, word budget adherence,
and unverified claim tagging.
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

COMPOSE_SYSTEM_PROMPT_TEMPLATE = """Bạn là Cố vấn và Chuyên gia Soạn thảo Văn bản Học thuật (Academic Composition Specialist).

NHIỆM VỤ:
Soạn thảo nội dung hoàn chỉnh cho công trình nghiên cứu dựa trên Cấu trúc dàn ý và Gói bằng chứng tài liệu được cung cấp.

QUY TẮC BẮT BUỘC:
1. TUÂN THỦ NGHIÊM NGẶT DÀN Ý:
   - BẮT BUỘC giữ nguyên đầy đủ tên và thứ tự các đề mục phân cấp trong dàn ý (Chương, Mục, Tiểu mục).
   - Nội dung chi tiết PHẢI được phân bổ viết nằm ngay dưới từng đề mục tương ứng. Tuyệt đối không lược bỏ đề mục hoặc viết một mạch văn xuôi không có cấu trúc.
2. ĐỊNH DẠNG SEMANTIC HTML (CHUẨN TIPTAP EDITOR):
   - Đề mục lớn / Chương: Dùng thẻ `<h2>...</h2>` (Ví dụ: `<h2>CHƯƠNG 1: TỔNG QUAN</h2>`).
   - Tiểu mục cấp 2 / Mục con: Dùng thẻ `<h3>...</h3>` (Ví dụ: `<h3>1.1. Khái niệm cơ bản</h3>`).
   - Từng đoạn văn học thuật: BẮT BUỘC bọc trong thẻ `<p>...</p>`.
   - KHÔNG bọc kết quả trong khối mã markdown (không dùng ```html ... ```). Trả về trực tiếp chuỗi HTML.
3. TỔNG HỢP ĐA NGUỒN: Tổng hợp và liên kết ý tưởng từ ít nhất 2 nguồn tài liệu khác nhau. So sánh, đối chiếu hoặc tổng hợp luận điểm sâu sắc.
4. CHUẨN TRÍCH DẪN {citation_style_upper}:
   {citation_instructions}
   - Mọi số liệu, luận điểm hoặc kết luận lấy từ tài liệu PHẢI được gắn trích dẫn in-text tương ứng.
5. LIÊM CHÍNH HỌC THUẬT & [UNVERIFIED]:
   - Nếu bạn đưa ra nhận định tổng kết, suy luận mở rộng hoặc liên hệ thực tiễn KHÔNG CÓ trong gói bằng chứng đã cung cấp, hãy đánh dấu bằng thẻ `[UNVERIFIED]` ở cuối câu để người dùng thẩm định lại.
6. VĂN PHONG VÀ NGÔN NGỮ:
   - Sử dụng Tiếng Việt học thuật chuẩn mực, khách quan, không dùng ngôi thứ nhất ("tôi", "chúng tôi").
   - Liên kết mạch lạc giữa các câu và các đoạn ("Bên cạnh đó", "Ngược lại", "Các nghiên cứu thực nghiệm cho thấy", ...).
7. TUÂN THỦ ĐỘ DÀI:
   - Mục tiêu dung lượng: ~{word_budget} từ.
8. KẾT HỢP HÀI HÒA VỚI BẢN THẢO HIỆN CÓ:
   - Nếu được cung cấp bản thảo hiện có từ trình soạn thảo, bạn hãy kế thừa và phát triển thêm các luận điểm còn thiếu, nâng cấp văn phong học thuật bám sát từng đề mục tương ứng trong Dàn ý.
"""


def _get_citation_instructions(style: str) -> str:
    s = (style or "apa7").lower()
    if "ieee" in s:
        return (
            "- Sử dụng định dạng số ngoặc vuông [1], [2] tương ứng với danh sách nguồn được đánh số.\n"
            "- Ví dụ: 'Theo các nghiên cứu trước đây [1], [2], công nghệ này...'"
        )
    elif "bgddt" in s:
        return (
            "- Sử dụng định dạng số ngoặc vuông theo chuẩn Bộ GD&ĐT Việt Nam: [1], [2].\n"
            "- Ví dụ: 'Nghiên cứu của tác giả Nguyễn Văn A [1] đã chỉ ra...'"
        )
    else:  # APA 7 default
        return (
            "- Sử dụng định dạng (Tác giả, Năm) theo chuẩn APA 7.\n"
            "- 1 tác giả: (Smith, 2021) hoặc Smith (2021).\n"
            "- 2 tác giả: (Smith & Johnson, 2021).\n"
            "- 3 tác giả trở lên: (Smith et al., 2021) hoặc Smith và cộng sự (2021)."
        )


def _ensure_clean_academic_html(text: str) -> str:
    """Normalize LLM output into clean semantic HTML for Tiptap Editor."""
    if not text:
        return ""
    # Strip markdown code fences if present
    cleaned = re.sub(r"^```(?:html)?\s*", "", text.strip())
    cleaned = re.sub(r"\s*```$", "", cleaned.strip())

    # If already mostly HTML (contains <h2 or <p>), return with basic cleanup
    has_html_tags = bool(re.search(r"<(?:h[1-6]|p|div|ul|ol|table)\b", cleaned, re.IGNORECASE))
    if has_html_tags:
        cleaned = re.sub(r"(?m)^###\s+(.+)$", r"<h3>\1</h3>", cleaned)
        cleaned = re.sub(r"(?m)^##\s+(.+)$", r"<h2>\1</h2>", cleaned)
        cleaned = re.sub(r"(?m)^#\s+(.+)$", r"<h1>\1</h1>", cleaned)
        return cleaned

    # Otherwise, convert markdown blocks to HTML
    blocks = [b.strip() for b in cleaned.split("\n\n") if b.strip()]
    html_parts = []
    for block in blocks:
        if block.startswith("### "):
            html_parts.append(f"<h3>{block[4:].strip()}</h3>")
        elif block.startswith("## "):
            html_parts.append(f"<h2>{block[3:].strip()}</h2>")
        elif block.startswith("# "):
            html_parts.append(f"<h2>{block[2:].strip()}</h2>")
        else:
            html_parts.append(f"<p>{block}</p>")

    return "".join(html_parts)


class ComposeAgent(BaseAgent):
    """Agent responsible for composing academic content per section."""

    def __init__(self, llm_service_instance: Optional[LLMService] = None):
        super().__init__(llm_service_instance=llm_service_instance)

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run content composition.

        Input: section, evidence_bundle, citation_style, word_budget, topic, current_draft
        Output: composed_content with source_refs, word_count, unverified_claims
        """
        return await self.compose_section(
            section=input_data.get("section") or input_data.get("outline", {}),
            evidence_bundle=input_data.get("evidence_bundle", []),
            citation_style=input_data.get("citation_style", "apa7"),
            word_budget=input_data.get("word_budget", 400),
            topic=input_data.get("topic", ""),
            language=input_data.get("language", "vi"),
            prompt=input_data.get("prompt", ""),
            current_draft=input_data.get("current_draft", ""),
        )

    async def compose_section(
        self,
        section: Dict[str, Any],
        evidence_bundle: List[Dict[str, Any]],
        citation_style: str = "apa7",
        word_budget: int = 400,
        topic: str = "",
        language: str = "vi",
        prompt: str = "",
        current_draft: str = "",
    ) -> Dict[str, Any]:
        """Compose academic text synthesizing outline, current draft, and evidence bundle."""

        # Format outline details including chapters, subsections, and key points
        outline_repr = ""
        inner = section.get("outline") or section if isinstance(section, dict) else section
        if isinstance(inner, dict) and (inner.get("sections") or inner.get("chapters")):
            sections = inner.get("sections") or inner.get("chapters") or []
            if isinstance(sections, dict):
                sections = list(sections.values())
            elif not isinstance(sections, list):
                sections = [sections]

            for s in sections:
                if isinstance(s, str):
                    outline_repr += f"\n## {s}\n"
                elif isinstance(s, dict):
                    title = s.get("title") or s.get("heading") or "Mục"
                    outline_repr += f"\n## {title}\n"
                    # Include chapter level key points if any
                    ch_kps = s.get("key_points", [])
                    if ch_kps:
                        ch_kps_list = ch_kps if isinstance(ch_kps, list) else [ch_kps]
                        for ckp in ch_kps_list:
                            outline_repr += f"- Luận cứ trọng tâm: {ckp}\n"

                    subs = s.get("subsections", [])
                    subs_list = subs if isinstance(subs, list) else (list(subs.values()) if isinstance(subs, dict) else [subs])
                    for sub in subs_list:
                        if isinstance(sub, dict):
                            sub_title = sub.get("title") or "Tiểu mục"
                            outline_repr += f"### {sub_title}\n"
                            kps = sub.get("key_points", [])
                            kps_list = kps if isinstance(kps, list) else (list(kps.values()) if isinstance(kps, dict) else [kps])
                            for kp in kps_list:
                                if kp:
                                    outline_repr += f"  - Ý chính: {kp}\n"
                        else:
                            outline_repr += f"### {sub}\n"
                else:
                    outline_repr += f"\n## {s}\n"
        elif isinstance(inner, list):
            for s in inner:
                outline_repr += f"\n## {s}\n"
        elif isinstance(section, dict) and section.get("title"):
            outline_repr = f"## {section.get('title')}\n"
            kps = section.get("key_points", [])
            kps_list = kps if isinstance(kps, list) else (list(kps.values()) if isinstance(kps, dict) else [kps])
            for kp in kps_list:
                outline_repr += f"- Ý chính: {kp}\n"
        else:
            outline_repr = "Soạn thảo phát triển nội dung trọng tâm cho đề tài nghiên cứu."

        # Format evidence sources
        evidence_lines = []
        numbered_sources = []
        evidence_list = evidence_bundle if isinstance(evidence_bundle, list) else (list(evidence_bundle.values()) if isinstance(evidence_bundle, dict) else [])
        for idx, ev in enumerate(evidence_list[:6], 1):
            if not isinstance(ev, dict):
                continue
            title = ev.get("title", f"Nguồn {idx}")
            authors = ev.get("authors", [])
            if not isinstance(authors, list):
                authors = [str(authors)] if authors else []
            year = ev.get("year", "N/A")
            summary = ev.get("summary", "")
            claims = ev.get("claims", [])
            if not isinstance(claims, list):
                claims = [str(claims)] if claims else []
            findings = ev.get("key_findings", [])
            if not isinstance(findings, list):
                findings = [str(findings)] if findings else []

            author_str = str(authors[0]) if authors else "Tác giả"
            if len(authors) > 2:
                author_str += " et al."
            elif len(authors) == 2:
                author_str += f" & {authors[1]}"

            ref_tag = f"[{idx}]" if "ieee" in citation_style.lower() or "bgddt" in citation_style.lower() else f"({author_str}, {year})"

            details = []
            if summary:
                details.append(f"Tóm tắt: {summary[:250]}")
            if claims:
                details.append(f"Luận điểm: {'; '.join(str(c) for c in claims[:2])}")
            if findings:
                details.append(f"Bằng chứng/Số liệu: {'; '.join(str(f) for f in findings[:2])}")

            evidence_lines.append(f"Nguồn {ref_tag} - \"{title}\" ({author_str}, {year}):\n" + "\n".join(details))
            numbered_sources.append({
                "index": idx,
                "ref_tag": ref_tag,
                "paper_id": ev.get("paper_id"),
                "title": title,
                "authors": authors,
                "year": year,
            })

        evidence_text = "\n\n".join(evidence_lines) if evidence_lines else "Chưa có tài liệu trích dẫn trực tiếp."

        citation_instructions = _get_citation_instructions(citation_style)
        system_prompt = COMPOSE_SYSTEM_PROMPT_TEMPLATE.format(
            citation_style_upper=citation_style.upper(),
            citation_instructions=citation_instructions,
            word_budget=word_budget,
        )

        draft_context_block = ""
        if current_draft and current_draft.strip():
            draft_clean = current_draft.strip()
            if len(draft_clean) > 4000:
                draft_clean = draft_clean[:4000] + "... [nội dung bản thảo tiếp theo]"
            draft_context_block = (
                f"NỘI DUNG BẢN THẢO HIỆN CÓ TRONG TRÌNH SOẠN THẢO (DATABASE):\n"
                f"\"\"\"\n{draft_clean}\n\"\"\"\n\n"
                f"YÊU CẦU ĐỒNG BỘ: Dựa trên bản thảo hiện có ở trên, hãy hoàn thiện, bổ sung hoặc nâng cấp vào đúng các đề mục tương ứng của Dàn ý, đảm bảo tính liên kết chặt chẽ và không làm xáo trộn bố cục.\n\n"
            )

        user_prompt = (
            f"Chủ đề tổng thể: {topic}\n"
            f"Yêu cầu cụ thể từ người dùng: {prompt or 'Soạn thảo nội dung học thuật chuẩn mực theo dàn ý.'}\n\n"
            f"CẤU TRÚC DÀN Ý BẮT BUỘC:\n{outline_repr}\n\n"
            f"{draft_context_block}"
            f"Gói bằng chứng tài liệu hỗ trợ:\n{evidence_text}\n\n"
            f"Hãy soạn thảo nội dung hoàn chỉnh theo đúng cấu trúc Dàn ý và định dạng Semantic HTML."
        )

        try:
            response_text, usage = await self.llm_service.generate_text_with_usage(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.4,
            )

            # Extract [UNVERIFIED] tags and remove or collect them
            unverified_claims = []
            for match in re.finditer(r"([^.!?\n]+)\[UNVERIFIED\]", response_text):
                unverified_claims.append(match.group(1).strip())

            # Identify which sources were actually cited in the text
            used_source_refs = []
            for src in numbered_sources:
                tag = src["ref_tag"]
                authors = src.get("authors", [])
                first_author = str(authors[0]) if authors else ""
                year_str = str(src.get("year", ""))

                if tag in response_text or (first_author and first_author in response_text) or f"[{src['index']}]" in response_text:
                    used_source_refs.append(f"{src['title']} ({first_author}, {year_str})")

            clean_html = _ensure_clean_academic_html(response_text)
            word_count = len(re.sub(r"<[^>]+>", " ", clean_html).split())

            return {
                "composed_content": clean_html,
                "word_count": word_count,
                "source_refs": used_source_refs,
                "unverified_claims": unverified_claims,
                "confidence": 0.82 if len(used_source_refs) >= 2 else 0.70,
                "status": "success",
                "current_step": "content_composed",
                "_tokens_used": usage.get("total_tokens", 0),
            }

        except Exception as e:
            logger.error("ComposeAgent failed: %s", e, exc_info=True)
            return {
                "error": str(e),
                "status": "failed",
                "current_step": "compose_error",
            }


compose_agent = ComposeAgent()
