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
        ProjectCitationFormatRequest,
        ProjectCitationFormatResponse,
        FormattedPaperCitation,
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
        ProjectCitationFormatRequest,
        ProjectCitationFormatResponse,
        FormattedPaperCitation,
    )
    from services.ai_use_logger import ai_use_logger
    from services.citation_formatter import CitationFormatterService
    from services.credit_service import deduct_credits
    import services.project_service as project_service
    from agents.citation_agent import citation_agent

router = APIRouter(tags=["citation"])

CITATION_CHECK_COST = 2


def _resolve_style(*candidates: Any) -> CitationStyle:
    """Pick the first valid citation style from the given candidates."""
    valid = {s.value for s in CitationStyle}
    for candidate in candidates:
        if not candidate:
            continue
        value = str(getattr(candidate, "value", candidate)).lower()
        if value in valid:
            return CitationStyle(value)
    return CitationStyle.APA7


async def _load_project_papers(db: AsyncSession, project: Any) -> List[Dict[str, Any]]:
    """Load every SelectedPaper of a project (CachedPaper eagerly attached)."""
    sel_stmt = (
        select(SelectedPaper)
        .options(selectinload(SelectedPaper.cached_paper))
        .where(SelectedPaper.project_id == project.id)
    )
    sel_res = await db.execute(sel_stmt)
    selected_papers = sel_res.scalars().all()

    papers_payload: List[Dict[str, Any]] = []
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
            "year": (cp.year if cp else None) or 2024,
            "venue": cp.source if cp else None,
            "doi": cp.doi if cp else None,
            "url": cp.url if cp else None,
        })
    return papers_payload


def _filter_papers_by_ids(
    papers_payload: List[Dict[str, Any]], paper_ids: List[str]
) -> List[Dict[str, Any]]:
    """Keep only papers whose SelectedPaper id *or* CachedPaper id was requested."""
    wanted = {str(pid) for pid in paper_ids}
    return [
        paper
        for paper in papers_payload
        if str(paper.get("id")) in wanted or str(paper.get("cached_paper_id")) in wanted
    ]


def _build_bibliography_html(entries: List[str], style: CitationStyle) -> str:
    """Render a bibliography list as HTML (ordered for numbered styles)."""
    if style in (CitationStyle.IEEE, CitationStyle.BGDDT):
        html_items = "".join(f"<li>{entry}</li>" for entry in entries)
        return f"<ol class='bibliography-list'>{html_items}</ol>"
    html_items = "".join(f"<p class='apa-reference'>{entry}</p>" for entry in entries)
    return f"<div class='bibliography-container'>{html_items}</div>"


@router.post("/projects/{project_id}/citation/check", response_model=CitationCheckResponse)
async def check_citations_route(
    project_id: str,
    body: CitationCheckRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CitationCheckResponse:
    """
    Citation Check API (trừ **2 credits**):

    * tách câu an toàn với viết tắt (`et al.`, `TS.`, `pp.`...) rồi phát hiện in-text
      citation APA (`(Nguyen, 2023)`) và IEEE (`[1, 2]`, `[1-3]`);
    * phần chính là **rule-based** (regex + whitelist câu thuộc về chính tác giả) nên
      tìm được câu/nhận định cần nguồn nhưng *thiếu trích dẫn* mà không cần LLM;
    * đối chiếu 2 chiều với tài liệu đã chọn của project: ghost citation, sai năm,
      paper chưa được trích dẫn (có thể giới hạn danh mục bằng ``paper_ids``);
    * trả về `missing[]` = `{text, index, suggestion}` (kèm `total_missing`) và bản đầy
      đủ `missing_claims[]` với offset `sentence_index`/`char_offset`/`char_end` cho Tiptap.
    """
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
    #    (``paper_ids`` optionally narrows the reference catalog to a subset).
    papers_payload = await _load_project_papers(db, project)
    if body.paper_ids:
        papers_payload = _filter_papers_by_ids(papers_payload, body.paper_ids)

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

    target_style = _resolve_style(style, project.citation_style)

    papers_payload = await _load_project_papers(db, project)

    bib_list = citation_agent.format_citations(papers_payload, target_style.value)
    html_formatted = _build_bibliography_html(bib_list, target_style)

    return ProjectBibliographyResponse(
        project_id=str(project.id),
        style=target_style,
        total_references=len(bib_list),
        bibliography=bib_list,
        bibliography_text="\n".join(bib_list),
        html_formatted=html_formatted,
    )


@router.post("/citation/format", response_model=FormatCitationResponse)
async def format_citation_standalone(body: FormatCitationRequest) -> FormatCitationResponse:
    return CitationFormatterService.format_citation(
        metadata=body.metadata,
        style=body.style,
        index=body.index,
    )


@router.post(
    "/projects/{project_id}/citation/format",
    response_model=ProjectCitationFormatResponse,
)
async def format_project_citations_route(
    project_id: str,
    body: Optional[ProjectCitationFormatRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectCitationFormatResponse:
    """
    Project-scoped Citation Formatter API:

    * reads the selected papers of the project (optionally a subset via
      ``selected_paper_ids``);
    * formats every paper with the rule-based formatter in the requested style
      (``apa7`` | ``ieee`` | ``bgddt``), falling back to the project style;
    * returns per-paper in-text + full citations **and** the complete sorted
      bibliography ready to be inserted into the draft.
    """
    body = body or ProjectCitationFormatRequest()

    project = await project_service.get_project(db, project_id, current_user.id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    target_style = _resolve_style(body.style, project.citation_style)

    papers_payload = await _load_project_papers(db, project)
    requested_ids = body.selected_paper_ids or body.paper_ids
    if requested_ids:
        papers_payload = _filter_papers_by_ids(papers_payload, requested_ids)

    detailed = citation_agent.format_citations_detailed(papers_payload, target_style.value)
    bibliography = citation_agent.format_citations(papers_payload, target_style.value)
    html_formatted = _build_bibliography_html(bibliography, target_style)

    citations = [
        FormattedPaperCitation(
            **{
                **entry,
                "in_text_citation": entry["in_text_citation"] if body.include_in_text else "",
            }
        )
        for entry in detailed
    ]

    return ProjectCitationFormatResponse(
        project_id=str(project.id),
        style=target_style,
        total_citations=len(citations),
        citations=citations,
        bibliography=bibliography,
        bibliography_text="\n".join(bibliography),
        html_formatted=html_formatted,
    )

