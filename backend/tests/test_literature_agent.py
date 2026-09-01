import pytest
from unittest.mock import AsyncMock

from backend.schemas.literature_schemas import (
    PaperSource,
    QueryGeneratorResponse,
    SearchQueryItem,
    PaperSummaryResponse,
)
from backend.services.scholar_service import scholar_service
from backend.services.arxiv_service import arxiv_service
from backend.services.openalex_service import openalex_service
from backend.services.search_aggregator import search_aggregator
from backend.services.ai_use_logger import AIUseLogger
from backend.agents.literature_agent import LiteratureAgent


def test_services_initialized():
    """Verify all 3 services and aggregator are successfully initialized."""
    assert scholar_service is not None
    assert arxiv_service is not None
    assert openalex_service is not None
    assert search_aggregator is not None
    assert search_aggregator.scholar_client is not None
    assert search_aggregator.arxiv_client is not None
    assert search_aggregator.openalex_client is not None


def test_doi_normalization():
    """Test DOI cleaning helper across multiple formats."""
    assert search_aggregator.normalize_doi("https://doi.org/10.1016/j.neucom.2020.01") == "10.1016/j.neucom.2020.01"
    assert search_aggregator.normalize_doi("http://doi.org/10.1016/j.neucom.2020.01") == "10.1016/j.neucom.2020.01"
    assert search_aggregator.normalize_doi("doi: 10.1016/j.neucom.2020.01") == "10.1016/j.neucom.2020.01"
    assert search_aggregator.normalize_doi("  10.1016/J.NEUCOM.2020.01  ") == "10.1016/j.neucom.2020.01"
    assert search_aggregator.normalize_doi(None) is None


def test_title_normalization():
    """Test title cleaning helper."""
    assert (
        search_aggregator.normalize_title("Deep Residual Learning for Image Recognition!")
        == "deep residual learning for image recognition"
    )
    assert (
        search_aggregator.normalize_title("BERT:   Pre-training of Deep...")
        == "bert pre training of deep"
    )


@pytest.mark.asyncio
async def test_ai_use_logger_credit_calculation():
    """Test token to credit conversion logic."""
    logger = AIUseLogger()
    assert logger.calculate_credits(0) == 0
    assert logger.calculate_credits(500) == 1
    assert logger.calculate_credits(1000) == 1
    assert logger.calculate_credits(1200) == 2
    assert logger.calculate_credits(5000) == 5


@pytest.mark.asyncio
async def test_literature_agent_generate_queries():
    """Test Query Generator prompt strategy and response formatting."""
    mock_llm = AsyncMock()
    mock_llm.generate_structured_output_with_usage.return_value = (
        QueryGeneratorResponse(
            queries=[
                "Deep learning for academic writing assistant",
                "Automated outline generation NLP",
                "LLM literature review automation",
                "Tóm tắt bài báo khoa học tự động",
            ],
            search_queries=[
                SearchQueryItem(query="Deep learning for academic writing assistant", language="en", target_aspect="Core concept"),
                SearchQueryItem(query="Automated outline generation NLP", language="en", target_aspect="Methodology"),
                SearchQueryItem(query="LLM literature review automation", language="en", target_aspect="Application"),
                SearchQueryItem(query="Tóm tắt bài báo khoa học tự động", language="vi", target_aspect="Vietnamese context"),
            ],
            explanation="Generated 4 queries covering deep learning, outline generation, and literature review.",
        ),
        {"prompt_tokens": 150, "completion_tokens": 80, "total_tokens": 230},
    )

    mock_logger = AsyncMock()
    agent = LiteratureAgent(llm_service_instance=mock_llm, logger_instance=mock_logger)

    res = await agent.generate_queries(
        topic="Ứng dụng AI trong hỗ trợ viết bài báo khoa học",
        outline="1. Mở đầu\n2. Phương pháp\n3. Thử nghiệm",
        user_id="user_123",
        project_id="proj_456",
    )

    assert len(res.queries) == 4
    assert res.queries[0] == "Deep learning for academic writing assistant"
    assert res.search_queries[3].language == "vi"

    # Verify logger recorded tokens & agent name
    mock_logger.log_ai_usage.assert_called_once()
    call_args = mock_logger.log_ai_usage.call_args[1]
    assert call_args["agent_name"] == "LiteratureAgent.generate_queries"
    assert call_args["tokens_used"] == 230
    assert call_args["user_id"] == "user_123"
    assert call_args["project_id"] == "proj_456"


@pytest.mark.asyncio
async def test_literature_agent_summarize_paper():
    """Test LLM Summarizer prompt strategy (2-3 Vietnamese sentences & relevance score)."""
    mock_llm = AsyncMock()
    mock_llm.generate_structured_output_with_usage.return_value = (
        PaperSummaryResponse(
            summary_vi=(
                "Bài báo đề xuất mô hình Transformer nâng cao để tự động phân tích và tóm tắt bài báo học thuật. "
                "Phương pháp áp dụng thuật toán chú ý đa đầu giúp trích xuất các ý chính của Abstract với độ chính xác cao. "
                "Nghiên cứu thể hiện đóng góp lớn cho hệ thống hỗ trợ viết báo khoa học."
            ),
            relevance_score=0.92,
            key_findings=[
                "Tăng độ chính xác tóm tắt văn bản học thuật lên 15%",
                "Rút ngắn thời gian xử lý Abstract bài báo",
            ],
        ),
        {"prompt_tokens": 210, "completion_tokens": 120, "total_tokens": 330},
    )

    mock_logger = AsyncMock()
    agent = LiteratureAgent(llm_service_instance=mock_llm, logger_instance=mock_logger)

    res = await agent.summarize_paper(
        title="Automated Academic Abstract Summarization using Transformer Models",
        abstract="This paper proposes an enhanced Transformer model for academic document summarization...",
        topic="Ứng dụng AI trong hỗ trợ viết bài báo khoa học",
        user_id="user_123",
        project_id="proj_456",
    )

    assert 0.0 <= res.relevance_score <= 1.0
    assert res.relevance_score == 0.92
    assert "Bài báo đề xuất" in res.summary_vi

    # Verify logger recorded tokens & agent name
    mock_logger.log_ai_usage.assert_called_once()
    call_args = mock_logger.log_ai_usage.call_args[1]
    assert call_args["agent_name"] == "LiteratureAgent.summarize_paper"
    assert call_args["tokens_used"] == 330
    assert call_args["user_id"] == "user_123"


