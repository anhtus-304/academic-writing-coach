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


# Compiled Graph Singleton
academic_graph = build_academic_writing_graph()
