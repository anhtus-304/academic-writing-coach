from fastapi import APIRouter, Depends, HTTPException, status, Response, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Any
from pydantic import BaseModel
try:
    from backend.api.dependencies import get_current_user
    from backend.database import get_db
    from backend.models.user import User
    from backend.schemas.project_schemas import (
        ProjectCreate,
        ProjectUpdate,
        ProjectResponse,
        DocumentDraftUpdate,
        DocumentDraftResponse,
    )
    from backend.services import project_service
except ImportError:
    from api.dependencies import get_current_user
    from database import get_db
    from models.user import User
    from schemas.project_schemas import (
        ProjectCreate,
        ProjectUpdate,
        ProjectResponse,
        DocumentDraftUpdate,
        DocumentDraftResponse,
    )
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


class ExportRequest(BaseModel):
    html_content: str
    topic: Optional[str] = None


# --- DRAFT DOCUMENT ENDPOINTS ---
@router.get("/{project_id}/document")
async def get_document(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    doc = await project_service.get_project_document(db, project_id, current_user.id)
    if not doc:
        return {"success": False, "document": None}

    content_val = doc.content
    html_val = content_val.get("html") if isinstance(content_val, dict) else str(content_val)

    return {
        "success": True,
        "document": {
            "id": doc.id,
            "project_id": doc.project_id,
            "content": content_val,
            "html": html_val,
            "chapter_ref": doc.chapter_ref,
            "word_count": doc.word_count,
            "version": doc.version,
            "created_at": str(doc.created_at) if doc.created_at else None,
            "updated_at": str(doc.updated_at) if doc.updated_at else None,
        }
    }


@router.put("/{project_id}/document")
async def save_document(
    project_id: str,
    body: DocumentDraftUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    doc = await project_service.save_project_document(
        db, project_id, current_user.id, body.content, body.chapter_ref, body.word_count or 0
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Project not found")

    content_val = doc.content
    html_val = content_val.get("html") if isinstance(content_val, dict) else str(content_val)

    return {
        "success": True,
        "document": {
            "id": doc.id,
            "project_id": doc.project_id,
            "content": content_val,
            "html": html_val,
            "chapter_ref": doc.chapter_ref,
            "word_count": doc.word_count,
            "version": doc.version,
            "updated_at": str(doc.updated_at) if doc.updated_at else None,
        }
    }


# --- EXPORT ENDPOINTS ---
@router.post("/{project_id}/export/docx")
async def export_docx(
    project_id: str,
    body: ExportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = await project_service.get_project(db, project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        from backend.services import export_service
    except ImportError:
        from services import export_service

    topic = body.topic or project.topic or "Bao_Cao_Nghien_Cuu"
    buffer = export_service.export_to_docx(topic=topic, html_content=body.html_content)

    clean_filename = "".join(c for c in topic if c.isalnum() or c in (" ", "_", "-")).strip().replace(" ", "_")
    if not clean_filename:
        clean_filename = "Academic_Paper"

    return Response(
        content=buffer.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f'attachment; filename="{clean_filename}.docx"'
        }
    )


@router.post("/{project_id}/export/markdown")
async def export_markdown(
    project_id: str,
    body: ExportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = await project_service.get_project(db, project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        from backend.services import export_service
    except ImportError:
        from services import export_service

    topic = body.topic or project.topic or "Bao_Cao_Nghien_Cuu"
    md_content = export_service.export_to_markdown(topic=topic, html_content=body.html_content)

    clean_filename = "".join(c for c in topic if c.isalnum() or c in (" ", "_", "-")).strip().replace(" ", "_")
    if not clean_filename:
        clean_filename = "Academic_Paper"

    return Response(
        content=md_content,
        media_type="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{clean_filename}.md"'
        }
    )


# --- IMPORT ENDPOINTS ---
@router.post("/{project_id}/import/outline")
async def import_outline(
    project_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = await project_service.get_project(db, project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        from backend.services import import_service
    except ImportError:
        from services import import_service

    file_bytes = await file.read()
    filename = file.filename or ""
    ext = filename.lower().split(".")[-1] if "." in filename else ""

    if ext in ("docx", "doc"):
        nodes = import_service.parse_outline_from_docx(file_bytes)
    elif ext in ("md", "markdown", "txt"):
        content_str = file_bytes.decode("utf-8", errors="replace")
        nodes = import_service.parse_outline_from_markdown(content_str)
    else:
        raise HTTPException(status_code=400, detail="Định dạng file không hỗ trợ. Vui lòng tải lên file .docx hoặc .md")

    return {"success": True, "nodes": nodes, "filename": filename}


@router.post("/{project_id}/import/document")
async def import_document(
    project_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = await project_service.get_project(db, project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        from backend.services import import_service
    except ImportError:
        from services import import_service

    file_bytes = await file.read()
    filename = file.filename or ""

    try:
        html = import_service.convert_file_to_editor_html(file_bytes, filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi đọc file: {str(e)}")

    return {"success": True, "html_content": html, "filename": filename}