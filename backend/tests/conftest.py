"""Shared pytest configuration and fixtures (Week 3 backend task).

Design goals
------------
* **Hermetic**: every required setting gets a deterministic default *before* any
  backend module is imported, so tests never touch the real PostgreSQL database,
  never call OpenRouter and never need a ``backend/.env`` file.
* **Isolated**: a dedicated throwaway SQLite file (``_test_week3.db``) is used and
  each fixture creates its own user/project, so tests can run in any order and
  alongside the older test modules.
* **Async first**: ``asyncio_mode = auto`` (see ``pytest.ini``) plus
  ``httpx.AsyncClient`` + ``ASGITransport`` exercise the real ASGI app.

Available fixtures
------------------
``client``        -> ``httpx.AsyncClient`` bound to the FastAPI app
``db_session``    -> ``AsyncSession`` for direct DB assertions/seeding
``test_user``     -> persisted ``User`` with credits
``token``         -> signed JWT for ``test_user``
``auth_headers``  -> ``{"Authorization": "Bearer <jwt>"}``
``project``       -> persisted ``Project`` owned by ``test_user``
"""
import asyncio
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# 1. Test environment (must run before importing any backend module)
# ---------------------------------------------------------------------------
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

TEST_DB_FILE = "_test_week3.db"

# Every pytest session must start from a clean throwaway database: the SQLite file
# persists between runs, and modules that seed fixed data through the shared session
# DB (e.g. test_literature_credits_e2e.py seeding test@example.com) would otherwise
# fail with UNIQUE constraint errors on the second run.
_test_db_path = Path(TEST_DB_FILE)
if _test_db_path.exists():
    _test_db_path.unlink()

_ENV_DEFAULTS = {
    "DATABASE_URL": f"sqlite+aiosqlite:///./{TEST_DB_FILE}",
    "LITERATURE_MODE": "mock",
    "PROJECT_NAME": "Academic Writing Coach (test)",
    "API_V1_STR": "/api/v1",
    "APP_ENV": "test",
    "ENVIRONMENT": "test",
    "DEBUG": "True",
    "POSTGRES_SERVER": "localhost",
    "POSTGRES_USER": "postgres",
    "POSTGRES_PASSWORD": "postgres",
    "POSTGRES_DB": "academic_writing_test",
    "OPENROUTER_API_KEY": "test-openrouter-key",
    "OPENROUTER_BASE_URL": "https://openrouter.ai/api/v1",
    "DEFAULT_MODEL": "deepseek/deepseek-chat",
    "FALLBACK_MODEL": "deepseek/deepseek-r1",
    "JWT_SECRET": "test-jwt-secret",
    "JWT_SECRET_KEY": "test-jwt-secret",
    "JWT_ALGORITHM": "HS256",
    "JWT_EXPIRATION_MINUTES": "60",
    "ACCESS_TOKEN_EXPIRE_MINUTES": "60",
    "GOOGLE_REDIRECT_URI": "http://localhost:8000/api/v1/auth/google/callback",
    "SEMANTIC_SCHOLAR_SEARCH_URL": "https://api.semanticscholar.org/graph/v1/paper/search",
    "ARXIV_API_URL": "https://export.arxiv.org/api/query",
    "OPENALEX_WORKS_URL": "https://api.openalex.org/works",
    "BACKEND_CORS_ORIGINS": '["http://localhost:3000"]',
    # Rate limiting runs with the production default (60 req/phút); the per-test
    # tokens below keep every request in its own bucket, so the suite never trips it.
    "RATE_LIMIT_ENABLED": "True",
    "RATE_LIMIT_REQUESTS": "60",
    "RATE_LIMIT_WINDOW_SECONDS": "60",
}

for _key, _value in _ENV_DEFAULTS.items():
    os.environ.setdefault(_key, _value)

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from database import AsyncSessionLocal, Base, engine  # noqa: E402
from models.cached_paper import CachedPaper  # noqa: E402
from models.project import Project  # noqa: E402
from models.search_session import SearchSession  # noqa: E402
from models.user import User  # noqa: E402
from security import create_access_token  # noqa: E402


def run_async(coro):
    """Run a coroutine from synchronous code (e.g. module-level seeding)."""
    return asyncio.run(coro)


def unique_email(prefix: str = "week3") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}@example.com"


async def ensure_schema() -> None:
    """Create all tables in the throwaway test database (idempotent)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def create_user_with_project(
    credit_balance: int = 20,
    style: str = "apa7",
) -> tuple[User, Project]:
    """Seed one user + one project; returns the persisted ORM objects."""
    await ensure_schema()
    async with AsyncSessionLocal() as session:
        user = User(email=unique_email(), display_name="Week 3 Tester", credit_balance=credit_balance)
        session.add(user)
        await session.flush()
        project = Project(
            user_id=user.id,
            topic="Ứng dụng AI trong viết học thuật",
            document_type="tieu_luan",
            citation_style=style,
            status="draft",
        )
        session.add(project)
        await session.commit()
        await session.refresh(user)
        await session.refresh(project)
        return user, project


async def create_cached_paper(
    session,
    title: str = "Deep Learning for Academic Writing",
    abstract: str = "A study on transformer based writing assistants.",
    doi: str = None,
    year: int = 2023,
    relevance_score: float = 0.5,
    project_id: str = None,
) -> CachedPaper:
    """Insert a CachedPaper (with its SearchSession parent) into ``session``.

    ``CachedPaper.session_id``/``SearchSession.project_id`` are NOT NULL, so a
    throwaway owner + project is created when ``project_id`` is not supplied.
    """
    if project_id is None:
        _user, project = await create_user_with_project()
        project_id = str(project.id)

    search_session = SearchSession(
        project_id=project_id,
        query="seed",
        filters={},
        total_results=1,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=48),
    )
    session.add(search_session)
    await session.flush()

    paper = CachedPaper(
        session_id=search_session.id,
        title=title,
        authors=["Nguyen Van An"],
        abstract=abstract,
        doi=doi or f"10.1000/{uuid.uuid4().hex[:8]}",
        source="semantic_scholar",
        year=year,
        relevance_score=relevance_score,
    )
    session.add(paper)
    await session.commit()
    await session.refresh(paper)
    return paper


# ---------------------------------------------------------------------------
# 2. Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def db_setup():
    """Ensure the schema exists in the throwaway test database."""
    await ensure_schema()
    yield


@pytest_asyncio.fixture
async def db_session(db_setup):
    """Raw ``AsyncSession`` for direct DB assertions/seeding."""
    async with AsyncSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_setup):
    """HTTP client talking to the real ASGI app (no network socket needed)."""
    from main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client


@pytest_asyncio.fixture
async def test_user(db_setup) -> User:
    """Persisted user with enough credits for agent calls."""
    user, _project = await create_user_with_project()
    return user


@pytest.fixture
def token(test_user) -> str:
    """Signed access token for :func:`test_user`."""
    return create_access_token(str(test_user.id))


@pytest.fixture
def auth_headers(token) -> dict:
    """Authorization header built from :func:`token`."""
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def project(test_user) -> Project:
    """Persisted project owned by :func:`test_user`."""
    async with AsyncSessionLocal() as session:
        project = Project(
            user_id=test_user.id,
            topic="Week 3 - LangGraph pipeline",
            document_type="tieu_luan",
            citation_style="apa7",
            status="draft",
        )
        session.add(project)
        await session.commit()
        await session.refresh(project)
        return project