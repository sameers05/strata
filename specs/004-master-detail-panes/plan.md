# Implementation Plan: Master-Detail Pane UI

**Branch**: `004-master-detail-panes` | **Date**: 2026-07-09 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-master-detail-panes/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Replace Strata's full-page-per-entity navigation (list/detail/new/edit pages for Project and Group-task, plus the top-level `/deleted` page) with a single persistent two-pane shell at one static URL (`GET /`): a resizable left list/breadcrumb/drill pane and a right always-editable details pane, both kept in sync purely through server-rendered HTMX fragments and out-of-band swaps — the server stays fully stateless per request, with no session store. Alpine.js (newly vendored, matching the project's existing no-CDN convention for HTMX/Pico.css) is added for exactly two things vanilla HTMX can't express: an unsaved-changes navigation guard (dirty-tracking + a global `htmx:confirm` interception gated by a shared marker attribute) and divider drag + `localStorage` persistence. All existing Project/Group-task service-layer functions and business rules (uniqueness scoping, cascade-delete blocking, field validation) are reused unchanged (FR-028); only the routers and templates around them are rewritten to return fragments instead of full pages or `HX-Redirect`s. The trickiest design problem this plan resolves is FR-017a — how a stateless server knows whether the row just deleted is also the entity currently open in the details pane — solved by having every details-pane fragment self-describe its selected entity via `data-entity-type`/`data-entity-id` attributes that delete requests echo back as request parameters, rather than any server-side session tracking.

## Technical Context

**Language/Version**: Python 3.12 (unchanged from 001/002/003)

**Primary Dependencies**: FastAPI, SQLModel (SQLAlchemy 2.x + Pydantic v2), Jinja2, HTMX (vendored, `app/static/htmx.min.js`), **Alpine.js (NEW, vendored, `app/static/alpine.min.js`)**, Pico.css (vendored, `app/static/pico.min.css`), Alembic (present, but no migration needed by this feature)

**Storage**: SQLite, same `DATABASE_URL`-driven engine as prior slices; **no schema changes** — this feature adds no tables/columns and needs no migration (data-model.md)

**Testing**: pytest + httpx `TestClient`, same `tests/conftest.py` isolated-engine fixtures; `tests/integration/test_projects_routes.py`, `test_group_task_routes.py`, `test_deleted_routes.py` are **substantially rewritten** (the full-page routes they tested no longer exist), not extended — a rare case where prior integration tests are replaced rather than added to. `tests/unit/test_project_service.py` and `test_group_task_service.py` are unaffected (FR-028 keeps business logic unchanged)

**Target Platform**: Local venv, same as prior slices. Two-pane layout targets desktop/wide-viewport browser usage only — a dedicated mobile/narrow-viewport layout is explicitly out of scope (spec.md Assumptions)

**Project Type**: Single web-service project; extends the existing `app/` package — no new top-level project or service boundary

**Performance Goals**: Not throughput-sensitive (single user, unchanged from prior slices); FR-015's delete-eligibility batching (one combined query per list load, not per-row) must hold up to ~200 active items per parent (SC-007), same scale prior slices target

**Constraints**: Single static home URL, no deep-linking/server-side routing to any drill level, selected entity, or the Deleted Items view — a reload always returns to the home state (FR-001/FR-002); every prior full-page route for Project and Group-task is fully removed, not kept as a redirect/alias (FR-027); the server introduces no session/state-tracking mechanism of any kind (client-side DOM attributes and `localStorage` carry everything that must survive across requests, per research.md); divider position is the only thing that must survive a browser reload, drill/selection state explicitly must not (FR-002 vs. FR-025)

**Scale/Scope**: Same as 003 — up to ~200 active items per parent level; this feature touches Project and Group-task's presentation layer only, Task remains entirely out of scope (spec.md FR-006/FR-029)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is still the unpopulated template — unchanged since 001/002/003, no ratified principles exist to gate this plan against. This plan follows the same structural conventions already established by prior slices (service-layer validation reused unchanged, vendored-not-CDN frontend dependencies, OOB-fragment error containers) and introduces nothing that conflicts with the template's placeholder guidance.

**Recommendation carried over from prior slices**: still worth running `/speckit-constitution` at some point, not a blocker here either.

*Post-Phase-1 re-check*: No new violations introduced by data-model.md, contracts/, or quickstart.md. Still no ratified constitution to gate against.

## Project Structure

### Documentation (this feature)

```text
specs/004-master-detail-panes/
├── plan.md                          # This file (/speckit-plan command output)
├── research.md                      # Phase 0 output
├── data-model.md                    # Phase 1 output
├── quickstart.md                    # Phase 1 output
├── contracts/                       # Phase 1 output
│   ├── pane-read-routes.md          # GET routes: shell, left-pane list/drill fragments, details-pane select/blank-create fragments, Deleted Items
│   ├── pane-mutation-routes.md      # POST/PUT/DELETE routes: OOB row insert/replace/remove, FR-017a mechanism
│   └── client-state-contract.md     # Alpine/HTMX DOM conventions: dirty-guard, divider persistence, Back-control store
└── tasks.md                         # Phase 2 output (/speckit-tasks — NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
app/
├── main.py                              # unchanged: still mounts /static, includes projects/group_tasks/deleted routers
├── database.py                          # unchanged
├── models.py                            # unchanged — no schema changes
├── services.py                          # ADDITIVE only: + list_active_projects_with_delete_eligibility(session)
│                                         #   (batched LEFT JOIN + GROUP BY query, FR-015); all existing functions unchanged (FR-028)
├── routers/
│   ├── projects.py                      # REWRITTEN: GET / (home shell), GET /panes/projects (list+OOB details default),
│   │                                     #   GET /panes/projects/new, GET /panes/projects/{id} (select),
│   │                                     #   POST /panes/projects, PUT /panes/projects/{id}, DELETE /panes/projects/{id}
│   │                                     #   (OOB row insert/replace/remove + conditional FR-017a details-pane swap)
│   ├── group_tasks.py                   # REWRITTEN, stays nested throughout (mirrors 003): GET /panes/projects/{id}/group-tasks
│   │                                     #   (list+OOB details default), GET /panes/projects/{id}/group-tasks/new,
│   │                                     #   GET /panes/projects/{id}/group-tasks/{group_task_id} (select),
│   │                                     #   POST /panes/projects/{id}/group-tasks,
│   │                                     #   PUT/DELETE /panes/projects/{id}/group-tasks/{group_task_id} —
│   │                                     #   every route keeps declaring project: Project = Depends(get_active_project_or_404),
│   │                                     #   unchanged from 003, so 003's FR-015a parent-active-or-404 check still fires
│   │                                     #   on every one of these routes, not only on create
│   └── deleted.py                       # REWRITTEN: GET /panes/deleted (left-pane fragment + OOB empty details-pane), was GET /deleted (full page)
├── static/
│   ├── htmx.min.js                      # unchanged
│   ├── pico.min.css                     # unchanged
│   └── alpine.min.js                    # NEW, vendored
└── templates/
    ├── base.html                        # REWRITTEN: two-pane shell (#left-pane, #details-pane, divider), Alpine root
    │                                     #   x-data (dirty-guard listener, divider drag+localStorage, last-list-URL store),
    │                                     #   + <script src="/static/alpine.min.js">
    ├── panes/                           # NEW directory — fragment partials returned directly by pane routes
    │   ├── left_projects.html           # root Project list: breadcrumb(none), "+ New Project", "Deleted Items" link, rows
    │   ├── left_group_tasks.html        # drilled Group-task list: breadcrumb, "+ New Group-task", "Deleted Items" link, rows
    │   ├── left_deleted.html            # two-section read-only Deleted Items view + Back control
    │   ├── details_project.html         # Project select/populated form wrapper (embeds _project_form.html), data-entity-* attrs
    │   ├── details_group_task.html      # Group-task select/populated form wrapper (embeds _group_task_form.html), data-entity-* attrs
    │   ├── details_create_prompt.html   # empty-list "create first [entity]" prompt, parameterized by entity label + new-URL
    │   └── details_empty.html           # Deleted-Items-active empty state (FR-009) — genuinely no selectable content
    └── partials/
        ├── _breadcrumb.html             # NEW: shared breadcrumb partial, included by left_projects.html/left_group_tasks.html
        ├── _project_row.html            # MODIFIED: + delete control (data-pane-nav on title link only, not delete), disabled per FR-015 flag
        ├── _group_task_row.html         # MODIFIED: + delete control, unconditionally enabled (no Task yet, research.md)
        ├── _project_form.html           # MODIFIED: hx-post/hx-put retarget to /panes/projects[...]; hx-target=#details-pane; OOB row fragment
        ├── _group_task_form.html        # MODIFIED: hx-post/hx-put/hx-delete all retarget to nested /panes/projects/{project_id}/group-tasks[/{id}] paths
        └── _form_errors.html            # unchanged, reused as-is

# REMOVED entirely (full-page templates replaced by panes/ fragments above):
#   app/templates/projects/list.html, projects/detail.html, projects/new.html, projects/edit.html
#   app/templates/group_tasks/new.html, group_tasks/detail.html, group_tasks/edit.html
#   app/templates/deleted.html (top-level page version)

tests/
├── unit/
│   ├── test_project_service.py          # unaffected; may gain a small addition testing the new batched-eligibility query
│   └── test_group_task_service.py       # unaffected (FR-028)
└── integration/
    ├── test_projects_routes.py          # SUBSTANTIALLY REWRITTEN: old full-page/HX-Redirect assertions replaced with
    │                                     #   fragment + OOB assertions against the new /panes/... routes
    ├── test_group_task_routes.py        # SUBSTANTIALLY REWRITTEN: same, + coverage that get_active_project_or_404's
    │                                     #   404 (003's FR-015a) still fires on select/update/delete, not only create
    └── test_deleted_routes.py           # SUBSTANTIALLY REWRITTEN: GET /panes/deleted fragment + OOB empty details-pane
```

**Structure Decision**: Extends the existing single-project `app/` package — no new project, service boundary, or build unit, same as prior slices. `GET /` lives in `app/routers/projects.py` rather than a new module, since Project is the root/home entity and the home route's content (root Project list + first Project's details) is otherwise identical to what `GET /panes/projects` already computes — keeping it in the same file avoids a one-route module for a single trivial addition. `services.py` changes are strictly additive (two new functions); every existing service function signature and validation rule is untouched, which is what lets the router rewrite proceed without touching `test_project_service.py`/`test_group_task_service.py` at all. Group-task's routes — list/drill, blank-create, select, create, update, delete — all stay nested under `/panes/projects/{project_id}/group-tasks/...`, exactly mirroring 003's full-page convention; every one of them keeps declaring `project: Project = Depends(get_active_project_or_404)`, the same shared dependency 003 introduced, so 003's FR-015a parent-active-or-404 protection is fully preserved, not silently dropped by this feature's rewrite (research.md; FR-028 requires existing business rules stay unchanged). Templates split into a new `templates/panes/` directory for the fragments pane routes return directly, distinct from `templates/partials/`, which keeps holding the smaller reusable pieces (`_project_form.html`, row partials, breadcrumb) that both a pane template and (potentially, in the future) something else might embed — mirroring the existing `partials/` convention from 001/003 rather than inventing a new split. `_form_errors.html` is reused completely unchanged, same as 003 reused it unchanged from 001 — it's already an entity-agnostic, fixed `#form-errors` container with no per-feature markup to update. `tests/` continues to mirror `app/` by layer, unchanged in structure even though two of the three integration test files are rewritten in content.

## Complexity Tracking

*No constitution gates are currently ratified (see Constitution Check above), so there is nothing to justify here.*
