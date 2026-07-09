# Implementation Plan: Group-task Management

**Branch**: `003-group-task-management` | **Date**: 2026-07-08 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/003-group-task-management/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Deliver `GroupTask` as the second vertical slice of Strata's hierarchy: a SQLModel-backed table nested under `Project` via a required, immutable `project_id`, an Alembic migration adding composite partial-unique indexes scoped by parent Project (not global, a step up from Project's own single-column indexes), a new FastAPI router mounted at `/projects/{project_id}/group-tasks` covering create/detail/edit/delete, a nested read-only list embedded on the Project detail page, and a relocated `/deleted` view aggregating soft-deleted Projects and soft-deleted Group-tasks in two labeled sections. This slice also retrofits `soft_delete_project` to reject deletion while active Group-tasks exist, surfacing the rejection through the `_page_errors.html` OOB container that `002-relocate-project-delete` built specifically for this purpose. The primary technical challenges are (1) scoping every uniqueness/ordering invariant to `project_id` instead of globally, (2) a cross-cutting "resolve active parent Project or 404" check that must run identically at the top of every nested Group-task route per FR-015a, and (3) the `/deleted` view needing to identify a Group-task's parent Project by identity even in the edge case where that parent has *also* since been soft-deleted.

## Technical Context

**Language/Version**: Python 3.12 (unchanged from 001/002)

**Primary Dependencies**: FastAPI, SQLModel (SQLAlchemy 2.x + Pydantic v2), Jinja2, HTMX (vendored, `app/static/htmx.min.js`), Pico.css (vendored, `app/static/pico.min.css`, added in 002), Alembic

**Storage**: SQLite, same `DATABASE_URL`-driven engine as 001/002; this slice adds one new table, `group_task`, with a required foreign key to `project.id` (no `ON DELETE CASCADE` — hard delete never happens in this system, so cascade semantics are moot; default RESTRICT/no-action is correct)

**Testing**: pytest + httpx `TestClient`, same `tests/conftest.py` isolated-engine fixtures as 001/002; new `tests/unit/test_group_task_service.py` and `tests/integration/test_group_task_routes.py`, plus extensions to the existing Project test files for the retrofit

**Target Platform**: Local venv for this slice, same as 001/002. Podman containerization remains outside spec-kit-tracked scope (verified manually per README, not part of this plan)

**Project Type**: Single web-service project; extends the existing `app/` package — no new top-level project or service boundary

**Performance Goals**: Not throughput-sensitive (single user, unchanged from 001); nested-list and detail interactions must feel instantaneous up to the volumes in Scale/Scope below

**Constraints**: Every uniqueness/ordering invariant that was global in Project (title uniqueness, `serial_num` uniqueness/auto-assignment) is now scoped to `(project_id, ...)` for Group-task (spec FR-004 through FR-007); a Project's own soft-delete gains a new precondition (zero active Group-tasks, FR-016/FR-017); every nested Group-task route must independently verify its parent Project is active before touching the Group-task, returning 404 otherwise (FR-015a); title/description reject blank-or-whitespace-only values in addition to length limits (FR-008a); cross-Project reassignment of a Group-task is permanently out of scope (FR-030) — `project_id` is write-once at creation, never part of the edit form

**Scale/Scope**: Up to ~200 active Group-tasks per Project (per spec SC-006); Group-task is the only new entity — Task remains entirely out of scope (FR-029)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is still the unpopulated template — unchanged since 001 and 002, no ratified principles exist to gate this plan against. This plan introduces nothing that conflicts with the template's placeholder guidance, and follows the same structural conventions already established by 001 (package layout, service-layer validation, autogenerate-then-review migrations) and 002 (OOB error containers, `HX-Redirect` on success).

**Recommendation carried over from 001**: still worth running `/speckit-constitution` at some point, not a blocker here either.

*Post-Phase-1 re-check*: No new violations introduced by data-model.md, contracts/, or quickstart.md. Still no ratified constitution to gate against.

## Project Structure

### Documentation (this feature)

```text
specs/003-group-task-management/
├── plan.md                              # This file (/speckit-plan command output)
├── research.md                          # Phase 0 output
├── data-model.md                        # Phase 1 output
├── quickstart.md                        # Phase 1 output
├── contracts/                           # Phase 1 output
│   ├── group-tasks-routes.md            # New nested Group-task routes
│   └── projects-retrofit-contract.md    # Changed Project routes (detail, delete, deleted→/deleted)
└── tasks.md                             # Phase 2 output (/speckit-tasks — NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
app/
├── main.py                          # + mount group_tasks.router alongside projects.router
├── database.py                      # unchanged
├── models.py                        # + GroupTask table (Status enum reused, no new enum)
├── routers/
│   ├── projects.py                  # detail: also fetches active Group-tasks for the nested list
│   │                                 # delete: catches new cascade-block rejection, renders _page_errors OOB (200) instead of always succeeding
│   │                                 # deleted-items route relocated out of this router (see below)
│   └── group_tasks.py                # NEW: APIRouter(prefix="/projects/{project_id}/group-tasks"); create/detail/edit/update/delete;
│                                      # defines get_active_project_or_404(project_id: int, session=Depends(get_session)) -> Project,
│                                      # a single shared FastAPI dependency; every route below takes
│                                      # project: Project = Depends(get_active_project_or_404) instead of re-checking inline (FR-015a)
├── routers/deleted.py                # NEW (or a top-level route in main.py — see research.md): GET /deleted, aggregates
│                                      # list_deleted_projects() + list_deleted_group_tasks_grouped_by_project()
├── static/                           # unchanged (htmx.min.js, pico.min.css)
└── templates/
    ├── base.html                     # + update the one "Deleted items" link to /deleted
    ├── deleted.html                  # RELOCATED (was projects/deleted.html): two sections,
    │                                 # "Deleted Projects" (unchanged behavior) + "Deleted Group-tasks" (grouped by parent)
    ├── projects/
    │   ├── list.html                 # unchanged
    │   ├── detail.html                # + nested Group-task table (via _group_task_row.html), + "New group-task" link
    │   ├── new.html / edit.html       # unchanged
    ├── group_tasks/
    │   ├── new.html                   # NEW: dedicated create page, wraps _group_task_form.html, scoped to one project_id
    │   ├── detail.html                # NEW: all fields incl. description/notes, link back to parent Project, Edit link,
    │   │                              # sole delete control, + _page_errors.html include (future Task-rejection area, FR-022)
    │   └── edit.html                  # NEW: dedicated edit page, wraps _group_task_form.html, populated
    └── partials/
        ├── _project_row.html          # unchanged
        ├── _project_form.html         # unchanged
        ├── _form_errors.html          # unchanged, reused as-is by _group_task_form.html
        ├── _page_errors.html          # unchanged, reused as-is by group_tasks/detail.html and projects/detail.html
        ├── _group_task_row.html       # NEW: nested-list row — serial_num, title, status, start_date, finished_date only
        │                              # (no description/notes per FR-018), link to detail + separate Edit link, no delete control
        └── _group_task_form.html      # NEW: shared create/edit form body, same pattern as _project_form.html;
                                       # project_id is never a form field — it's always taken from the URL path
                                       # (hx-post="/projects/{{ project_id }}/group-tasks" / hx-put=".../{{ group_task.id }}")

alembic/versions/
└── <new revision>_create_group_task_table.py   # `alembic revision --autogenerate`, then hand-reviewed
                                                  # (composite partial unique indexes + FK need verification, per 001's research.md precedent)

tests/
├── unit/
│   ├── test_project_service.py       # + cascade-block tests (soft_delete_project rejects/accepts based on active Group-tasks)
│   └── test_group_task_service.py    # NEW: mirrors test_project_service.py, project_id-scoped variants of every rule,
│                                     # + blank/whitespace title/description tests (FR-008a)
└── integration/
    ├── test_projects_routes.py       # + retrofit tests (blocked delete renders page-errors OOB; /deleted relocation)
    └── test_group_task_routes.py    # NEW: full HTTP flows for all six user stories, incl. parent-404 checks (FR-015a)
```

**Structure Decision**: Extends the existing single-project `app/` package from 001/002 — no new project, service boundary, or build unit. `GroupTask` gets its own router (`app/routers/group_tasks.py`) rather than folding its routes into `projects.py`, since the nested path (`/projects/{project_id}/group-tasks/...`) and its nesting-specific concerns are cleanly separable and this mirrors the one-router-per-entity convention already set by `projects.py`. FR-015a's "resolve active parent Project or 404" check exists in exactly one place among the five nested Group-task routes: a FastAPI dependency function, `get_active_project_or_404`, declared once in `app/routers/group_tasks.py` and wired via `Depends(...)` into all five route signatures — none of them reimplements the check inline, so it cannot drift between routes if changed later. The nested list itself is embedded on `projects.py`'s own `GET /projects/{id}` route, which isn't a `group_tasks.py` route and so doesn't use this dependency; it already performs its own not-found handling via the existing `services.get_active_project` lookup, unchanged from 001 (see contracts/group-tasks-routes.md). The relocated `/deleted` view is a top-level route (own small router or a function in `main.py`, decided in research.md) since it no longer belongs under `/projects` at all — it aggregates two entities and its URL reflects that. Templates keep the established split: `templates/group_tasks/` for full pages (mirroring `templates/projects/`) and new partials alongside the existing ones in `templates/partials/`, reusing `_form_errors.html` and `_page_errors.html` unchanged rather than cloning them, since both are already entity-agnostic (`#form-errors` / `#page-errors` fixed containers with no Project-specific markup). `_group_task_form.html` carries no `project_id` field of any kind — every create/edit route is already nested under `/projects/{project_id}/group-tasks/...`, so the form's own `hx-post`/`hx-put` URL is the sole source of `project_id`. `tests/` continues to mirror `app/` by layer.

## Complexity Tracking

*No constitution gates are currently ratified (see Constitution Check above), so there is nothing to justify here.*
