# Decisions

Every important design decision taken while building Varagh is recorded here
together with its rationale.

## D1 — One initial migration for the whole schema

- **Decision:** All first-version tables were created in a single `0001_initial`
  migration instead of one migration per model.
- **Why:** The schema was designed in a short window; splitting it into dozens of
  migrations only created overhead. From now on every schema change gets its own
  reversible migration.
- **Consequence:** `alembic downgrade base && alembic upgrade head` must always
  work (covered by an automated test).

## D2 — PostgreSQL only, no portability layer

- **Decision:** `JSONB`, `ILIKE` and `CHECK` constraints are used; other database
  engines are not supported.
- **Why:** The app is local-only. A single database keeps the schema simple and
  the tests fast.

## D3 — Enum-like columns are `String` + `CHECK`

- **Decision:** `status` / `kind` / … are stored as `String` with a `CHECK`
  constraint instead of a native PostgreSQL `ENUM`.
- **Why:** Changing enum values requires `ALTER TYPE` in PostgreSQL, which is
  painful in migrations; `CHECK` gives the same guarantee with more flexibility.

## D4 — The three honest time layers

- **Decision:** Three separate values are kept: `measured` (from `time_entries`),
  `estimated` (from `effort_minutes_estimate`) and `elapsed`
  (`completed_at - started_at`).
- **Why:** In real work, time is often not recorded. An estimate or an elapsed
  span is never presented as "hours worked", and every report states its own
  basis.
- **Consequence:** The AI only ever receives these numbers as structured JSON
  and is never allowed to invent them.

## D5 — Only Friday is a weekend day by default

- **Decision:** `weekend_weekdays` is a setting; its default value contains
  Friday only (index 6 in the Saturday-first ordering).
- **Why:** The brief said "Friday is the weekend". Working days in Iran have
  changed in recent years, so the user should decide. Tuesday/Thursday can be
  enabled as weekend days too.

## D6 — The holiday list is a user-owned file

- **Decision:** `data/holidays_jalali.json` holds a list of Jalali dates and is
  editable from the settings page.
- **Why:** We must not invent or hard-code an official calendar; the data
  belongs to the user.

## D7 — Timestamps in UTC, displayed in `Asia/Tehran`

- **Decision:** Every time column is `TIMESTAMP WITH TIME ZONE` and always
  stored in UTC; conversion happens only in the presentation layer.
- **Why:** Changing the timezone must never corrupt historical data.

## D8 — Jinja2 + HTMX, no Node build step

- **Decision:** All front-end libraries are vendored into `app/static/vendor`.
- **Why:** The brief demands "no CDN and no build step"; the app must work
  offline.

## D9 — The test gate

- **Decision:** The `tests` compose service runs `ruff check` and `pytest`
  before `app` and `worker` start, using
  `depends_on: … condition: service_completed_successfully`.
- **Why:** No version of the application should ever come up with failing tests.

## D10 — OS notifications come from the browser

- **Decision:** The worker only decides what should be notified and records it
  in `notification_log`; the page polls `/api/notifications/due` and raises
  Web Notifications.
- **Why:** A Docker container cannot notify the host operating system. This
  limitation is documented in the README.

## D11 — AI is entirely optional behind an interface

- **Decision:** An `AIProvider` interface with `Anthropic`, `OpenAICompatible`
  and `Fake` implementations; without an API key every non-AI feature works
  completely.
- **Why:** The app must not depend on an external service and must stay usable
  offline.

## D12 — No user login in the MVP

- **Decision:** A single user; authentication is optional via
  `BASIC_AUTH_USER` / `BASIC_AUTH_PASSWORD`.
- **Why:** The simplest possible local setup; multi-user support is on the
  roadmap.
