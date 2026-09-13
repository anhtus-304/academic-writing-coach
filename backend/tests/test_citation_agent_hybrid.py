import os
import sys
import pytest
from unittest.mock import AsyncMock, patch

# Ensure backend root is in sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from agents.citation_agent import CitationAgent, SemanticCitationAnalysis, ClaimAnalysisItem
from schemas.citation_schemas import DocumentType, CitationStyle


@pytest.fixture
def sample_papers():
    return [
        {
            "id": "paper-1",
            "title": "Attention Is All You Need",
            "authors": ["Vaswani, Ashish", "Shazeer, Noam"],
            "year": 2017,
            "doc_type": DocumentType.CONFERENCE,
        },
        {
            "id": "paper-2",
            "title": "Deep Residual Learning for Image Recognition",
            "authors": ["He, Kaiming", "Zhang, Xiangyu"],
            "year": 2016,
            "doc_type": DocumentType.JOURNAL,
        },
        {
            "id": "paper-3",
            "title": "Generative Adversarial Nets",
            "authors": ["Goodfellow, Ian", "Bengio, Yoshua"],
            "year": 2014,
            "doc_type": DocumentType.JOURNAL,
        },
    ]


def test_abbreviation_dot_protection():
    agent = CitationAgent()
    text = (
        "Theo nghiên cứu của Vaswani et al. (2017), kiến trúc Transformer có hiệu quả vượt trội. "
        "TS. Nguyễn Văn A cùng GS. Trần Văn B cũng đồng thuận với nhận định này."
    )
    sentences = agent.split_into_sentences(text)
    assert len(sentences) == 2
    assert "et al." in sentences[0]
    assert "TS. Nguyễn Văn A" in sentences[1]


def test_ieee_numeric_range_expansion(sample_papers):
    agent = CitationAgent()
    text = "Các mô hình học sâu hiện đại đã có bước tiến lớn [1-3]."
    res = agent.extract_in_text_citations(text)
    assert len(res) == 1
    assert res[0]["type"] == "numeric"
    assert res[0]["indices"] == [1, 2, 3]

    invalid, warnings, uncited, verified = agent.cross_reference_citations(
        in_text_citations=res,
        selected_papers=sample_papers,
        citation_style="ieee",
    )
    assert verified == 3
    assert len(uncited) == 0
    assert len(invalid) == 0


def test_narrative_citation(sample_papers):
    agent = CitationAgent()
    text = "Vaswani et al. (2017) đã đề xuất cơ chế tự chú ý giúp tăng tốc độ huấn luyện."
    cites = agent.extract_in_text_citations(text)
    assert len(cites) >= 1
    narrative_cite = next((c for c in cites if c["type"] == "narrative"), None)
    assert narrative_cite is not None
    assert "Vaswani" in narrative_cite["author_text"]
    assert narrative_cite["year"] == 2017

    invalid, warnings, uncited, verified = agent.cross_reference_citations(
        in_text_citations=cites,
        selected_papers=sample_papers,
        citation_style="apa7",
    )
    assert verified == 1
    assert len(invalid) == 0


def test_multiple_citations_in_one_bracket(sample_papers):
    agent = CitationAgent()
    text = "Các kiến trúc học sâu kinh điển đã được chứng minh hiệu quả (Vaswani et al., 2017; He et al., 2016)."
    cites = agent.extract_in_text_citations(text)
    assert len(cites) == 2

    invalid, warnings, uncited, verified = agent.cross_reference_citations(
        in_text_citations=cites,
        selected_papers=sample_papers,
        citation_style="apa7",
    )
    assert verified == 2
    assert len(invalid) == 0


def test_ieee_out_of_order_warning(sample_papers):
    agent = CitationAgent()
    text = "Đoạn văn đầu tiên sử dụng kiến trúc [2]. Đoạn văn tiếp theo sử dụng [1]."
    cites = agent.extract_in_text_citations(text)
    invalid, warnings, uncited, verified = agent.cross_reference_citations(
        in_text_citations=cites,
        selected_papers=sample_papers,
        citation_style="ieee",
    )
    assert len(warnings) > 0
    assert any("Quy tắc IEEE yêu cầu trích dẫn số xuất hiện tuần tự" in w for w in warnings)


def test_self_claim_filtering():
    agent = CitationAgent()
    text = [
        "Trong đồ án này, chúng tôi đã tăng số lượng epoch lên 100 và đạt độ chính xác 95%.",
        "Mục tiêu của nghiên cứu này là tối ưu hóa tài nguyên phần cứng đạt 40%.",
        "Theo một nghiên cứu độc lập, 85% doanh nghiệp thất bại khi triển khai giải pháp mới.",
    ]
    candidates = agent.detect_candidate_missing_claims(text)
    # The first two sentences should be filtered out because they are author self-contributions
    assert len(candidates) == 1
    assert "85% doanh nghiệp" in candidates[0]


def test_uncited_papers_in_text_code(sample_papers):
    agent = CitationAgent()
    invalid, warnings, uncited, verified = agent.cross_reference_citations(
        in_text_citations=[],
        selected_papers=sample_papers,
        citation_style="apa7",
    )
    assert len(uncited) == 3
    assert uncited[0].in_text_code is not None
    assert "Vaswani" in uncited[0].in_text_code


@pytest.mark.asyncio
async def test_semantic_arbitration_mocked(sample_papers):
    mock_analysis = SemanticCitationAnalysis(
        analyzed_claims=[
            ClaimAnalysisItem(
                sentence="Theo thống kê, 85% doanh nghiệp thất bại khi áp dụng AI.",
                is_claim_requiring_citation=True,
                reason="Số liệu thống kê vĩ mô cần nguồn dẫn chứng",
                recommended_paper_id="paper-1",
                recommended_paper_title="Attention Is All You Need",
                in_text_suggestion="(Vaswani & Shazeer, 2017)",
            ),
            ClaimAnalysisItem(
                sentence="Mạng Internet đóng vai trò cực kỳ quan trọng trong đời sống hiện nay.",
                is_claim_requiring_citation=False,
                reason="Kiến thức phổ thông",
            ),
        ]
    )

    mock_llm = AsyncMock()
    mock_llm.generate_structured_output.return_value = mock_analysis

    agent = CitationAgent(llm_service_instance=mock_llm)
    candidates = [
        "Theo thống kê, 85% doanh nghiệp thất bại khi áp dụng AI.",
        "Mạng Internet đóng vai trò cực kỳ quan trọng trong đời sống hiện nay.",
    ]

    claims = await agent.arbitrate_claims_with_llm(candidates, sample_papers, citation_style="apa7")
    assert len(claims) == 1
    assert claims[0].recommended_paper_id == "paper-1"
    assert claims[0].recommended_paper_title == "Attention Is All You Need"
    assert claims[0].in_text_suggestion == "(Vaswani & Shazeer, 2017)"
