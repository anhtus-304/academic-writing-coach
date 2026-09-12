import re
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from backend.api.dependencies import get_current_user
    from backend.database import get_db
    from backend.models.selected_paper import SelectedPaper
    from backend.models.cached_paper import CachedPaper
    from backend.models.user import User
    from backend.agents.citation_agent import citation_agent
    from backend.schemas.citation_schemas import (
        CitationMetadataSchema,
        CitationStyle,
        FormatCitationRequest,
        FormatCitationResponse,
    )
    from backend.services.ai_use_logger import ai_use_logger
    from backend.services.citation_formatter import CitationFormatterService
    from backend.services.credit_service import deduct_credits
    from backend.services import project_service
except ImportError:
    from api.dependencies import get_current_user
    from database import get_db
    from models.selected_paper import SelectedPaper
    from models.cached_paper import CachedPaper
    from models.user import User
    from agents.citation_agent import citation_agent
    from schemas.citation_schemas import (
        CitationMetadataSchema,
        CitationStyle,
        FormatCitationRequest,
        FormatCitationResponse,
    )
    from services.ai_use_logger import ai_use_logger
    from services.citation_formatter import CitationFormatterService
    from services.credit_service import deduct_credits
    import services.project_service as project_service

router = APIRouter(tags=["citation"])

CITATION_CHECK_COST = 2

CLAIM_INDICATORS = [
    r"\b\d+[\.,]?\d*%",
    r"\bchiếm\s+\d+",
    r"\btăng\s+\d+",
    r"\bgiảm\s+\d+",
    r"\btheo\s+nghiên\s+cứu\b",
    r"\bcác\s+nghiên\s+cứu\s+chỉ\s+ra\b",
    r"\btheo\s+báo\s+cáo\b",
    r"\bthống\s+kê\s+cho\s+thấy\b",
    r"\bkết\s+quả\s+cho\s+thấy\b",
    r"\bđược\s+chứng\s+minh\s+là\b",
    r"\bkhảo\s+sát\s+tại\b",
]

CITATION_PATTERNS = [
    r"\[\d+\]",                       # IEEE [1]
    r"\([A-ZÀ-Ỹa-zà-ỹ\s]+,\s*\d{4}\)", # APA (Author, 2023)
    r"\([A-ZÀ-Ỹa-zà-ỹ\s]+et\s+al\.,\s*\d{4}\)",
]


class CitationCheckRequest(BaseModel):
    content: str = Field(..., min_length=10, description="Draft text or HTML content to analyze")
    citation_style: Optional[str] = Field("apa7", description="Citation style: apa7, ieee, bgddt")


class MissingCitationClaim(BaseModel):
    sentence: str
    reason: str
    suggested_action: str


class CitationCheckResponse(BaseModel):
    total_issues: int
    missing_claims: List[MissingCitationClaim]
    invalid_citations: List[str]
    verified_count: int
    credits_charged: int
    suggestions: List[Dict[str, Any]] = Field(default_factory=list)
    bibliography: List[str] = Field(default_factory=list)


def _clean_html_to_text(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _split_into_sentences(text: str) -> List[str]:
    # Split by periods, question marks, exclamation marks followed by whitespace or end
    raw_sentences = re.split(r"(?<=[.?!])\s+", text)
    return [s.strip() for s in raw_sentences if len(s.strip()) > 15]


@router.post("/projects/{project_id}/citation/check", response_model=CitationCheckResponse)
async def check_citations_route(
    project_id: str,
    body: CitationCheckRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CitationCheckResponse:
    project = await project_service.get_project(db, project_id, current_user.id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # 1. Deduct 2 Credits
    deducted = await deduct_credits(
        db,
        current_user,
        CITATION_CHECK_COST,
        "Kiểm tra trích dẫn toàn bài (Citation Agent)",
    )
    if not deducted:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Số dư không đủ để kiểm tra trích dẫn toàn bài (Cần 2 Credits).",
        )

    # 2. Get Selected Papers of project for cross-referencing
    sel_stmt = (
        select(SelectedPaper)
        .where(SelectedPaper.project_id == project.id)
    )
    sel_res = await db.execute(sel_stmt)
    selected_papers = sel_res.scalars().all()

    selected_metadata: List[Dict[str, Any]] = []
    for sp in selected_papers:
        cp = await db.get(CachedPaper, sp.cached_paper_id)
        if cp and cp.authors:
            selected_metadata.append({
                "title": cp.title,
                "authors": cp.authors,
                "year": cp.year,
                "doi": cp.doi,
                "url": cp.url,
                "abstract": cp.abstract,
                "publicationType": cp.source,
            })

    # 3. Analyze content through the shared agent implementation
    plain_text = _clean_html_to_text(body.content)
    agent_result = await citation_agent.run({
        "content": plain_text,
        "citation_style": body.citation_style,
        "selected_papers": selected_metadata,
    })
    missing_claims = [MissingCitationClaim(**claim) for claim in agent_result["missing_claims"]]
    invalid_citations = agent_result["invalid_citations"]
    verified_count = agent_result["verified_count"]
    total_issues = len(missing_claims) + len(invalid_citations)

    # 4. Log AI usage
    try:
        await ai_use_logger.log_ai_usage(
            agent_name="CitationAgent",
            tokens_used=len(plain_text) // 4,
            user_id=str(current_user.id),
            project_id=str(project.id),
            input_summary={"word_count": len(plain_text.split()), "citation_style": body.citation_style},
            output_summary={"total_issues": total_issues, "missing_claims": len(missing_claims)},
            credits_charged=CITATION_CHECK_COST,
            db=db,
        )
    except Exception as exc:
        pass

    await db.commit()

    return CitationCheckResponse(
        total_issues=total_issues,
        missing_claims=missing_claims,
        invalid_citations=invalid_citations,
        verified_count=verified_count,
        credits_charged=CITATION_CHECK_COST,
        suggestions=agent_result["suggestions"],
        bibliography=agent_result["bibliography"],
    )


@router.post("/citation/format", response_model=FormatCitationResponse)
async def format_citation_standalone(body: FormatCitationRequest) -> FormatCitationResponse:
    return CitationFormatterService.format_citation(
        metadata=body.metadata,
        style=body.style,
        index=body.index,
    )
