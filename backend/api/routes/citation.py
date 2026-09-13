from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from backend.api.dependencies import get_current_user
    from backend.database import get_db
    from backend.models.selected_paper import SelectedPaper
    from backend.models.cached_paper import CachedPaper
    from backend.models.user import User
    from backend.schemas.citation_schemas import (
        CitationMetadataSchema,
        CitationStyle,
        FormatCitationRequest,
        FormatCitationResponse,
        CitationCheckRequest,
        CitationCheckResponse,
        ProjectBibliographyResponse,
    )
    from backend.services.ai_use_logger import ai_use_logger
    from backend.services.citation_formatter import CitationFormatterService
    from backend.services.credit_service import deduct_credits
    from backend.services import project_service
    from backend.agents.citation_agent import citation_agent
except ImportError:
    from api.dependencies import get_current_user
    from database import get_db
    from models.selected_paper import SelectedPaper
    from models.cached_paper import CachedPaper
    from models.user import User
    from schemas.citation_schemas import (
        CitationMetadataSchema,
        CitationStyle,
        FormatCitationRequest,
        FormatCitationResponse,
        CitationCheckRequest,
        CitationCheckResponse,
        ProjectBibliographyResponse,
    )
    from services.ai_use_logger import ai_use_logger
    from services.citation_formatter import CitationFormatterService
    from services.credit_service import deduct_credits
    import services.project_service as project_service
    from agents.citation_agent import citation_agent

router = APIRouter(tags=["citation"])

CITATION_CHECK_COST = 2


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

    # 2. Get Selected Papers of project with CachedPaper for cross-referencing
    sel_stmt = (
        select(SelectedPaper)
        .options(selectinload(SelectedPaper.cached_paper))
        .where(SelectedPaper.project_id == project.id)
    )
    sel_res = await db.execute(sel_stmt)
    selected_papers = sel_res.scalars().all()

    # If cached_paper relationship is not loaded or None, fallback to query directly
    papers_payload = []
    for sp in selected_papers:
        cp = sp.cached_paper
        if not cp and sp.cached_paper_id:
            cp = await db.get(CachedPaper, sp.cached_paper_id)
        papers_payload.append({
            "id": sp.id,
            "cached_paper_id": sp.cached_paper_id,
            "cached_paper": cp,
            "title": cp.title if cp else "Tài liệu",
            "authors": cp.authors if cp else [],
            "year": cp.year if cp else (cp.publication_year if cp else 2024),
            "venue": cp.source if cp else None,
            "doi": cp.doi if cp else None,
            "url": cp.url if cp else None,
        })

    # 3. Execute CitationAgent analysis
    style = body.citation_style or project.citation_style or "apa7"
    agent_res = await citation_agent.check_document_citations(
        content=body.content,
        selected_papers=papers_payload,
        citation_style=style,
    )

    # 4. Log AI usage
    try:
        plain_len = len(citation_agent.clean_html_to_text(body.content))
        await ai_use_logger.log_ai_usage(
            agent_name="CitationAgent",
            tokens_used=plain_len // 4,
            user_id=str(current_user.id),
            project_id=str(project.id),
            input_summary={"word_count": plain_len // 6, "citation_style": style},
            output_summary={
                "total_issues": agent_res.total_issues,
                "missing_claims": len(agent_res.missing_claims),
                "invalid_citations": len(agent_res.invalid_citations),
                "uncited_papers": len(agent_res.uncited_papers),
            },
            credits_charged=CITATION_CHECK_COST,
            db=db,
        )
    except Exception:
        pass

    await db.commit()

    return agent_res


@router.post("/projects/{project_id}/citation/bibliography", response_model=ProjectBibliographyResponse)
async def generate_project_bibliography_route(
    project_id: str,
    style: Optional[str] = Query(None, description="Optional citation style override (apa7, ieee, bgddt)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectBibliographyResponse:
    """
    Bibliography Generator API:
    Automatically fetches all selected papers of the project, formats each entry according
    to the target academic style (APA 7, IEEE, or Bộ GD&ĐT), and returns the sorted bibliography.
    """
    project = await project_service.get_project(db, project_id, current_user.id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    target_style_str = (style or project.citation_style or "apa7").lower()
    target_style = CitationStyle(target_style_str) if target_style_str in [s.value for s in CitationStyle] else CitationStyle.APA7

    sel_stmt = (
        select(SelectedPaper)
        .options(selectinload(SelectedPaper.cached_paper))
        .where(SelectedPaper.project_id == project.id)
    )
    sel_res = await db.execute(sel_stmt)
    selected_papers = sel_res.scalars().all()

    papers_payload = []
    for sp in selected_papers:
        cp = sp.cached_paper
        if not cp and sp.cached_paper_id:
            cp = await db.get(CachedPaper, sp.cached_paper_id)
        papers_payload.append({
            "id": sp.id,
            "cached_paper_id": sp.cached_paper_id,
            "cached_paper": cp,
            "title": cp.title if cp else "Tài liệu",
            "authors": cp.authors if cp else [],
            "year": cp.year if cp else (cp.publication_year if cp else 2024),
            "venue": cp.source if cp else None,
            "doi": cp.doi if cp else None,
            "url": cp.url if cp else None,
        })

    bib_list = citation_agent.generate_project_bibliography(
        selected_papers=papers_payload,
        citation_style=target_style.value,
    )

    # Format into HTML unordered list or ordered list
    if target_style in (CitationStyle.IEEE, CitationStyle.BGDDT):
        html_items = "".join(f"<li>{entry}</li>" for entry in bib_list)
        html_formatted = f"<ol class='bibliography-list'>{html_items}</ol>"
    else:
        html_items = "".join(f"<p class='apa-reference'>{entry}</p>" for entry in bib_list)
        html_formatted = f"<div class='bibliography-container'>{html_items}</div>"

    return ProjectBibliographyResponse(
        project_id=str(project.id),
        style=target_style,
        total_references=len(bib_list),
        bibliography=bib_list,
        html_formatted=html_formatted,
    )


@router.post("/citation/format", response_model=FormatCitationResponse)
async def format_citation_standalone(body: FormatCitationRequest) -> FormatCitationResponse:
    return CitationFormatterService.format_citation(
        metadata=body.metadata,
        style=body.style,
        index=body.index,
    )

