# Per-case documentation isolation — design

Date: 2026-07-18

## Problem

Case Companion stores all documents, timeline events, questions, and
obligations in one flat SQLite database with no concept of a "case". A user
handling more than one matter cannot keep the documentation for each matter
separate, and cannot switch back and forth between them. Every panel
(documents/RAG, timeline, warnings, ask-your-attorney) shows everything mixed
together.

## Goal

Let a user create named cases, switch between them, and have every
case-specific panel follow the active case. Documents uploaded under one case
must not appear in another case's RAG answers, timeline, warnings, or
questions.

## Decisions (locked during brainstorming)

1. **Case creation:** explicit "New case" button + a case switcher (dropdown).
   No auto-inference of a case from document content.
2. **Active-case state:** server-side. The DB records which single case is
   active; existing endpoints implicitly scope to it. The frontend does not
   pass `case_id` on every request.
3. **Existing data:** wipe and start fresh. No migration of pre-existing
   un-scoped rows. This is a deliberate, one-time reset (destroys current
   `data/case_companion.db` contents).
4. **Threading:** a central `cases` module owns active-case state; each store
   module reads `cases.active_id()` internally (Approach A). Endpoint
   signatures stay stable.

## Scope

**In scope (scoped per case):** documents/chunks (RAG corpus), timeline,
questions, obligations.

**Out of scope (shared across all cases):** the authorities library and
`deadline_rules.json` — these are reference data, not case-specific.

Single-user, on-device app: exactly one active case at a time is sufficient.

## Data model

New table:

```
cases:
    id          INTEGER PRIMARY KEY AUTOINCREMENT
    name        TEXT
    created     TEXT
    is_active   INTEGER DEFAULT 0    -- exactly one row is 1 at a time
```

Add `case_id INTEGER` to each case-specific table:

```
chunks:      + case_id INTEGER
timeline:    + case_id INTEGER
questions:   + case_id INTEGER   (UNIQUE constraint becomes UNIQUE(case_id, question))
obligations: + case_id INTEGER
```

Because we wipe and start fresh, these tables are created with `case_id` from
the start — no ALTER/migration. On first run with an empty `cases` table, the
app auto-creates one case named **"My case"** and marks it active, so the UI is
never in a "no active case" state.

## Components

### New: `app/cases.py`

Owns the `cases` table and the active-case state. Depends only on the DB (no
import cycle with the other stores).

```
init()                    # create cases table; if empty, create "My case" active
list_all() -> list[dict]  # [{id, name, created, is_active}], newest first
active_id() -> int        # currently active case id; always valid (self-heals)
create(name) -> int       # insert new case, switch to it, return id
set_active(id) -> None    # clear all is_active, set this one (single transaction)
```

Rules:
- `active_id()` always returns a valid id. If none is active, it activates the
  most recent case, or creates "My case" if the table is empty.
- `create(name)` switches to the new case. Blank name falls back to
  "Untitled case".
- `set_active(id)`: `UPDATE cases SET is_active=0`, then
  `UPDATE cases SET is_active=1 WHERE id=?`.

### Changed stores

Each reads `cases.active_id()` internally when scoping a query.

- **store.py**: `add_chunks()` stamps `case_id`; `search()` filters
  `WHERE case_id = active` (RAG only sees the active case's documents);
  `clear_uploads()` scoped to active case.
- **timeline.py**: `add_event()` stamps `case_id`; `list_events()` filters.
- **questions.py**: `add()` stamps `case_id`; unique constraint becomes
  `UNIQUE(case_id, question)`; `list_open()` and `resolve()` scoped.
- **obligations.py**: `add()` stamps `case_id`; `list_open()`, `try_satisfy()`,
  `warnings()` all scoped.
- **deadlines.py**: no change — it calls `obligations.add()` and
  `timeline.add_event()`, which now self-scope.

### API (`app/main.py`)

New endpoints:

```
GET  /api/cases          -> {cases: [{id, name, created, is_active}], active_id}
POST /api/cases {name}   -> create + switch, returns updated {cases, active_id}
POST /api/cases/switch {id} -> set active, returns updated {cases, active_id}
```

Existing endpoints (`/api/upload`, `/api/ask`, `/api/timeline`,
`/api/warnings`, `/api/questions`, ...) are unchanged in signature and now
implicitly operate on the active case. Startup calls `cases.init()` before the
other store inits.

### Frontend (`web/index.html`, `web/app.js`)

- Case switcher in the header: a `<select>` of cases + a "＋ New case" button.
- Selecting a case -> `POST /api/cases/switch` then reload all panels
  (facts card hidden until next upload; timeline/warnings/questions refetched).
- "New case" -> prompt for name -> `POST /api/cases` -> reload panels + switcher.
- On page load: fetch `/api/cases`, populate the switcher, select the active
  case, then load the panels (as today).

## Data flow

1. User picks a case in the switcher -> `/api/cases/switch` sets `is_active`.
2. Frontend refetches timeline / warnings / questions; each backend handler
   calls the store, which scopes by `cases.active_id()`.
3. User uploads a document -> chunks/timeline/obligations/questions are all
   stamped with the active `case_id`.
4. User asks a question -> `store.search()` retrieves only chunks whose
   `case_id` is active, so RAG answers are isolated to that case.

## Error handling

- No active case (shouldn't occur): `active_id()` self-heals by activating the
  most recent case or creating "My case".
- Switch to a non-existent case id: return the current state unchanged (no-op),
  do not error the whole request.
- Blank new-case name: fall back to "Untitled case".

## Testing / verification

- Unit: `cases.create()` switches active; `set_active()` leaves exactly one
  active; `active_id()` self-heals on an empty table.
- Isolation: create case A, upload a doc, create case B; confirm B's timeline,
  warnings, questions are empty and RAG in B does not retrieve A's chunks;
  switch back to A and confirm its data returns.
- Manual: run the app, create two cases, upload different docs into each, ask a
  question in each, switch back and forth, confirm every panel follows.

## Non-goals

- Multi-user / concurrent active cases.
- Migrating existing un-scoped data (explicitly wiped).
- Deleting or renaming cases (can be added later; not requested).
- Scoping authorities or deadline rules per case (they stay shared).
