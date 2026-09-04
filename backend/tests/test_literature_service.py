from services.literature_service import normalize_paper_record


def test_normalize_paper_record_handles_semantic_scholar_shape():
    payload = {
        "paperId": "abc-123",
        "title": "Transformer-based architecture for academic writing assistance",
        "authors": [
            {"name": "Nguyen Thi Lan"},
            {"name": "Tran Van An"},
        ],
        "year": 2024,
        "venue": "Journal of Applied AI",
        "abstract": "This paper explores a transformer-based framework for writing assistance.",
        "url": "https://example.com/paper",
        "citationCount": 42,
    }

    result = normalize_paper_record(payload, source="semantic_scholar")

    assert result["id"] == "abc-123"
    assert result["title"] == "Transformer-based architecture for academic writing assistance"
    assert result["authors"] == ["Nguyen Thi Lan", "Tran Van An"]
    assert result["year"] == 2024
    assert result["source"] == "semantic_scholar"
    assert result["publicationType"] == "Journal of Applied AI"
    assert result["citationCount"] == 42
