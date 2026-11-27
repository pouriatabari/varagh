# ورق — Varagh

A personal, local-first, Persian task and work-journal web app.

> **Quickstart:** `cp .env.example .env` then `docker compose up --build`.
> The test gate runs first (ruff + pytest); the app starts on
> <http://localhost:8000> only if everything passes.

## What Varagh solves

Varagh replaces a paper notebook with a personal digital work journal: tasks
(assigned to you or self-initiated), time tracking (regular work, overtime
with a reason, study), books and courses, a free-form daily journal, and
periodic self-reviews (month, quarter, half-year, year, or any custom range).

The difference from team tools like Jira or Notion is that Varagh is a personal
**evidence ledger**: what I did, how long it took, what I achieved, what I
learned, and how I improved compared to the previous period.

The interface is Persian and right-to-left by default; the Jalali (Shamsi)
calendar is used throughout. Everything runs locally with no cloud dependency
and no CDN — fonts (Vazirmatn) and JavaScript (HTMX, Alpine.js, Chart.js) are
vendored into `app/static`.

## Quickstart

```bash
cp .env.example .env
docker compose up --build
```

Then open <http://localhost:8000>.

## Features

| Screen | What it does |
| --- | --- |
| **داشبورد** (dashboard) | Overdue / today / done-this-week counters, measured hours by kind, weekly target, 90-day activity heatmap with streak, the day plan, two charts (minutes per day, tasks per context) |
| **تسک‌ها** (tasks) | CRUD, filters, Markdown notes, soft delete (single and in bulk), quick-add bar, draggable sticky board, a marker to draw on the board, AI domain classification |
| **تقویم** (calendar) | Jalali month grid with the daily totals, click to add a task, running-timer chip, a dedicated form for the overtime |
| **یادداشت روزانه** (journal) | Free-form entries; the AI proposes a structure that is written only after you confirm it |
| **یادگیری** (learning) | Syllabus parsing, units, "read up to here", progress bars, stale-item report, deletion (single and in bulk), a chart per item and for the minutes |
| **تالار افتخارات** (hall of honours) | The medals the musters give, the degrees, the title of the user and the gates of the next one. Nothing is registered by hand: the honours come from the reviews |
| **ارزیابی‌ها** (reviews) | Jalali month/quarter/half-year/year periods, an immutable stats snapshot, comparison with the previous period, a wizard with an AI draft and its charts, Markdown export, a read-only view of a finished review, a rating that shows its scale (۴ از ۵), deletion (single and in bulk), a chart of the hours per kind and of the rating of every review |
| **تنظیمات** (settings) | Timezone, weekend days, weekly target, notification channels with test buttons, holidays, the AI provider, key and model, JSON export |
| **اضافه‌کاری** (overtime) | A tab of its own: a dedicated form, the total, the split between the off days and the working days, a chart of the last sixty days and the list of the entries |

## The test gate

The `tests` service in `docker-compose.yml` runs `ruff check` and then `pytest`
against a separate `varagh_test` database on the same PostgreSQL instance. The
`app` and `worker` services depend on it with
`condition: service_completed_successfully`, so the application starts **only**
if the whole suite is green. Alembic migrations run after the gate, when `app`
starts.

```bash
make up      # build + start everything (tests run first)
make test    # run ruff + pytest only
make down    # stop the stack
make logs    # follow app and worker logs
```

## Environment variables

| Variable | Default | Meaning |
| --- | --- | --- |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | `varagh` | PostgreSQL credentials and database name |
| `DATABASE_URL` | `postgresql+psycopg://varagh:varagh@db:5432/varagh` | Application connection string |
| `TEST_DATABASE_URL` | `…/varagh_test` | Database used by the test service |
| `POSTGRES_IMAGE` / `PYTHON_IMAGE` | `public.ecr.aws/docker/library/…` | Base images; the defaults use the official Docker Hub library images through the public ECR mirror (no rate limits). Set them to `postgres:16-alpine` / `python:3.12-slim` to pull from Docker Hub directly |
| `APP_PORT` | `8000` | Host port of the web UI |
| `SECRET_KEY` | dev value | Session/CSRF secret — change it |
| `TIMEZONE` | `Asia/Tehran` | Timezone used for display |
| `BASIC_AUTH_USER` / `BASIC_AUTH_PASSWORD` | empty | Optional HTTP Basic auth for the single user |
| `AI_PROVIDER` / `AI_API_KEY` / `AI_MODEL` / `AI_BASE_URL` | empty | Optional AI provider (`anthropic`, `openai`, `custom`) |
| `AI_TIMEOUT_SECONDS` | `30` | AI request timeout |
| `AI_MAX_OUTPUT_TOKENS` | `2048` | Maximum number of tokens the model may answer with |
| `AI_AUTH_HEADER` | `both` | How the key is sent: `x-api-key`, `bearer` or `both` |
| `AI_CUSTOM_URL` / `AI_CUSTOM_METHOD` / `AI_CUSTOM_HEADERS` | empty | Custom provider: endpoint URL, request shape (`json`, `openai`, `anthropic`, `prompt`) and extra headers |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASSWORD` / `SMTP_FROM` | empty | Optional email channel |
| `WEBHOOK_URL` / `WEBHOOK_FORMAT` | empty / `slack` | Optional webhook channel (`json` or `slack`) |

Secrets are only read from the environment; `.env` is git-ignored and must
never be committed.

## Enabling AI

AI is completely optional. Without a key every other feature works: tasks,
time, calendar, statistics and manual reviews.

### From the settings page

The **تنظیمات → هوش مصنوعی** card writes the configuration into the database:
the provider, the API key, the model, the base URL, the timeout, the maximum
number of output tokens and the way the key is sent. There is a **آزمایش اتصال**
button that calls the endpoint once and reports what happened. As soon as
something is saved there, it wins over the environment variables.

```bash
AI_PROVIDER=anthropic   # or "openai" for any OpenAI-compatible endpoint
AI_API_KEY=sk-...
AI_MODEL=<model id>     # never hard-coded in the app
# AI_BASE_URL=https://my-endpoint.example/v1   # only for OpenAI-compatible providers
```

### A custom provider

Any endpoint that answers with JSON can be used — a local model, a gateway or
a proxy:

```bash
AI_PROVIDER=custom
AI_CUSTOM_URL=https://my-model.example/v1/answer
AI_CUSTOM_METHOD=json      # json | openai | anthropic | prompt
AI_CUSTOM_HEADERS=X-Api-Key: abc, X-Tenant: personal
AI_MODEL=<model id>
```

The request body is chosen by `AI_CUSTOM_METHOD`:

| Method | Body |
| --- | --- |
| `json` | `{model, system, messages, payload}` — the generic shape |
| `openai` | an OpenAI chat-completions request |
| `anthropic` | an Anthropic messages request |
| `prompt` | `{model, prompt}` — the answer is plain text that is parsed as JSON |

The answer may be a bare JSON object or an OpenAI/Anthropic-shaped one; all
three are understood. Whatever the provider returns is validated against a
strict schema, and a draft that cites a task the model never saw is rejected.

### An Anthropic-compatible gateway

Many gateways speak the Anthropic protocol and expect the key as
`Authorization: Bearer …` instead of `x-api-key`. Pick the way the key is
sent in the settings page (`x-api-key`, `bearer` or `both`) and point the base
URL at the gateway — the app appends `/v1/messages` to it:

```
base URL: https://my-gateway.example/anthropic
model:    minimax/MiniMax-M2.5
key:      the token of the gateway
```

The stored key is never sent back to the browser and is redacted from
`/export.json`; the `pg_dump` backup of `make backup` still contains it.

## Enabling notification channels

In the settings page each channel can be toggled and tested:

- **Browser** — enabled by default; uses the Web Notifications API.
- **Email** — set the `SMTP_*` variables and add a recipient address.
- **Webhook** — set `WEBHOOK_URL`; `WEBHOOK_FORMAT=slack` posts a
  Slack/Mattermost-compatible payload, `json` posts a generic JSON document.

## How OS notifications work

A Docker container cannot notify the host operating system directly. Varagh's
worker only *decides* that something needs attention and records it in the
`notification_log` table (with de-duplication). The open page polls
`/api/notifications/due` every 30–60 seconds and raises the actual OS
notification through the browser's Notification API. This works on
`http://localhost:8000`, and the app can be installed as a PWA.

## Charts in the AI answers

An AI answer may come with charts: the plan of the day, the draft of a review
and the answer of «از داده‌هایم بپرس» can show a bar, line or doughnut chart.

The model never sends a number. It names a **series** of the payload it was
given — `measured_minutes_by_kind`, `measured_minutes_by_day`,
`counts_by_context`, `counts_by_status` — and the server resolves the labels
and the values out of the database. A chart that names a series the payload
does not have is rejected, exactly like a draft that cites an unknown task id.
Every chart states its basis (measured, estimated or elapsed) and its unit.

## The three-layer time model

Time is often not recorded, so every number states its basis:

1. **measured** — derived from `time_entries` (real timers and manual entries).
2. **estimated** — the `effort_minutes_estimate` you wrote on the task.
3. **elapsed** — lead time: `completed_at` minus `started_at` (falling back to
   `created_at`); always available.

Estimates and elapsed spans are never shown as measured hours, and the AI only
ever receives the real numbers from the database as structured JSON.

## Holidays file format

`data/holidays_jalali.json` is yours to edit:

```json
{
  "holidays": [
    { "date": "1404/01/01", "title": "نام تعطیلی" }
  ]
}
```

Dates are Jalali (`YYYY/MM/DD`); `title` is optional. The file ships empty on
purpose — no official holidays are hard-coded. Dates can also be added and
removed from the settings page.

## Backup, restore and export

```bash
make backup                                  # pg_dump into ./backups
make restore BACKUP_FILE=backups/<file>.sql  # restore a dump
make seed                                    # Persian demo data
```

`GET /export.json` returns every table as a single JSON document (tasks,
entries, notes, board items, journal, learning items, reviews, achievements,
settings).

## The icons

Every icon is a small SVG file in `app/static/icons`, and the pages inline
it, so an icon takes the colour of the text it sits in and costs no extra
request. The files come from Tabler Icons (MIT) and from game-icons.net
(CC BY 3.0); `app/static/icons/manifest.json` names the source, the author
and the licence of every one of them, and the page `/about/credits` shows
the same list.

```bash
# the icons are plain files; open one in a browser to see it
open app/static/icons/tasks.svg
```

## The two lexicons

The interface speaks in one of two Persian packs, and the user chooses the
pack in the settings page:

- **medieval** (the default) — the missions are orders, the review is a
  muster, the learning is a library and the overtime is a night watch;
- **plain** — the everyday words of the app.

The two packs have exactly the same keys, so no screen can miss a word. A
medieval term carries its plain wording with it: the mouse shows it in the
tooltip, and a long press on a touch screen shows it in a small box.

The pack only touches the presentation layer. The exports, the ledger, the
mail and the webhooks always speak plainly, and the code, the columns and
the URLs keep their neutral English names (`task`, `review`, `achievement`).
The words of the interface live in `app/i18n`, and a test refuses any
Persian word written directly in a template.

## The two themes

The night (the default) and the parchment are two sets of CSS variables:
the night is the dark of a watchtower with a warm gold and a green ink,
the parchment is the warm paper of a ledger. The setting lives in the
settings page; the system preference (`prefers-color-scheme`) only decides
the theme the very first time, before the user has chosen one.

## The hall of honours

The hall of honours is not a list the user fills in by hand. The honours
come from the musters (the reviews): at the end of every Jalali month the
worker writes the draft of the muster of that month, the AI proposes the
medals with the tasks that back them, and the user confirms the muster. Only
then are the medals written — and the server checks every proposal again
before it gives anything:

- a medal may only be backed by a task that is finished, that is allowed to
  count and that does not back another medal;
- the tier the proposal asks for is lowered to what the evidence proves
  (bronze 1, silver 2, gold 4 points of value);
- a month counts at most 10 points of value, and the second medal of the
  same domain in the same month counts for half;
- six points of value make one degree, and the titles go from the page to
  the king — the king needs 65 degrees, which is 39 months at the cap.

Every number of the engine lives in `config/rewards.yaml` and is validated
when it is read, so a wrong number is reported instead of breaking a muster.

## Project structure

```
app/
├── api/        # thin HTTP routes and FastAPI dependencies
├── services/   # all business logic
├── models/     # SQLAlchemy 2.0 models
├── schemas/    # Pydantic v2 schemas
├── templates/  # Jinja2 templates (RTL)
├── static/     # CSS / JS / the isometric icons / vendored fonts
├── ai/         # AIProvider interface and implementations
├── notify/     # notification channels and rules
├── worker/     # APScheduler worker
└── i18n/       # the two Persian packs: the plain one and the medieval one
```

## Troubleshooting

- **The app never starts** — the `tests` gate failed; run `make test` and read
  the output.
- **Database connection errors** — the `db` service is not healthy yet, or
  `DATABASE_URL` points somewhere else. Check `make logs`.
- **No OS notifications** — the browser needs permission for the site, and the
  page must be open. See "How OS notifications work" above.
- **Docker Hub is unreachable** — the defaults already pull through the public
  ECR mirror; if you forced `docker.io`, switch back to
  `public.ecr.aws/docker/library/postgres:16-alpine` and
  `public.ecr.aws/docker/library/python:3.12-slim`.

## Roadmap

- [x] M1 — foundation: compose, migrations, RTL layout, test gate
- [x] M2 — tasks: CRUD, quick-add, filters, Markdown, soft delete
- [x] M3 — time and calendar: timer, overtime rules, Jalali calendar, journal
- [x] M4 — dashboard: counters, measured hours by kind, weekly target, heatmap
- [x] M5 — notifications: browser/PWA, worker rules, email, webhook
- [x] M6 — task board and notes timeline
- [x] M7 — reviews, achievements, period-over-period comparison
- [x] M7b — learning tracker: syllabus, units, progress, stale report
- [x] M8 — AI features behind the `AIProvider` interface
- [x] M9 — export, backup/restore, seed data, final polish
- [x] M10 — the two lexicons, the two themes, the icon manifest and the credits
- [x] M11 — the reward engine: the musters, the medals, the degrees and the titles

Still open:

- The court chart, the round table and the heraldry of the hall of the honours
  are not drawn yet.
- The realm map and the saga of the musters are not written yet.
- The learning report is generated per item; a yearly summary page is missing.
- The dashboard heatmap is a flat 90-day grid; a calendar-shaped heatmap would
  read better.
- The journal stores the confirmed proposal as JSON but does not create time
  entries out of it yet.

Out of scope (roadmap only): notebook-photo → tasks via vision, Excalidraw /
tldraw boards, Telegram bot, ICS export, multi-user support, host-side
notifier agent.
