"""Week-3 tests - LangGraph Outline -> Literature -> Citation pipeline.

.. note::
   The backend modules can be imported as ``agents.x`` (``uvicorn main:app`` from
   ``backend/``) *and* ``backend.agents.x`` (``uvicorn backend.main:app`` from the
   repo root). Those are two distinct module objects, and ``agents/graph.py``
   resolves the agent singletons through the ``backend.`` alias - so every patch
   below targets the ``backend.agents.*`` alias, matching the call sites inside
   the pipeline (and the rest of the test suite).
"""
import pytest

from backend.agents.graph import (
    academic_graph,
    build_academic_writing_graph,
    checkpoint_store,
    memory_checkpointer,
    run_academic_pipeline,
)
from backend.schemas.outline_schemas import AcademicOutline, OutlineSection, OutlineSubSection

DRAFT_HTML = "<p>The survey reports that 85% of students use AI writing tools.</p>"


def _mock_outline() -> AcademicOutline:
    return AcademicOutline(
        topic="Citation checking with LangGraph",
        document_type="tieu_luan",
        field="Computer Science",
        language="vi",
        total_estimated_pages="12 trang",
        sections=[
            OutlineSection(
                section_code="CH1",
                title="CHUONG 1: TONG QUAN",
                description="Literature background",
                subsections=[
                    OutlineSubSection(
                        title="1.1 Citation practice",
                        description="How students cite sources",
                        estimated_word_count=600,
                        key_points=["Citation styles", "Plagiarism"],
                    )
                ],
            )
        ],
        research_methodology_suggestion="Rule-based verification with LLM assistance.",
        key_academic_keywords=["Citation", "LangGraph"],
        writing_guidelines="Write clearly and cite every empirical claim.",
    )


@pytest.fixture
def stubbed_nodes(monkeypatch):
    """Stub the outline LLM and the citation arbitrator (offline, deterministic)."""
    from backend.agents.citation_agent import citation_agent
    from backend.agents.outline_agent import outline_agent

    outline = _mock_outline()

    async def _fake_outline(*args, **kwargs):
        return outline

    class _OfflineLLM:
        async def generate_structured_output(self, *args, **kwargs):
            raise RuntimeError("offline test: LLM arbitration disabled")

        async def generate_structured_output_with_usage(self, *args, **kwargs):
            raise RuntimeError("offline test: LLM arbitration disabled")

    async def _fake_queries(*args, **kwargs):
        raise RuntimeError("offline test: LLM query generation disabled")

    monkeypatch.setattr(outline_agent, "generate_outline", _fake_outline, raising=False)
    monkeypatch.setattr(citation_agent, "llm_service", _OfflineLLM(), raising=False)

    try:
        from backend.agents.literature_agent import literature_agent
    except ImportError:
        from agents.literature_agent import literature_agent

    monkeypatch.setattr(literature_agent, "generate_queries", _fake_queries, raising=False)
    return outline


def test_graph_exposes_the_three_pipeline_nodes():
    nodes = set(academic_graph.get_graph().nodes)
    assert {"generate_outline", "search_literature", "check_citations"} <= nodes


async def test_pipeline_runs_outline_literature_citation(stubbed_nodes):
    checkpoint_store.clear("w3-test-run")

    final_state = await run_academic_pipeline(
        {
            "topic": "citation checking",
            "document_type": "tieu_luan",
            "draft_content": DRAFT_HTML,
            "citation_style": "apa7",
        },
        run_id="w3-test-run",
    )

    assert final_state["status"] == "success"
    assert final_state["steps_completed"] == ["outline", "literature", "citation"]
    assert final_state["outline"]["topic"] == stubbed_nodes.topic

    # Literature node pulled the deterministic mock corpus (LITERATURE_MODE=mock)
    assert final_state["literature_review"]["total_results"] > 0
    assert final_state["literature_review"]["papers"]

    # Citation node detected the uncited statistical claim...
    assert final_state["citation_check"]["total_issues"] >= 1
    assert any("85%" in claim["sentence"] for claim in final_state["citation_check"]["missing_claims"])

    # ...and produced the bibliography for the discovered papers.
    assert final_state["bibliography"]
    assert final_state["citations"][0]["full_citation"]

    # In-process checkpoints: one snapshot per node.
    history = final_state["checkpoints"]
    assert [record["step"] for record in history] == ["outline", "literature", "citation"]
    assert checkpoint_store.latest("w3-test-run")["state"]["status"] == "success"


async def test_pipeline_halts_when_outline_fails(monkeypatch):
    from backend.agents.outline_agent import outline_agent

    async def _boom(*args, **kwargs):
        raise RuntimeError("outline service unavailable")

    monkeypatch.setattr(outline_agent, "generate_outline", _boom, raising=False)

    checkpoint_store.clear("w3-test-fail")
    final_state = await run_academic_pipeline(
        {"topic": "broken outline", "draft_content": DRAFT_HTML},
        run_id="w3-test-fail",
    )

    assert final_state["status"] == "failed"
    assert "outline service unavailable" in final_state["error"]
    assert final_state["steps_completed"] == ["outline"]
    assert "literature_review" not in final_state
    assert [record["step"] for record in final_state["checkpoints"]] == ["outline"]


async def test_literature_node_short_circuits_on_existing_review(stubbed_nodes):
    existing_review = {"query": "precomputed", "papers": [], "total_results": 0}

    final_state = await run_academic_pipeline(
        {
            "topic": "citation checking",
            "literature_review": existing_review,
            "draft_content": DRAFT_HTML,
            "citation_style": "apa7",
        },
        run_id="w3-test-existing-review",
    )

    assert final_state["literature_review"] == existing_review
    assert "literature" in final_state["steps_completed"]
    assert final_state["status"] == "success"


async def test_skip_literature_flag_avoids_search(stubbed_nodes):
    final_state = await run_academic_pipeline(
        {"topic": "citation checking", "skip_literature": True, "draft_content": DRAFT_HTML},
        run_id="w3-test-skip",
    )

    review = final_state["literature_review"]
    assert review["skipped"] is True
    assert review["papers"] == []


async def test_langgraph_memory_checkpointer_persists_state(stubbed_nodes):
    saver = memory_checkpointer()
    graph = build_academic_writing_graph(checkpointer=saver)
    config = {"configurable": {"thread_id": "w3-native-checkpoint"}}

    await graph.ainvoke(
        {
            "topic": "citation checking",
            "draft_content": DRAFT_HTML,
            "citation_style": "apa7",
            "steps_completed": [],
            "language": "vi",
            "document_type": "tieu_luan",
        },
        config=config,
    )

    snapshot = await graph.aget_state(config)
    assert snapshot.values["steps_completed"] == ["outline", "literature", "citation"]
    assert snapshot.values["bibliography"]

    history = [state async for state in graph.aget_state_history(config)]
    assert len(history) >= 3


async def test_resume_reuses_previous_checkpoint(stubbed_nodes):
    saver = memory_checkpointer()
    run_id = "w3-test-resume"
    checkpoint_store.clear(run_id)

    first = await run_academic_pipeline(
        {"topic": "citation checking", "draft_content": DRAFT_HTML},
        run_id=run_id,
        checkpointer=saver,
    )
    assert first["status"] == "success"

    resumed = await run_academic_pipeline(
        {"topic": "citation checking", "draft_content": DRAFT_HTML},
        run_id=run_id,
        resume=True,
        checkpointer=saver,
    )

    assert resumed["run_id"] == run_id
    assert set(resumed["steps_completed"]) == {"outline", "literature", "citation"}
    assert resumed["status"] == "success"


async def test_dict_graph_mock_runs_pipeline_without_langgraph(stubbed_nodes):
    """``build_dict_graph`` is the dict-based fallback used when langgraph is absent.

    It must honour the same contract as the compiled LangGraph: shared dict state,
    partial node updates, ``get_graph().nodes``, ``ainvoke`` and state snapshots.
    """
    from backend.agents.graph import build_dict_graph, checkpoint_store

    graph = build_dict_graph()
    assert set(graph.get_graph().nodes) == {
        "generate_outline",
        "search_literature",
        "check_citations",
    }

    run_id = "w3-dict-mock"
    checkpoint_store.clear(run_id)

    final_state = await graph.ainvoke(
        {
            "topic": "citation checking",
            "draft_content": DRAFT_HTML,
            "citation_style": "apa7",
            "run_id": run_id,
            "steps_completed": [],
            "language": "vi",
            "document_type": "tieu_luan",
        },
        config={"configurable": {"thread_id": run_id}},
    )

    assert isinstance(final_state, dict)
    assert final_state["steps_completed"] == ["outline", "literature", "citation"]
    assert final_state["status"] == "success"
    assert final_state["outline"]["topic"] == "Citation checking with LangGraph"
    assert final_state["bibliography"]
    assert final_state["citation_check"]["total_missing"] >= 1

    snapshot = await graph.aget_state({"configurable": {"thread_id": run_id}})
    assert snapshot.values["status"] == "success"

    history = [
        state
        async for state in graph.aget_state_history({"configurable": {"thread_id": run_id}})
    ]
    assert len(history) == 1


async def test_dict_graph_mock_stops_when_a_node_records_an_error():
    """The mock mirrors the conditional edges: an ``error`` halts the pipeline."""
    from backend.agents.graph import DictGraphMock

    calls = []

    async def _outline(state):
        calls.append("outline")
        return {"steps_completed": ["outline"]}

    async def _literature(state):
        calls.append("literature")
        return {"error": "boom", "status": "failed"}

    async def _citation(state):  # pragma: no cover - must never run
        calls.append("citation")
        return {}

    graph = DictGraphMock(
        {
            "generate_outline": _outline,
            "search_literature": _literature,
            "check_citations": _citation,
        }
    )

    final_state = await graph.ainvoke({"topic": "x"})

    assert calls == ["outline", "literature"]
    assert final_state["error"] == "boom"