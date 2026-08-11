import os
import sys

# Ensure backend root is in sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

try:
    import pytest
except ImportError:
    class DummyPytest:
        @staticmethod
        def fixture(func):
            return func
    pytest = DummyPytest()



from schemas.citation_schemas import (
    CitationMetadataSchema,
    CitationStyle,
    DocumentType,
)
from services.citation_formatter import CitationFormatterService
from data.citation_styles.bgddt import sort_bgddt_bibliography


@pytest.fixture
def sample_paper_vn():
    return CitationMetadataSchema(
        title="Ảnh hưởng của mạng xã hội đến hành vi mua sắm của sinh viên",
        authors=["Nguyễn Văn An", "Trần Thị Bích"],
        year=2023,
        journal="Tạp chí Phát triển Kinh tế",
        volume="34",
        issue="2",
        pages="45-52",
        doi="10.1234/jde.2023.012",
        doc_type=DocumentType.JOURNAL,
    )


@pytest.fixture
def sample_paper_en():
    return CitationMetadataSchema(
        title="Generative AI in Academic Writing: Opportunities and Challenges",
        authors=["Smith, John Arthur", "Taylor, Robert"],
        year=2024,
        journal="Computers & Education",
        volume="180",
        pages="104-115",
        doi="10.1016/j.compedu.2024.104115",
        doc_type=DocumentType.JOURNAL,
    )


def test_apa7_formatting(sample_paper_en):
    res = CitationFormatterService.format_citation(sample_paper_en, style=CitationStyle.APA7)
    assert res.style == CitationStyle.APA7
    assert "(Smith & Taylor, 2024)" in res.in_text_citation
    assert "Smith, J. A., & Taylor, R." in res.full_citation
    assert "(2024)." in res.full_citation
    assert "Generative AI in Academic Writing: Opportunities and Challenges." in res.full_citation
    assert "https://doi.org/10.1016/j.compedu.2024.104115" in res.full_citation


def test_ieee_formatting(sample_paper_en):
    res = CitationFormatterService.format_citation(sample_paper_en, style=CitationStyle.IEEE, index=1)
    assert res.style == CitationStyle.IEEE
    assert res.in_text_citation == "[1]"
    assert "[1] J. A. Smith and R. Taylor," in res.full_citation
    assert '"Generative AI in Academic Writing: Opportunities and Challenges,"' in res.full_citation
    assert "vol. 180," in res.full_citation
    assert "2024." in res.full_citation
    assert "doi: 10.1016/j.compedu.2024.104115." in res.full_citation


def test_bgddt_formatting(sample_paper_vn):
    res = CitationFormatterService.format_citation(sample_paper_vn, style=CitationStyle.BGDDT, index=2)
    assert res.style == CitationStyle.BGDDT
    assert res.in_text_citation == "[2]"
    assert "[2] Nguyễn Văn An, Trần Thị Bích (2023)," in res.full_citation
    assert '"Ảnh hưởng của mạng xã hội đến hành vi mua sắm của sinh viên"' in res.full_citation
    assert "Tạp chí Phát triển Kinh tế" in res.full_citation
    assert "Tập 34 Số 2" in res.full_citation
    assert "tr. 45-52." in res.full_citation


def test_bgddt_sorting():
    item_bich = CitationMetadataSchema(
        title="Nghiên cứu thị trường",
        authors=["Trần Thị Bích"],
        year=2022,
    )
    item_an = CitationMetadataSchema(
        title="Tổng quan kinh tế",
        authors=["Nguyễn Văn An"],
        year=2023,
    )
    item_smith = CitationMetadataSchema(
        title="AI Research",
        authors=["Smith, John"],
        year=2024,
    )
    item_brown = CitationMetadataSchema(
        title="Deep Learning",
        authors=["Brown, Alex"],
        year=2021,
    )

    items = [item_bich, item_smith, item_an, item_brown]
    sorted_items = sort_bgddt_bibliography(items)

    # Expected order:
    # 1. VN Group sorted by Given Name: Nguyễn Văn "An" (0), Trần Thị "Bích" (1)
    # 2. EN Group sorted by Surname: "Brown", Alex (2), "Smith", John (3)
    assert sorted_items[0].authors[0] == "Nguyễn Văn An"
    assert sorted_items[1].authors[0] == "Trần Thị Bích"
    assert sorted_items[2].authors[0] == "Brown, Alex"
    assert sorted_items[3].authors[0] == "Smith, John"


def test_bibliography_formatting(sample_paper_vn, sample_paper_en):
    res = CitationFormatterService.format_bibliography(
        metadatas=[sample_paper_vn, sample_paper_en],
        style=CitationStyle.BGDDT,
    )
    assert len(res.citations) == 2
    assert "[1] Nguyễn Văn An" in res.citations[0]
    assert "[2] Smith J.A." in res.citations[1]


if __name__ == "__main__":
    vn = sample_paper_vn()
    en = sample_paper_en()
    print("Running Citation Formatter Unit Tests...")
    test_apa7_formatting(en)
    print("[PASS] APA7 Formatting Test Passed")
    test_ieee_formatting(en)
    print("[PASS] IEEE Formatting Test Passed")
    test_bgddt_formatting(vn)
    print("[PASS] Bo GD&DT Formatting Test Passed")
    test_bgddt_sorting()
    print("[PASS] Bo GD&DT Bibliography Sorting Test Passed")
    test_bibliography_formatting(vn, en)
    print("[PASS] Bibliography Formatting Test Passed")
    print("ALL TESTS PASSED SUCCESSFULLY! 100% Accuracy.")



