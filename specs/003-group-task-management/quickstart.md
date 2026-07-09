# Quickstart: Validating Group-task Management

This is a validation guide, not an implementation spec — see [data-model.md](./data-model.md) for entity/rule detail and [contracts/](./contracts/) for the exact route contracts this feature adds or changes.

## Prerequisites

- Same environment as 001/002: Python 3.12 venv, dependencies installed.
- `alembic upgrade head` applied, including this feature's new migration (adds `group_task` table + its indexes).

## Setup

```bash
uvicorn app.main:app --reload
```

## Automated validation

```bash
pytest tests/unit tests/integration
```

Expected new/changed test coverage:

- `tests/unit/test_group_task_service.py` — `serial_num` auto-assignment/reuse scoped per `project_id`, title/serial_num uniqueness scoped per `project_id` (incl. the same title/serial_num succeeding under a *different* Project), no-op same-value `serial_num` edit, date ordering, free-form status transitions, blank/whitespace title and description rejection (FR-008a).
- `tests/unit/test_project_service.py` — new cases: `soft_delete_project` rejects when active Group-tasks exist, succeeds once none remain, succeeds unchanged when there never were any.
- `tests/integration/test_group_task_routes.py` — full HTTP flows for all six user stories, including: `HX-Redirect` targets on create/edit/delete pointing at the parent Project's detail page; the OOB `#form-errors` fragment on validation failure; 404 on every nested route (list embedding, create, detail, edit, delete) when the parent Project is missing or soft-deleted, independent of the Group-task's own state (FR-015a).
- `tests/integration/test_projects_routes.py` — new cases: `DELETE /projects/{id}` returns the `#page-errors` OOB rejection fragment (200, no `HX-Redirect`) when active Group-tasks exist, and succeeds as before once they don't; `/deleted` (not `/projects/deleted`) serves the relocated view.

## Manual validation scenarios

**US1 — Create a Group-task and see it under its Project**
1. Open an active Project's detail page (`/projects/{id}`), follow "New group-task".
2. Create one with only title + description. Confirm it lands back on `/projects/{id}` and appears in the nested list with serial_num 0, status "new".
3. Create a second Group-task under a *different* Project using the exact same title. Confirm it succeeds (per-Project scoping).

**US2 — A Project cannot be deleted while it has active Group-tasks**
1. With at least one active Group-task under a Project, attempt to delete that Project from its detail page.
2. Confirm the deletion is rejected in place (no navigation), and the message "Cannot delete: this project still has active group-tasks" (or equivalent) appears in the page's error area.
3. Soft-delete the Group-task, then retry deleting the Project. Confirm it now succeeds and redirects to `/projects`.

**US3 — View a Group-task's full details**
1. From a Project's nested list, open a Group-task's detail page.
2. Confirm every field is shown (including description and notes, absent from the nested list row), a link back to the parent Project, an Edit link, and an empty `#page-errors` container in the page source.

**US4 — Edit a Group-task's fields**
1. Edit an existing Group-task's `serial_num` to a value already used by another active Group-task in the *same* Project — confirm rejection.
2. Edit it to a value already used by an active Group-task in a *different* Project — confirm success (no false conflict).
3. Edit its own current `serial_num` back to itself — confirm success (no-op, not a conflict).

**US5 — Soft-delete a Group-task from its own detail page**
1. Open a Group-task's detail page, trigger delete, confirm the `hx-confirm` dialog, confirm on success the browser lands on the parent Project's detail page.
2. Confirm the Group-task no longer appears in the nested list and its own detail URL now 404s.
3. Confirm no delete control exists in the Project's nested list row itself.

**US6 — Relocated Deleted Items view**
1. Follow the app's existing "Deleted items" link; confirm it now points at `/deleted` and loads successfully.
2. Confirm soft-deleted Projects still appear in a "Deleted Projects" section exactly as before.
3. Soft-delete Group-tasks under two different Projects; confirm a "Deleted Group-tasks" section lists them grouped by parent Project (ascending by parent `serial_num`), each row showing its own `serial_num`/title plus its parent's `serial_num`/title, plain text, no links.
4. Soft-delete one of those parent Projects too (after resolving any other active Group-tasks under it, per US2). Confirm the already-deleted Group-task's entry still correctly identifies that parent by name/number.

**Cross-cutting: stale/direct navigation 404s (FR-015a)**
1. Note a Group-task's URL, then soft-delete its parent Project's other Group-tasks and soft-delete the Project itself.
2. Attempt to open that Group-task's detail, edit, and delete URLs directly, and attempt `POST` to its create-page URL under the same now-deleted `project_id`. Confirm every one 404s.

## Expected end state

`pytest tests/unit tests/integration` is green, all six user stories and the cross-cutting FR-015a/FR-008a scenarios above pass, and Project's own create/list/edit/detail behavior (minus the two retrofit changes documented here) is unchanged from 002 (no regression).
