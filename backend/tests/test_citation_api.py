"""Week-3 integration tests - Citation Agent API.

* ``POST /api/v1/projects/{id}/citation/check``  -> missing claims + highlight
  offsets, credit deduction, auth/ownership guards.
* ``POST /api/v1/projects/{id}/citation/format`` -> per-paper in-text + full
  citations and the complete bibliography for apa7/ieee/bgddt.
* ``POST /api/v1/citation/format``               -> standalone single-metadata formatter.

The LLM arbitrator is stubbed to fail fast so the deterministic citation core
(which is what these assertions target) is exercised without network access.
"""
import pytest

from tests.conftest import create_user_with_project

UNCITED_CLAIM = "The survey reports that 85% of students use AI writing tools."
CITED_SENTENCE = "Prior work already documents this trend."
SELF_CLAIM = "In this study, we propose a rule-based citation checker."


@pytest.fixture(autouse=True)
def offline_citation_llm(monkeypatch):
    """Force the deterministic fallback path of the citation arbitrator."""
    try:
        from backend.agents.citation_agent import citation_agent
    except ImportError:
        from agents.citation_agent import citation_agent

    class _OfflineLLM:
        async def generate_structured_output(self, *args, **kwargs):
            raise RuntimeError("offline test: LLM arbitration disabled")

        async def generate_structured_output_with_usage(self, *args, **kwargs):
            raise RuntimeError("offline test: LLM arbitration disabled")

    monkeypatch.setattr(citation_agent, "llm_service", _OfflineLLM(), raising=False)
    return citation_agent


async def _select_paper(client, headers, project_id, title, doi, year=2023, authors=None):
    res = await client.post(
        f"/api/v1/projects/{project_id}/literature/select",
        headers=headers,
        json={
            "paper": {
                "title": title,
                "authors": authors or ["Nguyen Van An"],
                "year": year,
                "doi": doi,
                "url": f"https://example.org/{doi}",
                "abstract": f"Abstract of {title}.",
            }
        },
    )
    assert res.status_code == 200, res.text
    return res.json()


async def test_check_detects_missing_citation_with_offsets(client, project, auth_headers):
    draft = f"<p>{UNCITED_CLAIM}</p><p>{SELF_CLAIM}</p>"

    res = await client.post(
        f"/api/v1/projects/{project.id}/citation/check",
        headers=auth_headers,
        json={"content": draft, "citation_style": "apa7"},
    )
    assert res.status_code == 200, res.text
    body = res.json()

    assert body["credits_charged"] == 2
    assert body["total_issues"] >= 1
    assert len(body["missing_claims"]) >= 1

    claim = next(c for c in body["missing_claims"] if "85%" in c["sentence"])
    assert claim["reason"]
    assert claim["suggested_action"]
    # Highlight metadata required by the Tiptap editor
    assert isinstance(claim["char_offset"], int)
    assert isinstance(claim["char_end"], int)
    assert claim["char_end"] > claim["char_offset"]
    assert isinstance(claim["sentence_index"], int)
    # The span length must match the sentence length exactly.
    assert claim["char_end"] - claim["char_offset"] == len(claim["sentence"])

    # Self-contribution sentences must never be reported as missing citations.
    assert all("we propose" not in c["sentence"].lower() for c in body["missing_claims"])


async def test_check_reports_uncited_selected_papers(client, project, auth_headers):
    await _select_paper(client, auth_headers, project.id, "Cited Work", "10.1000/cited-1")
    await _select_paper(client, auth_headers, project.id, "Uncited Work", "10.1000/uncited-2")

    # Cite the first paper with an IEEE-style numeric marker (apa7 default style
    # still resolves the catalog entry for verification purposes).
    draft = f"<p>Automated scoring improves revision quality [1].</p><p>{SELF_CLAIM}</p>"
    res = await client.post(
        f"/api/v1/projects/{project.id}/citation/check",
        headers=auth_headers,
        json={"content": draft, "citation_style": "ieee"},
    )
    assert res.status_code == 200, res.text
    body = res.json()

    assert body["verified_count"] >= 1
    uncited_titles = [p["title"] for p in body["uncited_papers"]]
    assert "Uncited Work" in uncited_titles
    assert body["uncited_papers"][0]["in_text_code"]


async def test_check_flags_ghost_citation(client, project, auth_headers):
    await _select_paper(client, auth_headers, project.id, "Only Selection", "10.1000/only-1")

    draft = "<p>Some claim that is verified elsewhere [7] and again [9].</p>"
    res = await client.post(
        f"/api/v1/projects/{project.id}/citation/check",
        headers=auth_headers,
        json={"content": draft, "citation_style": "ieee"},
    )
    assert res.status_code == 200
    body = res.json()
    assert any("[7]" in item for item in body["invalid_citations"])


async def test_check_deducts_credits_and_blocks_when_insufficient(client):
    from security import create_access_token

    user, project = await create_user_with_project(credit_balance=1)
    headers = {"Authorization": f"Bearer {create_access_token(str(user.id))}"}

    res = await client.post(
        f"/api/v1/projects/{project.id}/citation/check",
        headers=headers,
        json={"content": f"<p>{UNCITED_CLAIM}</p>"},
    )
    assert res.status_code == 402


async def test_check_and_format_require_auth_and_ownership(client, auth_headers, project):
    assert (
        await client.post(
            f"/api/v1/projects/{project.id}/citation/check",
            json={"content": f"<p>{UNCITED_CLAIM}</p>"},
        )
    ).status_code == 401
    assert (
        await client.post(f"/api/v1/projects/{project.id}/citation/format", json={})
    ).status_code == 401

    import uuid

    missing = str(uuid.uuid4())
    assert (
        await client.post(
            f"/api/v1/projects/{missing}/citation/check",
            headers=auth_headers,
            json={"content": f"<p>{UNCITED_CLAIM}</p>"},
        )
    ).status_code == 404
    assert (
        await client.post(
            f"/api/v1/projects/{missing}/citation/format",
            headers=auth_headers,
            json={},
        )
    ).status_code == 404


async def test_format_project_citations_apa7(client, project, auth_headers):
    await _select_paper(
        client, auth_headers, project.id, "Alpha Study on Writing", "10.1000/alpha", authors=["Nguyen Van An"]
    )
    await _select_paper(
        client, auth_headers, project.id, "Beta Study on Writing", "10.1000/beta", authors=["Tran Thi B"]
    )

    res = await client.post(
        f"/api/v1/projects/{project.id}/citation/format",
        headers=auth_headers,
        json={"style": "apa7"},
    )
    assert res.status_code == 200, res.text
    body = res.json()

    assert body["style"] == "apa7"
    assert body["total_citations"] == 2
    assert len(body["bibliography"]) == 2

    by_title = {item["title"]: item for item in body["citations"]}
    alpha = by_title["Alpha Study on Writing"]
    assert "Nguyen" in alpha["full_citation"]
    assert alpha["in_text_citation"]
    assert alpha["style"] == "apa7"
    assert "bibliography-container" in body["html_formatted"]


async def test_format_project_citations_ieee_is_numbered(client, project, auth_headers):
    await _select_paper(client, auth_headers, project.id, "First Reference", "10.1000/ieee-1")
    await _select_paper(client, auth_headers, project.id, "Second Reference", "10.1000/ieee-2")

    res = await client.post(
        f"/api/v1/projects/{project.id}/citation/format",
        headers=auth_headers,
        json={"style": "ieee"},
    )
    assert res.status_code == 200, res.text
    body = res.json()

    assert body["style"] == "ieee"
    assert body["citations"][0]["in_text_citation"] == "[1]"
    assert body["citations"][1]["in_text_citation"] == "[2]"
    assert body["bibliography"][0].startswith("[1]")
    assert "<ol class='bibliography-list'>" in body["html_formatted"]


async def test_format_project_citations_subset_and_project_style_fallback(client, project, auth_headers):
    first = await _select_paper(client, auth_headers, project.id, "Subset One", "10.1000/sub-1")
    await _select_paper(client, auth_headers, project.id, "Subset Two", "10.1000/sub-2")

    # No style in the body -> falls back to the project"s citation_style (apa7).
    res = await client.post(
        f"/api/v1/projects/{project.id}/citation/format",
        headers=auth_headers,
        json={"selected_paper_ids": [first["id"]], "include_in_text": False},
    )
    assert res.status_code == 200, res.text
    body = res.json()

    assert body["style"] == "apa7"
    assert body["total_citations"] == 1
    assert body["citations"][0]["title"] == "Subset One"
    assert body["citations"][0]["in_text_citation"] == ""


async def test_format_project_citations_bgddt_style_override(client, project, auth_headers):
    await _select_paper(client, auth_headers, project.id, "Vietnamese Rules Study", "10.1000/bg-1")

    res = await client.post(
        f"/api/v1/projects/{project.id}/citation/format",
        headers=auth_headers,
        json={"style": "bgddt"},
    )

    assert res.status_code == 200, res.text
    body = res.json()
    assert body["style"] == "bgddt"
    assert body["bibliography"]


async def test_standalone_format_citation_endpoint(client):
    res = await client.post(
        "/api/v1/citation/format",
        json={
            "metadata": {
                "title": "Attention Is All You Need",
                # "Surname, Given" is the canonical form for APA 7 (see
                # CitationMetadataSchema.authors).
                "authors": ["Vaswani, Ashish"],
                "year": 2017,
                "journal": "NeurIPS",
                "doc_type": "conference",
            },
            "style": "apa7",
            "index": 1,
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["style"] == "apa7"
    assert body["in_text_citation"]
    assert "Vaswani" in body["full_citation"]


async def test_agent_public_api_detect_and_format(offline_citation_llm):
    """Unit-level contract required by the week-3 task: ``detect_missing_citations`` / ``format_citations``."""
    agent = offline_citation_llm
    papers = [
        {
            "id": "p1",
            "title": "Deep Learning for Essay Scoring",
            "authors": ["Nguyen Van An"],
            "year": 2023,
            "doi": "10.1000/agent-1",
        }
    ]

    claims = await agent.detect_missing_citations(f"{UNCITED_CLAIM} {SELF_CLAIM}", papers)
    assert isinstance(claims, list)
    assert any("85%" in item["sentence"] for item in claims)
    assert all(isinstance(item["char_offset"], int) for item in claims)

    bibliography = agent.format_citations(papers, style="apa7")
    assert isinstance(bibliography, list)
    assert len(bibliography) == 1
    assert "Nguyen" in bibliography[0]

    ieee = agent.format_citations(papers, style="ieee")
    assert ieee[0].startswith("[1]")

    detailed = agent.format_citations_detailed(papers, style="ieee")
    assert detailed[0]["in_text_citation"] == "[1]"
    assert detailed[0]["selected_paper_id"] == "p1"

    # No papers -> no bibliography, no crash
    assert agent.format_citations([], style="apa7") == []


async def test_check_returns_compact_missing_contract(client, project, auth_headers):
    """Week-3 contract: ``{missing: [{text, index, suggestion}], total_missing}``."""
    res = await client.post(
        f"/api/v1/projects/{project.id}/citation/check",
        headers=auth_headers,
        json={"content": f"<p>{UNCITED_CLAIM}</p>", "paper_ids": []},
    )
    assert res.status_code == 200, res.text
    body = res.json()

    assert body["total_missing"] == len(body["missing"]) >= 1

    item = body["missing"][0]
    assert set(item) == {"text", "index", "suggestion"}
    assert "85%" in item["text"]
    assert isinstance(item["index"], int)
    assert item["suggestion"]

    # The compact view mirrors the richer missing_claims list for the editor.
    assert body["total_missing"] == len(body["missing_claims"])
    assert item["text"] == body["missing_claims"][0]["sentence"]


async def test_check_honours_paper_ids_subset(client, project, auth_headers):
    """``paper_ids`` narrows the reference catalog used for cross-referencing."""
    first = await _select_paper(client, auth_headers, project.id, "Selected Only", "10.1000/sel-1")
    await _select_paper(client, auth_headers, project.id, "Ignored Paper", "10.1000/ignored-1")

    res = await client.post(
        f"/api/v1/projects/{project.id}/citation/check",
        headers=auth_headers,
        json={
            "content": "<p>Automated scoring improves revision quality [1].</p>",
            "citation_style": "ieee",
            "paper_ids": [first["id"]],
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()

    uncited_titles = [paper["title"] for paper in body["uncited_papers"]]
    assert "Ignored Paper" not in uncited_titles
    assert body["verified_count"] == 1


async def test_format_accepts_paper_ids_alias_and_returns_bibliography_text(client, project, auth_headers):
    first = await _select_paper(client, auth_headers, project.id, "Alias Study One", "10.1000/alias-1")
    await _select_paper(client, auth_headers, project.id, "Alias Study Two", "10.1000/alias-2")

    res = await client.post(
        f"/api/v1/projects/{project.id}/citation/format",
        headers=auth_headers,
        json={"paper_ids": [first["id"]], "style": "ieee"},
    )
    assert res.status_code == 200, res.text
    body = res.json()

    assert body["total_citations"] == 1
    assert body["citations"][0]["title"] == "Alias Study One"
    assert body["citations"][0]["in_text_citation"] == "[1]"
    # Week-3 contract: the whole bibliography is also exposed as a single string.
    assert isinstance(body["bibliography_text"], str)
    assert body["bibliography_text"].startswith("[1]")
    assert body["bibliography_text"] == "\n".join(body["bibliography"])


async def test_agent_detect_missing_public_api(offline_citation_llm):
    """``CitationAgent.detect_missing(text)`` -> ``[{text, index, suggestion}]``."""
    agent = offline_citation_llm

    claims = await agent.detect_missing(f"{UNCITED_CLAIM} {SELF_CLAIM}")
    assert isinstance(claims, list)
    assert claims

    item = next(claim for claim in claims if "85%" in claim["text"])
    assert item["text"] == item["sentence"]
    assert isinstance(item["index"], int)
    assert item["suggestion"]
    # Rich highlight fields are still available for the Tiptap editor.
    assert item["reason"] and isinstance(item["char_offset"], int)

    assert await agent.detect_missing("") == []
