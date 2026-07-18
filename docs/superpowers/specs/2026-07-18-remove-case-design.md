# Remove a case

Date: 2026-07-18

## Problem

Cases can be created, switched, and renamed, but never deleted. A user who
creates a test case or finishes a matter has no way to remove it. This design
adds case deletion, including cleanup of the case's scoped data.

## Constraints

- The app must always have at least one case. `cases.init()` and
  `cases.active_id()` both self-heal toward this invariant, and the rest of the
  app assumes an active case always exists.
- `app/cases.py` depends only on the DB (no import cycle with the per-case
  stores). This design preserves that: each store owns the deletion of its own
  table's rows, and `app/main.py` orchestrates.
- Shared corpus / reference chunks (`case_id IS NULL`) belong to no case and
  must survive any case deletion.

## Scope of a deletion

Removing a case deletes:

- its row in the `cases` table, and
- its scoped rows in `chunks` (uploads only), `timeline`, `questions`,
  `obligations`, matched by `case_id`.

It does not touch shared corpus chunks (`case_id IS NULL`).

## Layers

### `app/cases.py` — `delete(case_id: int) -> bool`

- If only one case exists: no-op, return `False` (last-case guard).
- If `case_id` does not exist: no-op, return `False`.
- Otherwise delete the `cases` row. If the deleted case was active, activate the
  most recent remaining case via `set_active(...)` so the app is never left in a
  no-active-case state.
- Return `True`.

This function deletes only the `cases` row; it does not import the per-case
stores.

### Per-case stores — `remove_case(case_id: int) -> None`

Add to `store.py`, `timeline.py`, `questions.py`, `obligations.py`. Each runs a
`DELETE ... WHERE case_id=?` against its own table. `store.py` restricts to
`kind='upload'` so shared corpus chunks stay.

These take an explicit `case_id` (not `active_id()`), because the case being
deleted may not be the active one.

### `app/main.py` — `POST /api/cases/delete`

```
body: { id: int }
if the case exists and is not the last one:
    store.remove_case(id)
    timeline.remove_case(id)
    questions.remove_case(id)
    obligations.remove_case(id)
    cases.delete(id)   # removes the case row + reactivates if needed
return _cases_state()
```

Scoped data is cleared first (while still identifiable), then the case row.
Returns the standard `{cases, active_id}` state so the frontend refreshes like
the other case endpoints. Requires a `CaseDeleteBody` model.

### `web/app.js`

- A remove button (🗑) next to the rename (✎) button, hidden when
  `state.cases.length <= 1` (nothing to fall back to).
- Handler: `confirm(t("deleteCasePrompt")(name))`; on confirm, POST
  `/api/cases/delete`, then reset the per-case UI (same reset performed by
  `switchCase`: reveal, msgs, adviceResult, resolvedLocal), then `refresh()`.
- i18n strings, English and Spanish: `deleteCase`, `deleteCaseTitle`,
  `deleteCasePrompt`.

## Testing (`tests/test_cases.py`)

- `delete` removes the case and its scoped chunks / timeline / questions /
  obligations.
- Deleting the active case reactivates another case (exactly one active
  remains).
- Deleting the last remaining case is a no-op (blocked by the guard).
- Deleting a non-existent id is a no-op.
- Shared corpus chunks survive a case deletion.
