import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock
try:
    from backend.main import app
    from backend.database import get_db
    from backend.schemas.outline_schemas import AcademicOutline, OutlineSection, OutlineSubSection
    from backend.agents.outline_agent import outline_agent
except ImportError:
    from main import app
    from database import get_db
    from schemas.outline_schemas import AcademicOutline, OutlineSection, OutlineSubSection
    from agents.outline_agent import outline_agent


@pytest.fixture
def mock_outline():
    return AcademicOutline(
        topic="Nghiên cứu ứng dụng Blockchain trong Nông nghiệp",
        document_type="tieu_luan",
        field="Công nghệ Thông tin",
        language="vi",
        total_estimated_pages="15 trang",
        sections=[
            OutlineSection(
                section_code="INTRO",
                title="MỞ ĐẦU",
                description="Tổng quan và tính cấp thiết",
                subsections=[
                    OutlineSubSection(
                        title="1. Đặt vấn đề",
                        description="Bối cảnh nông nghiệp số",
                        estimated_word_count=400,
                        key_points=["Nhu cầu truy xuất nguồn gốc"]
                    )
                ]
            ),
            OutlineSection(
                section_code="CH1",
                title="CHƯƠNG 1: TỔNG QUAN VỀ CÔNG NGHỆ BLOCKCHAIN",
                description="Lý thuyết cơ bản",
                subsections=[
                    OutlineSubSection(
                        title="1.1. Khái niệm Blockchain",
                        description="Định nghĩa và nguyên lý",
                        estimated_word_count=1000,
                        key_points=["Cấu trúc block", "Cơ chế đồng thuận"]
                    )
                ]
            )
        ],
        research_methodology_suggestion="Phương pháp phân tích tổng hợp tài liệu.",
        key_academic_keywords=["Blockchain", "Smart Contract", "Truy xuất nguồn gốc"],
        writing_guidelines="Trình bày mạch lạc, có hình ảnh minh họa."
    )

class MockDBSession:
    def __init__(self, users_store, projects_store, outlines_store):
        self.users = users_store
        self.projects = projects_store
        self.outlines = outlines_store

    async def execute(self, statement):
        mock_result = MagicMock()
        try:
            stmt_str = str(statement)
        except Exception:
            stmt_str = repr(statement)
        stmt_lower = stmt_str.lower()
        if "from users" in stmt_lower or "users." in stmt_lower or "users " in stmt_lower:
            user_list = list(self.users.values())
            mock_result.scalar_one_or_none = MagicMock(return_value=user_list[0] if user_list else None)
            mock_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=user_list)))
        elif "from projects" in stmt_lower or "projects." in stmt_lower or "projects " in stmt_lower:
            proj_list = list(self.projects.values())
            mock_result.scalar_one_or_none = MagicMock(return_value=proj_list[0] if proj_list else None)
            mock_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=proj_list)))
        elif "from outlines" in stmt_lower or "outlines." in stmt_lower or "outlines " in stmt_lower:
            out_list = list(self.outlines.values())
            mock_result.scalar_one_or_none = MagicMock(return_value=out_list[0] if out_list else None)
            mock_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=out_list)))

        else:
            mock_result.scalar_one_or_none = MagicMock(return_value=None)
            mock_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        return mock_result

    def add(self, obj):
        if hasattr(obj, "__tablename__"):
            if obj.__tablename__ == "users":
                self.users[obj.id] = obj
            elif obj.__tablename__ == "projects":
                self.projects[obj.id] = obj
            elif obj.__tablename__ == "outlines":
                self.outlines[obj.id] = obj

    async def commit(self):
        pass

    async def refresh(self, obj):
        pass

    async def delete(self, obj):
        if hasattr(obj, "__tablename__"):
            if obj.__tablename__ == "projects" and obj.id in self.projects:
                del self.projects[obj.id]

@pytest.mark.asyncio
async def test_auth_and_project_lifecycle(mock_outline, monkeypatch):
    # Mock LLM generation in OutlineAgent class
    try:
        from backend.agents.outline_agent import OutlineAgent
        monkeypatch.setattr(OutlineAgent, "generate_outline", AsyncMock(return_value=mock_outline))
    except ImportError:
        from agents.outline_agent import OutlineAgent
        monkeypatch.setattr(OutlineAgent, "generate_outline", AsyncMock(return_value=mock_outline))



    users_store = {}
    projects_store = {}
    outlines_store = {}

    async def override_get_db():
        yield MockDBSession(users_store, projects_store, outlines_store)

    try:
        from backend.database import get_db as backend_get_db
        app.dependency_overrides[backend_get_db] = override_get_db
    except ImportError:
        pass
    from database import get_db as bare_get_db
    app.dependency_overrides[bare_get_db] = override_get_db


    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Test Dev Login
        login_res = await client.post("/api/v1/auth/dev-login", json={"email": "testuser@edu.vn", "name": "Nguyễn Văn Test"})
        assert login_res.status_code == 200
        auth_data = login_res.json()
        assert "access_token" in auth_data
        token = auth_data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Test Get Me
        me_res = await client.get("/api/v1/auth/me", headers=headers)
        assert me_res.status_code == 200
        assert me_res.json()["email"] == "testuser@edu.vn"

        # 3. Test Create Project
        project_payload = {
            "topic": "Nghiên cứu ứng dụng Blockchain trong Nông nghiệp",
            "document_type": "tieu_luan",
            "field": "Công nghệ Thông tin",
            "university": "Đại học Bách Khoa",
            "citation_style": "apa7",
            "additional_requirements": "Cần tập trung vào chuỗi cung ứng"
        }
        create_res = await client.post("/api/v1/projects/", json=project_payload, headers=headers)
        assert create_res.status_code == 201
        project = create_res.json()
        assert project["topic"] == project_payload["topic"]
        project_id = project["id"]

        # 4. Test List Projects
        list_res = await client.get("/api/v1/projects/", headers=headers)
        assert list_res.status_code == 200
        projects = list_res.json()
        assert any(p["id"] == project_id for p in projects)

        # 5. Test Generate Outline
        gen_res = await client.post(f"/api/v1/projects/{project_id}/outline/generate", json={}, headers=headers)
        assert gen_res.status_code == 200
        outline_data = gen_res.json()
        assert outline_data["success"] is True
        assert outline_data["outline"]["title"] == mock_outline.topic

        # 6. Test Get Outline
        get_outline_res = await client.get(f"/api/v1/projects/{project_id}/outline", headers=headers)
        assert get_outline_res.status_code == 200
        fetched_outline = get_outline_res.json()
        assert fetched_outline["success"] is True
        assert fetched_outline["outline"]["id"] == outline_data["outline"]["id"]

        # 7. Test Update Outline
        updated_chapters = {"sections": [{"title": "Chương mới chỉnh sửa"}]}
        update_res = await client.put(
            f"/api/v1/projects/{project_id}/outline",
            json={"chapters": updated_chapters},
            headers=headers
        )
        assert update_res.status_code == 200
        assert update_res.json()["outline"]["chapters"] == updated_chapters

    app.dependency_overrides.clear()
