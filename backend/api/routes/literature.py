from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from backend.api.dependencies import get_current_user
    from backend.database import get_db
    from backend.models.user import User
    from backend.schemas.literature_schemas import (
        LiteratureSearchRequest,
        LiteratureSearchResponse,
        ProjectSelectedPapersResponse,
        RecentSearchResponse,
        SelectedPaperItem,
        SelectPaperRequest,
    )
    from backend.services import literature_service, project_service
except ImportError:
    from api.dependencies import get_current_user
    from database import get_db
    from models.user import User
    from schemas.literature_schemas import (
        LiteratureSearchRequest,
        LiteratureSearchResponse,
        ProjectSelectedPapersResponse,
        RecentSearchResponse,
        SelectedPaperItem,
        SelectPaperRequest,
    )
    from services import literature_service, project_service

router = APIRouter(tags=["literature"])


# -----------------------------------------------------------------------------
# 1. Direct literature search & summarization (Frontend Workspace UI)
# -----------------------------------------------------------------------------

@router.get("/literature/search")
async def search_literature_route(
    query: str = Query(..., min_length=1),
    source: Optional[str] = Query(default=None),
    year: Optional[str] = Query(default=None),
    publication_type: Optional[str] = Query(default=None),
    limit: int = Query(default=10, ge=1, le=20),
    enable_semantic_expansion: bool = Query(default=True),
):
    if not query.strip():
        raise HTTPException(status_code=400, detail="Query không được để trống")

    sources = None
    if source:
        sources = [source.lower()]

    papers, expanded_queries = await literature_service.search_direct_literature(
        query=query,
        limit=limit,
        sources=sources,
        enable_semantic_expansion=enable_semantic_expansion,
        return_expanded_queries=True,
    )

    if year == "2020s":
        papers = [paper for paper in papers if paper.get("year") and paper["year"] >= 2020]
    elif year == "2010s":
        papers = [paper for paper in papers if paper.get("year") and 2010 <= paper["year"] < 2020]

    if publication_type:
        target = publication_type.lower()
        papers = [
            paper for paper in papers
            if (paper.get("publicationType") or "").lower() == target
        ]

    return {
        "query": query,
        "expanded_queries": expanded_queries,
        "total_results": len(papers),
        "papers": papers,
    }


@router.post("/literature/summarize")
async def summarize_literature_route(payload: Dict[str, Any]):
    paper = payload.get("paper")
    if not paper:
        raise HTTPException(status_code=400, detail="Thiếu thông tin tài liệu để tóm tắt")

    try:
        summary_vi = await literature_service.summarize_paper(paper)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Không thể tóm tắt tài liệu: {exc}") from exc

    return {
        "paper_id": paper.get("id"),
        "summary_vi": summary_vi,
    }


# -----------------------------------------------------------------------------
# 2. Project-scoped literature search with 48h DB Caching & Credits (Task 11)
# -----------------------------------------------------------------------------

@router.post("/projects/{project_id}/literature/search", response_model=LiteratureSearchResponse)
async def search_literature_for_project(
    project_id: str,
    body: LiteratureSearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LiteratureSearchResponse:
    # Ensure the project exists and belongs to the authenticated user.
    project = await project_service.get_project(db, project_id, current_user.id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    result = await literature_service.search_project_literature(
        db,
        project,
        body.query,
        body.filters,
        current_user,
    )
    return LiteratureSearchResponse(**result)


# -----------------------------------------------------------------------------
# 3. Project-scoped Selected Papers Management & Recent Search Cache
# -----------------------------------------------------------------------------

@router.post("/projects/{project_id}/literature/select", response_model=SelectedPaperItem)
async def select_paper_route(
    project_id: str,
    body: SelectPaperRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SelectedPaperItem:
    project = await project_service.get_project(db, project_id, current_user.id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    res = await literature_service.select_paper_for_project(
        db=db,
        project=project,
        paper_data=body.paper,
        cached_paper_id=body.cached_paper_id,
        relevant_sections=body.relevant_sections,
        notes=body.notes,
    )
    return SelectedPaperItem(**res)


@router.get("/projects/{project_id}/literature/selected", response_model=ProjectSelectedPapersResponse)
async def get_selected_papers_route(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectSelectedPapersResponse:
    project = await project_service.get_project(db, project_id, current_user.id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    res = await literature_service.get_project_selected_papers(db, project_id)
    return ProjectSelectedPapersResponse(**res)


@router.delete("/projects/{project_id}/literature/selected/{selected_paper_id}")
async def remove_selected_paper_route(
    project_id: str,
    selected_paper_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = await project_service.get_project(db, project_id, current_user.id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    removed = await literature_service.remove_selected_paper(db, project_id, selected_paper_id)
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tài liệu đã chọn không tồn tại hoặc đã bị xóa.",
        )
    return {"message": "Đã xóa tài liệu khỏi danh mục thành công"}


@router.get("/projects/{project_id}/literature/recent-search", response_model=RecentSearchResponse)
async def get_recent_search_route(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RecentSearchResponse:
    project = await project_service.get_project(db, project_id, current_user.id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    res = await literature_service.get_recent_search_session(db, project_id)
    return RecentSearchResponse(**res)

