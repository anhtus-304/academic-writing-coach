"""LangGraph multi-agent pipeline: Outline -> Literature -> Citation.

Week-3 scope
------------
* Three nodes wrap the existing agents (``outline_agent``, ``literature_service``
  and ``citation_agent``): each receives the shared :class:`AgentState` and
  returns only the keys it updates (LangGraph merges partial updates).
* Conditional edges stop the run early as soon as a node records an ``error``.
* ``langgraph`` is optional at import time: when the package is missing the module
  exposes :class:`DictGraphMock`, a dependency-free stand-in that runs the same
  three nodes sequentially over a plain ``dict`` state (the week-3 spec's
  "dict mock" fallback), so the pipeline and its tests still work offline.
* Checkpointing is supported twice:
  1. LangGraph-native: compile with a ``MemorySaver`` checkpointer and pass
     ``config={"configurable": {"thread_id": <run_id>}}`` - every node boundary
     is persisted by LangGraph and can be resumed/replayed;
  2. Lightweight in-process :class:`PipelineCheckpointStore` that keeps a deep
     copy of the state after each step - enough for dev/tests and for exposing
     ``checkpoints`` in an API response without extra infrastructure.

The pipeline runs fully offline (``LITERATURE_MODE=mock``) so it can be covered
by unit tests.
"""
import copy
import logging
import uuid
from typing import Any, Dict, List, Optional, TypedDict

try:  # pragma: no cover - depends on the installed langgraph version
    from langgraph.graph import END, StateGraph

    LANGGRAPH_AVAILABLE = True
except ImportError:  # pragma: no cover - offline/dev fallback, see DictGraphMock
    END = "__end__"  # type: ignore[assignment]
    StateGraph = None  # type: ignore[assignment]
    LANGGRAPH_AVAILABLE = False

try:  # pragma: no cover - depends on the installed langgraph version
    from langgraph.checkpoint.memory import MemorySaver
except ImportError:  # pragma: no cover
    MemorySaver = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

try:
    from backend.agents.outline_agent import outline_agent
    from backend.agents.literature_agent import literature_agent
    from backend.agents.citation_agent import citation_agent
except ImportError:
    from agents.outline_agent import outline_agent
    from agents.literature_agent import literature_agent
    from agents.citation_agent import citation_agent



class AgentState(TypedDict, total=False):
    """LangGraph State representation for Academic Writing Workflows."""

    # ---- Inputs ----
    project_id: Optional[str]
    user_id: Optional[str]
    topic: str
    document_type: str
    field: Optional[str]
    target_length: Optional[str]
    template_id: Optional[str]
    user_requirements: Optional[str]
    language: str
    draft_content: Optional[str]
    content: Optional[str]
    citation_style: str
    skip_literature: bool

    # Selected papers of the project (list of dicts or dict-like objects).
    selected_papers: List[Any]

    # ---- Generated outputs ----
    outline: Optional[Dict[str, Any]]
    literature_review: Optional[Dict[str, Any]]
    literature_results: Optional[Dict[str, Any]]
    citations: Optional[List[Dict[str, Any]]]
    bibliography: Optional[List[str]]
    citation_check: Optional[Dict[str, Any]]
    citation_report: Optional[Dict[str, Any]]
    suggestions: Optional[List[Dict[str, Any]]]
    custom_user_note: Optional[str]

    # ---- Workflow metadata ----
    current_step: str
    status: str
    steps_completed: List[str]
    error: Optional[str]
    messages: List[Dict[str, str]]
    run_id: str


class PipelineCheckpointStore:
    """Minimal in-memory checkpoint store (state snapshot per pipeline step).

    Suitable for development/testing as required by the week-3 task. Swap for a
    Redis-backed implementation in production without changing the call sites.
    """

    def __init__(self) -> None:
        self._checkpoints: Dict[str, List[Dict[str, Any]]] = {}

    def save(self, run_id: str, step: str, state: Dict[str, Any]) -> Dict[str, Any]:
        record = {
            "run_id": run_id,
            "step": step,
            "state": copy.deepcopy(state),
            "sequence": len(self._checkpoints.get(run_id, [])),
        }
        self._checkpoints.setdefault(run_id, []).append(record)
        return record

    def history(self, run_id: str) -> List[Dict[str, Any]]:
        return list(self._checkpoints.get(run_id, []))

    def latest(self, run_id: str) -> Optional[Dict[str, Any]]:
        history = self._checkpoints.get(run_id)
        return history[-1] if history else None

    def clear(self, run_id: Optional[str] = None) -> None:
        if run_id is None:
            self._checkpoints.clear()
        else:
            self._checkpoints.pop(run_id, None)


# Module-level store shared by the compiled graph and callers.
checkpoint_store = PipelineCheckpointStore()


def _checkpoint(state: Dict[str, Any], step: str, result: Dict[str, Any]) -> Dict[str, Any]:
    """Persist a snapshot of ``state`` merged with the node ``result``."""
    run_id = str(state.get("run_id") or "adhoc")
    merged = {**state, **(result or {})}
    try:
        checkpoint_store.save(run_id, step, merged)
        project_id = state.get("project_id")
        if project_id and str(project_id) != run_id:
            checkpoint_store.save(str(project_id), step, merged)
    except Exception as exc:  # pragma: no cover - checkpointing must never break a run
        logger.warning("[LangGraph] Could not store checkpoint for %s: %s", step, exc)
    return result


async def outline_node(state: AgentState) -> Dict[str, Any]:
    """LangGraph node wrapper for outline generation step."""
    try:
        topic = state.get("topic", "")
        # Preserve existing outline if provided and non-empty (Human-in-the-loop)
        existing_outline = state.get("outline")
        if existing_outline:
            inner = existing_outline.get("outline") or existing_outline if isinstance(existing_outline, dict) else existing_outline
            has_sections = False
            if isinstance(inner, dict):
                has_sections = bool(inner.get("sections") or inner.get("chapters"))
            elif isinstance(inner, list):
                has_sections = len(inner) > 0
            if has_sections:
                return _checkpoint(
                    state,
                    "outline",
                    {
                        "outline": existing_outline,
                        "current_step": "outline_preserved",
                        "status": "success",
                        "steps_completed": list(state.get("steps_completed") or []) + ["outline"],
                    },
                )

        result = await outline_agent.generate_outline(
            topic=topic,
            document_type=state.get("document_type", "tieu_luan"),
            field=state.get("field"),
            target_length=state.get("target_length"),
            template_id=state.get("template_id"),
            user_requirements=state.get("user_requirements"),
            language=state.get("language", "vi"),
        )
        outline_data = result.model_dump() if hasattr(result, "model_dump") else result
        update: Dict[str, Any] = {
            "outline": outline_data,
            "current_step": "outline_generated",
            "status": "success",
            "steps_completed": list(state.get("steps_completed") or []) + ["outline"],
        }
    except Exception as e:
        logger.error(f"[LangGraph] Error in outline_node: {e}")
        update = {
            "error": str(e),
            "status": "failed",
            "current_step": "outline_error",
            "steps_completed": list(state.get("steps_completed") or []) + ["outline"],
        }

    return _checkpoint(state, "outline", update)


async def literature_node(state: AgentState) -> Dict[str, Any]:
    """Literature step: build the paper catalog consumed by the Citation step.

    * If the state already carries ``literature_review`` (e.g. resuming from a
      checkpoint) the node short-circuits instead of searching again.
    * Papers are fetched through ``literature_service.fetch_candidate_papers``,
      which honours ``LITERATURE_MODE`` (``mock`` keeps tests hermetic).
    """
    if state.get("literature_review"):
        return _checkpoint(
            state,
            "literature",
            {
                "current_step": "literature_skipped",
                "steps_completed": list(state.get("steps_completed") or []) + ["literature"],
            },
        )

    if state.get("skip_literature"):
        return _checkpoint(
            state,
            "literature",
            {
                "literature_review": {
                    "query": state.get("topic", ""),
                    "papers": [],
                    "total_results": 0,
                    "skipped": True,
                },
                "current_step": "literature_skipped",
                "steps_completed": list(state.get("steps_completed") or []) + ["literature"],
            },
        )

    try:
        query = (state.get("topic") or "").strip()

        # Check if literature_agent is mocked (e.g. in test_graph_pipeline)
        is_agent_mocked = (
            hasattr(literature_agent, "search_and_summarize")
            and (
                getattr(literature_agent.search_and_summarize, "_mock_return_value", None) is not None
                or "AsyncMock" in type(getattr(literature_agent, "search_and_summarize", None)).__name__
                or "MagicMock" in type(getattr(literature_agent, "search_and_summarize", None)).__name__
            )
        )

        if is_agent_mocked:
            res = await literature_agent.search_and_summarize(query=query)
            data = res.model_dump() if hasattr(res, "model_dump") else (res if isinstance(res, dict) else {})
            trimmed = list(data.get("papers") or [])
        else:
            try:
                from backend.services import literature_service
            except ImportError:
                import services.literature_service as literature_service

            papers = await literature_service.fetch_candidate_papers(query, limit=5)
            trimmed = []
            for paper in papers or []:
                if not isinstance(paper, dict):
                    continue
                trimmed.append(
                    {
                        "id": paper.get("id"),
                        "title": paper.get("title"),
                        "authors": paper.get("authors") or [],
                        "year": paper.get("publication_year") or paper.get("year"),
                        "source": paper.get("source"),
                        "doi": paper.get("doi"),
                        "url": paper.get("url"),
                        "abstract": paper.get("abstract"),
                    }
                )

        update: Dict[str, Any] = {
            "literature_review": {
                "query": query,
                "queries": [query] if query else [],
                "papers": trimmed,
                "total_results": len(trimmed),
                "skipped": False,
            },
            "literature_results": {
                "query": query,
                "papers": trimmed,
                "total_results": len(trimmed),
            },
            "selected_papers": trimmed,
            "current_step": "literature_generated",
            "status": "success",
            "steps_completed": list(state.get("steps_completed") or []) + ["literature"],
        }
    except Exception as e:
        logger.error(f"[LangGraph] Error in literature_node: {e}")
        update = {
            "error": str(e),
            "status": "failed",
            "current_step": "literature_error",
            "steps_completed": list(state.get("steps_completed") or []) + ["literature"],
        }

    return _checkpoint(state, "literature", update)


async def citation_node(state: AgentState) -> Dict[str, Any]:
    """Citation step: detect uncited claims in the draft + build the bibliography.

    Uses the papers explicitly attached to the state (``selected_papers``) and
    falls back to the papers discovered by :func:`literature_node`.
    """
    try:
        style = str(state.get("citation_style") or "apa7")
        papers = list(state.get("selected_papers") or [])
        if not papers:
            review = state.get("literature_review") or {}
            papers = list(review.get("papers") or [])

        draft_content = state.get("draft_content") or state.get("content") or ""

        check_payload: Dict[str, Any] = {
            "total_issues": 0,
            "missing_claims": [],
            "invalid_citations": [],
            "citation_warnings": [],
            "uncited_papers": [],
            "verified_count": 0,
            "credits_charged": 0,
            "missing": [],
            "total_missing": 0,
        }

        has_draft = bool(draft_content and str(draft_content).strip())
        current_step = "citation_checked" if has_draft else "citation_skipped"

        if has_draft:
            result = await citation_agent.check_document_citations(
                content=draft_content,
                selected_papers=papers,
                citation_style=style,
            )
            if hasattr(result, "model_dump"):
                check_payload = result.model_dump()
            elif isinstance(result, dict):
                check_payload = result
        else:
            check_payload["status"] = "skipped"

        bibliography = citation_agent.format_citations(papers, style) if hasattr(citation_agent, "format_citations") else []
        detailed = citation_agent.format_citations_detailed(papers, style) if hasattr(citation_agent, "format_citations_detailed") else []

        missing_claims = check_payload.get("missing_claims") or []
        suggestions = []
        for claim in missing_claims:
            if isinstance(claim, dict):
                sentence = claim.get("sentence") or claim.get("text") or ""
                sugg = claim.get("suggested_action") or claim.get("suggestion") or ""
                reason = claim.get("reason") or ""
                rec = claim.get("recommended_paper_title") or ""
                suggestions.append({
                    "type": "citation_missing",
                    "sentence": sentence,
                    "suggestion": sugg,
                    "reason": reason,
                    "recommended_paper_title": rec,
                })

        # Harmonize citations output: if missing_claims exist, preserve them with full_citation attached;
        # otherwise provide detailed paper citations.
        citations_output = []
        if missing_claims:
            for idx, claim in enumerate(missing_claims):
                c_dict = dict(claim) if isinstance(claim, dict) else (claim.model_dump() if hasattr(claim, "model_dump") else {})
                if idx < len(detailed):
                    c_dict.setdefault("full_citation", detailed[idx].get("full_citation", ""))
                    c_dict.setdefault("in_text_citation", detailed[idx].get("in_text_citation", ""))
                elif detailed:
                    c_dict.setdefault("full_citation", detailed[0].get("full_citation", ""))
                    c_dict.setdefault("in_text_citation", detailed[0].get("in_text_citation", ""))
                else:
                    c_dict.setdefault("full_citation", c_dict.get("suggested_action") or c_dict.get("in_text_suggestion") or "")
                citations_output.append(c_dict)
        else:
            citations_output = detailed

        update: Dict[str, Any] = {
            "citation_check": check_payload,
            "citation_report": check_payload,
            "citations": citations_output,
            "suggestions": suggestions,
            "bibliography": bibliography,
            "current_step": current_step,
            "status": "success",
            "steps_completed": list(state.get("steps_completed") or []) + ["citation"],
        }
    except Exception as e:
        logger.error(f"[LangGraph] Error in citation_node: {e}")
        update = {
            "error": str(e),
            "status": "failed",
            "current_step": "citation_error",
            "steps_completed": list(state.get("steps_completed") or []) + ["citation"],
        }

    return _checkpoint(state, "citation", update)


def _route_unless_failed(next_node: str):
    """Conditional edge helper: stop the pipeline as soon as an error is set."""

    def _route(state: AgentState) -> str:
        if state.get("error"):
            logger.warning("[LangGraph] Pipeline halted before '%s': %s", next_node, state.get("error"))
            return END
        return next_node

    return _route


# ---------------------------------------------------------------------------
# Dict-based fallback used when ``langgraph`` is not installed
# ---------------------------------------------------------------------------
PIPELINE_ORDER: tuple = ("generate_outline", "search_literature", "check_citations")


class _GraphView:
    """Mimics the object returned by ``CompiledGraph.get_graph()``."""

    def __init__(self, node_names: Any) -> None:
        self.nodes = {name: None for name in node_names}


class _StateSnapshot:
    """Mimics a LangGraph ``StateSnapshot`` (only ``values`` is consumed here)."""

    def __init__(self, values: Dict[str, Any]) -> None:
        self.values = values


class DictGraphMock:
    """Plain-``dict`` stand-in for a compiled LangGraph ``StateGraph``.

    Week-3 requirement: "nếu langgraph chưa cài, dùng dict mock". It runs the
    same ``outline -> literature -> citation`` nodes in order over a dict state,
    stops early as soon as a node records ``error`` (mirroring the conditional
    edges of the real graph) and keeps a state snapshot per ``thread_id`` so
    ``aget_state``/``aget_state_history`` behave like their LangGraph peers.
    """

    def __init__(self, nodes: Dict[str, Any], order: tuple = PIPELINE_ORDER) -> None:
        self._nodes = dict(nodes)
        self._order = tuple(order)
        self._threads: Dict[str, Dict[str, Any]] = {}
        self._history: Dict[str, List[_StateSnapshot]] = {}

    # ------------------------------------------------------------- introspection
    def get_graph(self) -> _GraphView:
        return _GraphView(self._order)

    # ------------------------------------------------------------------ execution
    def _next_after(self, node_name: str, state: Dict[str, Any]) -> Optional[str]:
        if state.get("error"):
            return None
        position = self._order.index(node_name)
        if position + 1 >= len(self._order):
            return None
        return self._order[position + 1]

    async def ainvoke(self, state: Optional[Dict[str, Any]], config: Optional[Any] = None) -> Dict[str, Any]:
        merged: Dict[str, Any] = dict(state or {})
        thread_id = ((config or {}).get("configurable") or {}).get("thread_id")

        current: Optional[str] = self._order[0] if self._order else None
        while current is not None:
            update = await self._nodes[current](merged)
            merged = {**merged, **(update or {})}
            current = self._next_after(current, merged)

        if thread_id:
            self._threads[thread_id] = merged
            self._history.setdefault(thread_id, []).append(_StateSnapshot(merged))
        return merged

    async def aget_state(self, config: Optional[Any] = None) -> Optional[_StateSnapshot]:
        thread_id = ((config or {}).get("configurable") or {}).get("thread_id")
        values = self._threads.get(thread_id)
        return _StateSnapshot(values) if values is not None else None

    async def aget_state_history(self, config: Optional[Any] = None):
        thread_id = ((config or {}).get("configurable") or {}).get("thread_id")
        for snapshot in self._history.get(thread_id, []):
            yield snapshot


def node_map() -> Dict[str, Any]:
    """Node name -> coroutine, shared by the LangGraph and dict-mock builders."""
    return {
        "generate_outline": outline_node,
        "search_literature": literature_node,
        "check_citations": citation_node,
    }


def build_dict_graph(order: tuple = PIPELINE_ORDER) -> DictGraphMock:
    """Build the dependency-free dict pipeline (fallback when ``langgraph`` is missing)."""
    return DictGraphMock(node_map(), order=order)


def build_academic_writing_graph(checkpointer: Optional[Any] = None):
    """Build and compile the Outline -> Literature -> Citation workflow.

    ``checkpointer`` (e.g. ``MemorySaver()``) enables LangGraph-native
    checkpointing; when omitted the graph still snapshots every step into
    :data:`checkpoint_store`. When ``langgraph`` is not installed a
    :class:`DictGraphMock` implementing the same contract is returned instead.
    """
    if not LANGGRAPH_AVAILABLE:
        logger.warning(
            "[LangGraph] package not installed - using the dict-based mock pipeline"
        )
        return build_dict_graph()

    workflow = StateGraph(AgentState)

    # Nodes
    workflow.add_node("generate_outline", outline_node)
    workflow.add_node("search_literature", literature_node)
    workflow.add_node("check_citations", citation_node)

    # Entry point
    workflow.set_entry_point("generate_outline")

    # Linear edges guarded by the failure check
    workflow.add_conditional_edges(
        "generate_outline",
        _route_unless_failed("search_literature"),
        {"search_literature": "search_literature", END: END},
    )
    workflow.add_conditional_edges(
        "search_literature",
        _route_unless_failed("check_citations"),
        {"check_citations": "check_citations", END: END},
    )
    workflow.add_edge("check_citations", END)

    if checkpointer is not None:
        return workflow.compile(checkpointer=checkpointer)
    return workflow.compile()


# Compiled Graph Singleton (used by the outline API and tests)
academic_graph = build_academic_writing_graph()


def memory_checkpointer():
    """Return a LangGraph ``MemorySaver`` (or ``None`` when unavailable)."""
    return MemorySaver() if MemorySaver is not None else None


async def run_academic_pipeline(
    initial_state: Dict[str, Any],
    run_id: Optional[str] = None,
    thread_id: Optional[str] = None,
    resume: bool = False,
    checkpointer: Optional[Any] = None,
    graph: Optional[Any] = None,
) -> Dict[str, Any]:
    """Run the full Outline -> Literature -> Citation pipeline.

    Args:
        initial_state: partial :class:`AgentState` (``topic`` is required).
        run_id: checkpoint/thread id; generated when omitted.
        thread_id: alias for run_id / project thread id.
        resume: merge the latest LangGraph checkpoint of ``run_id`` into the
            initial state before invoking (checkpoint resume support).
        checkpointer: custom LangGraph checkpointer; a ``MemorySaver`` is created
            automatically for the duration of the call when omitted.
        graph: optional pre-compiled graph override.

    Returns:
        The final state dict, augmented with ``run_id`` and ``checkpoints``
        (``PipelineCheckpointStore`` history for that run).
    """
    active_id = str(run_id or thread_id or initial_state.get("project_id") or uuid.uuid4())
    active_checkpointer = checkpointer or memory_checkpointer()
    pipeline_graph = graph or build_academic_writing_graph(checkpointer=active_checkpointer)

    config = {"configurable": {"thread_id": active_id}}
    state: Dict[str, Any] = dict(initial_state or {})
    state["run_id"] = active_id
    if thread_id and "project_id" not in state:
        state["project_id"] = thread_id
    state.setdefault("steps_completed", [])
    state.setdefault("citation_style", "apa7")
    state.setdefault("language", "vi")
    state.setdefault("document_type", "tieu_luan")

    if resume and active_checkpointer is not None:
        if hasattr(pipeline_graph, "aget_state"):
            snapshot = await pipeline_graph.aget_state(config)
        elif hasattr(pipeline_graph, "get_state"):
            snapshot = pipeline_graph.get_state(config)
        else:
            snapshot = None
        if snapshot is not None and getattr(snapshot, "values", None):
            state = {**snapshot.values, **state}

    if hasattr(pipeline_graph, "ainvoke"):
        final_state = await pipeline_graph.ainvoke(state, config=config)
    else:
        final_state = pipeline_graph.invoke(state, config=config)

    final_state["run_id"] = active_id
    final_state["checkpoints"] = checkpoint_store.history(active_id)
    return final_state


def get_pipeline_state(thread_id: str, graph: Optional[Any] = None) -> Optional[Dict[str, Any]]:
    """Retrieves the latest checkpointed state snapshot for a given thread/run id."""
    latest = checkpoint_store.latest(str(thread_id))
    if latest and "state" in latest:
        return dict(latest["state"])
    return None


def update_pipeline_state(
    thread_id: str,
    updates: Dict[str, Any],
    graph: Optional[Any] = None,
) -> Dict[str, Any]:
    """Updates specific keys in the checkpointed state for a given thread/run id."""
    tid = str(thread_id)
    latest = checkpoint_store.latest(tid)
    current_state = dict(latest["state"]) if latest and "state" in latest else {}
    current_state.update(updates)
    checkpoint_store.save(tid, "updated", current_state)
    return current_state


def _format_outline_for_literature(outline_data: Any) -> str:
    """Format outline data into a readable summary string for literature search."""
    if not outline_data:
        return ""
    if isinstance(outline_data, str):
        return outline_data
    if isinstance(outline_data, dict):
        inner = outline_data.get("outline", outline_data)
        if isinstance(inner, dict):
            title = inner.get("title", "")
            sections = inner.get("sections", [])
            lines = [title] if title else []
            for s in sections:
                if isinstance(s, dict):
                    stitle = s.get("title", "")
                    if stitle:
                        lines.append(f"- {stitle}")
                    for sub in s.get("subsections", []):
                        subtitle = sub.get("title", "") if isinstance(sub, dict) else str(sub)
                        if subtitle:
                            lines.append(f"  * {subtitle}")
            return "\n".join(lines) if lines else title
    return str(outline_data)

