"""FastAPI application factory and wiring."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.security import CSRF_COOKIE, basic_auth_middleware

logger = logging.getLogger("varagh")

BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"


def create_app() -> FastAPI:
    """Build the FastAPI application."""
    settings = get_settings()
    logging.basicConfig(
        level=logging.DEBUG if settings.debug else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s %(message)s",
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        logger.info("varagh started (environment=%s)", settings.environment)
        yield
        logger.info("varagh stopped")

    app = FastAPI(
        title=settings.app_name,
        description="Personal Persian-first task and work journal.",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
    )

    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    app.middleware("http")(basic_auth_middleware)

    @app.middleware("http")
    async def csrf_cookie(request: Request, call_next):  # noqa: ANN001, ANN202
        response: Response = await call_next(request)
        token = getattr(request.state, "csrf_token", None) or request.cookies.get(CSRF_COOKIE)
        if token and request.cookies.get(CSRF_COOKIE) != token:
            response.set_cookie(
                CSRF_COOKIE,
                token,
                httponly=False,
                samesite="lax",
                max_age=60 * 60 * 24 * 30,
            )
        return response

    from app.api import (
        ai,
        board,
        insignia,
        learning,
        notifications,
        realms,
        reviews,
        tasks,
        timing,
        web,
    )
    from app.api import settings as settings_api

    app.include_router(web.router)
    app.include_router(tasks.router)
    app.include_router(timing.router)
    app.include_router(board.router)
    app.include_router(reviews.router)
    app.include_router(insignia.router)
    app.include_router(realms.router)
    app.include_router(learning.router)
    app.include_router(ai.router)
    app.include_router(notifications.router)
    app.include_router(settings_api.router)

    @app.get("/healthz", include_in_schema=False)
    async def healthz() -> JSONResponse:
        """Liveness probe used by Docker."""
        return JSONResponse({"status": "ok", "app": settings.app_name})

    @app.get("/sw.js", include_in_schema=False)
    async def service_worker() -> Response:
        """Serve the service worker from the root scope so the PWA can install."""
        path = STATIC_DIR / "sw.js"
        return Response(
            path.read_text(encoding="utf-8"),
            media_type="application/javascript",
            headers={"Service-Worker-Allowed": "/", "Cache-Control": "no-cache"},
        )

    return app


app = create_app()
