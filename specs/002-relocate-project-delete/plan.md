# Implementation Plan: Relocate Project Deletion from List to Detail View

**Branch**: `002-relocate-project-delete` | **Date**: 2026-07-08 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-relocate-project-delete/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Move the Project delete action from the active list row to the project's own detail page, and align `DELETE /projects/{id}`'s success response with the `HX-Redirect: /projects` pattern already used by create/edit, since the detail page can no longer represent a project that has just been deleted. Add a standing, currently-empty page-level error container (`_page_errors.html`) on the detail page so a later cascade-blocking rule (once Group-task exists) can reject a delete and explain why, without further UI work. No model, migration, or business-logic change — `soft_delete_project` remains unconditional per FR-006.

## Technical Context

**Language/Version**: Python 3.12 — unchanged, reusing 001-project-management's stack

**Primary Dependencies**: FastAPI, SQLModel, Jinja2, HTMX (vendored, `app/static/`) — all already in place; no new dependency is introduced by this feature

**Storage**: SQLite via the existing `project` table — no schema or migration change; this feature only changes a route's response headers and two templates

**Testing**: pytest + FastAPI `TestClient`, extending the existing `tests/integration/test_projects_routes.py`; no new unit-test surface since `services.soft_delete_project` itself is untouched

**Target Platform**: Local venv (same as 001-project-management; Podman containerization remains deferred to Stage 5 and is out of scope here)

**Project Type**: Single web-service project — reuses the existing `app/` package from 001-project-management, no new top-level structure

**Performance Goals**: Not applicable — no performance-sensitive change

**Constraints**: Must preserve FR-006's unconditional-success delete semantics exactly; must not alter list/create/edit behavior beyond removing the list row's delete control (FR-001, FR-009); the relocated control and its error-container mechanism must work without a full page reload (FR-004, FR-005)

**Scale/Scope**: Same as 001-project-management (~500 active projects); this feature touches 1 route handler, 1 existing template, 1 removed control, and 1 new partial

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is still the unpopulated template — no ratified principles exist for this project (unchanged from 001-project-management's plan). This feature introduces no new dependency, entity, or architectural pattern beyond what 001 already established, so there is nothing here that could conflict with the template's placeholder guidance.

**Post-Phase-1 re-check**: No new violations introduced by data-model.md, contracts/, or quickstart.md. Still no ratified constitution to gate against.

## Project Structure

### Documentation (this feature)

```text
specs/002-relocate-project-delete/
├── plan.md                          # This file (/speckit-plan command output)
├── research.md                      # Phase 0 output (/speckit-plan command)
├── data-model.md                    # Phase 1 output (/speckit-plan command) — no entity changes
├── quickstart.md                    # Phase 1 output (/speckit-plan command)
├── contracts/
│   └── projects-delete-contract.md  # Phase 1 output — the changed DELETE contract only
└── tasks.md                         # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
app/
├── routers/
│   └── projects.py                  # DELETE /projects/{id} success response: 200 -> 200 + HX-Redirect: /projects (404 path unchanged)
└── templates/
    ├── partials/
    │   ├── _project_row.html        # delete control (hx-delete/-target/-swap/-confirm) removed; title + Edit links remain
    │   └── _page_errors.html        # NEW: OOB page-level error container, id="page-errors", parallel to _form_errors.html
    └── projects/
        └── detail.html              # delete button added (hx-delete, hx-swap="none", hx-confirm); includes _page_errors.html once, always present

tests/
└── integration/
    └── test_projects_routes.py      # extend US4 test with the new HX-Redirect assertion; add a test asserting no hx-delete in the list page
```

**Structure Decision**: Reuses the single-project package layout established in 001-project-management verbatim — no new directories, no new dependencies. Only one route handler's response, one existing template, and one new partial are touched; `app/services.py` and `app/models.py` are untouched, matching this feature's explicit "route/template only" scope.

## Complexity Tracking

*No constitution gates are currently ratified (see Constitution Check above), so there is nothing to justify here.*
