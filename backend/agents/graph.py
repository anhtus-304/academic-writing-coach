import logging
from typing import Dict, Any, List, Optional, TypedDict
from langgraph.graph import StateGraph, END

logger = logging.getLogger(__name__)


class AgentState(TypedDict, total=False):
    """LangGraph State representation for Academic Writing Workflows."""
    topic: str
    document_type: str
    field: Optional[str]
    target_length: Optional[str]
    template_id: Optional[str]
    user_requirements: Optional[str]
    language: str
    
    # Generated Outputs
    outline: Optional[Dict[str, Any]]
    literature_review: Optional[Dict[str, Any]]
    citations: Optional[List[Dict[str, Any]]]
    document: Optional[str]
    citation_style: Optional[str]
    citation_issues: Optional[List[Dict[str, Any]]]
    citation_suggestions: Optional[List[Dict[str, Any]]]
    bibliography: Optional[List[str]]
    citation_metadata: Optional[List[Dict[str, Any]]]
    selected_papers: Optional[List[Dict[str, Any]]]
    
    # Workflow Metadata
    current_step: str
    status: str
    error: Optional[str]
    messages: List[Dict[str, str]]


async def outline_node(state: AgentState) -> Dict[str, Any]:
    """LangGraph node wrapper for outline generation step."""
    try:
        from backend.agents.outline_agent import outline_agent
    except ImportError:
        from agents.outline_agent import outline_agent
    
    try:
        result = await outline_agent.generate_outline(
            topic=state.get("topic", ""),
            document_type=state.get("document_type", "tieu_luan"),
            field=state.get("field"),
            target_length=state.get("target_length"),
            template_id=state.get("template_id"),
            user_requirements=state.get("user_requirements"),
            language=state.get("language", "vi"),
        )
        return {
            "outline": result.model_dump(),
            "current_step": "outline_generated",
            "status": "success",
        }
    except Exception as e:
        logger.error(f"[LangGraph] Error in outline_node: {e}")
        return {
            "error": str(e),
            "status": "failed",
            "current_step": "outline_error",
        }


async def literature_node(state: AgentState) -> Dict[str, Any]:
    """Run LiteratureAgent using the generated outline as context."""
    try:
        from backend.agents.literature_agent import literature_agent
    except ImportError:
        from agents.literature_agent import literature_agent

    try:
        result = await literature_agent.run({
            "action": "search_and_summarize",
            "topic": state.get("topic", ""),
            "outline": state.get("outline"),
            "limit": state.get("literature_limit", 5),
            "user_id": state.get("user_id"),
            "project_id": state.get("project_id"),
        })
        return {"literature_review": result, "current_step": "literature_completed", "status": "success"}
    except Exception as exc:
        logger.exception("[LangGraph] Error in literature_node")
        return {"error": str(exc), "status": "failed", "current_step": "literature_error"}


async def citation_node(state: AgentState) -> Dict[str, Any]:
    """Analyze document text against selected paper metadata."""
    try:
        from backend.agents.citation_agent import citation_agent
    except ImportError:
        from agents.citation_agent import citation_agent

    try:
        result = await citation_agent.run({
            "content": state.get("document", ""),
            "citation_style": state.get("citation_style", "apa7"),
            "selected_papers": state.get("selected_papers", []),
        })
        return {
            "citations": result.get("citation_issues", []),
            "citation_issues": result.get("citation_issues", []),
            "citation_suggestions": result.get("suggestions", []),
            "bibliography": result.get("bibliography", []),
            "citation_metadata": result.get("citation_metadata", []),
            "current_step": "citation_completed",
            "status": "success",
        }
    except Exception as exc:
        logger.exception("[LangGraph] Error in citation_node")
        return {"error": str(exc), "status": "failed", "current_step": "citation_error"}


async def formatter_node(state: AgentState) -> Dict[str, Any]:
    """Format the selected metadata with the rule-based citation service."""
    try:
        from backend.schemas.citation_schemas import CitationMetadataSchema, CitationStyle
        from backend.services.citation_formatter import CitationFormatterService
    except ImportError:
        from schemas.citation_schemas import CitationMetadataSchema, CitationStyle
        from services.citation_formatter import CitationFormatterService

    style_value = state.get("citation_style", "apa7")
    try:
        style = CitationStyle(style_value)
    except ValueError:
        style = CitationStyle.APA7
    metadata = [CitationMetadataSchema.model_validate(item) for item in state.get("citation_metadata", [])]
    bibliography = CitationFormatterService.format_bibliography(metadata, style=style).citations
    return {
        "bibliography": bibliography,
        "current_step": "citation_formatted",
        "status": "success",
    }


def build_academic_writing_graph() -> StateGraph:
    """Builds and compiles the core LangGraph workflow."""
    workflow = StateGraph(AgentState)

    # Add Nodes
    workflow.add_node("generate_outline", outline_node)

    # Set Entry Point
    workflow.set_entry_point("generate_outline")

    # Add Edge to END
    workflow.add_edge("generate_outline", END)

    return workflow.compile()


def build_full_academic_writing_graph() -> StateGraph:
    """Build the end-to-end graph while keeping the legacy graph unchanged."""
    workflow = StateGraph(AgentState)
    workflow.add_node("generate_outline", outline_node)
    workflow.add_node("run_literature", literature_node)
    workflow.add_node("run_citation", citation_node)
    workflow.add_node("run_formatter", formatter_node)
    workflow.set_entry_point("generate_outline")
    workflow.add_edge("generate_outline", "run_literature")
    workflow.add_edge("run_literature", "run_citation")
    workflow.add_edge("run_citation", "run_formatter")
    workflow.add_edge("run_formatter", END)
    return workflow.compile()


# Compiled Graph Singleton
academic_graph = build_academic_writing_graph()
full_academic_graph = build_full_academic_writing_graph()
