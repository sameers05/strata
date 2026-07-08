---

description: "Task list template for feature implementation"
---

# Tasks: Project Management

**Input**: Design documents from `/specs/001-project-management/` (plan.md, research.md, data-model.md, contracts/projects-routes.md, quickstart.md, spec.md)

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/projects-routes.md, quickstart.md — all present

**Tests**: Included — unit tests (Phase 4) and integration tests (Phase 7) are both explicitly requested for this feature.

**Organization**: Per explicit user instruction, this feature is organized by **technical layer/phase**, not by user story, and phases must appear in the exact order below:

1. Scaffolding
2. Model + migration
3. Service-layer business logic
4. Service-layer unit tests (written immediately after Phase 3)
5. Routes
6. Templates + HTMX wiring
7. Integration/route-level tests (written immediately after Phase 6)

Each task is still tagged `[US#]` where it maps to a specific user story from spec.md (US1 Create & list, US2 View detail, US3 Edit, US4 Soft-delete & Deleted Items), for traceability — but tasks are grouped by phase, not by story, so a phase may (and generally does) contain tasks from several stories.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no unresolved dependency on another incomplete task in this list)
- **[Story]**: Which user story this task serves (US1–US4), omitted for pure infrastructure/wiring tasks with no single-story owner
- File paths are relative to repo root

## Path Conventions

Single project. `app/` holds the application package, `alembic/` holds migrations, `tests/` mirrors `app/` by layer (`tests/unit/`, `tests/integration/`), per plan.md's Project Structure.

---

## Phase 1: Scaffolding

**Purpose**: Project package skeleton, vendored HTMX + static file serving, DB engine wiring, base layout — everything later phases assume exists.

- [X] T001 Initialize the Python package: create `app/__init__.py`, `app/routers/__init__.py`, and a `pyproject.toml` (or `requirements.txt`) pinning `fastapi`, `sqlmodel`, `alembic`, `jinja2`, `python-multipart`, `uvicorn`, `pytest`, `httpx`
- [X] T002 [P] Vendor HTMX: add a pinned `app/static/htmx.min.js`; do not reference any CDN URL anywhere in the templates
- [X] T003 [P] Implement `app/database.py`: SQLModel engine + `get_session()` FastAPI dependency, reading `DATABASE_URL` from the environment and defaulting to `sqlite:///./data/strata.db`; ensure the `data/` directory is created at startup if missing
- [X] T004 [P] Add `data/` to `.gitignore` at repo root if not already covered
- [X] T005 [P] Create `app/templates/base.html`: layout shell with a content block and `<script src="/static/htmx.min.js"></script>`
- [X] T006 Implement `app/main.py`: instantiate `FastAPI()`, configure Jinja2 templates pointed at `app/templates`, mount `StaticFiles` at `/static` from `app/static` (depends on: T002, T003, T005)

**Checkpoint**: App boots (even with no routes yet) and serves the vendored HTMX file from `/static/htmx.min.js`.

---

## Phase 2: Model + migration

**Purpose**: The `Project` SQLModel table and its reviewed Alembic migration, including the two partial unique indexes the whole feature's validation logic depends on.

- [X] T007 Define `app/models.py`: `Project` SQLModel table and a `Status` string enum (`new`, `in-progress`, `complete`, `blocked`, `deferred`, `archived`) with fields `id`, `serial_num`, `title` (≤~200 chars), `description` (≤~2000 chars), `start_date`, `finished_date`, `notes` (plain `str`, no `max_length`), `status` (default `new`), `deleted` (default `False`) — per data-model.md (depends on: T001)
- [X] T008 Initialize Alembic (`alembic init alembic`) and wire `alembic/env.py` to import `app.database`'s engine and `SQLModel.metadata` as the migration target (depends on: T003, T007)
- [X] T009 Generate the initial migration: `alembic revision --autogenerate -m "create project table"` (depends on: T008)
- [X] T010 Manually review and clean up the generated `alembic/versions/..._create_project.py`: verify column types/nullability match models.py, and add the two partial unique indexes — on `title` and on `serial_num` — each scoped `WHERE deleted = false`, since autogenerate does not reliably produce conditional indexes (depends on: T009)
- [X] T011 Apply and verify the migration: run `alembic upgrade head` against the local dev DB and confirm the `project` table and both partial indexes exist (depends on: T010)

**Checkpoint**: `alembic upgrade head` runs clean; the `project` table and its two partial unique indexes exist in `./data/strata.db`.

---

## Phase 3: Service-layer business logic

**Purpose**: All cross-row validation and mutation logic lives here, in one place, before any route or test touches it — per research.md, none of these rules (title/serial_num uniqueness, date ordering, free-form status) can be expressed as plain SQLModel/Pydantic field validators since they require querying sibling rows.

- [X] T012 [US1] Implement `create_project(...)` in `app/services.py`: auto-assign `serial_num` = (max active `serial_num`) + 1, or 0 if none exist (R1); enforce active-scoped title uniqueness (R4); enforce title/description length limits (R5); enforce `finished_date` not before `start_date` when both present (R3); default `status="new"`, `deleted=False` (depends on: T007)
- [X] T013 [US3] Implement `update_project(...)` in `app/services.py`: enforce active-scoped `serial_num` uniqueness, treating an edit to the project's own current value as a no-op success rather than a conflict (R2); enforce active-scoped title uniqueness (R4); enforce date ordering (R3); enforce length limits (R5); allow `status` to move to any of the six values with no restriction (R6) (depends on: T012)
- [X] T014 [US4] Implement `soft_delete_project(...)` in `app/services.py`: set `deleted=True` without recomputing or ever touching `serial_num` again (R7); this is the only delete path — there is no hard-delete function anywhere (R8); raise a not-found condition if the project is missing or already soft-deleted (depends on: T012)
- [X] T015 Implement `list_active_projects()`, `get_active_project(id)`, and `list_deleted_projects()` query helpers in `app/services.py`, both list queries ordered ascending by `serial_num` (depends on: T007)
- [X] T016 Define a `ProjectValidationError` exception (carrying field → message pairs) in `app/services.py`, raised by T012–T014 on every rejected rule, to be caught by the routers added in Phase 5 (depends on: T007)

**Checkpoint**: All business rules (R1–R8) are implemented and importable, with no route or template depending on them yet.

---

## Phase 4: Service-layer unit tests

**Purpose**: Written immediately after Phase 3, before any route exists, to lock down every rule in research.md's testing-strategy list against the service functions directly.

- [X] T017 Create `tests/conftest.py`: an isolated test DB fixture (temp-file or `:memory:` SQLite via `StaticPool`) yielding a fresh `Session` per test; must never open or touch `./data/strata.db` (depends on: T003, T007)
- [X] T018 [US1] `tests/unit/test_project_service.py::test_serial_num_assignment_and_reuse` — first project ever gets `serial_num=0`; next gets `max+1`; soft-deleting the project holding the current max `serial_num` lets a subsequently created project reuse that number (depends on: T012, T014, T017)
- [X] T019 [US3] `test_serial_num_uniqueness_conflict_and_noop` — editing a project's `serial_num` to one already used by another *active* project is rejected and the original value is retained; editing it to its own current value succeeds as a no-op (depends on: T013, T017)
- [X] T020 [US1][US3] `test_title_uniqueness_active_scope` — creating or editing to a title already used by another active project is rejected; a title matching a *soft-deleted* project's title is allowed (depends on: T012, T013, T014, T017)
- [X] T021 [US1][US3] `test_date_ordering_validation` — a `finished_date` earlier than `start_date` is rejected on both create and edit; `start_date`/`finished_date` may each be set or cleared independently (depends on: T012, T013, T017)
- [X] T022 [US3] `test_status_free_form_transitions` — any status value can move directly to any other, including `new` → `archived` with no intermediate step (depends on: T013, T017)
- [X] T023 [US4] `test_soft_delete_visibility_and_frozen_serial_num` — a soft-deleted project is excluded from `list_active_projects`/`get_active_project`, appears in `list_deleted_projects` with its `serial_num` frozen at its last active value (depends on: T014, T015, T017)
- [X] T024 [US1][US3] `test_length_limits` — a title beyond ~200 chars or a description beyond ~2000 chars is rejected on create and edit (depends on: T012, T013, T017)

**Checkpoint**: `pytest tests/unit` is green and exercises every rule in R1–R8 before a single HTTP route exists.

---

## Phase 5: Routes

**Purpose**: `app/routers/projects.py` — thin HTTP layer over the Phase 3 service functions, implementing the exact success/failure contract from contracts/projects-routes.md (HX-Redirect on success, 200 + OOB error fragment on validation failure, row-level delete). Routes reference templates from Phase 6 by name; they are not renderable end-to-end until Phase 6 exists, which is expected given the requested phase order.

- [ ] T025 [US1] `GET /projects` — call `list_active_projects`, render `projects/list.html` (must render an empty-state, never an error, when there are no active projects) (depends on: T015)
- [ ] T026 [US1] `GET /projects/new` — render `projects/new.html` with a blank form (depends on: none new)
- [ ] T027 [US1] `POST /projects` — call `create_project`; on success return `200` with `HX-Redirect: /projects`; on `ProjectValidationError` return `200` with only the OOB `#form-errors` fragment, leaving the submitted form untouched (depends on: T012, T016, T026)
- [ ] T028 [US2] `GET /projects/{id}` — render `projects/detail.html` showing every field, including blank optionals; `404` if missing or soft-deleted (depends on: T015)
- [ ] T029 [US3] `GET /projects/{id}/edit` — render `projects/edit.html` pre-filled; `404` if missing or soft-deleted (depends on: T015)
- [ ] T030 [US3] `PUT /projects/{id}` — call `update_project`; same success/failure contract as T027 (depends on: T013, T016, T029)
- [ ] T031 [US4] `DELETE /projects/{id}` — call `soft_delete_project`; `200` with empty body on success (HTMX removes the row via `hx-swap="delete"` regardless of body); `404` if already missing/soft-deleted (depends on: T014)
- [ ] T032 [US4] `GET /projects/deleted` — render `projects/deleted.html`, strictly read-only, ascending by `serial_num` (depends on: T015)
- [ ] T033 Wire the router into the app: `app.include_router(projects.router)` in `app/main.py` (depends on: T006, T025–T032)

**Checkpoint**: All 8 routes exist and call into the correct service functions with the correct success/failure response shape; full end-to-end rendering requires Phase 6.

---

## Phase 6: Templates + HTMX wiring

**Purpose**: The Jinja2 templates and partials the Phase 5 routes render, implementing the fixed HTMX convention from research.md exactly: shared row/form partials, OOB error banner, row-level `hx-delete`.

- [ ] T034 [P] [US4] `app/templates/partials/_project_row.html` — a single `<tr>` rendering every `Project` field, with the delete control using `hx-delete="/projects/{id}"`, `hx-target="closest tr"`, `hx-swap="delete"` (depends on: T007)
- [ ] T035 [P] `app/templates/partials/_form_errors.html` — the `#form-errors` OOB fragment (`hx-swap-oob="true"`) rendering a list of validation messages (depends on: none new)
- [ ] T036 [US1][US3] `app/templates/partials/_project_form.html` — shared form body (title, description, start_date, finished_date, notes, status select, serial_num), parameterized so it can `hx-post` (create) or `hx-put` (edit), including the always-present `#form-errors` container placeholder (depends on: T035)
- [ ] T037 [US1] `app/templates/projects/list.html` — extends `base.html`; iterates active projects via `_project_row.html`; empty-state copy; link to `/projects/new` (depends on: T034, T005)
- [ ] T038 [P] [US2] `app/templates/projects/detail.html` — extends `base.html`; shows every field including blank optionals rendered as empty, not an error; link to edit (depends on: T005)
- [ ] T039 [P] [US1] `app/templates/projects/new.html` — extends `base.html`; includes `_project_form.html` configured to `hx-post` to `/projects` (depends on: T036)
- [ ] T040 [P] [US3] `app/templates/projects/edit.html` — extends `base.html`; includes `_project_form.html` pre-filled, configured to `hx-put` to `/projects/{id}` (depends on: T036)
- [ ] T041 [P] [US4] `app/templates/projects/deleted.html` — extends `base.html`; read-only table reusing row rendering minus the delete control; ascending by `serial_num`; no edit/restore control anywhere on the page (depends on: T005)

**Checkpoint**: Every route from Phase 5 now renders end-to-end; manual browser testing of all four user stories (quickstart.md) is possible.

---

## Phase 7: Integration/route-level tests

**Purpose**: Written immediately after Phase 6, exercising the full HTTP stack (FastAPI `TestClient`/`httpx.ASGITransport`) for all four user stories, including the `HX-Redirect` success path and the OOB error-fragment failure path that unit tests can't observe (those only exist at the HTTP layer).

- [ ] T042 [US1] `tests/integration/test_projects_routes.py::test_us1_create_and_list_flow` — `POST /projects` success returns `HX-Redirect: /projects`; `serial_num` is 0 then 1 across two creates; `GET /projects` lists them ascending; a duplicate title or a blank required field returns `200` with the OOB error fragment and no redirect (depends on: T027, T025, T017)
- [ ] T043 [US2] `test_us2_view_detail_flow` — `GET /projects/{id}` shows every field, including blank optionals, with no error (depends on: T028)
- [ ] T044 [US3] `test_us3_edit_flow` — `PUT` moving `status` from `new` directly to `archived` succeeds and redirects; a `serial_num` conflict returns `200` + OOB fragment and leaves the original value unchanged; `finished_date` before `start_date` is rejected the same way; a `notes` edit persists across a subsequent `GET`; renaming an active project to a soft-deleted project's former title succeeds (depends on: T030, T028, T031)
- [ ] T045 [US4] `test_us4_soft_delete_and_deleted_items_flow` — `DELETE` removes the project from `/projects` and makes `GET /projects/{id}` 404; `GET /projects/deleted` shows it with its `serial_num` frozen; multiple soft-deletes appear ascending by `serial_num`; no edit/restore route is reachable for a deleted item (depends on: T031, T032, T025, T028)
- [ ] T046 Execute quickstart.md's manual validation scenarios end-to-end as a final sanity pass (depends on: T042–T045)

**Checkpoint**: `pytest tests/unit tests/integration` is green; quickstart.md's manual scenarios all pass; the slice is complete.

---

## Dependencies & Execution Order

This feature is one vertical slice built as a single linear pipeline, not independently-deliverable per-story increments — the phase order below is fixed by explicit instruction and must not be reordered or parallelized across phases:

1. **Phase 1 (Scaffolding)** — no dependencies, start immediately.
2. **Phase 2 (Model + migration)** — depends on Phase 1 (needs `app/database.py`).
3. **Phase 3 (Service-layer business logic)** — depends on Phase 2 (needs the `Project` model).
4. **Phase 4 (Service-layer unit tests)** — must be written immediately after Phase 3, against Phase 3's functions directly; depends on Phase 3.
5. **Phase 5 (Routes)** — depends on Phase 3 (calls its functions) and Phase 4 having locked the service contract down; templates it renders don't exist until Phase 6.
6. **Phase 6 (Templates + HTMX wiring)** — depends on Phase 5 (routes reference these template names) and Phase 1 (`base.html`).
7. **Phase 7 (Integration/route-level tests)** — must be written immediately after Phase 6, once routes render end-to-end; depends on Phases 5 and 6.

### Within-phase parallel opportunities

- Phase 1: T002, T003, T004, T005 touch different files and can proceed in parallel once T001 exists.
- Phase 2: strictly sequential (each step operates on the migration produced by the last).
- Phase 3: strictly sequential — all functions live in the single file `app/services.py`.
- Phase 4: strictly sequential — all tests live in the single file `tests/unit/test_project_service.py`; write them in order but each test is logically independent.
- Phase 5: strictly sequential — all routes live in the single file `app/routers/projects.py`.
- Phase 6: T034, T035 can start in parallel; T038, T039, T040, T041 touch different files and can proceed in parallel once their respective dependencies (T005/T036) are done.
- Phase 7: strictly sequential — all tests live in the single file `tests/integration/test_projects_routes.py`.

## Parallel Example: Phase 1

```bash
# After T001 (package skeleton) completes, launch together:
Task: "Vendor HTMX into app/static/htmx.min.js"
Task: "Implement app/database.py engine/session + DATABASE_URL handling"
Task: "Add data/ to .gitignore"
Task: "Create app/templates/base.html layout shell"
```

## Parallel Example: Phase 6

```bash
# After T005 (base.html) and T036 (_project_form.html) are done, launch together:
Task: "Create app/templates/projects/detail.html"
Task: "Create app/templates/projects/new.html"
Task: "Create app/templates/projects/edit.html"
Task: "Create app/templates/projects/deleted.html"
```

## Implementation Strategy

Because this slice delivers one entity (`Project`) end-to-end rather than several independently-shippable stories, there is no meaningful partial-story MVP the way a multi-story feature would have one — the seven phases together **are** the MVP. The closest thing to an incremental checkpoint is:

1. Complete Phases 1–2 → schema exists, nothing to demo yet.
2. Complete Phases 3–4 → business rules are proven correct in isolation (`pytest tests/unit` green), still nothing to click on.
3. Complete Phases 5–6 → the whole feature is demoable in a browser for the first time; run quickstart.md's manual scenarios.
4. Complete Phase 7 → the full automated safety net (`pytest tests/unit tests/integration`) is in place alongside the manual pass.

There is no supported path to stop after, say, Phase 5 alone and call US1 "done," since routes aren't renderable until Phase 6's templates exist — this is a deliberate consequence of the requested phase grouping (technical layer, not per-story).

## Notes

- `[P]` tasks = different files, no unresolved dependency on another incomplete task
- `[US#]` labels are for traceability back to spec.md's user stories; they do not imply story-based delivery order here — phase order governs
- Tests (Phases 4 and 7) are written immediately *after* the implementation they cover, not before — Phase 4 targets Phase 3's already-implemented service functions, and Phase 7 targets Phase 5/6's already-implemented, already-renderable routes. This is not TDD red-green; each phase's tests should pass against existing code as soon as they're written, and any failure indicates a bug in the prior phase, not an expected pre-implementation red state
- Commit after each task or logical group
- Stop at any phase checkpoint to validate before continuing
