from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_current_user
from database import get_db
from models.user import User
from schemas.literature_schemas import (
    LiteratureSearchRequest,
    LiteratureSearchResponse,
)
from services import literature_service, project_service

router = APIRouter(
    prefix="/projects/{project_id}/literature",
    tags=["literature"],
)


@router.post("/search", response_model=LiteratureSearchResponse)
async def search_literature(
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

    result = await literature_service.search_literature(
        db,
        project,
        body.query,
        body.filters,
        current_user,
    )
    return LiteratureSearchResponse(**result)