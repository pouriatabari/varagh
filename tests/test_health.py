"""Smoke tests for the application shell."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_healthz_is_ok(client: TestClient) -> None:
    """The Docker healthcheck endpoint answers."""
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_dashboard_renders_rtl_persian(client: TestClient) -> None:
    """The dashboard is served as a Persian RTL document."""
    response = client.get("/")
    assert response.status_code == 200
    body = response.text
    assert '<html lang="fa" dir="rtl"' in body
    assert "ورق" in body


def test_static_assets_are_vendored(client: TestClient) -> None:
    """No CDN is used: fonts and JS are served from the app itself."""
    for path in (
        "/static/css/app.css",
        "/static/vendor/htmx.min.js",
        "/static/vendor/alpine.min.js",
        "/static/vendor/chart.umd.min.js",
        "/static/fonts/Vazirmatn-Regular.woff2",
        "/static/manifest.webmanifest",
    ):
        response = client.get(path)
        assert response.status_code == 200, path
