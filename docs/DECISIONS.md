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

## D13 — `notification_log` is both the ledger and the browser queue

- **Decision:** The unique constraint on `(kind, ref_id, channel, window_key)`
  de-duplicates every channel, and the rows of the `browser` channel double as
  the queue the page polls. A nullable `delivered_at` marks the rows the
  browser has already shown, and the payload of the message is stored as JSON
  in the same row.
- **Why:** One table keeps the de-duplication and the queue consistent; a
  notification can never be sent twice, and the browser never misses one.

## D14 — Notifications are decided by the worker, delivered by the page

- **Decision:** The worker evaluates the rules every five minutes and writes
  to `notification_log`. The browser polls `/api/notifications/due` every 45
  seconds and raises the OS notification itself. The email and webhook
  channels deliver immediately from the worker.
- **Why:** Docker cannot reach the host notification daemon, but the browser
  can; keeping the decision in the worker means the rules run even when no
  page is open.

## D15 — The AI may only speak about tasks it was given

- **Decision:** Every AI feature builds its payload out of the database, and
  the answers are validated against strict Pydantic schemas that refuse
  unknown fields. The review draft is rejected when it cites a task id that is
  not part of the statistics snapshot.
- **Why:** The AI must never invent a number or a task. The validation makes
  that a hard failure instead of a silent mistake.

## D16 — A custom AI provider is a first-class option

- **Decision:** Besides `anthropic` and `openai`, the provider `custom` calls
  any endpoint configured with `AI_CUSTOM_URL`, `AI_CUSTOM_METHOD` and
  `AI_CUSTOM_HEADERS`. The request shape is chosen by the method (`json`,
  `openai`, `anthropic` or `prompt`) and the answer may come back as a bare
  JSON object or in one of the two vendor shapes.
- **Why:** The user may run a local model, a gateway or a proxy. The whole
  application must keep working without touching the vendor-specific code.
