import os
import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./_test_selected.db")
os.environ.setdefault("LITERATURE_MODE", "mock")

from backend.database import Base, AsyncSessionLocal, engine
from backend.main import app


from backend.models.user import User
from backend.models.project import Project
from backend.models.cached_paper import CachedPaper
from backend.models.search_session import SearchSession
from backend.security import create_access_token


@pytest.fixture(scope="module", autouse=True)
def prepare_db():
    if os.path.exists("_test_selected.db"):
        os.remove("_test_selected.db")


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def auth_setup(client):
    async def _seed():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with AsyncSessionLocal() as db:
            user = User(email="author@example.com", display_name="Author", credit_balance=10)
            db.add(user)
            await db.flush()
            project = Project(user_id=user.id, title="Thesis on NLP", topic="AI NLP", citation_style="apa7", status="draft")
            db.add(project)
            await db.commit()
            await db.refresh(user)
            await db.refresh(project)
            return user, project

    import asyncio
    user, project = asyncio.run(_seed())
    token = create_access_token(str(user.id))
    return {
        "headers": {"Authorization": f"Bearer {token}"},
        "project_id": str(project.id),
        "user_id": str(user.id),
    }


def test_select_paper_and_retrieve(client, auth_setup):
    headers = auth_setup["headers"]
    project_id = auth_setup["project_id"]

    # 1. Select a new paper directly
    paper_payload = {
        "paper": {
            "title": "Machine Learning in Academic Writing",
            "authors": ["Nguyen Van A", "Tran Thi B"],
            "year": 2023,
            "publicationType": "IEEE Transactions",
            "doi": "10.1109/MLA.2023.123",
            "url": "https://example.com/mla",
            "abstract": "A comprehensive study on ML writing assistants.",
        },
        "notes": "Quan trọng cho chương 2",
    }
    r = client.post(f"/api/v1/projects/{project_id}/literature/select", headers=headers, json=paper_payload)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["project_id"] == project_id
    assert data["paper"]["title"] == "Machine Learning in Academic Writing"
    assert "Nguyen" in data["citation_formatted"]
    selected_id = data["id"]

    # 2. Get all selected papers
    r_list = client.get(f"/api/v1/projects/{project_id}/literature/selected", headers=headers)
    assert r_list.status_code == 200
    list_data = r_list.json()
    assert list_data["total"] == 1
    assert list_data["selected_papers"][0]["id"] == selected_id

    # 3. Delete selected paper
    r_del = client.delete(f"/api/v1/projects/{project_id}/literature/selected/{selected_id}", headers=headers)
    assert r_del.status_code == 200

    # 4. Verify empty list
    r_list2 = client.get(f"/api/v1/projects/{project_id}/literature/selected", headers=headers)
    assert r_list2.status_code == 200
    assert r_list2.json()["total"] == 0


def test_citation_check_deducts_credit(client, auth_setup):
    headers = auth_setup["headers"]
    project_id = auth_setup["project_id"]

    # Initial balance check
    r_bal = client.get("/api/v1/credits/balance", headers=headers)
    init_balance = r_bal.json()["balance"]

    # Content with an uncited claim: "chiếm 85% tổng số sinh viên"
    draft_content = "<p>Nghiên cứu của chúng tôi cho thấy việc áp dụng AI chiếm 85% tổng số sinh viên tham gia khảo sát.</p>"
    r_check = client.post(
        f"/api/v1/projects/{project_id}/citation/check",
        headers=headers,
        json={"content": draft_content, "citation_style": "apa7"}
    )
    assert r_check.status_code == 200, r_check.text
    res_data = r_check.json()
    assert res_data["credits_charged"] == 2
    assert res_data["total_issues"] >= 1
    assert len(res_data["missing_claims"]) >= 1

    # Verify balance reduced by 2
    r_bal2 = client.get("/api/v1/credits/balance", headers=headers)
    assert r_bal2.json()["balance"] == init_balance - 2
