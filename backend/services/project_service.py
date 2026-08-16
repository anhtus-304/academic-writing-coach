from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models.project import Project
from schemas.project_schemas import ProjectCreate, ProjectUpdate
import uuid

async def create_project(db: AsyncSession, user_id: str, project_in: ProjectCreate) -> Project:
    project = Project(
        id=str(uuid.uuid4()),
        user_id=user_id,
        topic=project_in.topic,
        document_type=project_in.document_type.value,
        field=project_in.field,
        university=project_in.university,
        citation_style=project_in.citation_style.value,
        additional_requirements=project_in.additional_requirements,
        status="draft"
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