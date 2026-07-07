# Implementation Plan: Project Management

**Branch**: `001-project-management` | **Date**: 2026-07-07 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-project-management/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Deliver the `Project` entity as a complete, standalone vertical slice of Strata: a SQLModel-backed table with an Alembic migration, a FastAPI router exposing list/detail/create/edit/soft-delete routes, and server-rendered HTMX + Jinja2 templates for the active project list, detail view, create/edit forms, and a read-only Deleted Items view. No Group-task or Task concepts are introduced. The primary technical challenges are enforcing two cross-row invariants outside of what Pydantic/SQLModel field validators can express — active-scoped title uniqueness and active-scoped `serial_num` uniqueness/auto-assignment — and doing so safely under SQLite's concurrency model.

## Technical Context

**Language/Version**: Python 3.12 (LTS-style ecosystem support window; see research.md for why not 3.14, which is already installed on the host)

**Primary Dependencies**: FastAPI, SQLModel (SQLAlchemy 2.x + Pydantic v2), Jinja2, HTMX (vendored, served from `app/static/` — no CDN dependency), Alembic

**Storage**: SQLite, path from `DATABASE_URL` env var, defaulting to `sqlite:///./data/strata.db` (gitignored, inside repo) for local dev; test suite uses an isolated DB (separate file or in-memory, fresh per run) and must never touch `./data/strata.db`

**Testing**: pytest + httpx `ASGITransport`/`TestClient` for route-level tests, plus direct SQLModel session tests for repository/service logic; isolated test DB wired via `tests/conftest.py` fixtures

**Target Platform**: Local venv for this slice (Linux dev host). Rootless Podman containerization, and verifying `DATABASE_URL` behavior inside vs. outside a container, are explicitly **deferred to Stage 5** and out of scope for this plan.

**Project Type**: Single web-service project, package layout from the start (not a flat `main.py`) — FastAPI serving both HTMX-driven fragments/redirects and full Jinja2 pages, no separate frontend build

**Performance Goals**: Not throughput-sensitive (single user); list/detail interactions must feel instantaneous (no perceptible delay per SC-001) up to the expected data volume

**Constraints**: Single-user, no authentication (per FR-027 and Assumptions); no hard delete ever (FR-017); all cross-row validation (title/serial_num uniqueness, date ordering) must be enforced at the service layer since SQLModel/Pydantic field validators cannot see sibling rows; `notes` is a plain `str` with no `max_length` (TEXT affinity, genuinely unbounded per spec)

**Scale/Scope**: Up to ~500 active projects (per SC-004); one entity (`Project`) only — Group-task and Task are explicitly out of scope for this slice

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is still the unpopulated template (no principles have been ratified for this project yet). There is therefore no ratified gate to check this plan against, and this plan does not introduce anything that conflicts with the template's placeholder guidance (library-first, test-first, simplicity are all consistent with the single-project structure chosen below).

**Recommendation**: run `/speckit-constitution` before or alongside implementation to ratify real principles (e.g., test-first for validation logic, since the uniqueness/ordering rules in this slice are exactly the kind of business logic that benefits from tests written first). Not a blocker for this plan.

*Post-Phase-1 re-check*: No new violations introduced by data-model.md, contracts/, or quickstart.md. Still no ratified constitution to gate against.

## Project Structure

### Documentation (this feature)

```text
specs/001-project-management/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── projects-routes.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
app/
├── main.py                     # app assembly/wiring (FastAPI() instance, router mounting, template env)
├── database.py                 # engine/session handling; reads DATABASE_URL, defaults to sqlite:///./data/strata.db
├── models.py                   # SQLModel definitions (Project, Status enum)
├── routers/
│   └── projects.py             # all Project routes: list, new, create, detail, edit, update, delete, deleted-items
├── static/
│   └── htmx.min.js             # vendored HTMX, served by FastAPI's StaticFiles — no CDN dependency
└── templates/
    ├── base.html                # layout shell, <script src="/static/htmx.min.js">
    ├── projects/
    │   ├── list.html            # full-page list (persistent partial-swap surface)
    │   ├── detail.html
    │   ├── new.html              # dedicated create page, wraps _project_form.html
    │   ├── edit.html              # dedicated edit page, wraps _project_form.html
    │   └── deleted.html          # read-only Deleted Items page
    └── partials/
        ├── _project_row.html     # single <tr>, reused by list.html and the delete response
        └── _project_form.html    # shared form body, reused identically by new.html and edit.html

data/                            # gitignored; holds strata.db for local dev (created at runtime, not committed)

alembic/
├── env.py
└── versions/
    └── 0001_create_project.py   # generated via `alembic revision --autogenerate` from models.py, reviewed/cleaned before applying

tests/
├── conftest.py                      # isolated test DB fixture (separate file or in-memory, fresh per run) — must never touch ./data/strata.db
├── unit/
│   └── test_project_service.py     # serial_num assignment/reuse, title/serial_num uniqueness (incl. no-op same-value edit), date ordering, status free-form transitions
└── integration/
    └── test_projects_routes.py     # full HTTP flows for all four user stories, incl. HX-Redirect on success and oob error-fragment on validation failure
```

**Structure Decision**: Single project (Option 1), package layout (`app/`) from the start rather than a flat `main.py`, since this slice is explicitly the first of several (Group-task, Task to follow) and a package avoids a restructuring pass later. Strata is one FastAPI application serving server-rendered HTML (HTMX + Jinja2) directly — there is no separate frontend build/deploy, so the "web application" split (backend/ + frontend/) does not apply. Templates are split into full pages (`templates/projects/`) and reusable partials (`templates/partials/`) so the row and form markup is defined once and reused identically between full-page renders and any HTMX-returned fragment, per the fixed HTMX convention in research.md. `alembic/` is top-level per its own convention; `tests/` mirrors `app/` by layer (unit for service/model logic, integration for HTTP routes), with an isolated DB that never touches the dev `data/strata.db`. Rootless Podman packaging is deferred to Stage 5 and has no bearing on this structure.

## Complexity Tracking

*No constitution gates are currently ratified (see Constitution Check above), so there is nothing to justify here.*
