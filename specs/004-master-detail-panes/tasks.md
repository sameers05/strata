---

description: "Task list template for feature implementation"
---

# Tasks: Master-Detail Pane UI

**Input**: Design documents from `/specs/004-master-detail-panes/` (plan.md, research.md, data-model.md, contracts/pane-read-routes.md, contracts/pane-mutation-routes.md, contracts/client-state-contract.md, quickstart.md, spec.md)

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md — all present

**Tests**: Included — per plan.md's Testing section (integration tests substantially rewritten alongside the routes they cover) and quickstart.md, which maps automated coverage to every user story. Pure client-side mechanics (divider drag, `confirm()` interception) aren't driveable via httpx `TestClient`; those are covered by quickstart.md's manual scenarios and by lightweight "expected markup/attributes present" integration assertions instead.

**Organization**: Tasks are grouped by user story (from spec.md), in priority order (P1, P1, P1, P2, P2, P2, P3).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no unresolved dependency on another incomplete task in this list)
- **[Story]**: Which user story this task serves (US1–US7), per spec.md
- File paths are relative to repo root

## Path Conventions

Single project, extending the existing `app/` package and `tests/` layout from 001/002/003. This feature is a wholesale rewrite of `app/routers/projects.py`, `app/routers/group_tasks.py`, `app/routers/deleted.py`, and `app/templates/base.html`, adds a new `app/templates/panes/` directory and `app/static/alpine.min.js`, and removes every prior full-page template under `app/templates/projects/`, `app/templates/group_tasks/`, and the top-level `app/templates/deleted.html`. No new database table or migration (data-model.md).

---

## Phase 1: Setup

**Purpose**: Add this feature's one new dependency before anything references it.

- [X] T001 Vendor Alpine.js: add `app/static/alpine.min.js` (pinned minified release build), matching the existing no-CDN convention already used for `htmx.min.js`/`pico.min.css` (depends on: none)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The two-pane shell and shared breadcrumb partial every subsequent story's templates render inside/reuse. Nothing in US1 onward can be implemented before this phase completes.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T002 Restructure `app/templates/base.html` into the two-pane shell: replace the old single `<main>{% block content %}{% endblock %}</main>` body (there is only one page now, so no template extends `base.html` anymore) with a persistent `<div id="left-pane">...</div>`, a divider element, and `<div id="details-pane">...</div>`; add `<script src="/static/alpine.min.js" defer></script>` alongside the existing `htmx.min.js`/`pico.min.css` tags; declare an empty shell-root `x-data` scaffold (dirty flag, divider split, last-list-URL store are wired up in US7/US5/US6 respectively — this task only lays out the two containers and script tags) (depends on: T001)
- [X] T003 [P] Create `app/templates/partials/_breadcrumb.html`: shared breadcrumb partial, parameterized by an optional ancestor (root state renders just "Projects" with no ancestor link; drilled state renders "Projects › {project.title}", the "Projects" segment itself a `hx-get="/panes/projects"` link carrying `data-pane-nav`) (depends on: none)

**Checkpoint**: Two-pane shell and breadcrumb partial exist; no pane routes exist yet.

---

## Phase 3: User Story 1 - Browse the hierarchy in a persistent two-pane layout (Priority: P1) 🎯 MVP

**Goal**: Home load shows the root Project list + first Project's details in one page load; clicking a Project's title drills the left pane into its Group-tasks (breadcrumb updates); a Group-task's title selects its own details directly (no further drill, since Task doesn't exist); a Project's "View" control selects its own details without drilling; reload always returns to the home state.

**Independent Test**: Load `/`, confirm both panes render the described home state; click a Project's title, confirm the left pane shows that Project's Group-tasks and the breadcrumb updates; click an ancestor breadcrumb link to jump back; reload mid-drill and confirm it returns to home.

### Implementation for User Story 1

- [X] T004 [US1] Add `list_active_projects_with_delete_eligibility(session) -> list[tuple[Project, bool]]` to `app/services.py`: single `LEFT JOIN group_task ... GROUP BY project.id` query per data-model.md/FR-015, used from here on as the Project list's data source (the boolean is unused by templates until US4 wires up delete-control disabling) (depends on: none)
- [X] T005 [US1] Create `app/templates/panes/details_create_prompt.html`: parameterized empty-list "create your first [entity]" prompt, taking an entity label and a new-item URL (depends on: none)
- [X] T006 [P] [US1] Modify `app/templates/partials/_project_row.html`: title link drills to `/panes/projects/{{ project.id }}/group-tasks` (`hx-get`, `hx-target="#left-pane"`, `data-pane-nav`); a separate "View" link selects `/panes/projects/{{ project.id }}` (`hx-get`, `hx-target="#details-pane"`, `data-pane-nav`) per FR-004/FR-005; existing `id="project-row-{{ project.id }}"` preserved (needed for OOB replace in US3); no delete control yet (added in US4) (depends on: none)
- [X] T007 [P] [US1] Modify `app/templates/partials/_group_task_row.html`: title link selects `/panes/projects/{{ group_task.project_id }}/group-tasks/{{ group_task.id }}` directly (`hx-get`, `hx-target="#details-pane"`, `data-pane-nav`) per FR-006 — single click target, no drill, no separate View control, since Task doesn't exist; existing `id="group-task-row-{{ group_task.id }}"` preserved; no delete control yet (added in US4) (depends on: none)
- [X] T008 [US1] Create `app/templates/panes/details_project.html`: wraps `partials/_project_form.html`; when `project` is provided, the fragment's root element carries `data-entity-type="project"` `data-entity-id="{{ project.id }}"` per the DOM contract (data-model.md); when `project` is `None` (blank create form, used starting in US2), those two attributes are absent (depends on: none)
- [X] T009 [US1] Create `app/templates/panes/details_group_task.html`: wraps `partials/_group_task_form.html`; same `data-entity-type="group_task"`/`data-entity-id` contract as T008, present when `group_task` is provided, absent when `None` (depends on: none)
- [X] T010 [US1] Create `app/templates/panes/left_projects.html`: includes `_breadcrumb.html` (root state), a `<tbody id="project-list-body">` looping `_project_row.html` over `list_active_projects_with_delete_eligibility` results, empty-state text if none — "+ New Project"/"Deleted Items" links land in US2/US6 (depends on: T003, T004, T006)
- [X] T011 [US1] Create `app/templates/panes/left_group_tasks.html`: includes `_breadcrumb.html` (drilled state, current Project's title), a `<tbody id="group-task-list-body">` looping `_group_task_row.html` over `services.list_active_group_tasks(project_id)`, empty-state text if none (depends on: T003, T007)
- [X] T012 [US1] Rewrite `app/routers/projects.py`: drop the router-level `prefix="/projects"` (routes now declare full paths individually since `GET /` shares no common prefix with `/panes/...`); remove the old full-page `GET /projects`, `GET /projects/{project_id}`, and the retired `/projects/deleted` 404 stub; add `GET /` (home shell — renders `base.html` embedding `left_projects.html` plus `details_project.html` for the first active Project, or `details_create_prompt.html` if none exist), `GET /panes/projects` (renders `left_projects.html` + an OOB `#details-pane` swap using the same first-item-or-create-prompt default), `GET /panes/projects/{project_id}` (`404` if missing/soft-deleted, else renders `details_project.html`) — `POST`/`PUT`/`DELETE /panes/projects...` land in US2/US3/US4 (depends on: T004, T008, T010)
- [X] T013 [US1] Modify `app/routers/group_tasks.py`: change the router-level prefix to `/panes/projects/{project_id}/group-tasks` (the `get_active_project_or_404` dependency itself is reused unchanged from 003); remove the old full-page `GET .../new`, `GET .../{id}`, `GET .../{id}/edit` (rebuilt with new paths/response shapes in US2/US3); add `GET ""` (list — renders `left_group_tasks.html` + OOB `#details-pane` default) and `GET /{group_task_id}` (`project: Project = Depends(get_active_project_or_404)`, then `404` if the Group-task itself is missing/soft-deleted, else renders `details_group_task.html`) (depends on: T009, T011)
- [X] T014 [US1] Delete `app/templates/projects/list.html`, `app/templates/projects/detail.html`, `app/templates/group_tasks/detail.html` — superseded by `panes/left_projects.html`, `panes/details_project.html`, `panes/details_group_task.html` (depends on: T012, T013)

### Tests for User Story 1

- [X] T015 [P] [US1] `tests/integration/test_projects_routes.py::test_us1_home_and_list_and_select` — `GET /` renders the shell with the first active Project selected (or `details_create_prompt.html` if empty); `GET /panes/projects` returns the list fragment + OOB `#details-pane` default; `GET /panes/projects/{id}` returns the populated fragment with `data-entity-type="project"` `data-entity-id="{id}"`; `404` on missing/soft-deleted id (depends on: T012)
- [X] T016 [P] [US1] `tests/integration/test_group_task_routes.py::test_us1_drill_and_select` — `GET /panes/projects/{id}/group-tasks` returns the drilled list fragment (breadcrumb present) + OOB `#details-pane` default; `GET /panes/projects/{id}/group-tasks/{gid}` returns the populated fragment with `data-entity-type="group_task"`; `404` when the parent Project is missing/soft-deleted, independent of the Group-task's own state (003's FR-015a, preserved) (depends on: T013)

**Checkpoint**: Home load, drill, select-without-drill, and breadcrumb-driven list swaps all work end-to-end. Create/edit/delete/divider/dirty-guard/Deleted-Items don't exist yet — an expected intermediate state (this app cannot yet create, edit, delete, or resize anything), not a regression, since the old full-page routes for those actions were already removed by T012/T013's rewrite.

---

## Phase 4: User Story 2 - Create a new entity from the current drill level (Priority: P1)

**Goal**: A persistent "+ New [entity]" control at both list levels opens a blank always-editable form in the details pane; saving inserts the new row into the left pane in place; validation failure surfaces in a fixed error area without navigating away.

**Independent Test**: From any drill level, with the list empty or populated, click "+ New," fill required fields, save, confirm the new row appears with the details pane showing it as selected.

### Implementation for User Story 2

- [X] T017 [P] [US2] Modify `app/templates/partials/_project_form.html`: retarget the blank-create branch's `hx-post` to `/panes/projects`, `hx-target="#details-pane"`, `hx-swap="innerHTML"` (depends on: none)
- [X] T018 [P] [US2] Modify `app/templates/partials/_group_task_form.html`: retarget the blank-create branch's `hx-post` to `/panes/projects/{{ project_id }}/group-tasks` (depends on: none)
- [X] T019 [US2] Modify `app/templates/panes/left_projects.html`: add the persistent "+ New Project" control (`hx-get="/panes/projects/new"`, `hx-target="#details-pane"`, `data-pane-nav`) per FR-010 (depends on: T010)
- [X] T020 [US2] Modify `app/templates/panes/left_group_tasks.html`: add the persistent "+ New Group-task" control (`hx-get="/panes/projects/{{ project.id }}/group-tasks/new"`, same attributes) per FR-010 (depends on: T011)
- [X] T021 [US2] Add `GET /panes/projects/new` to `app/routers/projects.py`: renders `details_project.html` with `project=None` (blank form) (depends on: T008, T012)
- [X] T022 [US2] Add `POST /panes/projects` to `app/routers/projects.py`: calls `services.create_project` unchanged (FR-028); success → `details_project.html` (saved, populated) + OOB `<tr hx-swap-oob="beforeend:#project-list-body">` appending the new row; failure (`ProjectValidationError`) → OOB `#form-errors` fragment inside the still-blank form, entered values retained, no navigation (FR-022) (depends on: T017, T021)
- [X] T023 [US2] Add `GET /panes/projects/{project_id}/group-tasks/new` to `app/routers/group_tasks.py`: `project: Project = Depends(get_active_project_or_404)` (404 if parent missing/soft-deleted, checked before rendering), renders `details_group_task.html` with `group_task=None` (depends on: T009, T013)
- [X] T024 [US2] Add `POST ""` (i.e. `/panes/projects/{project_id}/group-tasks`) to `app/routers/group_tasks.py`: `get_active_project_or_404` checked first (before validation, per contracts/pane-mutation-routes.md), calls `services.create_group_task` unchanged; success → `details_group_task.html` + OOB append into `#group-task-list-body`; failure → OOB `#form-errors`, values retained (depends on: T018, T023)

### Tests for User Story 2

- [X] T025 [P] [US2] `tests/integration/test_projects_routes.py::test_us2_create_project_flow` — `GET /panes/projects/new` renders a blank form; `POST` success returns the updated details-pane fragment + OOB row append with correct auto-assigned `serial_num`; `POST` with invalid values returns OOB `#form-errors`, entered values retained, no row added (depends on: T022)
- [X] T026 [P] [US2] `tests/integration/test_group_task_routes.py::test_us2_create_group_task_flow` — same coverage for Group-task, plus `404` on both the blank-form `GET` and the `POST` when `project_id` is missing/soft-deleted (parent-active check preserved on create) (depends on: T024)

### Cleanup for User Story 2

- [X] T027 [US2] Delete `app/templates/projects/new.html` — superseded by `GET /panes/projects/new` + `details_project.html` (depends on: T021)
- [X] T028 [US2] Delete `app/templates/group_tasks/new.html` — superseded by `GET /panes/projects/{id}/group-tasks/new` + `details_group_task.html` (depends on: T023)

**Checkpoint**: Both entities can now be created from any drill level, with the new row appearing in place and no full navigation. Combined with US1, browsing + creating now cover two of this feature's three P1 stories.

---

## Phase 5: User Story 3 - Edit an existing entity's fields (Priority: P1)

**Goal**: The same always-editable form used for creation, now pre-populated (already true since US1's select routes), saves changes in place — left pane row updates via OOB replace, details pane reflects the saved state, validation failure behaves identically to creation.

**Independent Test**: Select an existing row, confirm the form is pre-populated, change a field, save, confirm the change is reflected in both the left pane row and the details pane.

### Implementation for User Story 3

- [X] T029 [P] [US3] Modify `app/templates/partials/_project_form.html`: retarget the populated-edit branch's `hx-put` to `/panes/projects/{{ project.id }}`, `hx-target="#details-pane"` (depends on: none)
- [X] T030 [P] [US3] Modify `app/templates/partials/_group_task_form.html`: retarget the populated-edit branch's `hx-put` to `/panes/projects/{{ project_id }}/group-tasks/{{ group_task.id }}` (depends on: none)
- [X] T031 [US3] Add `PUT /panes/projects/{project_id}` to `app/routers/projects.py`: calls `services.update_project` unchanged; success → `details_project.html` (updated) + OOB `<tr id="project-row-{{ project.id }}" hx-swap-oob="true">` replacing the existing row; failure → OOB `#form-errors`, values retained; `404` if missing/soft-deleted (depends on: T029, T012)
- [X] T032 [US3] Add `PUT /panes/projects/{project_id}/group-tasks/{group_task_id}` to `app/routers/group_tasks.py`: `get_active_project_or_404` checked first, calls `services.update_group_task` unchanged; success → `details_group_task.html` (updated) + OOB row replacement; failure → OOB `#form-errors`; `404` per the same parent/own-state conditions as select (depends on: T030, T013)

### Tests for User Story 3

- [X] T033 [P] [US3] `tests/integration/test_projects_routes.py::test_us3_edit_project_flow` — `PUT` success updates the OOB row and details pane in one response; `PUT` with invalid values returns OOB `#form-errors` with retained values; `404` on missing/soft-deleted (depends on: T031)
- [X] T034 [P] [US3] `tests/integration/test_group_task_routes.py::test_us3_edit_group_task_flow` — same coverage for Group-task, plus parent-404 preserved on `PUT` (depends on: T032)

### Cleanup for User Story 3

- [X] T035 [US3] Delete `app/templates/projects/edit.html` — superseded by `PUT /panes/projects/{id}` + `details_project.html` (depends on: T031)
- [X] T036 [US3] Delete `app/templates/group_tasks/edit.html` — superseded by `PUT .../group-tasks/{id}` + `details_group_task.html` (depends on: T032)

**Checkpoint**: All three P1 stories (browse, create, edit) are complete — this is the feature's true minimum meaningful replacement of the old full-page app (see Implementation Strategy below).

---

## Phase 6: User Story 4 - Delete an entity guarded by active children (Priority: P2)

**Goal**: A delete control on every row, disabled when the entity has active children (Project only — Group-task's is unconditionally enabled, since Task doesn't exist); confirmation + soft-delete + row removal in place; if the deleted entity was the one open in the details pane, it auto-selects the next remaining active item.

**Independent Test**: View a list with one entity with active children and one without; confirm the blocked row's control is disabled and the other's triggers confirmation and removes the row in place.

### Implementation for User Story 4

- [X] T037 [US4] Modify `app/templates/partials/_project_row.html`: add the delete control — `hx-delete="/panes/projects/{{ project.id }}"`, `hx-swap="none"` (no `hx-target`; row removal happens via an explicit OOB element in the response, not `hx-swap`'s implicit target-removal), `hx-confirm="Delete this project?"`, `hx-vals='js:{selected_type: document.getElementById("details-pane").dataset.entityType, selected_id: document.getElementById("details-pane").dataset.entityId}'`; `disabled` when the row's `has_active_children` flag (from T004) is true (FR-013/FR-014) (depends on: T004)
- [X] T038 [US4] Modify `app/templates/partials/_group_task_row.html`: add the delete control, same pattern (`hx-swap="none"`, no `hx-target`), `hx-delete="/panes/projects/{{ group_task.project_id }}/group-tasks/{{ group_task.id }}"`, unconditionally enabled — no Task table exists yet to block on (research.md) (depends on: none)
- [X] T039 [US4] Add `DELETE /panes/projects/{project_id}` to `app/routers/projects.py`: calls `services.soft_delete_project` unchanged; success → empty-bodied `200` **plus** an OOB `<tr id="project-row-{{ project.id }}" hx-swap-oob="delete"></tr>` that explicitly removes the row (not `hx-swap="delete"` on the requesting element — see T037's note); if the request's `selected_type == "project"` and `selected_id == project_id`, the response body additionally contains an OOB `#details-pane` swap to the next remaining active Project (re-call `list_active_projects_with_delete_eligibility`, first result) or `details_create_prompt.html` if none remain; cascade-block rejection (active Group-tasks exist, unchanged rule from 003) → also a `200`, but with only the OOB error fragment inside `#details-pane`'s fixed error area and **no** `hx-swap-oob="delete"` row fragment, so the row correctly survives; `404` if missing/soft-deleted (depends on: T037, T012)
- [X] T040 [US4] Add `DELETE /panes/projects/{project_id}/group-tasks/{group_task_id}` to `app/routers/group_tasks.py`: `get_active_project_or_404` checked first, calls `services.soft_delete_group_task` unchanged; success → empty-bodied `200` plus an OOB `<tr id="group-task-row-{{ group_task.id }}" hx-swap-oob="delete"></tr>` explicitly removing the row; if `selected_type == "group_task"` and `selected_id == group_task_id`, OOB `#details-pane` swap to the next remaining active Group-task in that Project's list (re-call `list_active_group_tasks`, first result) or `details_create_prompt.html`; `404` per the same parent/own-state conditions (depends on: T038, T013)
- [X] T041 [US4] Add a fixed error-display area to `app/templates/panes/details_project.html` for the cascade-block rejection fragment (mirrors the `_page_errors.html` role from prior slices, now scoped inside the details pane's own chrome per contracts/pane-mutation-routes.md) (depends on: T008, T039)

### Tests for User Story 4

- [X] T042 [P] [US4] `tests/integration/test_projects_routes.py::test_us4_delete_flow` — delete control disabled when active Group-tasks exist; enabled and removes the row in place when none; deleting the currently-selected Project auto-selects the next active one (or `details_create_prompt.html`) via the OOB mechanism; deleting an unrelated row leaves `#details-pane` untouched; cascade-block rejection renders in place with the row surviving (depends on: T039, T041)
- [X] T043 [P] [US4] `tests/integration/test_group_task_routes.py::test_us4_delete_flow` — every Group-task row's delete control is unconditionally enabled; deleting removes the row and, when it was selected, auto-selects the next remaining active Group-task (or create-prompt) in that Project's list; deleting an unrelated row leaves `#details-pane` untouched (depends on: T040)

**Checkpoint**: Delete is fully guarded by active-children eligibility (computed in one batched query per FR-015) and correctly reconciles the details pane when the selected row is the one removed.

---

## Phase 7: User Story 5 - Resize the two panes via a draggable divider (Priority: P2)

**Goal**: Dragging the divider live-resizes both panes; the chosen split persists to `localStorage` and is restored on reload, defaulting to ~30/70 on first-ever load.

**Independent Test**: Drag the divider to a new position, reload the browser, confirm the same split is restored.

### Implementation for User Story 5

- [X] T044 [US5] Modify `app/templates/base.html`: add the divider drag Alpine component — `pointerdown` on the divider element begins tracking, `pointermove` updates `splitPct` live (both panes resize live via bound inline widths, FR-024), `pointerup` writes the final value to a fixed `localStorage` key, per contracts/client-state-contract.md §3 (depends on: T002)
- [X] T045 [US5] Modify `app/templates/base.html`: the shell-root `x-init` reads that `localStorage` key on load and applies it before first paint if present, falling back to a 30/70 default otherwise (FR-025) (depends on: T044)

### Tests for User Story 5

- [X] T046 [P] [US5] `tests/integration/test_projects_routes.py::test_us5_shell_markup` — `GET /` response includes the divider element and its Alpine/`localStorage`-key attributes (smoke-level markup check only; live drag/resize/persistence behavior itself is manual-only per quickstart.md, not driveable via httpx `TestClient`) (depends on: T045)

**Checkpoint**: Divider resize and cross-reload persistence work in a real browser (verified via quickstart.md's manual US5 scenario).

---

## Phase 8: User Story 6 - View soft-deleted history from any drill level (Priority: P2)

**Goal**: The persistent "Deleted Items" link, available at any drill depth, swaps the left pane into the existing two-section read-only view with the details pane showing genuinely no selectable content; a dedicated Back control (not the breadcrumb) returns to whichever list was active before.

**Independent Test**: From any drill depth, click "Deleted Items," confirm the two-section read-only view and empty details pane; return to normal browsing via Back and confirm it resumes correctly.

### Implementation for User Story 6

- [X] T047 [US6] Create `app/templates/panes/left_deleted.html`: two labeled sections — "Deleted Projects" (reuses `_project_row.html` with `readonly=true`, unchanged behavior from 001/003) and "Deleted Group-tasks" (grouped by parent Project ascending by the parent's `serial_num`, plain text rows, reuses `services.list_deleted_group_tasks_grouped_by_project` unchanged) — plus the dedicated Back control (FR-009a) (depends on: none)
- [X] T048 [P] [US6] Create `app/templates/panes/details_empty.html`: genuinely empty details-pane state — no selectable/editable content, distinct from `details_create_prompt.html` (FR-009) (depends on: none)
- [X] T049 [US6] Modify `app/templates/panes/left_projects.html` and `app/templates/panes/left_group_tasks.html`: add the persistent "Deleted Items" link (`hx-get="/panes/deleted"`, `hx-target="#left-pane"`, `data-pane-nav`) per FR-008 (depends on: T010, T011)
- [X] T050 [US6] Rewrite `app/routers/deleted.py`: `GET /panes/deleted` (was `GET /deleted`) calling `services.list_deleted_projects()` and `services.list_deleted_group_tasks_grouped_by_project()` unchanged, rendering `left_deleted.html` + an OOB `#details-pane` swap to `details_empty.html` (depends on: T047, T048)
- [X] T051 [US6] Modify `app/templates/base.html`'s shell-root Alpine component: add the in-memory last-shown-list-URL store and an `htmx:afterSwap` listener scoped to `#left-pane` that records the triggering request's source URL whenever the swapped-in view is a list (`/panes/projects` or `/panes/projects/{id}/group-tasks`), skipping the record when the swapped-in view is Deleted Items itself, per contracts/client-state-contract.md §4 (depends on: T002)
- [X] T052 [US6] Wire `left_deleted.html`'s Back control: `hx-get` bound to the Alpine store from T051 (`:hx-get`), defaulting to `/panes/projects` if unset, `data-pane-nav` (depends on: T047, T051)

### Tests for User Story 6

- [X] T053 [P] [US6] Rewrite `tests/integration/test_deleted_routes.py`: `GET /panes/deleted` renders both sections unchanged in content/grouping from 003, plus the OOB empty `#details-pane` fragment; `GET /deleted` (old path) no longer resolves (depends on: T050)
- [X] T054 [P] [US6] `tests/integration/test_projects_routes.py` / `test_group_task_routes.py` — add assertions that both list fragments include the "Deleted Items" link (depends on: T049)

### Cleanup for User Story 6

- [X] T055 [US6] Delete `app/templates/deleted.html` (top-level page version) — superseded by `panes/left_deleted.html` (depends on: T050)

**Checkpoint**: Deleted Items is reachable from anywhere, shows genuinely no selectable details-pane content while active, and Back correctly returns to the prior list.

---

## Phase 9: User Story 7 - Warn before discarding unsaved changes (Priority: P3)

**Goal**: Any unsaved edit in the details pane triggers a confirmation prompt before the user navigates away via any nav control; saving or navigating with no unsaved changes never prompts; deleting an unrelated row never prompts.

**Independent Test**: Edit a field without saving, click a different row, confirm a warning appears; confirming discards and proceeds, cancelling keeps the edit.

### Implementation for User Story 7

- [X] T056 [US7] Modify `app/templates/base.html`: add the dirty-tracking Alpine component scoped to `#details-pane` — `x-init` snapshots each field's initial value on every swap-in (re-runs automatically, since htmx-swapped content re-triggers Alpine's `x-init`), any `input`/`change` event sets an in-memory `dirty` flag, per contracts/client-state-contract.md §1 (depends on: T002)
- [X] T057 [US7] Modify `app/templates/base.html`: add the single document-wide `htmx:confirm` listener at the shell root — no-ops unless `evt.detail.elt` carries `data-pane-nav`; when `dirty` is true, calls the native `confirm()` and prevents the request on cancel; proceeds on confirm or when not dirty (depends on: T056)
- [X] T058 [US7] Audit `data-pane-nav` coverage across every navigation control built in prior phases (row title/View links in `_project_row.html`/`_group_task_row.html`, breadcrumb links in `_breadcrumb.html`, "+ New" controls in `left_projects.html`/`left_group_tasks.html`, the Deleted Items link, the Back control) and confirm it is present on all of them and absent from the Save button and the divider drag handle; fix any gaps found (depends on: T006, T007, T003, T019, T020, T049, T052)

### Tests for User Story 7

- [X] T059 [P] [US7] `tests/integration/test_projects_routes.py::test_us7_nav_guard_markup` — rendered fragments carry `data-pane-nav` on every required control and it is absent from the Save button; the `confirm()` interception behavior itself is manual-only (quickstart.md), not driveable via httpx `TestClient` (depends on: T058)

**Checkpoint**: All seven user stories are complete and independently verifiable.

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Confirm the full slice validates end-to-end and that every prior full-page route is genuinely gone, not just superseded.

- [ ] T060 Run `pytest tests/unit tests/integration` and confirm all pass, with no regression to any existing business rule or validation behavior beyond the routing/response-shape rewrite (FR-028) (depends on: T001–T059)
- [ ] T061 Execute quickstart.md's manual validation scenarios (US1–US7) end-to-end in a browser, including the divider drag/persistence and unsaved-changes-guard scenarios automated tests can't drive (depends on: T060)
- [ ] T062 Confirm every prior full-page route (`/projects`, `/projects/{id}`, `/projects/{id}/edit`, `/projects/{id}/group-tasks/...`, `/deleted`) now 404s or no longer resolves, and that no template remains under `app/templates/projects/`, `app/templates/group_tasks/`, or as a top-level `app/templates/deleted.html` (FR-027) (depends on: T061)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately.
- **Foundational (Phase 2)**: Depends on Setup (T001, for the `<script>` tag T002 adds); BLOCKS every user story below — nothing renders without the two-pane shell and breadcrumb partial existing.
- **User Story 1 (Phase 3, P1)**: Depends on Foundational only.
- **User Story 2 (Phase 4, P1)**: Depends on Foundational and on US1's templates/routes (`details_project.html`/`details_group_task.html`, `left_projects.html`/`left_group_tasks.html`, the rewritten router files) — creation extends the same files US1 established rather than starting fresh.
- **User Story 3 (Phase 5, P1)**: Depends on Foundational and, like US2, on US1's select routes/templates already existing (edit reuses the same `details_*.html` wrappers and rewritten router files).
- **User Story 4 (Phase 6, P2)**: Depends on Foundational, US1 (row templates, `details_create_prompt.html`), and T004 (the batched-eligibility query, built in US1).
- **User Story 5 (Phase 7, P2)**: Depends on Foundational (T002) only — independent of US2–US4's entity CRUD.
- **User Story 6 (Phase 8, P2)**: Depends on Foundational and on US1's list templates (T049 adds the Deleted Items link to them) and T002 (shell Alpine scaffold, extended in T051).
- **User Story 7 (Phase 9, P3)**: Depends on Foundational (T002) and, for its audit task (T058), on every nav-control-producing task from US1/US2/US6 having already run.
- **Polish (Phase 10)**: Depends on all seven user stories being complete.

### Within Each User Story

- US1: T004–T009 (service + standalone templates) have no dependency on each other; T010/T011 (list fragments) depend on T003/T004/T006 and T003/T007 respectively; T012/T013 (routers) depend on the templates/service they render; T014 (template deletion) depends on both routers being rewritten. Tests (T015, T016) come last.
- US2: T017/T018 (form retargeting) and T019/T020 (list template "+ New" controls) are independent of each other; T021/T023 (blank-form `GET`s) depend on US1's `details_*.html`; T022/T024 (`POST`s) depend on the form retargeting (T017/T018) and the `GET`s (T021/T023). Tests (T025, T026) before cleanup (T027, T028).
- US3: T029/T030 (form retargeting) independent of each other; T031/T032 (`PUT`s) depend on them. Tests (T033, T034) before cleanup (T035, T036).
- US4: T037/T038 (row delete controls) independent of each other; T039/T040 (`DELETE`s) depend on them; T041 (error area) depends on T008 and T039. Tests (T042, T043) last.
- US5: T044 → T045, strictly sequential (drag-and-write before load-and-apply). Test (T046) last.
- US6: T047/T048 independent; T049 depends on US1's list templates; T050 depends on T047/T048; T051 depends on T002 (Foundational); T052 depends on T047/T051. Tests (T053, T054) before cleanup (T055).
- US7: T056 → T057, sequential (dirty tracking before the listener that reads it); T058 depends on every nav-control task from US1/US2/US6. Test (T059) last.

### Parallel Opportunities

- T003 (Foundational) can run in parallel with T002 once T001 is done — different files.
- T004–T009 (US1) can all run in parallel with each other — six independent files/functions with no interdependency.
- T017 and T018 (US2 form retargeting) can run in parallel — different files.
- T019 and T020 (US2 list template edits) can run in parallel — different files.
- T029 and T030 (US3 form retargeting) can run in parallel.
- T037 and T038 (US4 row delete controls) can run in parallel.
- T042 and T043 (US4 tests) can run in parallel once their respective router tasks are done.
- T047 and T048 (US6 templates) can run in parallel.

---

## Parallel Example: User Story 1

```bash
# Once Foundational is complete, these six can proceed together:
Task: "Add list_active_projects_with_delete_eligibility to app/services.py (T004)"
Task: "Create app/templates/panes/details_create_prompt.html (T005)"
Task: "Modify app/templates/partials/_project_row.html (T006)"
Task: "Modify app/templates/partials/_group_task_row.html (T007)"
Task: "Create app/templates/panes/details_project.html (T008)"
Task: "Create app/templates/panes/details_group_task.html (T009)"
```

## Parallel Example: User Story 4

```bash
# These two can proceed together once T004 is done:
Task: "Add delete control to app/templates/partials/_project_row.html (T037)"
Task: "Add delete control to app/templates/partials/_group_task_row.html (T038)"
```

---

## Implementation Strategy

### MVP scope: Phases 3–5 together (US1 + US2 + US3), not US1 alone

Unlike a typical feature where "MVP = User Story 1 only" leaves a smaller but still-coherent product, this feature's US1 alone would leave the app able to browse but with **no way to create or edit anything** — a regression from the app that existed before this branch, since T012/T013's router rewrite removes the old full-page create/edit routes as part of building US1's own routes. Browse (US1), create (US2), and edit (US3) are all P1 for exactly this reason (spec.md's own "Why this priority" notes on US1–US3 make the same point). Treat **Phases 3, 4, and 5 together** as the feature's true minimum shippable state.

1. Complete Phase 1 (Setup) + Phase 2 (Foundational).
2. Complete Phase 3 (US1): browsing works, nothing can be created or edited yet.
3. Complete Phase 4 (US2): creation works.
4. Complete Phase 5 (US3): editing works.
5. **STOP and VALIDATE**: the app is now a complete (if unpolished) replacement for the old full-page create/list/edit flows for both Project and Group-task.

### Incremental Delivery

1. Setup + Foundational → shell exists, nothing renders inside it yet.
2. US1 → browse (MVP building block, not shippable alone — see above).
3. US2 → create (combined with US1, now genuinely usable).
4. US3 → edit (combined with US1+US2, this is the feature's real MVP).
5. US4 → delete, guarded by active-children eligibility.
6. US5 → divider resize + persistence (pure ergonomic add, no dependency on US4/US6/US7).
7. US6 → Deleted Items view + Back control.
8. US7 → unsaved-changes guard (P3, last — protects edits made possible by US3, but its absence never blocks any other story from working).
9. Phase 10 → full regression pass, manual quickstart sign-off, and confirmation every old route is truly gone.

### Parallel Team Strategy

With multiple developers, after Foundational:
- Developer A: US1 → US2 → US3 (the sequential P1 chain, since US2/US3 build on US1's files).
- Developer B: US5 (divider) — fully independent of the P1 chain past Foundational, can proceed in parallel.
- Once US1 lands: Developer C can start US6 (Deleted Items) in parallel with US2/US3, since US6 only needs US1's list templates (T049) plus the Foundational shell.
- US4 and US7 are best done after the P1 chain (US4 needs US1's row templates and eligibility query; US7's audit task needs every other story's nav controls to exist first to audit against).

---

## Notes

- `[P]` tasks = different files, no unresolved dependency on another incomplete task
- `[US#]` labels map tasks to spec.md's user stories for traceability
- Commit after each task or logical group
- Stop at any phase checkpoint to validate story independently
- No task in this list touches `app/models.py`, `alembic/`, or any existing service function's signature/validation logic — this feature is presentation/routing only (FR-028), confirmed by data-model.md's "no new or changed database entities"
- Task remains entirely unmodeled — no task in this list references it, per FR-006/FR-029
