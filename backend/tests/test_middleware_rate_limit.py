"""Week-3 tests - CORS + rate-limiting middleware (``api/middleware.py``)."""
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api.middleware import RateLimitMiddleware, setup_cors


def _build_app(
    limit: int = 3,
    window: int = 60,
    enabled: bool = True,
    exempt_paths=("/health",),
) -> FastAPI:
    app = FastAPI()

    @app.get("/ping")
    async def ping():
        return {"ok": True}

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    app.add_middleware(
        RateLimitMiddleware,
        requests_per_window=limit,
        window_seconds=window,
        enabled=enabled,
        exempt_paths=exempt_paths,
    )
    setup_cors(app, origins=["http://localhost:3000"])
    return app


def _client(app: FastAPI) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_rate_limit_blocks_after_quota():
    app = _build_app(limit=3)
    async with _client(app) as client:
        for _ in range(3):
            res = await client.get("/ping")
            assert res.status_code == 200
            assert res.headers["X-RateLimit-Limit"] == "3"
            assert int(res.headers["X-RateLimit-Remaining"]) >= 0

        blocked = await client.get("/ping")
        assert blocked.status_code == 429
        assert int(blocked.headers["Retry-After"]) >= 1

        body = blocked.json()
        assert body["limit"] == 3
        assert body["window_seconds"] == 60
        assert body["retry_after"] >= 1
        assert "detail" in body


async def test_exempt_paths_and_preflight_are_not_counted():
    app = _build_app(limit=1)
    async with _client(app) as client:
        for _ in range(5):
            assert (await client.get("/health")).status_code == 200

        for _ in range(3):
            preflight = await client.options(
                "/ping",
                headers={
                    "Origin": "http://localhost:3000",
                    "Access-Control-Request-Method": "GET",
                },
            )
            assert preflight.status_code == 200

        assert (await client.get("/ping")).status_code == 200
        assert (await client.get("/ping")).status_code == 429


async def test_limit_is_per_bearer_token():
    app = _build_app(limit=1)
    async with _client(app) as client:
        user_a = {"Authorization": "Bearer token-a"}
        user_b = {"Authorization": "Bearer token-b"}

        assert (await client.get("/ping", headers=user_a)).status_code == 200
        assert (await client.get("/ping", headers=user_a)).status_code == 429
        # A different student must not be throttled by someone else's traffic.
        assert (await client.get("/ping", headers=user_b)).status_code == 200


async def test_cors_headers_present_on_throttled_response():
    app = _build_app(limit=1)
    headers = {"Authorization": "Bearer cors-token", "Origin": "http://localhost:3000"}
    async with _client(app) as client:
        assert (await client.get("/ping", headers=headers)).status_code == 200
        blocked = await client.get("/ping", headers=headers)

        assert blocked.status_code == 429
        assert blocked.headers.get("access-control-allow-origin") == "http://localhost:3000"
        assert "access-control-allow-credentials" in blocked.headers


def test_default_rate_limit_is_60_requests_per_minute():
    """Week-3 requirement: max 60 req/phút (429 khi vượt)."""
    from config import Settings

    assert Settings.model_fields["RATE_LIMIT_REQUESTS"].default == 60
    assert Settings.model_fields["RATE_LIMIT_WINDOW_SECONDS"].default == 60


async def test_cors_allows_vercel_deploy_origins():
    """Vercel (production + preview) domains are accepted via allow_origin_regex."""
    app = _build_app(limit=5)
    async with _client(app) as client:
        for origin in (
            "http://localhost:3000",
            "https://academic-writing-coach.vercel.app",
            "https://academic-writing-coach-git-feature-anhtus.vercel.app",
        ):
            res = await client.get("/ping", headers={"Origin": origin})
            assert res.status_code == 200
            assert res.headers.get("access-control-allow-origin") == origin

        # An unrelated origin must not be echoed back.
        res = await client.get("/ping", headers={"Origin": "https://evil.example.com"})
        assert res.headers.get("access-control-allow-origin") is None


async def test_disabled_limiter_never_blocks():
    app = _build_app(limit=1, enabled=False)
    async with _client(app) as client:
        for _ in range(5):
            assert (await client.get("/ping")).status_code == 200


async def test_identity_helpers_cover_ip_and_forwarded_cases():
    """``_identity`` must degrade to IP-based keys (e.g. anonymous traffic)."""
    from starlette.requests import Request

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/ping",
        "headers": [(b"x-forwarded-for", b"10.1.2.3, 10.9.9.9")],
        "client": ("127.0.0.1", 1234),
    }
    request = Request(scope)
    assert RateLimitMiddleware._identity(request) == "ip:10.1.2.3"

    scope["headers"] = [(b"authorization", b"Bearer abc.def.ghi")]
    request = Request(scope)
    assert RateLimitMiddleware._identity(request).startswith("token:")