"""Security helpers: CSRF protection and optional HTTP Basic auth."""

from __future__ import annotations

import hmac
import secrets
from collections.abc import Awaitable, Callable

from fastapi import HTTPException, Request, Response, status
from starlette.responses import JSONResponse

from app.config import get_settings

CSRF_COOKIE = "varagh_csrf"
CSRF_HEADER = "x-csrf-token"
CSRF_FIELD = "csrf_token"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}


def new_csrf_token() -> str:
    """Return a fresh CSRF token."""
    return secrets.token_urlsafe(32)


def get_csrf_token(request: Request) -> str:
    """Return the CSRF token of the request, creating one if needed."""
    token = request.cookies.get(CSRF_COOKIE)
    if not token:
        token = new_csrf_token()
    request.state.csrf_token = token
    return token


async def validate_csrf(request: Request) -> None:
    """Validate the CSRF token of an unsafe request (double-submit cookie)."""
    if request.method in SAFE_METHODS:
        return
    expected = request.cookies.get(CSRF_COOKIE)
    provided = request.headers.get(CSRF_HEADER)
    if not provided:
        form = await request.form()
        provided = str(form.get(CSRF_FIELD) or "")
    if not expected or not provided or not hmac.compare_digest(expected, provided):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="csrf_invalid")


async def basic_auth_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Reject requests when HTTP Basic auth is enabled and the credentials are wrong."""
    settings = get_settings()
    if settings.basic_auth_enabled and request.url.path not in {"/healthz"}:
        import base64

        header = request.headers.get("authorization", "")
        scheme, _, payload = header.partition(" ")
        if scheme.lower() != "basic":
            return JSONResponse(
                {"detail": "authentication_required"},
                status_code=status.HTTP_401_UNAUTHORIZED,
                headers={"WWW-Authenticate": 'Basic realm="Varagh"'},
            )
        try:
            decoded = base64.b64decode(payload).decode("utf-8")
            user, _, password = decoded.partition(":")
        except (ValueError, UnicodeDecodeError):
            user, password = "", ""
        expected_user = settings.basic_auth_user
        expected_password = settings.basic_auth_password
        if not (
            hmac.compare_digest(user, expected_user)
            and hmac.compare_digest(password, expected_password)
        ):
            return JSONResponse(
                {"detail": "invalid_credentials"},
                status_code=status.HTTP_401_UNAUTHORIZED,
                headers={"WWW-Authenticate": 'Basic realm="Varagh"'},
            )
    return await call_next(request)
