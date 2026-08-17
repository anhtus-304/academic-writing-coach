import os
import asyncio
# pyrefly: ignore [missing-import]
import pytest
from unittest.mock import AsyncMock, MagicMock

from backend.agents.outline_agent import OutlineAgent, outline_agent
from backend.services.llm_service import LLMService
from backend.schemas.outline_schemas import (
    AcademicOutline,
    OutlineSection,
    OutlineSubSection,
    OutlineGenerationInput,
)
from backend.agents.graph import academic_graph


@pytest.fixture
def mock_academic_outline():
    return AcademicOutline(
        topic="Phân tích Chuỗi Cung ứng Thực phẩm Xanh tại Việt Nam",
        document_type="tieu_luan",
        field="Quản trị Kinh doanh",
        language="vi",
        total_estimated_pages="20 trang",
        sections=[
            OutlineSection(
                section_code="INTRO",
                title="MỞ ĐẦU",
                description="Giới thiệu bối cảnh và mục tiêu đề tài",
                subsections=[
                    OutlineSubSection(
                        title="1. Tính cấp thiết của đề tài",
                        description="Lý do chọn đề tài nghiên cứu",
                        estimated_word_count=500,
                        key_points=["Bối cảnh tiêu dùng xanh", "Áp lực phát triển bền vững"],
                    )
                ],
            ),
            OutlineSection(
                section_code="CH1",
                title="CHƯƠNG 1: CƠ SỞ LÝ LUẬN VỀ CHUỖI CUNG ỨNG XANH",
                description="Các lý thuyết nền tảng",
                subsections=[
                    OutlineSubSection(
                        title="1.1. Khái niệm và các thành phần chính",
                        description="Định nghĩa chuỗi cung ứng xanh",
                        estimated_word_count=1500,
                        key_points=["Khái niệm chuỗi cung ứng xanh", "Các mắt xích trong chuỗi"],
                    )
                ],
            ),
        ],
        research_methodology_suggestion="Phương pháp định tính thu thập dữ liệu thứ cấp kết hợp phỏng vấn sâu.",
        key_academic_keywords=["Green Supply Chain", "Phát triển bền vững", "Logistics xanh"],
        writing_guidelines="Chú ý liên hệ thực tiễn doanh nghiệp Việt Nam.",
    )


def test_template_loader_all_templates():
    """Verify that all 8 outline templates load correctly from YAML."""
    agent = OutlineAgent()
    template_keys = [
        "tieu_luan_default",
        "khoa_luan_default",
        "luan_van_thac_si",
        "bai_bao_khoa_hoc",
        "bao_cao_thuc_tap",
        "de_cuong_nghien_cuu",
        "tong_quan_tai_lieu",
        "phan_tich_case_study",
    ]

    for key in template_keys:
        tmpl = agent.load_template(key)
        assert tmpl is not None, f"Template '{key}' failed to load!"
        assert "id" in tmpl
        assert "name" in tmpl
        assert "sections" in tmpl
        assert len(tmpl["sections"]) > 0


def test_outline_schemas_validation(mock_academic_outline):
    """Test Pydantic model serialization and validation."""
    dumped = mock_academic_outline.model_dump()
    assert dumped["topic"] == "Phân tích Chuỗi Cung ứng Thực phẩm Xanh tại Việt Nam"
    assert len(dumped["sections"]) == 2
    
    # Reload from dict
    reloaded = AcademicOutline.model_validate(dumped)
    assert reloaded.topic == mock_academic_outline.topic


def test_outline_agent_with_mock_llm(mock_academic_outline):
    """Test OutlineAgent generate_outline method using a mocked LLMService."""
    async def run_test():
        mock_llm = MagicMock(spec=LLMService)
        mock_llm.generate_structured_output = AsyncMock(return_value=mock_academic_outline)

        agent = OutlineAgent(llm_service_instance=mock_llm)
        result = await agent.generate_outline(
            topic="Phân tích Chuỗi Cung ứng Thực phẩm Xanh tại Việt Nam",
            document_type="tieu_luan",
            field="Quản trị Kinh doanh",
        )

        assert result.topic == mock_academic_outline.topic
        assert len(result.sections) == 2
        mock_llm.generate_structured_output.assert_called_once()

    asyncio.run(run_test())


def test_langgraph_workflow_node(mock_academic_outline, monkeypatch):
    """Test LangGraph graph execution calling outline node."""
    async def run_test():
        async def mock_gen_outline(*args, **kwargs):
            return mock_academic_outline

        monkeypatch.setattr(outline_agent, "generate_outline", mock_gen_outline)

        initial_state = {
            "topic": "Đánh giá Năng lực Cạnh tranh của Doanh nghiệp SME Việt Nam",
            "document_type": "tieu_luan",
            "field": "Kinh tế Đầu tư",
        }

        final_state = await academic_graph.ainvoke(initial_state)

        assert final_state["status"] == "success"
        assert "outline" in final_state
        assert final_state["outline"]["topic"] == mock_academic_outline.topic

    asyncio.run(run_test())

