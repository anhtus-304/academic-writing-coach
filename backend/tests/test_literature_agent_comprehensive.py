import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic import ValidationError

from backend.schemas.literature_schemas import (
    PaperSource,
    PaperSchema,
    AuthorSchema,
    SearchResponseSchema,
    QueryGeneratorRequest,
    QueryGeneratorResponse,
    SearchQueryItem,
    PaperSummaryRequest,
    PaperSummaryResponse,
)
from backend.prompts.literature_prompts import (
    QUERY_GENERATOR_SYSTEM_PROMPT,
    QUERY_GENERATOR_USER_PROMPT_TEMPLATE,
    LLM_SUMMARIZER_SYSTEM_PROMPT,
    LLM_SUMMARIZER_USER_PROMPT_TEMPLATE,
)
from backend.services.ai_use_logger import AIUseLogger, ai_use_logger
from backend.agents.literature_agent import LiteratureAgent
from backend.services.llm_service import LLMService


# ==============================================================================
# 1. Prompt Template & Strategy Tests
# ==============================================================================

def test_query_generator_prompt_structure():
    """Verify Query Generator system prompt adheres to 3-5 queries and language requirements."""
    assert "3 đến 5" in QUERY_GENERATOR_SYSTEM_PROMPT or "3-5" in QUERY_GENERATOR_SYSTEM_PROMPT
    assert "tiếng Anh" in QUERY_GENERATOR_SYSTEM_PROMPT
    assert "tiếng Việt" in QUERY_GENERATOR_SYSTEM_PROMPT
    assert "JSON" in QUERY_GENERATOR_SYSTEM_PROMPT


def test_query_generator_user_prompt_formatting():
    """Test user prompt formatting with and without outline."""
    prompt_with_outline = QUERY_GENERATOR_USER_PROMPT_TEMPLATE.format(
        topic="Ứng dụng AI trong giáo dục đại học",
        outline="1. Đặt vấn đề\n2. Phương pháp\n3. Kết quả",
    )
    assert "Ứng dụng AI trong giáo dục đại học" in prompt_with_outline
    assert "1. Đặt vấn đề" in prompt_with_outline

    prompt_no_outline = QUERY_GENERATOR_USER_PROMPT_TEMPLATE.format(
        topic="Ứng dụng AI trong giáo dục đại học",
        outline="Không có dàn ý chi tiết.",
    )
    assert "Ứng dụng AI trong giáo dục đại học" in prompt_no_outline
    assert "Không có dàn ý chi tiết." in prompt_no_outline


def test_llm_summarizer_prompt_structure():
    """Verify LLM Summarizer system prompt enforces 2-3 Vietnamese sentences and relevance score."""
    assert "2 đến 3 câu" in LLM_SUMMARIZER_SYSTEM_PROMPT or "2-3 câu" in LLM_SUMMARIZER_SYSTEM_PROMPT
    assert "TIẾNG VIỆT" in LLM_SUMMARIZER_SYSTEM_PROMPT
    assert "relevance_score" in LLM_SUMMARIZER_SYSTEM_PROMPT
    assert "0.0 đến 1.0" in LLM_SUMMARIZER_SYSTEM_PROMPT


def test_llm_summarizer_user_prompt_formatting():
    """Test user prompt formatting with title, abstract, and topic."""
    prompt = LLM_SUMMARIZER_USER_PROMPT_TEMPLATE.format(
        topic="Nghiên cứu thị giác máy tính trong y tế",
        title="Deep Learning for Medical Imaging Analysis",
        abstract="This paper introduces a novel CNN architecture for tumor detection in MRI scans.",
    )
    assert "Nghiên cứu thị giác máy tính trong y tế" in prompt
    assert "Deep Learning for Medical Imaging Analysis" in prompt
    assert "tumor detection in MRI scans" in prompt


# ==============================================================================
# 2. Schema Validation Tests
# ==============================================================================

def test_query_generator_request_validation():
    """Test QueryGeneratorRequest schema bounds."""
    # Valid
    req = QueryGeneratorRequest(topic="Machine Learning in Agriculture", num_queries=4)
    assert req.topic == "Machine Learning in Agriculture"
    assert req.num_queries == 4

    # Invalid num_queries < 3
    with pytest.raises(ValidationError):
        QueryGeneratorRequest(topic="Valid topic", num_queries=2)

    # Invalid num_queries > 5
    with pytest.raises(ValidationError):
        QueryGeneratorRequest(topic="Valid topic", num_queries=6)


def test_paper_summary_response_relevance_score_bounds():
    """Test PaperSummaryResponse relevance_score boundary constraints (0.0 to 1.0)."""
    # Valid bounds
    valid_min = PaperSummaryResponse(summary_vi="Tóm tắt 1. Tóm tắt 2.", relevance_score=0.0)
    assert valid_min.relevance_score == 0.0

    valid_max = PaperSummaryResponse(summary_vi="Tóm tắt 1. Tóm tắt 2.", relevance_score=1.0)
    assert valid_max.relevance_score == 1.0

    valid_mid = PaperSummaryResponse(summary_vi="Tóm tắt 1. Tóm tắt 2.", relevance_score=0.85)
    assert valid_mid.relevance_score == 0.85

    # Out of bounds > 1.0
    with pytest.raises(ValidationError):
        PaperSummaryResponse(summary_vi="Tóm tắt", relevance_score=1.05)

    # Out of bounds < 0.0
    with pytest.raises(ValidationError):
        PaperSummaryResponse(summary_vi="Tóm tắt", relevance_score=-0.1)


# ==============================================================================
# 3. AI Use Logger Comprehensive Tests
# ==============================================================================

def test_ai_use_logger_credit_calculation_comprehensive():
    """Test credit calculation across multiple boundary conditions."""
    logger = AIUseLogger()
    assert logger.calculate_credits(0) == 0
    assert logger.calculate_credits(-50) == 0
    assert logger.calculate_credits(1) == 1
    assert logger.calculate_credits(999) == 1
    assert logger.calculate_credits(1000) == 1
    assert logger.calculate_credits(1001) == 2
    assert logger.calculate_credits(2000) == 2
    assert logger.calculate_credits(2001) == 3
    assert logger.calculate_credits(10500) == 11

    # Custom rate test
    assert logger.calculate_credits(1000, rate_per_1000_tokens=2.5) == 3


@pytest.mark.asyncio
async def test_ai_use_logger_log_ai_usage_with_db_session():
    """Test AIUseLogger when a DB session is provided."""
    logger = AIUseLogger()
    mock_db = AsyncMock()

    log_entry = await logger.log_ai_usage(
        agent_name="TestAgent",
        tokens_used=1500,
        user_id="usr_test_123",
        project_id="prj_test_456",
        input_summary={"prompt": "test prompt"},
        output_summary={"result": "test output"},
        duration_ms=450,
        db=mock_db,
    )

    assert log_entry is not None
    assert log_entry.agent_name == "TestAgent"
    assert log_entry.tokens_used == 1500
    assert log_entry.credits_charged == 2
    assert log_entry.user_id == "usr_test_123"
    assert log_entry.project_id == "prj_test_456"
    assert log_entry.duration_ms == 450

    mock_db.add.assert_called_once_with(log_entry)
    mock_db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_ai_use_logger_custom_credits_and_anonymous_user():
    """Test explicit credit charge override and anonymous user default."""
    logger = AIUseLogger()
    mock_db = AsyncMock()

    log_entry = await logger.log_ai_usage(
        agent_name="LiteratureAgent.generate_queries",
        tokens_used=800,
        user_id=None,  # Should become system_anonymous
        credits_charged=5,  # Explicit override
        db=mock_db,
    )

    assert log_entry.user_id == "system_anonymous"
    assert log_entry.credits_charged == 5


@pytest.mark.asyncio
async def test_ai_use_logger_resilience_on_db_exception():
    """Test that DB errors during logging are caught and do not crash the caller."""
    logger = AIUseLogger()
    failing_db = AsyncMock()
    failing_db.flush.side_effect = Exception("DB connection timeout")

    # Should not raise exception
    log_entry = await logger.log_ai_usage(
        agent_name="ResilienceTest",
        tokens_used=500,
        user_id="user_err",
        db=failing_db,
    )

    assert log_entry is not None
    assert log_entry.tokens_used == 500


# ==============================================================================
# 4. Literature Agent Detailed Functionality Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_generate_queries_without_outline_and_backfill():
    """Test query generator when outline is None and LLM returns only `queries` list."""
    mock_llm = AsyncMock()
    # LLM returns search_queries as empty, requiring agent to backfill
    mock_llm.generate_structured_output_with_usage.return_value = (
        QueryGeneratorResponse(
            queries=[
                "Artificial intelligence in higher education",
                "Machine learning predictive analytics students",
                "Ứng dụng trí tuệ nhân tạo trong đại học",
            ],
            search_queries=[],  # empty, should be backfilled
            explanation="Generated 3 queries",
        ),
        {"prompt_tokens": 120, "completion_tokens": 60, "total_tokens": 180},
    )

    mock_logger = AsyncMock()
    agent = LiteratureAgent(llm_service_instance=mock_llm, logger_instance=mock_logger)

    res = await agent.generate_queries(
        topic="Ứng dụng AI trong giáo dục",
        outline=None,
        user_id="u_01",
    )

    assert len(res.queries) == 3
    # Check backfilled search_queries
    assert len(res.search_queries) == 3
    assert res.search_queries[0].query == "Artificial intelligence in higher education"
    assert res.search_queries[0].language == "en"
    assert res.search_queries[2].query == "Ứng dụng trí tuệ nhân tạo trong đại học"
    # Vietnamese query detected
    assert res.search_queries[2].language in ["en", "vi"]

    # Verify logger was called
    mock_logger.log_ai_usage.assert_called_once()
    assert mock_logger.log_ai_usage.call_args[1]["tokens_used"] == 180


@pytest.mark.asyncio
async def test_summarize_paper_without_topic():
    """Test paper summarizer when topic is not explicitly provided."""
    mock_llm = AsyncMock()
    mock_llm.generate_structured_output_with_usage.return_value = (
        PaperSummaryResponse(
            summary_vi="Bài báo khảo sát các mô hình Transformer trong phân loại văn bản y tế. "
                       "Tác giả sử dụng kiến trúc BERT tinh chỉnh trên tập dữ liệu lâm sàng. "
                       "Kết quả đạt F1-score 94.5% vượt trội so với các phương pháp truyền thống.",
            relevance_score=0.88,
            key_findings=["F1 đạt 94.5%", "Giảm 30% thời gian huấn luyện"],
        ),
        {"prompt_tokens": 200, "completion_tokens": 100, "total_tokens": 300},
    )

    mock_logger = AsyncMock()
    agent = LiteratureAgent(llm_service_instance=mock_llm, logger_instance=mock_logger)

    res = await agent.summarize_paper(
        title="Clinical BERT for Text Classification",
        abstract="We investigate fine-tuning BERT on clinical medical notes for disease prediction...",
        topic=None,
    )

    assert res.relevance_score == 0.88
    assert "Bài báo khảo sát" in res.summary_vi
    assert len(res.key_findings) == 2
    mock_logger.log_ai_usage.assert_called_once()


@pytest.mark.asyncio
async def test_search_and_summarize_pipeline():
    """Test full pipeline: query gen -> search aggregator -> paper summarization -> relevance sorting."""
    # Mock LLM
    mock_llm = AsyncMock()
    # 1st call: generate_queries
    query_resp = QueryGeneratorResponse(
        queries=["AI in healthcare", "Machine learning diagnosis"],
        search_queries=[SearchQueryItem(query="AI in healthcare", language="en")],
    )
    # Summarize paper 2 (processed first in list)
    sum_resp_ax2 = PaperSummaryResponse(
        summary_vi="Bài báo đề xuất phương pháp phân đoạn ảnh y tế tự động. "
                   "Sử dụng kiến trúc U-Net kết hợp cơ chế chú ý không gian. "
                   "Hiệu quả cải thiện đáng kể trên các ca ảnh có độ tương phản thấp.",
        relevance_score=0.75,
    )
    # Summarize paper 1 (processed second in list)
    sum_resp_ss1 = PaperSummaryResponse(
        summary_vi="Nghiên cứu áp dụng mạng nơ-ron tích chập trong chẩn đoán X-quang phổi. "
                   "Mô hình được huấn luyện trên 10,000 ảnh chụp X-quang thực tế. "
                   "Độ chính xác chẩn đoán viêm phổi đạt 96%.",
        relevance_score=0.95,
    )

    mock_llm.generate_structured_output_with_usage.side_effect = [
        (query_resp, {"total_tokens": 150}),
        (sum_resp_ax2, {"total_tokens": 240}),
        (sum_resp_ss1, {"total_tokens": 250}),
    ]

    # Mock Search Aggregator
    mock_aggregator = AsyncMock()
    paper1 = PaperSchema(
        id="ss_1",
        source=PaperSource.SEMANTIC_SCHOLAR,
        external_id="ext_1",
        title="Deep CNN for Chest X-Ray",
        abstract="We present a convolutional neural network architecture trained on 10k x-ray images...",
        citation_count=50,
    )
    paper2 = PaperSchema(
        id="ax_2",
        source=PaperSource.ARXIV,
        external_id="ext_2",
        title="Attention U-Net for Medical Image Segmentation",
        abstract="This paper introduces spatial attention gates into standard U-Net models...",
        citation_count=30,
    )
    paper3_short_abstract = PaperSchema(
        id="oa_3",
        source=PaperSource.OPENALEX,
        external_id="ext_3",
        title="Short Note on Medical AI",
        abstract="Too short",  # < 30 chars, should not trigger summarizer
        citation_count=2,
    )

    mock_aggregator.aggregate_search.return_value = SearchResponseSchema(
        query="AI in healthcare",
        total_results=3,
        papers=[paper2, paper1, paper3_short_abstract],  # paper2 initially first
    )

    mock_logger = AsyncMock()
    agent = LiteratureAgent(
        llm_service_instance=mock_llm,
        logger_instance=mock_logger,
        aggregator_instance=mock_aggregator,
    )

    res = await agent.search_and_summarize(
        topic="Ứng dụng AI trong chẩn đoán hình ảnh y tế",
        limit=5,
    )

    assert res.total_results == 3
    # Check that papers were sorted by relevance score descending:
    # paper1 (score 0.95) should be first, paper2 (score 0.75) second, paper3 (score None/0.0) third
    assert res.papers[0].id == "ss_1"
    assert res.papers[0].relevance_score == 0.95
    assert "chẩn đoán X-quang phổi" in res.papers[0].summary_vi

    assert res.papers[1].id == "ax_2"
    assert res.papers[1].relevance_score == 0.75

    assert res.papers[2].id == "oa_3"
    assert res.papers[2].summary_vi is None  # not summarized because abstract too short


@pytest.mark.asyncio
async def test_search_and_summarize_resilience_when_summarization_fails():
    """Verify search_and_summarize does not crash if summarization fails for one paper."""
    mock_llm = AsyncMock()
    query_resp = QueryGeneratorResponse(
        queries=["Natural language processing"],
        search_queries=[SearchQueryItem(query="Natural language processing", language="en")],
    )
    sum_resp = PaperSummaryResponse(
        summary_vi="Tóm tắt bài báo 2 bằng tiếng Việt.",
        relevance_score=0.8,
    )

    # 1st call succeeds (queries), 2nd fails (paper 1), 3rd succeeds (paper 2)
    mock_llm.generate_structured_output_with_usage.side_effect = [
        (query_resp, {"total_tokens": 100}),
        Exception("LLM timeout or JSON parse error"),
        (sum_resp, {"total_tokens": 200}),
    ]

    mock_aggregator = AsyncMock()
    paper1 = PaperSchema(
        id="p1",
        source=PaperSource.SEMANTIC_SCHOLAR,
        external_id="1",
        title="Paper One With Long Abstract",
        abstract="This is a sufficiently long abstract for paper one exceeding thirty characters.",
    )
    paper2 = PaperSchema(
        id="p2",
        source=PaperSource.ARXIV,
        external_id="2",
        title="Paper Two With Long Abstract",
        abstract="This is another sufficiently long abstract for paper two exceeding thirty characters.",
    )
    mock_aggregator.aggregate_search.return_value = SearchResponseSchema(
        query="Natural language processing",
        total_results=2,
        papers=[paper1, paper2],
    )

    agent = LiteratureAgent(
        llm_service_instance=mock_llm,
        logger_instance=AsyncMock(),
        aggregator_instance=mock_aggregator,
    )

    res = await agent.search_and_summarize(topic="NLP Research")
    assert res.total_results == 2
    # paper1 was preserved despite summarization failure
    p1 = next(p for p in res.papers if p.id == "p1")
    assert p1.summary_vi is None
    # paper2 was successfully summarized
    p2 = next(p for p in res.papers if p.id == "p2")
    assert p2.summary_vi == "Tóm tắt bài báo 2 bằng tiếng Việt."


# ==============================================================================
# 5. LiteratureAgent.run() Entry Point Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_literature_agent_run_actions():
    """Test the run method dispatcher with all supported actions and invalid action."""
    agent = LiteratureAgent()

    # Mock the internal methods
    agent.generate_queries = AsyncMock(
        return_value=QueryGeneratorResponse(queries=["Q1", "Q2", "Q3"])
    )
    agent.summarize_paper = AsyncMock(
        return_value=PaperSummaryResponse(summary_vi="Tóm tắt", relevance_score=0.9)
    )
    agent.search_and_summarize = AsyncMock(
        return_value=SearchResponseSchema(query="Q1", total_results=1, papers=[])
    )

    # 1. Action: generate_queries
    res1 = await agent.run({"action": "generate_queries", "topic": "AI", "outline": "1. Intro"})
    assert "queries" in res1
    agent.generate_queries.assert_awaited_once_with("AI", "1. Intro", user_id=None, project_id=None)

    # 2. Action: summarize_paper
    res2 = await agent.run({"action": "summarize_paper", "title": "T", "abstract": "A", "topic": "AI"})
    assert res2["relevance_score"] == 0.9
    agent.summarize_paper.assert_awaited_once_with("T", "A", "AI", user_id=None, project_id=None)

    # 3. Action: search_and_summarize
    res3 = await agent.run({"action": "search_and_summarize", "topic": "AI", "limit": 3})
    assert res3["query"] == "Q1"
    agent.search_and_summarize.assert_awaited_once_with("AI", None, 3, user_id=None, project_id=None)

    # 4. Invalid action
    with pytest.raises(ValueError, match="Unknown action 'unknown_action'"):
        await agent.run({"action": "unknown_action"})


# ==============================================================================
# 6. LLMService generate_structured_output_with_usage Backward Compatibility
# ==============================================================================

@pytest.mark.asyncio
async def test_llm_service_generate_structured_output_backward_compatibility():
    """Verify that LLMService.generate_structured_output still returns only parsed object."""
    llm = LLMService()

    fake_parsed = PaperSummaryResponse(summary_vi="Tóm tắt 1. Tóm tắt 2.", relevance_score=0.85)
    fake_usage = {"total_tokens": 150}

    with patch.object(
        llm,
        "generate_structured_output_with_usage",
        AsyncMock(return_value=(fake_parsed, fake_usage)),
    ):
        result = await llm.generate_structured_output(
            system_prompt="sys",
            user_prompt="usr",
            schema=PaperSummaryResponse,
        )

        # Must return only the Pydantic instance, not a tuple
        assert isinstance(result, PaperSummaryResponse)
        assert result.relevance_score == 0.85
