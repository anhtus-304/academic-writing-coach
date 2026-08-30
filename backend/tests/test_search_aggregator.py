import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch

from schemas.literature_schemas import (
    AuthorSchema,
    PaperSchema,
    PaperSource,
    SearchResponseSchema,
)
from services.scholar_service import ScholarService
from services.arxiv_service import ArxivService
from services.openalex_service import OpenAlexService
from services.search_aggregator import SearchAggregator


# ---------------------------------------------------------------------------
# 1. Unit Tests for Semantic Scholar Client Parsing
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scholar_service_mock_search():
    client = ScholarService()
    mock_payload = {
        "data": [
            {
                "paperId": "abc12345",
                "title": "Attention Is All You Need",
                "authors": [
                    {"authorId": "1", "name": "Ashish Vaswani"},
                    {"authorId": "2", "name": "Noam Shazeer"},
                ],
                "year": 2017,
                "venue": "NeurIPS",
                "abstract": "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks...",
                "externalIds": {"DOI": "https://doi.org/10.48550/arXiv.1706.03762"},
                "url": "https://www.semanticscholar.org/paper/abc12345",
                "citationCount": 95000,
            }
        ]
    }

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        mock_resp.json = lambda: mock_payload
        mock_get.return_value = mock_resp

        results = await client.search("Attention Is All You Need", limit=5)

        assert len(results) == 1
        paper = results[0]
        assert paper.source == PaperSource.SEMANTIC_SCHOLAR
        assert paper.external_id == "abc12345"
        assert paper.title == "Attention Is All You Need"
        assert len(paper.authors) == 2
        assert paper.authors[0].name == "Ashish Vaswani"
        assert paper.year == 2017
        assert paper.venue == "NeurIPS"
        assert paper.doi == "10.48550/arXiv.1706.03762"
        assert paper.citation_count == 95000


# ---------------------------------------------------------------------------
# 2. Unit Tests for arXiv Client Parsing
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_arxiv_service_mock_search():
    client = ArxivService()
    mock_atom_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
      <entry>
        <id>http://arxiv.org/abs/1706.03762v7</id>
        <published>2017-06-12T17:57:34Z</published>
        <title>
          Attention Is All You Need
        </title>
        <summary>
          We propose a new simple network architecture, the Transformer, based solely on attention mechanisms.
        </summary>
        <author>
          <name>Ashish Vaswani</name>
        </author>
        <author>
          <name>Noam Shazeer</name>
        </author>
        <arxiv:doi>10.48550/arXiv.1706.03762</arxiv:doi>
        <arxiv:primary_category term="cs.CL"/>
      </entry>
    </feed>
    """

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        mock_resp.text = mock_atom_xml
        mock_get.return_value = mock_resp

        results = await client.search("Attention Is All You Need", limit=5)

        assert len(results) == 1
        paper = results[0]
        assert paper.source == PaperSource.ARXIV
        assert paper.external_id == "1706.03762v7"
        assert paper.title == "Attention Is All You Need"
        assert len(paper.authors) == 2
        assert paper.authors[0].name == "Ashish Vaswani"
        assert paper.year == 2017
        assert paper.doi == "10.48550/arXiv.1706.03762"
        assert "Transformer" in (paper.abstract or "")


# ---------------------------------------------------------------------------
# 3. Unit Tests for OpenAlex Client Parsing & Inverted Index Abstract
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_openalex_service_mock_search():
    client = OpenAlexService()
    mock_payload = {
        "results": [
            {
                "id": "https://openalex.org/W2741809807",
                "doi": "https://doi.org/10.48550/arxiv.1706.03762",
                "title": "Attention is all you need",
                "publication_year": 2017,
                "cited_by_count": 92000,
                "primary_location": {
                    "source": {"display_name": "Advances in Neural Information Processing Systems"},
                    "landing_page_url": "https://arxiv.org/abs/1706.03762"
                },
                "authorships": [
                    {
                        "author": {"id": "https://openalex.org/A50123", "display_name": "Ashish Vaswani"},
                        "institutions": [{"display_name": "Google Brain"}]
                    }
                ],
                "abstract_inverted_index": {
                    "The": [0],
                    "Transformer": [1],
                    "model": [2],
                    "is": [3],
                    "introduced": [4]
                }
            }
        ]
    }

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        mock_resp.json = lambda: mock_payload
        mock_get.return_value = mock_resp

        results = await client.search("Attention is all you need", limit=5)

        assert len(results) == 1
        paper = results[0]
        assert paper.source == PaperSource.OPENALEX
        assert paper.external_id == "W2741809807"
        assert paper.title == "Attention is all you need"
        assert paper.authors[0].name == "Ashish Vaswani"
        assert paper.authors[0].affiliations == ["Google Brain"]
        assert paper.doi == "10.48550/arxiv.1706.03762"
        assert paper.citation_count == 92000
        assert paper.abstract == "The Transformer model is introduced"


# ---------------------------------------------------------------------------
# 4. Deduplication Tests: DOI Normalization & Title Matching
# ---------------------------------------------------------------------------

def test_deduplication_exact_doi():
    aggregator = SearchAggregator()

    paper1 = PaperSchema(
        id="s2_1",
        source=PaperSource.SEMANTIC_SCHOLAR,
        external_id="1",
        title="Deep Residual Learning for Image Recognition",
        authors=[AuthorSchema(name="Kaiming He")],
        year=2016,
        venue="CVPR",
        abstract="Deep neural networks are more difficult to train.",
        doi="https://doi.org/10.1109/CVPR.2016.90",
        citation_count=180000,
    )

    paper2 = PaperSchema(
        id="arxiv_2",
        source=PaperSource.ARXIV,
        external_id="2",
        title="Deep Residual Learning for Image Recognition",
        authors=[AuthorSchema(name="Kaiming He"), AuthorSchema(name="Xiangyu Zhang")],
        year=2015,
        venue="arXiv preprint",
        abstract="Deeper neural networks are more difficult to train. We present a residual learning framework.",
        doi="10.1109/cvpr.2016.90",
        citation_count=50,
    )

    assert aggregator.are_duplicates(paper1, paper2) is True

    merged = aggregator.deduplicate_papers([paper1, paper2])
    assert len(merged) == 1
    # Merged record should retain the highest citation count (180,000)
    assert merged[0].citation_count == 180000
    # Merged record should retain the richer authors or longer abstract
    assert len(merged[0].authors) == 2
    assert "We present a residual learning framework" in (merged[0].abstract or "")


def test_deduplication_fuzzy_title_without_doi():
    aggregator = SearchAggregator()

    paper1 = PaperSchema(
        id="s2_3",
        source=PaperSource.SEMANTIC_SCHOLAR,
        external_id="3",
        title="BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding",
        authors=[AuthorSchema(name="Jacob Devlin")],
        year=2019,
        citation_count=75000,
    )

    paper2 = PaperSchema(
        id="openalex_4",
        source=PaperSource.OPENALEX,
        external_id="4",
        title="BERT Pre training of Deep Bidirectional Transformers for Language Understanding",
        authors=[AuthorSchema(name="Jacob Devlin")],
        year=2019,
        citation_count=70000,
    )

    assert aggregator.are_duplicates(paper1, paper2) is True
    merged = aggregator.deduplicate_papers([paper1, paper2])
    assert len(merged) == 1
    assert merged[0].citation_count == 75000


def test_distinct_papers_are_not_deduplicated():
    aggregator = SearchAggregator()

    paper1 = PaperSchema(
        id="s2_5",
        source=PaperSource.SEMANTIC_SCHOLAR,
        external_id="5",
        title="Generative Adversarial Nets",
        authors=[AuthorSchema(name="Ian Goodfellow")],
        year=2014,
        doi="10.1145/3422622",
        citation_count=60000,
    )

    paper2 = PaperSchema(
        id="arxiv_6",
        source=PaperSource.ARXIV,
        external_id="6",
        title="Attention Is All You Need",
        authors=[AuthorSchema(name="Ashish Vaswani")],
        year=2017,
        doi="10.48550/arXiv.1706.03762",
        citation_count=95000,
    )

    assert aggregator.are_duplicates(paper1, paper2) is False
    results = aggregator.deduplicate_papers([paper1, paper2])
    assert len(results) == 2


# ---------------------------------------------------------------------------
# 5. Ranking Algorithm Tests
# ---------------------------------------------------------------------------

def test_ranking_relevance_and_sorting():
    aggregator = SearchAggregator()

    # Highly relevant paper (matches query, high citations, recent)
    paper_high = PaperSchema(
        id="1",
        source=PaperSource.SEMANTIC_SCHOLAR,
        external_id="1",
        title="Graph Neural Networks in Drug Discovery: A Comprehensive Survey",
        abstract="We review graph neural networks for drug discovery and molecular property prediction.",
        year=2024,
        citation_count=250,
    )

    # Low relevance paper (only tangentially related, older, low citations)
    paper_low = PaperSchema(
        id="2",
        source=PaperSource.OPENALEX,
        external_id="2",
        title="An Old Study on Chemical Database Indexing",
        abstract="A historical overview of chemical storage techniques.",
        year=2010,
        citation_count=5,
    )

    ranked = aggregator.rank_papers([paper_low, paper_high], "Graph Neural Networks in Drug Discovery")

    assert len(ranked) == 2
    assert ranked[0].id == "1"
    assert ranked[0].relevance_score is not None
    assert ranked[1].relevance_score is not None
    assert ranked[0].relevance_score > ranked[1].relevance_score
    assert 0.0 <= ranked[0].relevance_score <= 1.0
    assert 0.0 <= ranked[1].relevance_score <= 1.0


# ---------------------------------------------------------------------------
# 6. Parallel Aggregate Search & Error Resilience Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_aggregate_search_parallel_success():
    mock_scholar = AsyncMock()
    mock_arxiv = AsyncMock()
    mock_openalex = AsyncMock()

    mock_scholar.search.return_value = [
        PaperSchema(
            id="s2_1",
            source=PaperSource.SEMANTIC_SCHOLAR,
            external_id="1",
            title="Transformer Models in NLP",
            year=2022,
            citation_count=100,
        )
    ]
    mock_arxiv.search.return_value = [
        PaperSchema(
            id="arxiv_2",
            source=PaperSource.ARXIV,
            external_id="2",
            title="Vision Transformers Overview",
            year=2023,
            citation_count=50,
        )
    ]
    mock_openalex.search.return_value = [
        PaperSchema(
            id="openalex_3",
            source=PaperSource.OPENALEX,
            external_id="3",
            title="Transformer Models in NLP",  # Duplicate with s2_1
            year=2022,
            citation_count=120,
        )
    ]

    aggregator = SearchAggregator(
        scholar_client=mock_scholar,
        arxiv_client=mock_arxiv,
        openalex_client=mock_openalex,
    )

    response: SearchResponseSchema = await aggregator.aggregate_search("Transformer Models", limit=10)

    assert response.query == "Transformer Models"
    # Deduplication should reduce 3 papers to 2 unique papers
    assert response.total_results == 2
    assert len(response.papers) == 2
    # Verify citations merged
    nlp_paper = next(p for p in response.papers if "NLP" in p.title)
    assert nlp_paper.citation_count == 120


@pytest.mark.asyncio
async def test_aggregate_search_resilience_when_one_api_fails():
    mock_scholar = AsyncMock()
    mock_arxiv = AsyncMock()
    mock_openalex = AsyncMock()

    # Semantic Scholar times out / throws error
    mock_scholar.search.side_effect = Exception("Semantic Scholar API 503 Service Unavailable")

    # arXiv and OpenAlex succeed
    mock_arxiv.search.return_value = [
        PaperSchema(
            id="arxiv_1",
            source=PaperSource.ARXIV,
            external_id="1",
            title="Federated Learning Survey",
            year=2023,
            citation_count=40,
        )
    ]
    mock_openalex.search.return_value = [
        PaperSchema(
            id="openalex_2",
            source=PaperSource.OPENALEX,
            external_id="2",
            title="Privacy-Preserving Machine Learning",
            year=2024,
            citation_count=80,
        )
    ]

    aggregator = SearchAggregator(
        scholar_client=mock_scholar,
        arxiv_client=mock_arxiv,
        openalex_client=mock_openalex,
    )

    # Aggregator should not crash, returning results from the remaining working sources
    response = await aggregator.aggregate_search("Federated Learning", limit=10)

    assert response.total_results == 2
    assert len(response.papers) == 2


@pytest.mark.asyncio
async def test_aggregate_search_empty_query():
    aggregator = SearchAggregator()
    response = await aggregator.aggregate_search("", limit=10)
    assert response.total_results == 0
    assert response.papers == []
