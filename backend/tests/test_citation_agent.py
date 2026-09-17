import os
import sys
import pytest

# Ensure backend directory is in sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from agents.citation_agent import CitationAgent, citation_agent
from schemas.citation_schemas import (
    CitationMetadataSchema,
    CitationStyle,
    DocumentType,
)


@pytest.fixture
def sample_catalog():
    return [
        {
            "id": "paper-1",
            "title": "Machine Learning for Official Statistics",
            "authors": ["Cedric De Boom", "Michael Reusens"],
            "year": 2023,
            "source": "arxiv",
            "doc_type": DocumentType.JOURNAL,
        },
        {
            "id": "paper-2",
            "title": "Nghiên cứu hành vi tiêu dùng trực tuyến của sinh viên",
            "authors": ["Nguyễn Văn An", "Lê Thị Bích"],
            "year": 2022,
            "source": "journal",
            "doc_type": DocumentType.JOURNAL,
        },
        {
            "id": "paper-3",
            "title": "Deep Learning Fundamentals",
            "authors": ["Goodfellow, Ian", "Bengio, Yoshua"],
            "year": 2016,
            "source": "book",
            "doc_type": DocumentType.BOOK,
            "publisher": "MIT Press",
        },
    ]


@pytest.mark.asyncio
async def test_detect_missing_claims():
    agent = CitationAgent()
    content = """
    Công nghệ trí tuệ nhân tạo đang phát triển nhanh chóng.
    Theo báo cáo mới nhất, có hơn 78.5% sinh viên sử dụng công cụ AI trong học tập và nghiên cứu.
    Tỷ lệ này chiếm 65% tổng số lượt truy cập nền tảng trực tuyến.
    """
    res = await agent.check_document_citations(content=content, selected_papers=[])
    assert len(res.missing_claims) >= 2
    claim_texts = [c.sentence for c in res.missing_claims]
    assert any("78.5%" in c for c in claim_texts)
    assert any("chiếm 65%" in c for c in claim_texts)


@pytest.mark.asyncio
async def test_ieee_numeric_cross_reference(sample_catalog):
    agent = CitationAgent()
    # [1] is valid, [9] is invalid (catalog only has 3 papers)
    content = """
    Phương pháp phân tích dữ liệu lớn được áp dụng thành công [1].
    Tuy nhiên, các thuật toán mới lại gặp hạn chế về tài nguyên tính toán [9].
    """
    res = await agent.check_document_citations(
        content=content,
        selected_papers=sample_catalog,
        citation_style="ieee",
    )
    assert res.verified_count == 1
    assert len(res.invalid_citations) == 1
    assert "[9]" in res.invalid_citations[0]
    assert "không tồn tại" in res.invalid_citations[0]


@pytest.mark.asyncio
async def test_apa_author_year_cross_reference_matching(sample_catalog):
    agent = CitationAgent()
    content = """
    Theo các phân tích thống kê (De Boom & Reusens, 2023), dữ liệu hành chính đóng vai trò cốt lõi.
    Hơn nữa, nghiên cứu tại Việt Nam (Nguyễn & Lê, 2022) cũng chỉ ra xu hướng tương tự.
    """
    res = await agent.check_document_citations(
        content=content,
        selected_papers=sample_catalog,
        citation_style="apa7",
    )
    assert res.verified_count == 2
    assert len(res.invalid_citations) == 0


@pytest.mark.asyncio
async def test_apa_year_mismatch_detection(sample_catalog):
    agent = CitationAgent()
    # De Boom is 2023, but author writes 2019
    content = """
    Khảo sát gần đây của nhóm tác giả (De Boom & Reusens, 2019) cho thấy kết quả khả quan.
    """
    res = await agent.check_document_citations(
        content=content,
        selected_papers=sample_catalog,
        citation_style="apa7",
    )
    assert res.verified_count == 0
    assert len(res.invalid_citations) == 1
    assert "sai năm xuất bản" in res.invalid_citations[0]
    assert "2023" in res.invalid_citations[0]


@pytest.mark.asyncio
async def test_ghost_citation_detection(sample_catalog):
    agent = CitationAgent()
    # Einstein is not in sample_catalog
    content = """
    Lý thuyết tương đối được phát biểu rất rõ ràng (Einstein, 1905).
    """
    res = await agent.check_document_citations(
        content=content,
        selected_papers=sample_catalog,
        citation_style="apa7",
    )
    assert len(res.invalid_citations) == 1
    assert "không tìm thấy tác giả" in res.invalid_citations[0]


@pytest.mark.asyncio
async def test_uncited_papers_detection(sample_catalog):
    agent = CitationAgent()
    # Content only cites paper 1: De Boom
    content = """
    Ứng dụng học máy vào thống kê (De Boom, 2023) mang lại độ chính xác cao.
    """
    res = await agent.check_document_citations(
        content=content,
        selected_papers=sample_catalog,
        citation_style="apa7",
    )
    # Paper 2 (Nguyễn Văn An) and Paper 3 (Goodfellow) should be flagged as uncited
    assert len(res.uncited_papers) == 2
    uncited_titles = [p.title for p in res.uncited_papers]
    assert "Nghiên cứu hành vi tiêu dùng trực tuyến của sinh viên" in uncited_titles
    assert "Deep Learning Fundamentals" in uncited_titles


def test_generate_project_bibliography(sample_catalog):
    agent = CitationAgent()

    # Test APA7
    bib_apa = agent.generate_project_bibliography(sample_catalog, citation_style="apa7")
    assert len(bib_apa) == 3
    assert any("De Boom" in b for b in bib_apa)
    assert any("MIT Press" in b for b in bib_apa)

    # Test IEEE
    bib_ieee = agent.generate_project_bibliography(sample_catalog, citation_style="ieee")
    assert len(bib_ieee) == 3
    assert "[1]" in bib_ieee[0]
    assert "[2]" in bib_ieee[1]
    assert "[3]" in bib_ieee[2]

    # Test Bộ GD&ĐT
    bib_bgddt = agent.generate_project_bibliography(sample_catalog, citation_style="bgddt")
    assert len(bib_bgddt) == 3
    # In Bộ GD&ĐT: Vietnamese authors sorted first
    assert "Nguyễn Văn An" in bib_bgddt[0]


def test_format_different_document_types():
    agent = CitationAgent()

    book = {
        "title": "Artificial Intelligence: A Modern Approach",
        "authors": ["Russell, Stuart", "Norvig, Peter"],
        "year": 2020,
        "publisher": "Pearson",
        "doc_type": DocumentType.BOOK,
    }

    conf = {
        "title": "Attention Is All You Need",
        "authors": ["Vaswani, Ashish", "Shazeer, Noam"],
        "year": 2017,
        "journal": "Advances in Neural Information Processing Systems",
        "pages": "5998-6008",
        "doc_type": DocumentType.CONFERENCE,
    }

    thesis = {
        "title": "Deep Residual Learning for Image Recognition",
        "authors": ["He, Kaiming"],
        "year": 2016,
        "publisher": "Stanford University",
        "doc_type": DocumentType.THESIS,
    }

    web = {
        "title": "OpenAI Documentation",
        "authors": ["OpenAI Team"],
        "year": 2023,
        "url": "https://platform.openai.com/docs",
        "doc_type": DocumentType.WEB,
    }

    papers = [book, conf, thesis, web]
    bib = agent.generate_project_bibliography(papers, citation_style="apa7")
    assert len(bib) == 4
    assert any("Pearson" in b for b in bib)
    assert any("In Advances in Neural Information Processing Systems" in b for b in bib)
    assert any("Stanford University" in b for b in bib)
    assert any("https://platform.openai.com/docs" in b for b in bib)
