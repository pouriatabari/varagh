"""The frontend: the order of the scripts and the helpers of the page."""

from __future__ import annotations

import re
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.services import tasks as task_service
from app.utils.time import utcnow

ROOT = Path(__file__).resolve().parents[1]


def test_the_helpers_of_the_page_run_before_alpine() -> None:
    """Alpine starts in a microtask: the helpers must exist before it runs."""
    html = (ROOT / "app/templates/base.html").read_text(encoding="utf-8")
    assert html.index("app.js") < html.index("alpine.min.js")


def test_the_csrf_helper_is_reachable_from_the_page() -> None:
    """The delete buttons call the token helper of the page."""
    source = (ROOT / "app/static/js/app.js").read_text(encoding="utf-8")
    assert "window.csrfToken = csrfToken;" in source


def test_the_navigation_carries_the_isometric_icons(client: TestClient) -> None:
    """Every entry of the navigation shows an icon of its own."""
    source = (ROOT / "app/templates/base.html").read_text(encoding="utf-8")
    for name in (
        "dashboard",
        "tasks",
        "calendar",
        "clock",
        "book",
        "trophy",
        "report",
        "settings",
    ):
        assert f"iso_icon('{name}'" in source


def test_the_icons_are_markup_and_not_text(client: TestClient) -> None:
    """An icon is drawn as a picture, not shown as its own source."""
    response = client.get("/")
    assert response.status_code == 200
    assert "<svg" in response.text
    assert "&lt;svg" not in response.text


def test_every_icon_file_is_valid_svg() -> None:
    """The icon files are well-formed SVG."""
    import xml.etree.ElementTree as ET

    directory = ROOT / "app/static/icons"
    files = sorted(directory.glob("*.svg"))
    assert files
    for path in files:
        root = ET.fromstring(path.read_text(encoding="utf-8"))
        assert root.tag.endswith("svg")
        assert list(root)


def test_the_selection_attribute_stays_parsable(client: TestClient, session: Session) -> None:
    """The ids of the list go into the attribute without breaking it."""
    task_service.create_task(session, title="تسک", now=utcnow())
    session.flush()
    response = client.get("/tasks")
    assert response.status_code == 200
    attributes = re.findall(r'x-data="varaghSelection\(([^)]*)\)"', response.text)
    assert attributes
    for attribute in attributes:
        assert re.fullmatch(r"\[[0-9, ]*\]", attribute)
