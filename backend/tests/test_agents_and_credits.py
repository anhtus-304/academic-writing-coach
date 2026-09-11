import pytest
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport
import sys

from main import app
from models.user import User
from models.project import Project
from schemas.outline_schemas import AcademicOutline, OutlineSection, OutlineSubSection

@pytest.fixture
def mock_outline_obj():
    return AcademicOutline(
        topic="Nghiên cứu ứng dụng Blockchain trong Nông nghiệp",
        document_type="tieu_luan",
        field="Công nghệ Thông tin",
        language="vi",
        total_estimated_pages="10 trang",
        sections=[
            OutlineSection(
                section_code="CH1",
                title="CHƯƠNG 1: TỔNG QUAN VỀ BLOCKCHAIN",
                description="Lý thuyết cơ bản",
                subsections=[
                    OutlineSubSection(
                        title="1.1. Khái niệm",
                        description="Định nghĩa",
                        estimated_word_count=500,
                        key_points=["Cấu trúc"]
                    )
                ]
            )
        ],
        research_methodology_suggestion="Phương pháp phân tích.",
        key_academic_keywords=["Blockchain"],
        writing_guidelines="Mạch lạc."
    )

class MockAgentsDBSession:
    def __init__(self, user):
        self.user = user
        self.objects = [user]

    async def execute(self, statement):
        mock_result = MagicMock()
        stmt_str = str(statement).lower()
        if "users" in stmt_str:
            mock_result.scalar_one_or_none = MagicMock(return_value=self.user)
            mock_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[self.user])))
        elif "projects" in stmt_str:
            proj = Project(
                id="test-proj-123",
                user_id=self.user.id,
                topic="Nghiên cứu ứng dụng Blockchain trong Nông nghiệp",
                document_type="tieu_luan",
                citation_style="apa7"
            )
            mock_result.scalar_one_or_none = MagicMock(return_value=proj)
            mock_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[proj])))
        else:
            mock_result.scalar_one_or_none = MagicMock(return_value=None)
            mock_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        return mock_result

    def add(self, obj):
        self.objects.append(obj)

    async def flush(self):
        pass

    async def commit(self):
        pass

    async def refresh(self, obj):
        pass

@pytest.mark.asyncio
async def test_agents_ask_success_and_credit_deduct(monkeypatch):
    test_user = User(id="usr-123", email="tester@edu.vn", credit_balance=50)

    from database import get_db
    async def override_db():
        yield MockAgentsDBSession(test_user)

    app.dependency_overrides[get_db] = override_db

    try:
        from backend.api.dependencies import get_current_user
        app.dependency_overrides[get_current_user] = lambda: test_user
    except ImportError:
        from api.dependencies import get_current_user
        app.dependency_overrides[get_current_user] = lambda: test_user

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            payload = {
                "selected_text": "Blockchain là một công nghệ sổ cái phân tán.",
                "action": "explain"
            }
            res = await client.post("/api/v1/agents/ask", json=payload)
            assert res.status_code == 200
            data = res.json()
            assert data["action"] == "explain"
            assert data["credits_charged"] == 1
            assert "response" in data
            assert test_user.credit_balance == 49
    finally:
        app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_agents_ask_insufficient_credits(monkeypatch):
    poor_user = User(id="poor-123", email="poor@edu.vn", credit_balance=0)

    from database import get_db
    async def override_db():
        yield MockAgentsDBSession(poor_user)

    app.dependency_overrides[get_db] = override_db

    try:
        from backend.api.dependencies import get_current_user
        app.dependency_overrides[get_current_user] = lambda: poor_user
    except ImportError:
        from api.dependencies import get_current_user
        app.dependency_overrides[get_current_user] = lambda: poor_user

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            payload = {
                "selected_text": "Blockchain là một công nghệ sổ cái phân tán.",
                "action": "academic_rewrite"
            }
            res = await client.post("/api/v1/agents/ask", json=payload)
            assert res.status_code == 402
            assert "Số dư không đủ" in res.json()["detail"]
    finally:
        app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_outline_generation_deducts_credits(mock_outline_obj, monkeypatch):
    user_with_credits = User(id="user-outline", email="outline@edu.vn", credit_balance=10)

    try:
        from backend.agents.outline_agent import OutlineAgent
        monkeypatch.setattr(OutlineAgent, "generate_outline", AsyncMock(return_value=mock_outline_obj))
    except ImportError:
        from agents.outline_agent import OutlineAgent
        monkeypatch.setattr(OutlineAgent, "generate_outline", AsyncMock(return_value=mock_outline_obj))

    from database import get_db
    async def override_db():
        yield MockAgentsDBSession(user_with_credits)

    app.dependency_overrides[get_db] = override_db

    try:
        from backend.api.dependencies import get_current_user
        app.dependency_overrides[get_current_user] = lambda: user_with_credits
    except ImportError:
        from api.dependencies import get_current_user
        app.dependency_overrides[get_current_user] = lambda: user_with_credits

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.post("/api/v1/projects/test-proj-123/outline/generate", json={})
            assert res.status_code == 200
            assert user_with_credits.credit_balance == 8

            user_with_credits.credit_balance = 1
            res_fail = await client.post("/api/v1/projects/test-proj-123/outline/generate", json={})
            assert res_fail.status_code == 402
    finally:
        app.dependency_overrides.clear()
