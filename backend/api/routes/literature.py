from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from services.literature_service import search_literature, summarize_paper

router = APIRouter(prefix="/literature", tags=["literature"])


@router.get("/search")
async def search_literature_route(
    query: str = Query(..., min_length=1),
    source: Optional[str] = Query(default=None),
    year: Optional[str] = Query(default=None),
    publication_type: Optional[str] = Query(default=None),
    limit: int = Query(default=10, ge=1, le=20),
):
    if not query.strip():
        raise HTTPException(status_code=400, detail="Query không được để trống")

    sources = None
    if source:
        sources = [source.lower()]

    papers = await search_literature(query=query, limit=limit, sources=sources)

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
        "total_results": len(papers),
        "papers": papers,
    }


@router.post("/summarize")
async def summarize_literature_route(payload: Dict[str, Any]):
    paper = payload.get("paper")
    if not paper:
        raise HTTPException(status_code=400, detail="Thiếu thông tin tài liệu để tóm tắt")

    try:
        summary_vi = await summarize_paper(paper)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Không thể tóm tắt tài liệu: {exc}") from exc

    return {
        "paper_id": paper.get("id"),
        "summary_vi": summary_vi,
    }
