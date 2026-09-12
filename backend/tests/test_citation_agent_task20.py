import asyncio

from backend.agents.citation_agent import citation_agent
from backend.agents.graph import build_full_academic_writing_graph, citation_node


def run_agent(payload):
    return asyncio.run(citation_agent.run(payload))


def test_citation_agent_detects_claim_without_source():
    result = run_agent({
        "content": "Nghiên cứu cho thấy việc áp dụng AI chiếm 85% tổng số sinh viên tham gia khảo sát.",
        "citation_style": "apa7",
        "selected_papers": [],
    })

    assert len(result["missing_claims"]) == 1
    assert result["suggestions"][0]["suggested_text"] is None
    assert "No selected paper" in result["suggestions"][0]["reason"]
    assert result["bibliography"] == []


def test_citation_agent_uses_selected_paper_without_inventing_source():
    result = run_agent({
        "content": "Nghiên cứu cho thấy việc áp dụng AI chiếm 85% tổng số sinh viên tham gia khảo sát.",
        "citation_style": "apa7",
        "selected_papers": [{
            "title": "Generative AI in Academic Writing",
            "authors": ["Smith, John", "Taylor, Robert"],
            "year": 2024,
            "doi": "10.1234/example",
        }],
    })

    suggestion = result["suggestions"][0]
    assert suggestion["source"]["title"] == "Generative AI in Academic Writing"
    assert suggestion["suggested_text"].endswith("(Smith & Taylor, 2024)")
    assert len(result["bibliography"]) == 1
    assert "Generative AI in Academic Writing" in result["bibliography"][0]


def test_citation_node_reaches_formatter_fields():
    result = asyncio.run(citation_node({
        "document": "Kết quả cho thấy tỷ lệ tham gia đạt 72% trong nhóm khảo sát.",
        "citation_style": "ieee",
        "selected_papers": [],
    }))

    assert result["current_step"] == "citation_completed"
    assert result["status"] == "success"
    assert result["citation_suggestions"]


def test_full_graph_contains_end_to_end_citation_stages():
    graph = build_full_academic_writing_graph()
    nodes = graph.get_graph().nodes

    assert "generate_outline" in nodes
    assert "run_literature" in nodes
    assert "run_citation" in nodes
    assert "run_formatter" in nodes
