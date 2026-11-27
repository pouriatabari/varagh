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

## D17 — The AI configuration lives in the database, the environment is the fallback

- **Decision:** The provider, the key, the model, the base URL, the timeout,
  the maximum number of output tokens and the authentication header are written
  by the settings page into the `settings` table. As soon as the user saves
  that form, the stored document wins as a whole; otherwise the `AI_*`
  environment variables decide. The key is never sent back to the browser and
  is redacted from `/export.json`.
- **Why:** The application is used by one person who should be able to switch
  provider, model or gateway without editing a file and restarting a
  container. A stored document that wins as a whole also allows a field to be
  cleared on purpose, which a per-field fallback would not allow.

## D18 — An AI chart names a series, never a number

- **Decision:** The model may ask for a chart, but it may only name a series
  of the payload (`measured_minutes_by_kind`, `measured_minutes_by_day`,
  `counts_by_context`, `counts_by_status`, …). The server resolves the labels
  and the values out of the database and rejects a chart of an unknown series.
- **Why:** The rule that the AI never invents a figure has to hold for the
  charts too: a model that sends its own numbers could show a bar that no
  time entry ever produced. Naming a series keeps the figure in the database
  and lets the labels stay in the app's own Persian wording.

## D19 — Every list shares one selection, and the deletion is a form built in the browser

- **Decision:** The task list, the learning items, the achievements and the
  reviews share the same Alpine component: a checkbox per row, a «select all»
  that ticks every box of the page, and a bulk action that deletes the
  selection. The request is a small form that the browser builds and sends,
  not a wrapping `<form>` around the list.
- **Why:** A wrapping form would put the per-row forms inside it, and nested
  forms are invalid HTML — the browsers drop them, which is why a per-row
  delete did nothing. Building the form in the browser keeps every page valid
  and lets the same component serve the four lists.

## D20 — The learning items are soft-deleted

- **Decision:** A deleted learning item keeps its row with a `deleted_at`
  marker (migration `0003`); the list and the detail page skip the deleted
  items. The tasks behave the same way.
- **Why:** The study logs of a learning item and the time entries that point
  at it must stay intact; a hard delete would take the history with it.

## D21 — The overtime has a form of its own

- **Decision:** The calendar carries a dedicated card for the overtime, next
  to the general time entry. The reason is mandatory there, and the reason of
  the general form becomes mandatory as soon as its kind is `overtime`.
- **Why:** The overtime is reported apart from the regular working time, with
  its own reason. It must be a deliberate act, not an accident of a dropdown.

## D22 — An entry with a duration is a finished measurement

- **Decision:** `create_entry` closes an entry that was given a duration: it
  sets `ended_at` to the start plus the duration. Only `start_timer` leaves an
  entry open.
- **Why:** An open entry is the running timer of the app. A manual entry that
  stayed open was picked up by the next stop of the timer, which froze it
  with the whole span between the two dates — days instead of the minutes the
  user wrote down. The reports then showed hundreds of hours that no one
  ever measured.

## D23 — The seed resets its own rows before it seeds again

- **Decision:** `python -m app.seed --force` removes the demo rows it wrote
  before it writes them again. The rows are recognised by their marks (the
  description of a demo task, the note of a demo entry, the text of a demo
  journal and review); the rows of the user are never touched.
- **Why:** Without the reset every run piled its demo rows on top of the
  previous ones, so the same work was counted again and again and the
  reports grew with every seed.

## D24 — The medals are computed, never stored

- **Decision:** A medal is a function of the database: the number of the
  finished tasks, the measured hours, the confirmed achievements, the finished
  learning items, the rated reviews and the streak of the days. The page
  computes them on every request and stores nothing.
- **Why:** A medal has to mean what it says. If the progress that earned it
  disappears — a task is undone, an item is deleted — the medal has to go
  away with it. Storing the medals would let a stale one stay in the list.

## D25 — The drawing of the board is a picture in the data directory

- **Decision:** The marker of the board draws on a canvas; the picture is
  sent as a PNG, saved in `data/drawings` and put on the board as an item of
  the type `drawing`. The board item only holds the name of the file.
- **Why:** A board holds pictures of many sizes; storing them as blobs in the
  database would make every load of the board heavy, and the notes of the
  task are Markdown — a picture does not belong in them.

## D26 — Two packs of words, one of them medieval

- **Decision:** The words of the interface live in two packs with the same
  keys: `fa_plain` (the everyday words) and `fa_medieval` (the language of a
  ledger — the missions are orders, the review is a muster). The user
  chooses the pack in the settings; the default is the medieval one. A
  medieval term keeps its plain wording with it, so the page can show it in
  a tooltip.
- **Why:** The vocabulary of the app is part of its character, but it must
  never cost the user the meaning of a word. The plain wording is always
  one hover away, and the exports, the ledger, the mail and the webhooks
  always speak plainly — the words of the interface never leave the
  presentation layer.

## D27 — The theme is a setting, the system only has the first word

- **Decision:** The night and the parchment are two sets of CSS variables.
  The theme is a setting of the user; `prefers-color-scheme` only decides
  the theme of the very first visit, before a choice was made.
- **Why:** A theme is a taste, and a taste belongs to the person, not to
  the machine. The system may have the first word, but never the last one.

## D28 — The honours hall is given by the reviews, never by hand

- **Decision:** The honours of the hall are computed by the reward engine
  out of the finished reviews and the work they measure. Nothing is
  registered by hand as an achievement: the page has no form to add one.
- **Why:** An honour that anyone can write down is worth nothing. The
  honour must come from the muster — the review that looked at the work —
  and from the work itself, so that it cannot be claimed and cannot be
  lost either.
