# Quickstart: Validating the Project Management Slice

This is a validation guide, not an implementation spec — see [data-model.md](./data-model.md) for field/rule details and [contracts/projects-routes.md](./contracts/projects-routes.md) for routes.

This slice targets a local venv only — Podman containerization and container-vs-venv `DATABASE_URL` verification are deferred to Stage 5 and are not covered here.

## Prerequisites

- Python 3.12 environment with project dependencies installed (FastAPI, SQLModel, Alembic, Jinja2, pytest — see research.md for version rationale).
- No `DATABASE_URL` env var needs to be set for local dev — it defaults to `sqlite:///./data/strata.db` (gitignored). Delete `data/strata.db` to start from a clean slate if needed.

## Setup

```bash
# from repo root, once app/ and alembic/ exist
alembic upgrade head          # creates the `project` table (generated via --autogenerate from app/models.py, reviewed before commit)
uvicorn app.main:app --reload
```

Open `http://localhost:8000/projects` — should show an empty active project list (no error state, per the "empty list" edge case).

## Automated validation

```bash
pytest tests/unit                 # serial_num assignment/reuse, uniqueness, date-ordering, status transitions (R1-R6)
pytest tests/integration           # full HTTP flows for US1-US4, incl. HX-Redirect success path and OOB error-fragment failure path
```

Both use the isolated test DB wired in `tests/conftest.py` — neither ever touches `./data/strata.db`.

## Manual validation scenarios (one per user story)

**US1 — Create and list projects**
1. From `/projects`, navigate to `/projects/new` (a dedicated page, not a modal/fragment). Create a project with only title + description filled in. Confirm the browser is redirected (via `HX-Redirect`) back to `/projects` and the project appears with `serial_num = 0`, `status = new`.
2. Create a second project. Confirm `serial_num = 1`.
3. Attempt to create a project with the same title as an existing active project. Confirm the page does **not** navigate away, the response is `200` (check devtools network tab, not a 4xx), the error message appears in the `#form-errors` container, and the values you typed are still in the form fields.
4. Attempt to submit the create form with title or description blank. Confirm the same in-place rejection behavior.

**US2 — View project details**
1. Open a project's detail view from the list. Confirm every field is shown, including blank optional fields (`start_date`, `finished_date`, `notes`) rendered as empty rather than causing an error.

**US3 — Edit project details**
1. From a project's detail or list row, navigate to `/projects/{id}/edit`. Edit its `status` directly from `new` to `archived`. Confirm it's accepted with no intermediate step and redirects back to `/projects`.
2. With two active projects at `serial_num` 3 and 5, edit the second one's `serial_num` to 3. Confirm the edit page stays put with an in-place error via `#form-errors`, and that the project's `serial_num` remains 5 (verify on `/projects`).
3. Set `finished_date` earlier than `start_date`. Confirm the same in-place rejection.
4. Edit `notes` (including a long, multi-paragraph value, since it has no `max_length`) and confirm the change persists across a page reload.
5. Soft-delete a project titled "Website Redesign", then create or rename another active project to "Website Redesign". Confirm this succeeds (soft-deleted titles aren't reserved).

**US4 — Soft-delete and Deleted Items**
1. From `/projects`, trigger the delete control on a row (an active project, including one in `archived` status). Confirm the `<tr>` disappears from the list in place with no page reload/navigation, and that the project's detail URL now 404s.
2. Open `/projects/deleted`. Confirm the project appears there with all fields intact and `serial_num` frozen at its last active value.
3. Confirm no edit or restore control is present anywhere on the Deleted Items view.
4. With multiple soft-deleted projects, confirm the Deleted Items view lists them ascending by `serial_num`.

## Expected end state

All eight items above pass, `pytest` is green, and the active list plus Deleted Items view together account for every project ever created, matching SC-002, SC-003, and SC-006.
