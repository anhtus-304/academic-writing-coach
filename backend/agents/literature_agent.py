import time
import logging
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from backend.agents.base_agent import BaseAgent
    from backend.services.llm_service import LLMService, llm_service
    from backend.services.ai_use_logger import AIUseLogger, ai_use_logger
    from backend.services.search_aggregator import SearchAggregator, search_aggregator
    from backend.schemas.literature_schemas import (
        QueryGeneratorRequest,
        QueryGeneratorResponse,
        SearchQueryItem,
        PaperSummaryRequest,
        PaperSummaryResponse,
        PaperSchema,
        SearchResponseSchema,
    )
    from backend.prompts.literature_prompts import (
        QUERY_GENERATOR_SYSTEM_PROMPT,
        QUERY_GENERATOR_USER_PROMPT_TEMPLATE,
        LLM_SUMMARIZER_SYSTEM_PROMPT,
        LLM_SUMMARIZER_USER_PROMPT_TEMPLATE,
    )
except ImportError:
    from agents.base_agent import BaseAgent
    from services.llm_service import LLMService, llm_service
    from services.ai_use_logger import AIUseLogger, ai_use_logger
    from services.search_aggregator import SearchAggregator, search_aggregator
    from schemas.literature_schemas import (
        QueryGeneratorRequest,
        QueryGeneratorResponse,
        SearchQueryItem,
        PaperSummaryRequest,
        PaperSummaryResponse,
        PaperSchema,
        SearchResponseSchema,
    )
    from prompts.literature_prompts import (
        QUERY_GENERATOR_SYSTEM_PROMPT,
        QUERY_GENERATOR_USER_PROMPT_TEMPLATE,
        LLM_SUMMARIZER_SYSTEM_PROMPT,
        LLM_SUMMARIZER_USER_PROMPT_TEMPLATE,
    )

logger = logging.getLogger(__name__)


class LiteratureAgent(BaseAgent):
    """Agent responsible for literature search query generation, paper summarization, and relevance scoring."""

    def __init__(
        self,
        llm_service_instance: Optional[LLMService] = None,
        logger_instance: Optional[AIUseLogger] = None,
        aggregator_instance: Optional[SearchAggregator] = None,
    ):
        super().__init__(llm_service_instance=llm_service_instance)
        self.ai_logger = logger_instance or ai_use_logger
        self.aggregator = aggregator_instance or search_aggregator

    async def generate_queries(
        self,
        topic: str,
        outline: Optional[str] = None,
        num_queries: int = 5,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> QueryGeneratorResponse:
        """Generates 3-5 academic search queries from research topic and outline."""
        start_time = time.time()
        user_prompt = QUERY_GENERATOR_USER_PROMPT_TEMPLATE.format(
            topic=topic,
            outline=outline or "Không có dàn ý chi tiết.",
        )

        response, usage = await self.llm_service.generate_structured_output_with_usage(
            system_prompt=QUERY_GENERATOR_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            schema=QueryGeneratorResponse,
        )

        duration_ms = int((time.time() - start_time) * 1000)
        tokens_used = usage.get("total_tokens", 0)

        # Backfill search_queries list if needed
        if not response.search_queries and response.queries:
            response.search_queries = [
                SearchQueryItem(
                    query=q,
                    language="en" if any(c.isalpha() and ord(c) < 128 for c in q) else "vi",
                    target_aspect="General academic search",
                )
                for q in response.queries
            ]

        # Log AI usage
        await self.ai_logger.log_ai_usage(
            agent_name="LiteratureAgent.generate_queries",
            tokens_used=tokens_used,
            user_id=user_id,
            project_id=project_id,
            input_summary={"topic": topic, "outline_provided": bool(outline)},
            output_summary={"num_queries_generated": len(response.queries)},
            duration_ms=duration_ms,
            db=db,
        )

        return response

    async def summarize_paper(
        self,
        title: str,
        abstract: str,
        topic: Optional[str] = None,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> PaperSummaryResponse:
        """Summarizes paper abstract into 2-3 Vietnamese sentences and scores relevance."""
        start_time = time.time()
        effective_topic = topic or "Chủ đề nghiên cứu tổng quát trong bài báo"
        user_prompt = LLM_SUMMARIZER_USER_PROMPT_TEMPLATE.format(
            topic=effective_topic,
            title=title,
            abstract=abstract,
        )

        response, usage = await self.llm_service.generate_structured_output_with_usage(
            system_prompt=LLM_SUMMARIZER_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            schema=PaperSummaryResponse,
        )

        duration_ms = int((time.time() - start_time) * 1000)
        tokens_used = usage.get("total_tokens", 0)

        # Log AI usage
        await self.ai_logger.log_ai_usage(
            agent_name="LiteratureAgent.summarize_paper",
            tokens_used=tokens_used,
            user_id=user_id,
            project_id=project_id,
            input_summary={"title": title, "topic": effective_topic},
            output_summary={"relevance_score": response.relevance_score},
            duration_ms=duration_ms,
            db=db,
        )

        return response

    async def search_and_summarize(
        self,
        topic: str,
        outline: Optional[str] = None,
        limit: int = 5,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> SearchResponseSchema:
        """Full pipeline: generate queries -> aggregate search results -> summarize abstracts & score relevance."""
        query_res = await self.generate_queries(
            topic=topic,
            outline=outline,
            user_id=user_id,
            project_id=project_id,
            db=db,
        )

        primary_query = query_res.queries[0] if query_res.queries else topic
        search_res = await self.aggregator.aggregate_search(query=primary_query, limit=limit)

        summarized_papers: List[PaperSchema] = []
        for paper in search_res.papers:
            if paper.abstract and len(paper.abstract.strip()) > 30:
                try:
                    summary_res = await self.summarize_paper(
                        title=paper.title,
                        abstract=paper.abstract,
                        topic=topic,
                        user_id=user_id,
                        project_id=project_id,
                        db=db,
                    )
                    updated_paper = paper.model_copy(
                        update={
                            "summary_vi": summary_res.summary_vi,
                            "relevance_score": summary_res.relevance_score,
                        }
                    )
                    summarized_papers.append(updated_paper)
                except Exception as err:
                    logger.error(f"Failed to summarize paper '{paper.title}': {err}")
                    summarized_papers.append(paper)
            else:
                summarized_papers.append(paper)

        # Sort by relevance score
        summarized_papers.sort(key=lambda p: p.relevance_score or 0.0, reverse=True)

        return SearchResponseSchema(
            query=primary_query,
            total_results=len(summarized_papers),
            papers=summarized_papers,
        )

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Main execution entry point for agent runner."""
        action = input_data.get("action", "generate_queries")
        topic = input_data.get("topic", "")
        outline = input_data.get("outline")
        user_id = input_data.get("user_id")
        project_id = input_data.get("project_id")

        if action == "generate_queries":
            res = await self.generate_queries(topic, outline, user_id=user_id, project_id=project_id)
            return res.model_dump()
        elif action == "summarize_paper":
            title = input_data.get("title", "")
            abstract = input_data.get("abstract", "")
            res = await self.summarize_paper(title, abstract, topic, user_id=user_id, project_id=project_id)
            return res.model_dump()
        elif action == "search_and_summarize":
            limit = input_data.get("limit", 5)
            res = await self.search_and_summarize(topic, outline, limit, user_id=user_id, project_id=project_id)
            return res.model_dump()
        else:
            raise ValueError(f"Unknown action '{action}' for LiteratureAgent.")


literature_agent = LiteratureAgent()
