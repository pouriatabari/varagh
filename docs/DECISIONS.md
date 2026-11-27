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

## D29 — The muster is a draft, and the confirmation gives the medals

- **Decision:** A muster has a status: it is a draft until the user
  confirms it. The draft holds the immutable snapshot of the statistics
  and the proposals of the AI (virtue, domain, the tier asked for, the
  tasks that back it). The confirmation writes the medals; the user may
  lower a tier, but a tier is never raised above what the evidence
  proves. A confirmed muster is never confirmed twice, and a title that
  was reached is never taken back.
- **Why:** The honour must be the work's own, and the work must be the
  muster's own reading of it. If the medal could be written before the
  user had seen the muster, the muster would be a formality; if the tier
  could be raised freely, the evidence would be a decoration. The draft
  keeps the reading and the giving apart, so the user always stands
  between the work and its honour.

## D30 — The pictures of the hall are read from the database, never drawn by the AI

- **Decision:** The arms, the tree of the ranks and the round table are generated
  by the server from the state of the honours: the title gives the crown,
  the domains the user works in give the colours of the field, the virtues
  the medals stand for give the charges, and the counted medals give the
  lit tiers and the lit seats. The generator is deterministic — the same
  state always gives the same SVG — and it never asks the AI for a picture.
- **Why:** A picture that an AI draws may be beautiful, but it would also
  be a picture that could say anything. The arms of the hall must be a
  reading of the work and not a story about it, so the colours, the
  charges and the crown are taken from the database and nothing else. The
  determinism also lets the pictures be tested: a snapshot of every picture
  is kept in the repository, and a change of a picture is a change that
  must be read in the diff.

## D31 — The map is the real geography, and the realms are taken next to each other

- **Decision:** The ground of the map is the real geography of Great
  Britain: the coastline and the county borders come from Natural Earth
  (public domain), are thinned once and are kept in the repository as
  paths. The realms are written in `data/realms.json`, with their names,
  their legend, the ground they cover and the realms that touch them. A
  realm is taken by the user for one of their domains, and it may only be
  taken next to a realm that is already taken; the first realm of the map
  is the exception. Every counted medal of a domain lights the next of
  the three castles of its realm, and the third castle claims it. The
  hidden realm opens with the order of the scholar.
- **Why:** The map is the picture of the work, so it must be the work
  itself and not a decoration: real counties, real coast, real names of
  the places the work is done in. The rule of the neighbours keeps the
  map a campaign — the ground is won from the ground that is already
  held, never scattered — and the castles keep the reward honest, since
  a realm is only claimed by three counted medals of its own domain and
  not by a claim that was written down.

## D32 — The colours of the pictures are checked, not chosen by eye

- **Decision:** Every picture of the app takes its colours from the
  theme: the six steps of a categorical palette (the six virtues of the
  round table, the series of a chart), one gold ramp for the states that
  are ordered (the progress of a realm and the claim), one teal ramp for
  the heat of the days, and the surfaces of the theme for the ground. The
  steps of the palette were checked with a validator: the contrast
  against the surface of the theme, the separation of the neighbours under
  the deuteranopia, the protanopia and the tritanopia, the lightness of
  every step and the monotony of every ramp. The states of the map are
  never told by the colour alone: the fog is hatched, the hidden realm is
  dotted, and every state has its word in the key of the map and in the
  table under it.
- **Why:** The eye is a poor judge of a palette: two colours that look
  apart on the screen can fall together under the colour blindness of one
  reader in six, and a colour that is pretty against a white paper can
  vanish against a dark one. The check is cheap and the answer is
  written down, so the next theme or the next chart is checked the same
  way and not by taste. The texture and the word keep the picture honest
  for the reader who does not see the colour at all.

## D33 — The badges of the ranks are drawn by the code, from a catalogue

- **Decision:** Every title has a badge, and the badge is drawn by the
  code from `data/insignia.json`: a heater shield, a rim in the metal of
  the title, an emblem and the studs of the degrees. The coronets and the
  crowns are drawn from numbers (the pearls, the leaves, the arches, the
  rays), never as a picture that was drawn once, so the drawing and the
  description of the title can never disagree. The states of a badge are
  told three times over: by the words of its `<title>`, by the lock of a
  badge that is not earned yet and by the frame of the next title, so the
  colour never carries the meaning alone. The ribbon rack gives every
  virtue a colour **and** a stripe pattern, and a pip of the best tier
  that was earned.
- **Why:** The insignia are the language of the rank in the hall, and a
  language that is drawn by hand drifts from its own rules: a title with
  four pearls in one place and six in another. A catalogue and a
  renderer keep the picture honest, and the tests can count the pearls of
  the picture and compare them with the numbers that are written down
  here.
- **The placements:** three places carry the badges today: the case of the
  insignia (`/insignia`), the header of the hall of honours (the badge of
  the title of the user, the studs of the degrees and the rack of the six
  ribbons) and the tree of the ranks (a badge beside every title, lit up
  to the title of the user and locked above it). Three more placements were
  asked for and are not built yet, because the flows behind them do not
  exist: the pinning ceremony (no route may promote a title by hand, so
  there is nothing to hang a badge on), the header of the saga (the saga of
  the musters is not written yet) and the official ledger (there is no
  ledger of the honours yet). The renderer is ready for them.
- **The visible counts:** the counts that are drawn in perspective are a
  choice of the drawing, and they are written down so that the test of
  the project can read them: the baron draws 4 pearls of its 6, the
  viscount 9 of its 16, the earl 5 leaves and 5 pearls of its 8 and 8,
  the marquess 4 leaves and 4 pearls of its 4 and 4, the duke 5 leaves
  and no pearl at all, the prince one arch, the king two arches with the
  orb and the cross, and the bretwalda twelve rays around the king
  crown.

## D34 — The budget of the answer is capped inside the app

- **Decision:** The number of tokens the model may answer with is clamped
  to 65536 before the call leaves the app, and the settings page offers no
  larger number. A gateway that is asked for a budget no model can give
  answers with a server error (502), and the message of the gateway hides
  the reason; every call of the app then fails and the user cannot see
  what to change. The budget of the answer is a number of the machine, not
  a wish: a model that can give 196608 tokens still answers well with
  65536, and the clamp keeps the calls alive.
- **Why:** The error was a `502 Bad Gateway` on every AI feature, with a
  message that named the URL and nothing else. The settings page now
  shows the number it will actually use, the failure carries the words of
  the gateway (for example `does not support max tokens > 196608`), and the
  page of the app shows the sentence of the lexicon with the technical
  detail in a smaller line beneath it.

## D35 — The guide is built out of the configuration, never written by hand

- **Decision:** The page `/guide` explains the whole round — the steps of a
  month, the tiers of a medal and the evidence of each, the monthly cap,
  the halving of the second medal of a domain, the degrees, the ladder of
  the titles with the gates of every one of them, the map and the rules —
  and every number on it is read from `config/rewards.yaml` when the page
  is drawn. The words live in the two lexicon packs (medieval and plain),
  like every other word of the interface; the numbers live in the
  configuration, like every other number of the engine.
- **Why:** A guide that repeats the numbers in its own text rots: the
  moment a threshold is changed, the guide lies. A guide that reads the
  configuration cannot lie, and the tests check that the numbers of the
  page are the numbers of the engine.
- **What the guide does not promise:** the orders (the quill, the scholar
  and the round table) and the quests are not given by the app yet, so the
  guide does not speak of them. The hidden realm of the map waits for the
  order of the scholar, and that is a rule of the map, not a promise of a
  date.

## D36 — The ceremony of the title is the app's own step

- **Decision:** When every gate of the next title is met, the app writes
  the title down by itself (`honours.promote_if_ready`), with the vigil of
  the ceremony, and the date stays in the case of the insignia. The user
  never registers a title by hand — the same rule that holds for the
  medals, and for the same reason: the honours must be earned, not typed.
- **Why:** The hall already said that the ceremony was due when the gates
  were met, but nothing ever performed it, so a title could never be
  reached and the badges of the ladder would stay closed for good. The
  promotion is now a step of the muster confirmation, where the medals are
  given, and the tests check that a title is given only when its gates are
  met and never taken back.

## D37 — The tree of the ranks is drawn from the data, and it is not a canvas to fight with

- **Decision:** The ladder of the titles is drawn as a tree of the ranks, in
  the manner of a skill tree of a game: the ranks are a chain of shields
  that runs from left to right, and the gates of the ranks hang under them
  like the pendants of a chain, each on its own stem. Every node and every
  path is computed from `config/rewards.yaml` and from the state of the
  user. The picture is a plain scrolling strip of SVG — no zoom, no drag, no
  panning. Clicking a node loads its panel with HTMX.
- **Why:** The tree was first drawn as a canvas that could be zoomed and
  dragged. It was fiddly to drive, easy to lose the thread of, and it hid
  the very thing the tree is for: the gates of the rank that waits. A long
  picture that scrolls the way a page scrolls is easier to read and easier
  to keep honest, and the panel of a node gives the detail that the picture
  has no room for. The shape of the picture follows the picture the design
  was taken from: a chain of nodes with the small medallions hanging under
  it, not a ladder of a chart. Nothing of the tree is written by hand: a
  title that the configuration does not know is never drawn, so the picture
  cannot drift away from the rules of the reward engine.
