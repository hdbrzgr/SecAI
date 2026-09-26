# SecAI — Copyright (C) 2026 hdbrzgr. Licensed under AGPL-3.0 with an attribution term; see NOTICE.
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from urllib.parse import urlsplit

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from redis.asyncio import Redis

from app.api.routes import account, admin, auth, health, scans, targets
from app.core.config import get_settings

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def _origin_of(url: str) -> str | None:
    parts = urlsplit(url)
    if not parts.scheme or not parts.netloc:
        return None
    return f"{parts.scheme}://{parts.netloc}"


def create_app() -> FastAPI:
    settings = get_settings()
    is_prod = settings.env == "production"

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if not hasattr(app.state, "redis"):
            app.state.redis = Redis.from_url(settings.redis_url, decode_responses=True)
        if not hasattr(app.state, "arq"):
            app.state.arq = await create_pool(RedisSettings.from_dsn(settings.redis_url))
        yield
        await app.state.redis.aclose()
        await app.state.arq.aclose()

    app = FastAPI(
        title="SecAI API",
        version="0.1.0",
        lifespan=lifespan,
        # Don't advertise the full API surface on production instances.
        docs_url=None if is_prod else "/docs",
        redoc_url=None,
        openapi_url=None if is_prod else "/openapi.json",
    )

    allowed_origin = _origin_of(settings.web_origin)

    @app.middleware("http")
    async def csrf_origin_check(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # Cookie-authenticated API: every state-changing request must come from the web app's
        # origin. Combined with SameSite=Lax cookies this blocks cross-site request forgery.
        if request.method not in SAFE_METHODS:
            origin = request.headers.get("origin")
            if origin is None and (referer := request.headers.get("referer")):
                origin = _origin_of(referer)
            if origin != allowed_origin:
                return JSONResponse({"detail": "Cross-origin request blocked"}, status_code=403)
        return await call_next(request)

    @app.middleware("http")
    async def security_headers(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        h = response.headers
        h.setdefault("X-Content-Type-Options", "nosniff")
        h.setdefault("X-Frame-Options", "DENY")
        h.setdefault("Referrer-Policy", "no-referrer")
        h.setdefault("Cache-Control", "no-store")
        h.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        if settings.cookie_secure:
            h.setdefault("Strict-Transport-Security", "max-age=63072000; includeSubDomains")
        return response

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(account.router)
    app.include_router(targets.router)
    app.include_router(scans.router)
    app.include_router(admin.router)
    return app


app = create_app()
