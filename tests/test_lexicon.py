"""The lexicon: the two packs, the tooltips and the themes."""

from __future__ import annotations

import re
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.i18n import PACKS, t, translate
from app.services import settings as settings_service

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "app/templates"

# A word of the interface is a run of at least two Persian letters; a
# single letter is the monogram of the app, and the digits are numbers.
PERSIAN_WORD = re.compile(r"[\u0621-\u064A\u066E-\u06D3]{2,}")


def test_the_two_packs_have_the_same_keys() -> None:
    """A key that is in one pack must be in the other one too."""
    plain = set(PACKS["plain"])
    medieval = set(PACKS["medieval"])
    assert plain == medieval
    assert len(plain) > 300


def test_every_key_is_used_somewhere() -> None:
    """A key that no template asks for is a key nobody reads."""
    templates = "\n".join(
        path.read_text(encoding="utf-8") for path in TEMPLATES.rglob("*.html")
    )
    asked = {
        key
        for key in re.findall(r"(?<![\w.])t\('([a-z0-9_.\-]+)'", templates)
        if not key.endswith(".")
    }
    unknown = asked - set(PACKS["plain"])
    assert not unknown, f"the templates ask for keys that do not exist: {sorted(unknown)}"


def test_no_persian_is_written_in_the_templates() -> None:
    """The words of the interface live in the packs, not in the templates."""
    offenders = []
    for path in sorted(TEMPLATES.rglob("*.html")):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if PERSIAN_WORD.search(line):
                offenders.append(f"{path.relative_to(ROOT)}:{number}: {line.strip()}")
    assert not offenders, "Persian text in the templates:\n" + "\n".join(offenders)


def test_the_plain_pack_stays_the_language_of_the_code() -> None:
    """The exports and the mail speak plainly, whatever the pack of the user."""
    assert t("nav.tasks") == "تسک‌ها"
    assert t("nav.overtime") == "اضافه‌کاری"


def test_a_medieval_term_remembers_its_plain_wording() -> None:
    """The tooltip of a term is the plain wording of the same key."""
    term = translate("nav.tasks", "medieval")
    assert term == "طومار مأموریت‌ها"
    assert term.plain == "تسک‌ها"


def test_the_page_shows_the_pack_of_the_user(
    client: TestClient, session: Session
) -> None:
    """The navigation follows the setting."""
    settings_service.set_setting(session, "lexicon", "medieval")
    session.commit()
    body = client.get("/").text
    assert "طومار مأموریت‌ها" in body
    assert 'title="تسک‌ها"' in body

    settings_service.set_setting(session, "lexicon", "plain")
    session.commit()
    body = client.get("/").text
    assert "تسک‌ها" in body
    assert "طومار مأموریت‌ها" not in body


def test_the_theme_of_the_user_is_the_theme_of_the_page(
    client: TestClient, session: Session
) -> None:
    """The setting chooses the theme; the system only decides the first time."""
    settings_service.set_setting(session, "theme", "parchment")
    session.commit()
    body = client.get("/").text
    assert 'data-theme="parchment"' in body
    assert 'data-theme-default="1"' not in body

    settings_service.set_setting(session, "theme", "night")
    session.commit()
    assert 'data-theme="night"' in client.get("/").text


def test_the_credits_page_names_every_source(client: TestClient) -> None:
    """The page of the credits lists the manifest of the icons."""
    body = client.get("/about/credits").text
    assert "Tabler Icons" in body
    assert "MIT" in body
