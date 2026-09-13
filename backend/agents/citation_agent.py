import re
import json
import logging
from typing import Any, Dict, List, Optional, Tuple, Set
from pydantic import BaseModel, Field

try:
    from agents.base_agent import BaseAgent
    from services.llm_service import LLMService, llm_service
    from services.citation_formatter import CitationFormatterService
    from schemas.citation_schemas import (
        CitationMetadataSchema,
        CitationStyle,
        DocumentType,
        MissingCitationClaim,
        UncitedPaperItem,
        CitationCheckResponse,
    )
except ImportError:
    from backend.agents.base_agent import BaseAgent
    from backend.services.llm_service import LLMService, llm_service
    from backend.services.citation_formatter import CitationFormatterService
    from backend.schemas.citation_schemas import (
        CitationMetadataSchema,
        CitationStyle,
        DocumentType,
        MissingCitationClaim,
        UncitedPaperItem,
        CitationCheckResponse,
    )

logger = logging.getLogger(__name__)

# Heuristic patterns for academic claims and statistical statements
CLAIM_INDICATORS = [
    r"\b\d+[\.,]?\d*%",
    r"\bchiếm\s+\d+",
    r"\btăng\s+\d+",
    r"\bgiảm\s+\d+",
    r"\btheo\s+nghiên\s+cứu\b",
    r"\bcác\s+nghiên\s+cứu\s+chỉ\s+ra\b",
    r"\btheo\s+báo\s+cáo\b",
    r"\bthống\s+kê\s+cho\s+thấy\b",
    r"\bkết\s+quả\s+cho\s+thấy\b",
    r"\bđược\s+chứng\s+minh\s+là\b",
    r"\bkhảo\s+sát\s+tại\b",
    r"\bđóng\s+vai\s+trò\s+quyết\s+định\b",
    r"\bgây\s+ra\s+hậu\s+quả\s+nghiêm\s+trọng\b",
    r"\baccording\s+to\b",
    r"\bstudies\s+show\b",
    r"\bresearch\s+indicates\b",
    r"\bstatistically\s+significant\b",
]

# Whitelist: sentences that express the author's own work/methods/goals do NOT need external citations
SELF_CLAIM_WHITELIST = [
    r"\bchúng\s+tôi\b",
    r"\btôi\b",
    r"\bđồ\s+án\s+này\b",
    r"\bđề\s+tài\s+này\b",
    r"\bnghiên\s+cứu\s+này\b",
    r"\bbài\s+viết\s+này\b",
    r"\bluận\s+văn\s+này\b",
    r"\bmục\s+tiêu\s+của\b",
    r"\bnhóm\s+tác\s+giả\b",
    r"\bphương\s+pháp\s+đề\s+xuất\b",
    r"\bwe\s+propose\b",
    r"\bin\s+this\s+study\b",
    r"\bin\s+this\s+paper\b",
    r"\bour\s+approach\b",
    r"\bwe\s+achieved\b",
]

# Common abbreviations in academic Vietnamese & English to protect against false sentence splits
SAFE_ABBREVIATIONS = [
    r"et\s+al",
    r"e\.g",
    r"i\.e",
    r"TS",
    r"ThS",
    r"GS",
    r"PGS",
    r"vol",
    r"pp",
    r"tr",
    r"No",
    r"vs",
    r"ca",
    r"Hình",
    r"Bảng",
]

# Standard In-text citation regex patterns for quick claim detection
CITATION_PATTERNS = [
    r"\[\d+(?:\s*[,-–—]\s*\d+)*\]",                              # IEEE numeric, e.g., [1] or [1, 2] or [1-3]
    r"\([A-ZÀ-Ỹa-zà-ỹ\s&,\.]+?[,\s]+(?:19|20)\d{2}[a-z]?\)",     # APA standard, e.g., (Nguyen, 2023) or (Smith, 2024)
    r"\b[A-ZÀ-Ỹ][a-zà-ỹA-ZÀ-Ỹ\s&,\.]+\s*\((?:19|20)\d{2}[a-z]?\)", # Narrative APA, e.g., Smith (2024), Vaswani et al. (2017)
]


class ClaimAnalysisItem(BaseModel):
    sentence: str
    is_claim_requiring_citation: bool = Field(
        ...,
        description="True nếu đây là số liệu/nhận định từ bên thứ ba cần dẫn chứng. False nếu là công việc của chính tác giả hoặc kiến thức phổ thông.",
    )
    reason: str = Field(..., description="Lý do học thuật ngắn gọn")
    recommended_paper_id: Optional[str] = Field(
        None,
        description="ID của bài báo trong danh mục đề tài phù hợp nhất để dẫn chứng, hoặc null",
    )
    recommended_paper_title: Optional[str] = Field(None, description="Tên bài báo gợi ý")
    in_text_suggestion: Optional[str] = Field(None, description="Mã trích dẫn gợi ý, ví dụ (Smith, 2024) hoặc [1]")


class SemanticCitationAnalysis(BaseModel):
    analyzed_claims: List[ClaimAnalysisItem] = Field(default_factory=list)


class CitationAgent(BaseAgent):
    """
    Hybrid Academic Citation Agent responsible for:
    1. Deterministic Core:
       - Safe sentence tokenization & abbreviation protection.
       - Extraction of numeric IEEE/ranges ([1-3]), APA parenthesized and narrative citations.
       - Mechanical cross-referencing: ghost citations, publication year verification, IEEE sequential order.
       - Identification of uncited selected papers with formatted in-text codes.
       - Heuristic pre-filtering of candidate missing claims (0 token cost).
    2. Semantic Arbitrator (LLM):
       - Filtering out self-contributions, methodology statements, and common knowledge.
       - Semantically matching verified claims to papers in the student's catalog (Smart Recommendation).
    """

    def __init__(self, llm_service_instance: Optional[LLMService] = None):
        super().__init__(llm_service_instance=llm_service_instance)
        self.formatter = CitationFormatterService()

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """BaseAgent interface implementation."""
        content = input_data.get("content", "")
        selected_papers = input_data.get("selected_papers", [])
        citation_style = input_data.get("citation_style", "apa7")

        result = await self.check_document_citations(
            content=content,
            selected_papers=selected_papers,
            citation_style=citation_style,
        )
        return result.model_dump()

    @staticmethod
    def clean_html_to_text(html: str) -> str:
        """Removes HTML markup and normalizes whitespaces."""
        if not html:
            return ""
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"&nbsp;", " ", text)
        text = re.sub(r"&amp;", "&", text)
        text = re.sub(r"&lt;", "<", text)
        text = re.sub(r"&gt;", ">", text)
        text = re.sub(r"&quot;", '"', text)
        text = re.sub(r"&#39;", "'", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    @staticmethod
    def split_into_sentences(text: str) -> List[str]:
        """
        Splits academic document text into distinct sentences, protecting abbreviations
        such as 'et al.', 'TS.', 'pp.', 'e.g.', 'vol.' from breaking sentence boundaries.
        """
        if not text:
            return []

        protected_text = text
        # Step 1: Protect academic abbreviations by replacing dot with placeholder
        for abbr in SAFE_ABBREVIATIONS:
            protected_text = re.sub(rf"\b({abbr})\.", r"\1__DOT__", protected_text, flags=re.IGNORECASE)

        # Step 2: Split at remaining period/exclamation/question marks followed by whitespace
        raw_sentences = re.split(r"(?<=[.?!])\s+", protected_text)

        # Step 3: Restore protected dots and filter out tiny fragments
        sentences = []
        for s in raw_sentences:
            restored = s.replace("__DOT__", ".").strip()
            if len(restored) > 15:
                sentences.append(restored)

        return sentences

    def normalize_paper_metadata(self, paper: Any) -> CitationMetadataSchema:
        """Extracts and normalizes CitationMetadataSchema from an ORM object or plain dictionary."""
        cp = getattr(paper, "cached_paper", None) or paper

        title = getattr(cp, "title", None) or (cp.get("title") if isinstance(cp, dict) else "Tài liệu học thuật")
        raw_authors = getattr(cp, "authors", None) or (cp.get("authors") if isinstance(cp, dict) else [])

        authors: List[str] = []
        if isinstance(raw_authors, list):
            for a in raw_authors:
                if isinstance(a, dict):
                    name = a.get("name") or a.get("family") or a.get("full_name")
                    if name:
                        authors.append(str(name).strip())
                elif a:
                    authors.append(str(a).strip())
        elif isinstance(raw_authors, str) and raw_authors.strip():
            authors = [a.strip() for a in raw_authors.split(",") if a.strip()]
        if not authors:
            authors = ["Unknown"]

        year = getattr(cp, "year", None) or getattr(cp, "publication_year", None)
        if year is None and isinstance(cp, dict):
            year = cp.get("year") or cp.get("publication_year")
        try:
            year_int = int(year) if year is not None else 2024
        except (ValueError, TypeError):
            year_int = 2024

        doi = getattr(cp, "doi", None) or (cp.get("doi") if isinstance(cp, dict) else None)
        url = getattr(cp, "url", None) or (cp.get("url") if isinstance(cp, dict) else None)
        venue = (
            getattr(cp, "venue", None)
            or getattr(cp, "publicationType", None)
            or getattr(cp, "journal", None)
            or (cp.get("venue") if isinstance(cp, dict) else None)
            or (cp.get("journal") if isinstance(cp, dict) else None)
        )
        publisher = getattr(cp, "publisher", None) or (cp.get("publisher") if isinstance(cp, dict) else None)
        pages = getattr(cp, "pages", None) or (cp.get("pages") if isinstance(cp, dict) else None)
        raw_doc_type = getattr(cp, "doc_type", None) or (cp.get("doc_type") if isinstance(cp, dict) else None)
        if hasattr(raw_doc_type, "value"):
            doc_type_val = raw_doc_type.value
        elif isinstance(raw_doc_type, str):
            doc_type_val = raw_doc_type
        else:
            doc_type_val = "journal"

        try:
            doc_type_enum = DocumentType(str(doc_type_val).lower())
        except (ValueError, TypeError):
            doc_type_enum = DocumentType.JOURNAL

        return CitationMetadataSchema(
            title=title or "Tài liệu học thuật",
            authors=authors,
            year=year_int,
            doi=doi,
            url=url,
            journal=venue,
            publisher=publisher,
            pages=pages,
            doc_type=doc_type_enum,
        )

    def detect_candidate_missing_claims(self, sentences: List[str]) -> List[str]:
        """
        Deterministic fast filter: finds candidate sentences that contain statistical/empirical
        claims but lack citations, filtering out obvious author self-contributions.
        """
        candidates: List[str] = []
        citation_regex = re.compile("|".join(CITATION_PATTERNS), re.IGNORECASE)
        self_claim_regex = re.compile("|".join(SELF_CLAIM_WHITELIST), re.IGNORECASE)

        for sentence in sentences:
            # If the sentence already has a recognized citation, skip
            if citation_regex.search(sentence):
                continue

            # If the sentence expresses author's own methodology or goals, skip
            if self_claim_regex.search(sentence):
                continue

            # Check if sentence contains statistical or empirical claim indicators
            for ind in CLAIM_INDICATORS:
                if re.search(ind, sentence, re.IGNORECASE):
                    candidates.append(sentence)
                    break

        return candidates

    @staticmethod
    def expand_numeric_citations(inner_str: str) -> List[int]:
        """
        Expands numerical range expressions such as '1-3', '1, 3', '1–4' into [1, 2, 3].
        """
        nums: Set[int] = set()
        parts = re.split(r"[,;]+", inner_str)
        for part in parts:
            part = part.strip()
            range_match = re.match(r"^(\d+)\s*[-–—]\s*(\d+)$", part)
            if range_match:
                start, end = int(range_match.group(1)), int(range_match.group(2))
                if start <= end and end - start <= 20:  # Safe range bound
                    nums.update(range(start, end + 1))
            elif part.isdigit():
                nums.add(int(part))
        return sorted(list(nums))

    def extract_in_text_citations(self, text: str) -> List[Dict[str, Any]]:
        """
        Extracts all recognized in-text citation instances across multiple academic styles:
        1. Numeric IEEE / Bộ GD&ĐT: [1], [2], [1, 3], [1-3]
        2. Author-Year APA / Bộ GD&ĐT: (Author, 2023), (Author et al., 2023)
        3. Multiple Citations in single parentheses: (Author1, 2020; Author2, 2022)
        4. Narrative Citations: Author (2024), Author et al. (2023)
        """
        extracted: List[Dict[str, Any]] = []

        # 1. Numeric IEEE / Bộ GD&ĐT: [1], [2], [1-3], [1, 3]
        for match in re.finditer(r"\[(\d+(?:\s*[,-–—]\s*\d+)*)\]", text):
            raw = match.group(0)
            inner = match.group(1)
            nums = self.expand_numeric_citations(inner)
            if nums:
                extracted.append({
                    "type": "numeric",
                    "raw": raw,
                    "indices": nums,
                    "span": match.span(),
                })

        # 2. Parenthesized Author-Year (Handles single and multiple citations separated by ';'):
        # Matches: (Smith, 2020; Johnson, 2022) or (Nguyen & Tran, 2023)
        for match in re.finditer(r"\(([^)]*?(?:19|20)\d{2}[^)]*?)\)", text):
            raw = match.group(0)
            inner = match.group(1).strip()
            # Split by semicolon if multiple citations are combined
            sub_entries = [e.strip() for e in inner.split(";") if e.strip()]
            for entry in sub_entries:
                sub_match = re.search(r"([A-ZÀ-Ỹa-zà-ỹ\s&,\.]+?)[,\s]+((?:19|20)\d{2}[a-z]?)", entry)
                if sub_match:
                    author_part = sub_match.group(1).strip()
                    year_part = int(sub_match.group(2)[:4])
                    extracted.append({
                        "type": "author_year",
                        "raw": f"({entry})",
                        "author_text": author_part,
                        "year": year_part,
                        "span": match.span(),
                    })

        # 3. Narrative Citations (Author outside parentheses, Year inside):
        # Matches: "Smith (2024)", "Vaswani et al. (2017)", "Nguyễn Văn An và cộng sự (2023)"
        narrative_pattern = (
            r"\b([A-ZÀ-Ỹ][a-zà-ỹA-ZÀ-Ỹ]+(?:\s+(?:et\s+al\.|và\s+cs\.|và\s+ctg\.|\&\s+[A-ZÀ-Ỹ][a-zà-ỹA-ZÀ-Ỹ]+|and\s+[A-ZÀ-Ỹ][a-zà-ỹA-ZÀ-Ỹ]+))?)"
            r"\s*\(((?:19|20)\d{2}[a-z]?)\)"
        )
        for match in re.finditer(narrative_pattern, text):
            raw = match.group(0)
            author_part = match.group(1).strip()
            year_part = int(match.group(2)[:4])
            extracted.append({
                "type": "narrative",
                "raw": raw,
                "author_text": author_part,
                "year": year_part,
                "span": match.span(),
            })

        return extracted

    def cross_reference_citations(
        self,
        in_text_citations: List[Dict[str, Any]],
        selected_papers: List[Any],
        citation_style: str = "apa7",
    ) -> Tuple[List[str], List[str], List[UncitedPaperItem], int]:
        """
        Executes bidirectional cross-referencing between in-text citations and Selected Papers:
        1. In-text -> SelectedPapers: Detect ghost citations, author mismatches, or year discrepancies.
        2. IEEE sequential appearance order validation.
        3. SelectedPapers -> In-text: Identify uncited selected papers with formatted in_text_code.

        Returns: (invalid_citations, citation_warnings, uncited_papers, verified_count)
        """
        invalid_citations: List[str] = []
        citation_warnings: List[str] = []
        verified_count = 0
        style_enum = CitationStyle(citation_style.lower()) if citation_style.lower() in [s.value for s in CitationStyle] else CitationStyle.APA7

        # Build normalized lookup catalog for Selected Papers
        paper_catalog: List[Dict[str, Any]] = []
        for idx, sp in enumerate(selected_papers):
            meta = self.normalize_paper_metadata(sp)
            paper_id = getattr(sp, "id", None) or (sp.get("id") if isinstance(sp, dict) else str(idx + 1))

            # Extract normalized author surnames for fuzzy matching
            surnames = []
            for a in meta.authors:
                clean_name = a.replace(",", " ").strip()
                tokens = [t.strip().lower() for t in clean_name.split() if len(t.strip()) > 1]
                if tokens:
                    surnames.append(tokens[0])   # First name / Vietnamese surname
                    surnames.append(tokens[-1])  # Last name / Western surname

            # Precompute in-text citation code for this paper
            formatted_in_text = self.formatter.format_citation(meta, style=style_enum, index=idx + 1).in_text_citation

            paper_catalog.append({
                "index": idx + 1,
                "id": str(paper_id),
                "meta": meta,
                "surnames": surnames,
                "in_text_code": formatted_in_text,
                "cited": False,
            })

        # --- Direction 1: Validate In-text Citations against Catalog ---
        seen_numeric_indices: List[int] = []

        for cite in in_text_citations:
            if cite["type"] == "numeric":
                for idx in cite["indices"]:
                    matching = next((p for p in paper_catalog if p["index"] == idx), None)
                    if matching:
                        matching["cited"] = True
                        verified_count += 1
                        if idx not in seen_numeric_indices:
                            # Validate IEEE sequential order: check if an unencountered lower index was skipped
                            if style_enum == CitationStyle.IEEE:
                                if not seen_numeric_indices and idx != 1:
                                    warn_msg = (
                                        f"Quy tắc IEEE yêu cầu trích dẫn số xuất hiện tuần tự bắt đầu từ [1]. "
                                        f"Hiện tại trích dẫn đầu tiên trong bài là [{idx}]."
                                    )
                                    if warn_msg not in citation_warnings:
                                        citation_warnings.append(warn_msg)
                                elif seen_numeric_indices:
                                    expected_next = max(seen_numeric_indices) + 1
                                    if idx > expected_next and any(p["index"] < idx and not p["cited"] for p in paper_catalog):
                                        warn_msg = (
                                            f"Quy tắc IEEE yêu cầu trích dẫn số xuất hiện tuần tự theo thứ tự xuất hiện đầu tiên. "
                                            f"Trích dẫn [{idx}] xuất hiện trước khi [{min(expected_next, len(paper_catalog))}] được sử dụng."
                                        )
                                        if warn_msg not in citation_warnings:
                                            citation_warnings.append(warn_msg)
                            seen_numeric_indices.append(idx)
                    else:
                        invalid_citations.append(
                            f"Trích dẫn số [{idx}] không tồn tại trong danh mục {len(selected_papers)} tài liệu đã chọn của đề tài."
                        )

            elif cite["type"] in ("author_year", "narrative"):
                author_text = cite["author_text"].lower()
                year = cite["year"]

                # Find candidate papers matching author surname
                matching_author_papers = []
                for p in paper_catalog:
                    if any(s in author_text for s in p["surnames"]):
                        matching_author_papers.append(p)

                if not matching_author_papers:
                    invalid_citations.append(
                        f"Trích dẫn '{cite['raw']}' không tìm thấy tác giả '{cite['author_text']}' trong danh mục tài liệu đã chọn của đề tài."
                    )
                else:
                    # Check year alignment
                    exact_match = next((p for p in matching_author_papers if p["meta"].year == year), None)
                    if exact_match:
                        exact_match["cited"] = True
                        verified_count += 1
                    else:
                        candidate_years = ", ".join(str(p["meta"].year) for p in matching_author_papers)
                        p_titles = ' / '.join(f"'{p['meta'].title}'" for p in matching_author_papers)
                        invalid_citations.append(
                            f"Trích dẫn '{cite['raw']}' sai năm xuất bản. Tài liệu tương ứng ({p_titles}) có năm xuất bản là: {candidate_years}."
                        )

        # --- Direction 2: Identify Uncited Selected Papers ---
        uncited_papers: List[UncitedPaperItem] = []
        for p in paper_catalog:
            if not p["cited"]:
                uncited_papers.append(
                    UncitedPaperItem(
                        id=p["id"],
                        title=p["meta"].title,
                        authors=p["meta"].authors,
                        year=p["meta"].year,
                        in_text_code=p["in_text_code"],
                        suggested_action=f"Tài liệu này đã lưu trong đề tài nhưng chưa trích dẫn. Hãy cân nhắc chèn {p['in_text_code']} vào các luận điểm liên quan.",
                    )
                )

        return invalid_citations, citation_warnings, uncited_papers, verified_count

    async def arbitrate_claims_with_llm(
        self,
        candidate_claims: List[str],
        selected_papers: List[Any],
        citation_style: str = "apa7",
    ) -> List[MissingCitationClaim]:
        """
        Phase 2 (Semantic Arbitrator): Uses LLM to evaluate suspicious candidate sentences.
        - Eliminates false positives (self-contributions, common knowledge).
        - Matches verified empirical claims with relevant papers from selected_papers.
        """
        if not candidate_claims:
            return []

        # Prepare a concise summary of selected papers for prompt injection
        catalog_items = []
        for idx, sp in enumerate(selected_papers):
            meta = self.normalize_paper_metadata(sp)
            p_id = getattr(sp, "id", None) or (sp.get("id") if isinstance(sp, dict) else str(idx + 1))
            authors_str = ", ".join(meta.authors[:2]) + (" et al." if len(meta.authors) > 2 else "")
            catalog_items.append(f"[{p_id}] '{meta.title}' ({authors_str}, {meta.year})")
        catalog_summary = "\n".join(catalog_items) if catalog_items else "(Chưa có tài liệu nào trong đề tài)"

        system_prompt = (
            "Bạn là chuyên gia cố vấn học thuật (Academic Citation Coach). "
            "Nhiệm vụ của bạn là thẩm định ngữ nghĩa các câu văn nghi vấn xem có thực sự cần trích dẫn tài liệu khoa học hay không."
        )

        user_prompt = (
            f"DANH MỤC TÀI LIỆU ĐÃ CHỌN CỦA ĐỀ TÀI:\n{catalog_summary}\n\n"
            f"CÁC CÂU NGHI VẤN CẦN THẨM ĐỊNH NGỮ NGHĨA:\n"
            + "\n".join([f"- {c}" for c in candidate_claims])
            + "\n\nQUY TẮC THẨM ĐỊNH:\n"
            "1. is_claim_requiring_citation = true: Khi câu chứa số liệu thống kê, tỷ lệ %, phát hiện thực nghiệm hoặc nhận định lý thuyết của bên thứ ba cần dẫn chứng khoa học.\n"
            "2. is_claim_requiring_citation = false: Khi câu là nghiên cứu/phương pháp/kết quả do CHÍNH TÁC GIẢ làm (dùng 'chúng tôi', 'đồ án này', 'mô hình đề xuất') hoặc là kiến thức hiển nhiên/phổ thông.\n"
            "3. Nếu cần trích dẫn, hãy kiểm tra danh mục tài liệu trên và chọn bài báo phù hợp nhất (nếu có) để gán recommended_paper_id, recommended_paper_title và in_text_suggestion."
        )

        try:
            analysis: SemanticCitationAnalysis = await self.llm_service.generate_structured_output(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                schema=SemanticCitationAnalysis,
                temperature=0.2,
                timeout=8.0,
            )

            verified_missing: List[MissingCitationClaim] = []
            for item in analysis.analyzed_claims:
                if item.is_claim_requiring_citation:
                    verified_missing.append(
                        MissingCitationClaim(
                            sentence=item.sentence,
                            reason=item.reason or "Chứa số liệu định lượng hoặc nhận định lý thuyết cần dẫn chứng khoa học",
                            suggested_action=f"Cân nhắc trích dẫn {item.in_text_suggestion}" if item.in_text_suggestion else "Bổ sung trích dẫn tài liệu tham khảo cho luận điểm này.",
                            recommended_paper_id=item.recommended_paper_id,
                            recommended_paper_title=item.recommended_paper_title,
                            in_text_suggestion=item.in_text_suggestion,
                        )
                    )
            return verified_missing

        except Exception as err:
            logger.warning(f"LLM semantic arbitration failed or timed out: {err}. Falling back to deterministic claims.")
            # Resilient fallback: return candidate claims with standard template
            fallback_claims: List[MissingCitationClaim] = []
            for c in candidate_claims:
                fallback_claims.append(
                    MissingCitationClaim(
                        sentence=c,
                        reason="Chứa dữ liệu số liệu định lượng, thống kê hoặc nhận định khẳng định cần dẫn chứng khoa học",
                        suggested_action="Bổ sung trích dẫn tài liệu tham khảo để chứng minh cho số liệu hoặc luận điểm này.",
                    )
                )
            return fallback_claims

    def generate_project_bibliography(
        self,
        selected_papers: List[Any],
        citation_style: str = "apa7",
    ) -> List[str]:
        """Generates sorted and standardized full bibliography entries for the project."""
        if not selected_papers:
            return []

        style_enum = CitationStyle(citation_style.lower()) if citation_style.lower() in [s.value for s in CitationStyle] else CitationStyle.APA7
        metadatas = [self.normalize_paper_metadata(sp) for sp in selected_papers]

        res = self.formatter.format_bibliography(metadatas=metadatas, style=style_enum)
        return res.citations

    async def check_document_citations(
        self,
        content: str,
        selected_papers: List[Any],
        citation_style: str = "apa7",
    ) -> CitationCheckResponse:
        """
        Hybrid Citation Check Pipeline:
        Phase 1 (Deterministic Core):
        1. Preprocess & tokenize sentences (protecting abbreviations like 'et al.').
        2. Extract in-text citations (numeric ranges, APA parenthesized, narrative).
        3. Deterministic cross-reference (ghost citations, year checks, IEEE order, uncited papers).
        4. Heuristic pre-filter of candidate missing claims (0 token cost).

        Phase 2 (Semantic Arbitrator):
        5. LLM filters out author self-claims and common knowledge, and matches candidate claims
           with suitable papers in selected_papers.
        """
        plain_text = self.clean_html_to_text(content)
        sentences = self.split_into_sentences(plain_text)

        # --- Phase 1: Deterministic In-text Extraction & Cross-referencing ---
        in_text_citations = self.extract_in_text_citations(plain_text)

        invalid_citations, citation_warnings, uncited_papers, verified_count = self.cross_reference_citations(
            in_text_citations=in_text_citations,
            selected_papers=selected_papers,
            citation_style=citation_style,
        )

        # Fast heuristic candidate pre-filtering
        candidate_claims = self.detect_candidate_missing_claims(sentences)

        # --- Phase 2: LLM Semantic Arbitration ---
        missing_claims = await self.arbitrate_claims_with_llm(
            candidate_claims=candidate_claims,
            selected_papers=selected_papers,
            citation_style=citation_style,
        )

        total_issues = len(missing_claims) + len(invalid_citations) + len(citation_warnings)

        return CitationCheckResponse(
            total_issues=total_issues,
            missing_claims=missing_claims,
            invalid_citations=invalid_citations,
            citation_warnings=citation_warnings,
            uncited_papers=uncited_papers,
            verified_count=verified_count,
            credits_charged=2,
        )


# Singleton instance for convenient reuse
citation_agent = CitationAgent()
