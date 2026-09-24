"""Week-3 integration tests - projects CRUD + ownership isolation."""
from tests.conftest import create_user_with_project, unique_email


async def test_project_crud_lifecycle(client, auth_headers, project):
    project_id = str(project.id)

    # READ (single)
    res = await client.get(f"/api/v1/projects/{project_id}", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["id"] == project_id

    # READ (list) - the composite index ix_projects_user_id_status backs this query
    listed = await client.get("/api/v1/projects/", headers=auth_headers)
    assert listed.status_code == 200
    assert any(item["id"] == project_id for item in listed.json())

    # UPDATE
    updated = await client.put(
        f"/api/v1/projects/{project_id}",
        headers=auth_headers,
        json={"topic": "Week 3 - updated topic", "status": "in_progress", "citation_style": "ieee"},
    )
    assert updated.status_code == 200
    body = updated.json()
    assert body["topic"] == "Week 3 - updated topic"
    assert body["status"] == "in_progress"
    assert body["citation_style"] == "ieee"

    # DELETE
    deleted = await client.delete(f"/api/v1/projects/{project_id}", headers=auth_headers)
    assert deleted.status_code == 204

    gone = await client.get(f"/api/v1/projects/{project_id}", headers=auth_headers)
    assert gone.status_code == 404


async def test_create_project_returns_201(client, auth_headers):
    res = await client.post(
        "/api/v1/projects/",
        headers=auth_headers,
        json={
            "topic": "Citation Agent evaluation",
            "document_type": "khoa_luan",
            "field": "Computer Science",
            "university": "HCMUT",
            "citation_style": "bgddt",
            "additional_requirements": "Focus on 2020+ sources",
        },
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["topic"] == "Citation Agent evaluation"
    assert body["status"] == "draft"
    assert body["citation_style"] == "bgddt"


async def test_create_project_requires_topic(client, auth_headers):
    res = await client.post("/api/v1/projects/", headers=auth_headers, json={"field": "CS"})
    assert res.status_code == 422


async def test_project_endpoints_require_auth(client):
    assert (await client.get("/api/v1/projects/")).status_code == 401
    assert (await client.post("/api/v1/projects/", json={"topic": "x"})).status_code == 401


async def test_cannot_read_foreign_project(client):
    owner_a, project_a = await create_user_with_project()
    _owner_b, project_b = await create_user_with_project()

    from security import create_access_token

    headers_b = {"Authorization": f"Bearer {create_access_token(str(project_b.user_id))}"}

    # User B may read their own project...
    assert (await client.get(f"/api/v1/projects/{project_b.id}", headers=headers_b)).status_code == 200
    # ...but never user A's project (404, not 403, to avoid leaking ids).
    assert (await client.get(f"/api/v1/projects/{project_a.id}", headers=headers_b)).status_code == 404
    assert (await client.delete(f"/api/v1/projects/{project_a.id}", headers=headers_b)).status_code == 404


async def test_unknown_project_returns_404(client, auth_headers):
    import uuid

    res = await client.get(f"/api/v1/projects/{uuid.uuid4()}", headers=auth_headers)
    assert res.status_code == 404


async def test_project_list_pagination(client, auth_headers):
    for index in range(3):
        await client.post(
            "/api/v1/projects/",
            headers=auth_headers,
            json={"topic": f"Pagination probe {index}", "document_type": "tieu_luan"},
        )

    res = await client.get("/api/v1/projects/?skip=0&limit=2", headers=auth_headers)
    assert res.status_code == 200
    assert len(res.json()) == 2
    assert unique_email()  # sanity: helper import is exercised


async def test_health_endpoint_is_public(client):
    res = await client.get("/api/v1/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}