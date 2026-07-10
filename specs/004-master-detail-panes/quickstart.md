# Quickstart: Validating Master-Detail Pane UI

This is a validation guide, not an implementation spec — see [data-model.md](./data-model.md) for the (lack of) schema changes and [contracts/](./contracts/) for exact route/DOM contracts this feature adds or changes.

## Prerequisites

- Same environment as 001/002/003: Python 3.12 venv, dependencies installed.
- No new migration to apply — this feature adds no tables/columns (`data-model.md`).
- `app/static/alpine.min.js` present (vendored, new in this feature).

## Setup

```bash
uvicorn app.main:app --reload
```

Open `http://localhost:8000/` — this is now the only URL the app ever navigates to (FR-001/FR-002); there is no `/projects`, `/projects/{id}`, etc. anymore.

## Automated validation

```bash
pytest tests/unit tests/integration
```

Expected coverage:

- `tests/integration/test_projects_routes.py` — **substantially rewritten**, not extended: old full-page-route assertions (`/projects`, `/projects/{id}`, `HX-Redirect` targets) no longer apply since those routes are removed (FR-027). New assertions cover `GET /`, `GET /panes/projects` (list + OOB details default), `GET /panes/projects/{id}` (select), `POST`/`PUT /panes/projects...` (OOB row insert/replace), `DELETE /panes/projects/{id}` (row removal, cascade-block rejection unchanged from 003, conditional OOB details-pane swap per FR-017a).
- `tests/integration/test_group_task_routes.py` — substantially rewritten, same reasoning: every route stays nested under `/panes/projects/{project_id}/group-tasks/...` (`contracts/pane-read-routes.md`), including new coverage that the `get_active_project_or_404` 404 (003's FR-015a) still fires on select/update/delete, not only on create; FR-017a OOB behavior scoped to the Group-task's own list.
- `tests/integration/test_deleted_routes.py` — substantially rewritten: `GET /panes/deleted` replaces `GET /deleted`, response is now a left-pane fragment + OOB empty `#details-pane` rather than a full page.
- `tests/unit/test_project_service.py`, `tests/unit/test_group_task_service.py` — **unaffected** (FR-028: business logic unchanged); may gain a small addition covering the new `list_active_projects_with_delete_eligibility` batched-count query, but no existing test changes.

## Manual validation scenarios

**US1 — Browse the hierarchy in a persistent two-pane layout**
1. Load `/`. Confirm both panes render: left pane lists active Projects, right pane shows the first Project's details (or a create-prompt if none exist) — one page load, no further navigation needed.
2. Click a Project's title. Confirm the left pane replaces its list with that Project's active Group-tasks, the breadcrumb now reads "Projects › {title}", and the details pane updates to that Project's first Group-task (or its create-prompt) — all without a full page reload (check the Network tab: no full HTML document request).
3. Click an ancestor link in the breadcrumb from two levels deep (not applicable yet with only Project/Group-task — confirm the one-level breadcrumb jump back to "Projects" instead) works and both panes update together.
4. Reload the browser mid-drill. Confirm it returns to the home state (root Project list, first Project's details) with no attempt to restore the prior drill position (FR-002).

**US2 — Create a new entity from the current drill level**
1. From the root Project list, click "+ New Project," fill in required fields, save. Confirm the new row appears in the left pane list (appended, correct `serial_num`) and the details pane shows it as selected, with no `HX-Redirect`/full navigation involved.
2. Drill into a Project's Group-tasks, click "+ New Group-task," submit invalid values (e.g., blank title). Confirm the error appears in the details pane's fixed error area, entered values are retained, and no navigation occurs.
3. With an empty Group-task list, confirm the details pane shows a create-prompt and "+ New Group-task" remains available and functional.

**US3 — Edit an existing entity's fields**
1. Select an existing Project via its row title. Confirm the form is pre-populated.
2. Change a field (e.g., status) and save. Confirm the left pane's row updates in place (OOB) and the details pane reflects the saved state, in one response.

**US4 — Delete an entity guarded by active children**
1. View a Project with at least one active Group-task. Confirm its delete control is disabled.
2. View a Project with zero active Group-tasks. Confirm its delete control is enabled, triggers a confirmation prompt, and removes the row in place on confirm.
3. With that Project's details currently open in the details pane, delete it from its own row. Confirm the details pane auto-selects the next remaining active Project (or the create-prompt) — this is the FR-017a OOB mechanism (`contracts/pane-mutation-routes.md`); confirm it does *not* fire if you delete a **different** row than the one currently selected (details pane stays untouched).
4. Confirm every Group-task row's delete control is enabled unconditionally (no Task exists yet to block it, per FR-006).

**US5 — Resize the two panes via a draggable divider**
1. Drag the divider to a new split. Confirm both panes resize live.
2. Reload the browser. Confirm the same split is restored (`localStorage`).
3. Clear `localStorage` (or open in a fresh profile) and reload. Confirm a sensible default split (~30/70) renders.

**US6 — View soft-deleted history from any drill level**
1. From any drill depth, click "Deleted Items." Confirm the left pane swaps to the two-section read-only view and the details pane shows genuinely no selectable content (not a create-prompt — a distinct empty state, FR-009).
2. Click the dedicated Back/root control (not the breadcrumb — Deleted Items has no breadcrumb). Confirm it returns to whichever list you were last viewing before Deleted Items, with the details pane correctly defaulted again.
3. From home (`/`), click Deleted Items immediately, then Back. Confirm it falls back to the root Project list (no prior list was ever recorded).

**US7 — Warn before discarding unsaved changes**
1. Edit a field in the details pane without saving, then click a different row's title. Confirm a confirmation prompt appears before navigation.
2. Confirm cancelling the prompt keeps you on the still-edited form; confirming discards and proceeds.
3. Edit a field, then click that same entity's own Save button. Confirm **no** prompt appears (the save-guard exclusion, `contracts/client-state-contract.md`).
4. With no unsaved changes, click a different row, breadcrumb link, "+ New," Deleted Items, and Back in turn. Confirm none of them prompt.
5. With unsaved changes, delete a **different**, unrelated row via its own delete control. Confirm this does **not** trigger the unsaved-changes prompt (delete controls aren't gated by it — see `contracts/client-state-contract.md`).

## Expected end state

`pytest tests/unit tests/integration` is green. All seven user stories above pass. No route under `/projects`, `/projects/{id}/group-tasks/...`, or `/deleted` (the old paths) responds — they're fully removed (FR-027); only `/`, `/panes/...` exist.
