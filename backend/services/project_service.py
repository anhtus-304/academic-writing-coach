from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
try:
    from backend.models.project import Project
    from backend.schemas.project_schemas import ProjectCreate, ProjectUpdate
except ImportError:
    from models.project import Project
    from schemas.project_schemas import ProjectCreate, ProjectUpdate

import uuid

from datetime import datetime, timezone

async def create_project(db: AsyncSession, user_id: str, project_in: ProjectCreate) -> Project:
    now = datetime.now(timezone.utc)
    project = Project(
        id=str(uuid.uuid4()),
        user_id=user_id,
        topic=project_in.topic,
        document_type=project_in.document_type.value,
        field=project_in.field,
        university=project_in.university,
        citation_style=project_in.citation_style.value,
        additional_requirements=project_in.additional_requirements,
        status="draft",
        created_at=now,
        updated_at=now
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project

async def get_project(db: AsyncSession, project_id: str, user_id: str) -> Project | None:
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == user_id)
    )
    return result.scalar_one_or_none()

async def list_projects(db: AsyncSession, user_id: str, skip: int = 0, limit: int = 100):
    result = await db.execute(
        select(Project)
        .where(Project.user_id == user_id)
        .order_by(Project.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

async def update_project(db: AsyncSession, project: Project, project_update: ProjectUpdate) -> Project:
    update_data = project_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if hasattr(project, key):
            setattr(project, key, value)
    await db.commit()
    await db.refresh(project)
    return project

async def delete_project(db: AsyncSession, project: Project) -> None:
    await db.delete(project)
    await db.commit()


async def get_project_outline(db: AsyncSession, project_id: str, user_id: str):
    try:
        from backend.models.outline import Outline
    except ImportError:
        from models.outline import Outline


    project = await get_project(db, project_id, user_id)
    if not project:
        return None
    result = await db.execute(
        select(Outline).where(Outline.project_id == project_id)
    )
    return result.scalar_one_or_none()


async def generate_project_outline(
    db: AsyncSession,
    project_id: str,
    user_id: str,
    template_id: str | None = None,
    user_requirements: str | None = None
):
    from fastapi import HTTPException, status
    try:
        from backend.models.outline import Outline
        from backend.models.user import User
        from backend.agents.outline_agent import outline_agent
        from backend.services.credit_service import deduct_credits
        from backend.services.ai_use_logger import ai_use_logger
    except ImportError:
        from models.outline import Outline
        from models.user import User
        from agents.outline_agent import outline_agent
        from services.credit_service import deduct_credits
        from services.ai_use_logger import ai_use_logger

    project = await get_project(db, project_id, user_id)
    if not project:
        return None

    user_res = await db.execute(select(User).where(User.id == user_id))
    user = user_res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    credit_deducted = await deduct_credits(
        db=db,
        user=user,
        amount=2,
        description=f"Sinh dàn ý AI cho dự án: {project.topic}",
    )
    if not credit_deducted:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Số dư không đủ để tạo dàn ý (Cần 2 Credits). Vui lòng nạp thêm credit."
        )

    academic_outline = await outline_agent.generate_outline(
        topic=project.topic,
        document_type=project.document_type,
        field=project.field,
        template_id=template_id,
        user_requirements=user_requirements or project.additional_requirements
    )

    outline_dict = academic_outline.model_dump()
    
    # Check if outline already exists for this project
    result = await db.execute(
        select(Outline).where(Outline.project_id == project_id)
    )
    outline = result.scalar_one_or_none()

    if not outline:
        outline = Outline(
            id=str(uuid.uuid4()),
            project_id=project_id,
            title=academic_outline.topic,
            chapters=outline_dict,
            suggestions={
                "research_methodology_suggestion": academic_outline.research_methodology_suggestion,
                "key_academic_keywords": academic_outline.key_academic_keywords,
                "writing_guidelines": academic_outline.writing_guidelines,
                "total_estimated_pages": academic_outline.total_estimated_pages,
            },
            template_source=template_id or project.document_type,
            version=1
        )
        db.add(outline)
    else:
        outline.title = academic_outline.topic
        outline.chapters = outline_dict
        outline.suggestions = {
            "research_methodology_suggestion": academic_outline.research_methodology_suggestion,
            "key_academic_keywords": academic_outline.key_academic_keywords,
            "writing_guidelines": academic_outline.writing_guidelines,
            "total_estimated_pages": academic_outline.total_estimated_pages,
        }
        outline.template_source = template_id or project.document_type
        outline.version += 1

    await db.commit()
    await db.refresh(outline)

    # Ghi nhận AI usage log
    try:
        await ai_use_logger.log_ai_usage(
            agent_name="OutlineAgent",
            tokens_used=1800,
            user_id=user_id,
            project_id=project_id,
            input_summary={"topic": project.topic, "template_id": template_id},
            output_summary={"chapters_count": len(academic_outline.chapters or [])},
            credits_charged=2,
            db=db,
        )
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("Failed to log outline AI usage: %s", exc)

    return outline


async def update_project_outline(
    db: AsyncSession,
    project_id: str,
    user_id: str,
    chapters_data: dict | list,
    suggestions_data: dict | None = None
):
    try:
        from backend.models.outline import Outline
    except ImportError:
        from models.outline import Outline

    project = await get_project(db, project_id, user_id)
    if not project:
        return None

    result = await db.execute(
        select(Outline).where(Outline.project_id == project_id)
    )
    outline = result.scalar_one_or_none()

    if not outline:
        outline = Outline(
            id=str(uuid.uuid4()),
            project_id=project_id,
            title=project.topic,
            chapters=chapters_data,
            suggestions=suggestions_data,
            version=1
        )
        db.add(outline)
    else:
        outline.chapters = chapters_data
        if suggestions_data is not None:
            outline.suggestions = suggestions_data
        outline.version += 1

    await db.commit()
    await db.refresh(outline)
    return outline