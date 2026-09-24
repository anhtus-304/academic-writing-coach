"""Cross-cutting HTTP middleware for the Academic Writing Coach backend.

This module centralises two concerns that used to live (partially) inside
``main.py``:

1. **CORS** - allow the Next.js frontend (``localhost:3000`` by default plus the
   Vercel deploys ``https://*.vercel.app``) to call the API with credentials/cookies.
2. **Rate limiting** - a dependency-free, in-memory sliding-window limiter that
   protects LLM-backed endpoints (agents, literature, citation) from abuse.
   Requests are keyed by bearer token (hashed) when present, otherwise by the
   client IP address. No Redis is required for development; the limiter is
   intentionally isolated behind :class:`RateLimitMiddleware` so it can be
   swapped for a Redis/``slowapi`` backend later without touching the routes.

Usage (see ``main.py``)::

    from api.middleware import setup_cors, setup_rate_limiting

    setup_rate_limiting(app)   # inner middleware
    setup_cors(app)            # outermost middleware (adds headers to 429 too)
"""
import hashlib
import logging
import time
from collections import deque
from threading import Lock
from typing import Deque, Dict, Iterable, Optional, Sequence

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# Sensible defaults when ``BACKEND_CORS_ORIGINS`` is empty/unset.
DEFAULT_ALLOWED_ORIGINS: Sequence[str] = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
)

# Deploy origins (Vercel production + preview, e.g. https://academic-writing-coach.vercel.app)
# are matched through ``allow_origin_regex`` so no env change is needed per preview URL.
DEFAULT_ORIGIN_REGEX = r"https://([a-z0-9-]+\.)*vercel\.app"

# Paths that must never be throttled (health checks, docs, preflight helpers).
DEFAULT_EXEMPT_PATHS: Sequence[str] = (
    "/api/v1/health",
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/favicon.ico",
)


def _load_settings():
    """Import the settings singleton supporting both import styles."""
    try:
        from backend.config import settings
    except ImportError:  # pragma: no cover - depends on how the app is launched
        from config import settings
    return settings


def setup_cors(
    app: FastAPI,
    origins: Optional[Iterable[str]] = None,
    origin_regex: Optional[str] = None,
) -> None:
    """Register the CORS middleware, allowing the frontend origins.

    ``origins`` defaults to ``settings.BACKEND_CORS_ORIGINS`` (or localhost
    fallbacks) and ``origin_regex`` to ``settings.BACKEND_CORS_ORIGIN_REGEX``
    (``https://*.vercel.app`` by default, covering production + preview deploys).
    Must be the *last* middleware added so that it is the outermost layer: CORS
    headers are then attached even to 429 responses produced by the rate limiter.
    """
    try:
        settings = _load_settings()
    except Exception:  # pragma: no cover - defensive: config must be valid anyway
        settings = None

    if origins is None:
        origins = getattr(settings, "BACKEND_CORS_ORIGINS", None) or DEFAULT_ALLOWED_ORIGINS
    if origin_regex is None:
        origin_regex = getattr(settings, "BACKEND_CORS_ORIGIN_REGEX", None) or DEFAULT_ORIGIN_REGEX

    allow_origins = [str(o).rstrip("/") for o in origins if o]
    if not allow_origins:
        allow_origins = list(DEFAULT_ALLOWED_ORIGINS)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_origin_regex=origin_regex or None,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "Retry-After"],
    )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """In-memory sliding-window rate limiter.

    * Keyed by the SHA-256 digest of the bearer token when present (so a shared
      IP/NAT does not throttle unrelated students), otherwise by client IP.
    * ``OPTIONS`` preflight requests and configured exempt paths are never
      throttled.
    * Responds with ``429 Too Many Requests`` plus ``Retry-After`` and
      ``X-RateLimit-*`` headers when the window is exceeded.
    """

    def __init__(
        self,
        app,
        requests_per_window: int = 120,
        window_seconds: int = 60,
        enabled: bool = True,
        exempt_paths: Optional[Iterable[str]] = None,
        header_name: str = "X-RateLimit-Remaining",
    ) -> None:
        super().__init__(app)
        self.requests_per_window = max(int(requests_per_window), 1)
        self.window_seconds = max(float(window_seconds), 1.0)
        self.enabled = bool(enabled)
        self.exempt_paths = (
            tuple(exempt_paths) if exempt_paths is not None else DEFAULT_EXEMPT_PATHS
        )
        self.header_name = header_name
        self._hits: Dict[str, Deque[float]] = {}
        self._lock = Lock()
        self._last_cleanup = time.monotonic()

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _identity(request: Request) -> str:
        """Build the throttling key: hashed bearer token, else client IP."""
        auth_header = request.headers.get("authorization") or ""
        if auth_header.lower().startswith("bearer "):
            raw_token = auth_header[7:].strip()
            if raw_token:
                digest = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()[:16]
                return f"token:{digest}"

        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return f"ip:{forwarded.split(',')[0].strip()}"
        client = request.client
        return f"ip:{client.host if client else 'unknown'}"

    def _is_exempt(self, path: str) -> bool:
        return any(
            path == exempt or path.startswith(exempt + "/") for exempt in self.exempt_paths
        )

    def _prune(self, key: str, now: float) -> Deque[float]:
        bucket = self._hits.setdefault(key, deque())
        threshold = now - self.window_seconds
        while bucket and bucket[0] <= threshold:
            bucket.popleft()
        return bucket

    def _cleanup_stale_keys(self, now: float) -> None:
        """Drop empty buckets periodically to keep memory bounded."""
        if now - self._last_cleanup < self.window_seconds:
            return
        self._last_cleanup = now
        stale = [
            key
            for key, bucket in self._hits.items()
            if not bucket or bucket[-1] <= now - self.window_seconds
        ]
        for key in stale:
            self._hits.pop(key, None)

    # ----------------------------------------------------------------- dispatch
    async def dispatch(self, request: Request, call_next):
        if (
            not self.enabled
            or request.method == "OPTIONS"
            or self._is_exempt(request.url.path)
        ):
            return await call_next(request)

        key = self._identity(request)
        now = time.monotonic()

        with self._lock:
            bucket = self._prune(key, now)
            exceeded = len(bucket) >= self.requests_per_window
            if not exceeded:
                bucket.append(now)
            remaining = max(self.requests_per_window - len(bucket), 0)
            retry_after = (
                int(self.window_seconds - (now - bucket[0])) + 1
                if bucket
                else int(self.window_seconds)
            )
            self._cleanup_stale_keys(now)

        if exceeded:
            logger.warning("[RateLimit] 429 for %s on %s", key, request.url.path)
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": (
                        "Bạn đã gửi quá nhiều yêu cầu. Vui lòng thử lại sau "
                        f"{max(retry_after, 1)} giây."
                    ),
                    "limit": self.requests_per_window,
                    "window_seconds": int(self.window_seconds),
                    "retry_after": max(retry_after, 1),
                },
                headers={
                    "Retry-After": str(max(retry_after, 1)),
                    "X-RateLimit-Limit": str(self.requests_per_window),
                    "X-RateLimit-Remaining": "0",
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_window)
        response.headers[self.header_name] = str(remaining)
        return response


def setup_rate_limiting(app: FastAPI) -> None:
    """Attach :class:`RateLimitMiddleware` using the application settings."""
    try:
        settings = _load_settings()
        enabled = settings.RATE_LIMIT_ENABLED
        limit = settings.RATE_LIMIT_REQUESTS
        window = settings.RATE_LIMIT_WINDOW_SECONDS
        exempt_paths = settings.RATE_LIMIT_EXEMPT_PATHS or DEFAULT_EXEMPT_PATHS
    except Exception:  # pragma: no cover - defensive
        enabled, limit, window, exempt_paths = True, 120, 60, DEFAULT_EXEMPT_PATHS

    app.add_middleware(
        RateLimitMiddleware,
        requests_per_window=limit,
        window_seconds=window,
        enabled=enabled,
        exempt_paths=exempt_paths,
    )

