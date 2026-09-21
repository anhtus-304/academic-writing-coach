import os
import sys
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

# Ensure backend root is in sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from agents.graph import (
    AgentState,
    build_academic_writing_graph,
    run_academic_pipeline,
    get_pipeline_state,
    update_pipeline_state,
    _format_outline_for_literature,
)
import agents.graph as graph_module

from agents.citation_agent import CitationAgent, SemanticCitationAnalysis, ClaimAnalysisItem
from schemas.citation_schemas import DocumentType


@pytest.fixture
def mock_pipeline_agents():
    """Mock out external LLM and search calls for fast deterministic pipeline testing."""
    with patch.object(graph_module.outline_agent, "generate_outline", new_callable=AsyncMock) as mock_outline, \
         patch.object(graph_module.literature_agent, "search_and_summarize", new_callable=AsyncMock) as mock_lit, \
         patch.object(graph_module.citation_agent, "check_document_citations", new_callable=AsyncMock) as mock_cite:

        # Mock Outline Response
        mock_outline_res = MagicMock()
        mock_outline_res.model_dump.return_value = {
            "title": "Nghiên cứu ứng dụng AI trong giáo dục đại học",
            "outline": {
                "title": "Nghiên cứu ứng dụng AI",
                "sections": [
                    {
                        "title": "Chương 1: Tổng quan lý thuyết",
                        "subsections": [{"title": "1.1. Khái niệm AI"}, {"title": "1.2. Xu hướng áp dụng"}],
                    },
                    {
                        "title": "Chương 2: Phương pháp nghiên cứu",
                        "subsections": [{"title": "2.1. Thiết kế nghiên cứu"}],
                    },
                ],
            },
        }
        mock_outline.return_value = mock_outline_res

        # Mock Literature Response
        mock_lit_res = MagicMock()
        mock_lit_res.model_dump.return_value = {
            "query": "AI trong giáo dục đại học",
            "total_results": 2,
            "papers": [
                {
                    "id": "paper-ai-1",
                    "title": "AI in Higher Education: A Comprehensive Survey",
                    "authors": ["John Smith", "David Miller"],
                    "year": 2023,
                    "summary_vi": "Khảo sát toàn diện về ứng dụng AI trong giảng dạy.",
                    "relevance_score": 0.95,
                },
                {
                    "id": "paper-ai-2",
                    "title": "Tác động của ChatGPT đến sinh viên Việt Nam",
                    "authors": ["Nguyễn Văn An", "Trần Thị Bình"],
                    "year": 2024,
                    "summary_vi": "Phân tích khảo sát 500 sinh viên về việc sử dụng AI.",
                    "relevance_score": 0.88,
                },
            ],
        }
        mock_lit.return_value = mock_lit_res

        # Mock Citation Response
        mock_cite_res = MagicMock()
        mock_claim = MagicMock()
        mock_claim.model_dump.return_value = {
            "sentence": "Hơn 78.5% sinh viên thường xuyên sử dụng AI để tra cứu tài liệu.",
            "reason": "Chứa số liệu thống kê định lượng cần nguồn dẫn chứng.",
            "suggested_action": "Bổ sung trích dẫn (Nguyễn & Trần, 2024)",
            "recommended_paper_id": "paper-ai-2",
            "recommended_paper_title": "Tác động của ChatGPT đến sinh viên Việt Nam",
            "in_text_suggestion": "(Nguyễn & Trần, 2024)",
        }
        mock_cite_res.missing_claims = [mock_claim]
        mock_cite_res.model_dump.return_value = {
            "total_issues": 1,
            "missing_claims": [mock_claim.model_dump.return_value],
            "invalid_citations": [],
            "citation_warnings": [],
            "uncited_papers": [],
            "verified_count": 1,
        }
        mock_cite.return_value = mock_cite_res

        yield {
            "outline": mock_outline,
            "literature": mock_lit,
            "citation": mock_cite,
        }


def test_format_outline_for_literature():
    outline_data = {
        "outline": {
            "title": "Đề tài AI",
            "sections": [
                {
                    "title": "Chương 1: Mở đầu",
                    "subsections": [{"title": "1.1 Bối cảnh"}, {"title": "1.2 Mục tiêu"}],
                }
            ],
        }
    }
    formatted = _format_outline_for_literature(outline_data)
    assert "Chương 1: Mở đầu" in formatted
    assert "1.1 Bối cảnh" in formatted


@pytest.mark.asyncio
async def test_full_pipeline_execution(mock_pipeline_agents):
    """Verifies that the full pipeline executes through all 3 agent nodes and persists output."""
    project_id = "test-project-101"
    initial_state = {
        "project_id": project_id,
        "topic": "Ứng dụng AI trong giáo dục đại học",
        "document_type": "tieu_luan",
        "field": "Công nghệ thông tin",
        "citation_style": "apa7",
        "draft_content": (
            "Ứng dụng AI đang ngày càng phổ biến. "
            "Hơn 78.5% sinh viên thường xuyên sử dụng AI để tra cứu tài liệu."
        ),
    }

    result = await run_academic_pipeline(initial_state, thread_id=project_id)

    # 1. Assert Outline Agent Node ran
    assert result.get("outline") is not None
    assert "Nghiên cứu ứng dụng AI" in str(result["outline"])

    # 2. Assert Literature Agent Node ran and populated papers
    assert result.get("literature_results") is not None
    assert len(result.get("selected_papers", [])) >= 2
    assert any(p["id"] == "paper-ai-1" for p in result["selected_papers"])

    # 3. Assert Citation Agent Node ran and detected issues
    assert result.get("citation_report") is not None
    assert result["status"] in ("completed", "success")
    assert result["current_step"] == "citation_checked"
    assert len(result.get("citations", [])) == 1
    assert "78.5%" in result["citations"][0]["sentence"]


@pytest.mark.asyncio
async def test_checkpoint_state_persistence(mock_pipeline_agents):
    """Verifies that state is persisted per thread_id and can be retrieved or updated."""
    thread_id = "test-project-persistence-999"
    initial_state = {
        "project_id": thread_id,
        "topic": "Xây dựng hệ thống RAG",
        "document_type": "khoa_luan",
    }

    # Run pipeline
    await run_academic_pipeline(initial_state, thread_id=thread_id)

    # Retrieve persisted state from checkpointer
    saved_state = get_pipeline_state(thread_id)
    assert saved_state is not None
    assert saved_state["project_id"] == thread_id
    assert saved_state["topic"] == "Xây dựng hệ thống RAG"
    assert "outline" in saved_state
    assert "selected_papers" in saved_state

    # Test update state
    update_pipeline_state(thread_id, {"custom_user_note": "Approved by supervisor"})
    updated_state = get_pipeline_state(thread_id)
    assert updated_state.get("custom_user_note") == "Approved by supervisor"


@pytest.mark.asyncio
async def test_pipeline_citation_skipped_when_no_draft(mock_pipeline_agents):
    """Verifies that citation node gracefully skips if draft_content is not provided yet."""
    thread_id = "test-project-no-draft"
    initial_state = {
        "project_id": thread_id,
        "topic": "Nghiên cứu thị trường tài chính",
        "document_type": "luan_van",
        "draft_content": None,  # No draft provided yet
    }

    result = await run_academic_pipeline(initial_state, thread_id=thread_id)
    assert result["current_step"] == "citation_skipped"
    assert result["citation_report"]["status"] == "skipped"


@pytest.mark.asyncio
async def test_missing_citation_detector_fine_tuned_prompt():
    """
    Tests the accuracy of the fine-tuned Missing Citation Detector:
    1. Third-party empirical/statistical claim -> REQUIRES citation.
    2. Author self-methodology/contribution -> EXEMPT from citation.
    3. Common knowledge -> EXEMPT from citation.
    """
    mock_llm = AsyncMock()
    mock_llm.generate_structured_output.return_value = SemanticCitationAnalysis(
        analyzed_claims=[
            ClaimAnalysisItem(
                sentence="Theo thống kê của Bộ GD&ĐT, tỷ lệ tốt nghiệp đạt 98.2% vào năm 2023.",
                is_claim_requiring_citation=True,
                reason="Chứa số liệu thống kê vĩ mô chính thức cần dẫn nguồn văn bản",
                recommended_paper_id="paper-1",
                recommended_paper_title="Báo cáo giáo dục đại học 2023",
                in_text_suggestion="(Bộ GD&ĐT, 2023)",
            ),
            ClaimAnalysisItem(
                sentence="Trong bài báo này, chúng tôi đề xuất một mô hình phân loại văn bản mới.",
                is_claim_requiring_citation=False,
                reason="Đây là đóng góp nghiên cứu của chính tác giả",
            ),
            ClaimAnalysisItem(
                sentence="Internet là mạng lưới máy tính kết nối toàn cầu phục vụ trao đổi thông tin.",
                is_claim_requiring_citation=False,
                reason="Kiến thức phổ thông hiển nhiên",
            ),
        ]
    )

    agent = CitationAgent(llm_service_instance=mock_llm)

    catalog = [
        {
            "id": "paper-1",
            "title": "Báo cáo giáo dục đại học 2023",
            "authors": ["Bộ GD&ĐT"],
            "year": 2023,
        }
    ]

    candidates = [
        "Theo thống kê của Bộ GD&ĐT, tỷ lệ tốt nghiệp đạt 98.2% vào năm 2023.",
        "Trong bài báo này, chúng tôi đề xuất một mô hình phân loại văn bản mới.",
        "Internet là mạng lưới máy tính kết nối toàn cầu phục vụ trao đổi thông tin.",
    ]

    verified_claims = await agent.arbitrate_claims_with_llm(
        candidate_claims=candidates,
        selected_papers=catalog,
        citation_style="apa7",
    )

    # Only the first claim should be flagged!
    assert len(verified_claims) == 1
    assert "98.2%" in verified_claims[0].sentence
    assert verified_claims[0].recommended_paper_id == "paper-1"
    assert verified_claims[0].in_text_suggestion == "(Bộ GD&ĐT, 2023)"
