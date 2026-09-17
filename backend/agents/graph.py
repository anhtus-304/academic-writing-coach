import logging
from typing import Dict, Any, List, Optional, TypedDict
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

try:
    from backend.agents.outline_agent import outline_agent
    from backend.agents.literature_agent import literature_agent
    from backend.agents.citation_agent import citation_agent
except ImportError:
    from agents.outline_agent import outline_agent
    from agents.literature_agent import literature_agent
    from agents.citation_agent import citation_agent

logger = logging.getLogger(__name__)


class AgentState(TypedDict, total=False):
    """LangGraph State representation for Academic Writing Workflows."""
    # Project & User Context
    project_id: str
    user_id: Optional[str]
    topic: str
    document_type: str
    field: Optional[str]
    target_length: Optional[str]
    template_id: Optional[str]
    user_requirements: Optional[str]
    citation_style: str  # "apa7", "ieee", "bgddt"
    language: str        # "vi", "en"

    # Inputs for subsequent stages
    draft_content: Optional[str]
    selected_papers: Optional[List[Dict[str, Any]]]

    # Generated Agent Outputs
    outline: Optional[Dict[str, Any]]
    literature_review: Optional[Dict[str, Any]]
    literature_results: Optional[Dict[str, Any]]
    citations: Optional[List[Dict[str, Any]]]
    citation_report: Optional[Dict[str, Any]]

    # Workflow Metadata & Orchestration
    current_step: str
    status: str          # "running", "success", "failed", "completed"
    error: Optional[str]
    messages: List[Dict[str, Any]]
    metadata: Optional[Dict[str, Any]]
    custom_user_note: Optional[str]


def _format_outline_for_literature(outline_dict: Optional[Dict[str, Any]]) -> str:
    """Helper to convert structured outline into a readable summary for LiteratureAgent."""
    if not outline_dict:
        return ""
    inner = outline_dict.get("outline") or outline_dict
    sections = inner.get("sections") or inner.get("chapters") or []
    lines: List[str] = []
    for s in sections:
        title = s.get("title") or s.get("heading") or ""
        if title:
            lines.append(f"- {title}")
        for sub in s.get("subsections", []):
            sub_title = sub.get("title") if isinstance(sub, dict) else str(sub)
            if sub_title:
                lines.append(f"  * {sub_title}")
    return "\n".join(lines) if lines else str(inner.get("title", ""))


# =====================================================================
# Node 1: Outline Generator
# =====================================================================
async def outline_node(state: AgentState) -> Dict[str, Any]:
    """LangGraph node wrapper for outline generation step using OutlineAgent."""
    try:
        topic = state.get("topic", "")
        logger.info(f"[LangGraph:outline_node] Generating outline for topic: '{topic}'")
        result = await outline_agent.generate_outline(
            topic=topic,
            document_type=state.get("document_type", "tieu_luan"),
            field=state.get("field"),
            target_length=state.get("target_length"),
            template_id=state.get("template_id"),
            user_requirements=state.get("user_requirements"),
            language=state.get("language", "vi"),
        )
        outline_data = result.model_dump()
        return {
            "outline": outline_data,
            "current_step": "outline_generated",
            "status": "success",
            "error": None,
        }
    except Exception as e:
        logger.error(f"[LangGraph] Error in outline_node: {e}", exc_info=True)
        return {
            "error": str(e),
            "status": "failed",
            "current_step": "outline_error",
        }


# =====================================================================
# Node 2: Literature Researcher
# =====================================================================
async def literature_node(state: AgentState) -> Dict[str, Any]:
    """LangGraph node wrapper for academic literature search & summarization using LiteratureAgent."""
    try:
        topic = state.get("topic", "")
        formatted_outline = _format_outline_for_literature(state.get("outline"))
        logger.info(f"[LangGraph:literature_node] Searching and summarizing literature for topic: '{topic}'")

        search_res = await literature_agent.search_and_summarize(
            topic=topic,
            outline=formatted_outline,
            limit=5,
            user_id=state.get("user_id"),
            project_id=state.get("project_id"),
        )

        lit_data = search_res.model_dump()
        papers = lit_data.get("papers", [])

        # Merge retrieved papers into existing selected_papers if needed
        existing_selected = list(state.get("selected_papers") or [])
        existing_ids = {str(p.get("id")) for p in existing_selected if isinstance(p, dict)}
        for p in papers:
            p_id = str(p.get("id"))
            if p_id not in existing_ids:
                existing_selected.append(p)
                existing_ids.add(p_id)

        return {
            "literature_results": lit_data,
            "literature_review": lit_data,
            "selected_papers": existing_selected,
            "current_step": "literature_completed",
            "status": "success",
            "error": None,
        }
    except Exception as e:
        logger.error(f"[LangGraph] Error in literature_node: {e}", exc_info=True)
        return {
            "error": str(e),
            "status": "failed",
            "current_step": "literature_error",
        }


# =====================================================================
# Node 3: Citation Validator & Missing Claim Detector
# =====================================================================
async def citation_node(state: AgentState) -> Dict[str, Any]:
    """LangGraph node wrapper for citation cross-referencing and missing claim detection using CitationAgent."""
    try:
        draft_content = state.get("draft_content")
        selected_papers = state.get("selected_papers") or []
        citation_style = state.get("citation_style", "apa7")

        if not draft_content or not draft_content.strip():
            logger.info("[LangGraph:citation_node] No draft_content provided; skipping citation check.")
            return {
                "citation_report": {
                    "status": "skipped",
                    "message": "Chưa có nội dung bản thảo (draft_content) để thẩm định trích dẫn.",
                },
                "current_step": "citation_skipped",
                "status": "success",
                "error": None,
            }

        logger.info(f"[LangGraph:citation_node] Checking citations (style: {citation_style}, papers: {len(selected_papers)})")
        report = await citation_agent.check_document_citations(
            content=draft_content,
            selected_papers=selected_papers,
            citation_style=citation_style,
        )
        report_data = report.model_dump()

        missing_claims_list = [c.model_dump() for c in report.missing_claims]

        return {
            "citation_report": report_data,
            "citations": missing_claims_list,
            "current_step": "citation_checked",
            "status": "completed",
            "error": None,
        }
    except Exception as e:
        logger.error(f"[LangGraph] Error in citation_node: {e}", exc_info=True)
        return {
            "error": str(e),
            "status": "failed",
            "current_step": "citation_error",
        }


# =====================================================================
# Routing Logic
# =====================================================================
def outline_route(state: AgentState) -> str:
    """Routes after outline: abort if failed or standalone outline call, else continue to literature search."""
    if state.get("status") == "failed":
        return END
    if state.get("mode") == "outline_only" or state.get("target_step") == "outline":
        return END
    # When executed without pipeline context (no project_id/draft_content/selected_papers), stop at outline
    if "project_id" not in state and "draft_content" not in state and "selected_papers" not in state:
        return END
    return "research_literature"


def literature_route(state: AgentState) -> str:
    """Routes after literature: abort if failed, else continue to citation validation."""
    if state.get("status") == "failed":
        return END
    return "validate_citations"


# =====================================================================
# Graph Construction & Checkpointing
# =====================================================================
shared_checkpointer = MemorySaver()


def build_academic_writing_graph(checkpointer: Optional[Any] = None) -> Any:
    """
    Builds and compiles the core 3-agent academic workflow.
    Pipeline: generate_outline -> research_literature -> validate_citations -> END
    """
    workflow = StateGraph(AgentState)

    # Register Nodes
    workflow.add_node("generate_outline", outline_node)
    workflow.add_node("research_literature", literature_node)
    workflow.add_node("validate_citations", citation_node)

    # Set Entry Point
    workflow.set_entry_point("generate_outline")

    # Conditional Edges for resilience
    workflow.add_conditional_edges(
        "generate_outline",
        outline_route,
        {"research_literature": "research_literature", END: END},
    )
    workflow.add_conditional_edges(
        "research_literature",
        literature_route,
        {"validate_citations": "validate_citations", END: END},
    )
    workflow.add_edge("validate_citations", END)

    if checkpointer is not None:
        return workflow.compile(checkpointer=checkpointer)
    return workflow.compile()


# Compiled Graph Singletons: persistent (with checkpointer) and direct (without checkpointer)
persistent_academic_graph = build_academic_writing_graph(checkpointer=shared_checkpointer)
academic_graph = build_academic_writing_graph(checkpointer=None)


# =====================================================================
# Orchestrator Public APIs
# =====================================================================
async def run_academic_pipeline(
    initial_state: Dict[str, Any],
    thread_id: Optional[str] = None,
    graph: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Executes or resumes the complete academic writing pipeline with state persistence.
    thread_id is mapped to project_id to isolate states across projects.
    """
    g = graph or persistent_academic_graph
    t_id = thread_id or initial_state.get("project_id", "default_project")
    config = {"configurable": {"thread_id": str(t_id)}}
    result = await g.ainvoke(initial_state, config=config)
    return result


def get_pipeline_state(thread_id: str, graph: Optional[Any] = None) -> Optional[Dict[str, Any]]:
    """Retrieves the latest checkpointed state snapshot for a given project thread."""
    g = graph or persistent_academic_graph
    config = {"configurable": {"thread_id": str(thread_id)}}
    snapshot = g.get_state(config)
    if snapshot and snapshot.values:
        return dict(snapshot.values)
    return None


def update_pipeline_state(
    thread_id: str,
    updates: Dict[str, Any],
    graph: Optional[Any] = None,
) -> Dict[str, Any]:
    """Updates specific keys in the checkpointed state for a given project thread."""
    g = graph or persistent_academic_graph
    config = {"configurable": {"thread_id": str(thread_id)}}
    g.update_state(config, updates)
    snapshot = g.get_state(config)
    return dict(snapshot.values) if snapshot and snapshot.values else {}
