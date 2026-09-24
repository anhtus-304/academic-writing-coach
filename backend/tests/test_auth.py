"""Week-3 integration tests - authentication (``/api/v1/auth/*``).

Covers the Google-OAuth/JWT contract that every other endpoint depends on:
token issuance (dev-login convenience flow), bearer + HttpOnly-cookie auth,
invalid/missing tokens and logout.
"""
from tests.conftest import unique_email


async def test_dev_login_issues_token_and_cookie(client):
    email = unique_email("auth")
    res = await client.post(
        "/api/v1/auth/dev-login",
        json={"email": email, "name": "Auth Tester"},
    )
    assert res.status_code == 200, res.text

    payload = res.json()
    assert payload["token_type"] == "bearer"
    assert payload["access_token"]
    assert payload["user"]["email"] == email
    assert payload["user"]["credits"] > 0
    assert "access_token" in res.cookies

    token = payload["access_token"]

    # 1. Bearer header auth (Postman/Swagger/tests)
    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == email

    # 2. HttpOnly cookie auth (browser flow)
    me_cookie = await client.get("/api/v1/auth/me", cookies={"access_token": token})
    assert me_cookie.status_code == 200
    assert me_cookie.json()["email"] == email


async def test_dev_login_reuses_existing_user(client):
    email = unique_email("auth-idem")
    first = await client.post("/api/v1/auth/dev-login", json={"email": email, "name": "First"})
    second = await client.post("/api/v1/auth/dev-login", json={"email": email, "name": "Second"})

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["user"]["id"] == second.json()["user"]["id"]
    assert second.json()["user"]["name"] == "Second"


async def test_me_requires_token(client):
    res = await client.get("/api/v1/auth/me")
    assert res.status_code == 401


async def test_me_rejects_malformed_token(client):
    res = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-real-jwt"})
    assert res.status_code == 401
    assert res.json()["detail"] == "Could not validate credentials"


async def test_token_of_deleted_user_is_rejected(client, db_session):
    from models.user import User
    from security import create_access_token

    user = User(email=unique_email("ghost"), display_name="Ghost", credit_balance=0)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    token = create_access_token(str(user.id))
    await db_session.delete(user)
    await db_session.commit()

    res = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 401


async def test_logout_clears_access_token_cookie(client, auth_headers):
    # Log in so the client holds a cookie, then log out and verify deletion.
    login = await client.post("/api/v1/auth/dev-login", json={"email": unique_email("logout")})
    assert login.status_code == 200
    assert "access_token" in client.cookies

    res = await client.post("/api/v1/auth/logout")
    assert res.status_code == 200
    assert "access_token=" in res.headers.get("set-cookie", "")