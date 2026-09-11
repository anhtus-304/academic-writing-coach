from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Any
from pydantic import BaseModel
try:
    from backend.api.dependencies import get_current_user
    from backend.database import get_db
    from backend.models.user import User
    from backend.schemas.project_schemas import ProjectCreate, ProjectUpdate, ProjectResponse
    from backend.services import project_service
except ImportError:
    from api.dependencies import get_current_user
    from database import get_db
    from models.user import User
    from schemas.project_schemas import ProjectCreate, ProjectUpdate, ProjectResponse
    from services import project_service


router = APIRouter(prefix="/projects", tags=["projects"])

class OutlineGenerateRequest(BaseModel):
    template_id: Optional[str] = None
    user_requirements: Optional[str] = None

class OutlineUpdateRequest(BaseModel):
    chapters: Any
    suggestions: Optional[Any] = None

@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_in: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await project_service.create_project(db, current_user.id, project_in)

@router.get("/", response_model=List[ProjectResponse])
async def list_projects(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await project_service.list_projects(db, current_user.id, skip, limit)

@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = await project_service.get_project(db, project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    project_update: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = await project_service.get_project(db, project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return await project_service.update_project(db, project, project_update)

@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = await project_service.get_project(db, project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    await project_service.delete_project(db, project)
    return None

@router.post("/{project_id}/outline/generate")
async def generate_outline(
    project_id: str,
    body: OutlineGenerateRequest = OutlineGenerateRequest(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        outline = await project_service.generate_project_outline(
            db, project_id, current_user.id, body.template_id, body.user_requirements
        )
        if not outline:
            raise HTTPException(status_code=404, detail="Project not found")
        return {
            "success": True,
            "outline": {
                "id": outline.id,
                "project_id": outline.project_id,
                "title": outline.title,
                "chapters": outline.chapters,
                "suggestions": outline.suggestions,
                "template_source": outline.template_source,
                "version": outline.version,
                "generated_at": str(outline.generated_at),
                "updated_at": str(outline.updated_at)
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{project_id}/outline")
async def get_outline(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    outline = await project_service.get_project_outline(db, project_id, current_user.id)
    if not outline:
        return {"success": False, "outline": None}
    return {
        "success": True,
        "outline": {
            "id": outline.id,
            "project_id": outline.project_id,
            "title": outline.title,
            "chapters": outline.chapters,
            "suggestions": outline.suggestions,
            "template_source": outline.template_source,
            "version": outline.version,
            "generated_at": str(outline.generated_at),
            "updated_at": str(outline.updated_at)
        }
    }

@router.put("/{project_id}/outline")
async def update_outline(
    project_id: str,
    body: OutlineUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    outline = await project_service.update_project_outline(
        db, project_id, current_user.id, body.chapters, body.suggestions
    )
    if not outline:
        raise HTTPException(status_code=404, detail="Project not found")
    return {
        "success": True,
        "outline": {
            "id": outline.id,
            "project_id": outline.project_id,
            "title": outline.title,
            "chapters": outline.chapters,
            "suggestions": outline.suggestions,
            "version": outline.version
        }
    }