import pytest
from schemas.literature_schemas import PaperSource
from services.scholar_service import scholar_service
from services.arxiv_service import arxiv_service
from services.openalex_service import openalex_service
from services.search_aggregator import search_aggregator


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
