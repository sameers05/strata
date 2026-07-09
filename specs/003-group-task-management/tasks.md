---

description: "Task list template for feature implementation"
---

# Tasks: Group-task Management

**Input**: Design documents from `/specs/003-group-task-management/` (plan.md, research.md, data-model.md, contracts/group-tasks-routes.md, contracts/projects-retrofit-contract.md, quickstart.md, spec.md)

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md — all present

**Tests**: Included — per plan.md's Testing section ("tests-after per phase, same discipline as slice 1") and this feature's own quickstart.md, which maps automated coverage to every user story.

**Organization**: Tasks are grouped by user story (from spec.md), in priority order (P1, P1, P2, P2, P2, P3).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no unresolved dependency on another incomplete task in this list)
- **[Story]**: Which user story this task serves (US1–US6), per spec.md
- File paths are relative to repo root

## Path Conventions

Single project, extending the existing `app/` package and `tests/` layout from 001/002. New files: `app/routers/group_tasks.py`, `app/routers/deleted.py`, `app/templates/group_tasks/`, `app/templates/deleted.html`, two new partials, one new Alembic migration, `tests/unit/test_group_task_service.py`, `tests/integration/test_group_task_routes.py`, `tests/integration/test_deleted_routes.py`.

---

## Phase 1: Setup

Not applicable — this feature introduces no new dependency or tooling; it extends the existing `app/` package with one new table, one new router pair, and new templates, all using the stack already in place since 001.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The `GroupTask` table (with its migration) and the shared FastAPI dependency that every nested Group-task route relies on. Nothing in US1, US3, US4, or US5 can be implemented before this phase completes — each adds a route to `group_tasks.py` that depends on both the table and the dependency function existing.

- [X] T001 Define `GroupTask` in `app/models.py`: fields `id`, `project_id` (FK → `project.id`, no `ON DELETE CASCADE`), `serial_num`, `title` (≤200 chars), `description` (≤2000 chars), `start_date`, `finished_date`, `notes` (plain `str`, no `max_length`), `status` (reuses the existing `Status` enum), `deleted` (default `False`); `__table_args__` with two partial composite unique indexes — `Index("ix_group_task_project_title_active", "project_id", "title", unique=True, sqlite_where=text("deleted = false"))` and the `serial_num` equivalent — plus a plain (non-unique) index on `project_id` alone, per data-model.md and research.md (depends on: none)
- [X] T002 Generate the migration: `alembic revision --autogenerate -m "create group_task table"` (depends on: T001)
- [X] T003 Manually review and correct the generated `alembic/versions/..._create_group_task_table.py`: verify the FK to `project.id`, verify/hand-fix both partial composite unique indexes (autogenerate is known to mishandle partial indexes, per 001's research.md precedent), and verify the plain `project_id` index is present (depends on: T002)
- [X] T004 Apply and verify: run `alembic upgrade head` and confirm the `group_task` table, its FK, and all three indexes exist (depends on: T003)
- [X] T005 [P] Scaffold `app/routers/group_tasks.py`: `APIRouter(prefix="/projects/{project_id}/group-tasks", tags=["group-tasks"])` plus the single shared dependency `get_active_project_or_404(project_id: int, session: Session = Depends(get_session)) -> Project` (wraps `services.get_active_project`, raises `HTTPException(404)` if `None`) — per plan.md/research.md, this is the *only* place this check is implemented; every route added in later phases takes `project: Project = Depends(get_active_project_or_404)` rather than checking inline (depends on: T001)
- [X] T006 Mount the new router in `app/main.py`: `app.include_router(group_tasks.router)` (depends on: T005)
- [X] T007 [P] Update `tests/conftest.py`: import `GroupTask` from `app.models` (alongside the existing `Project` import) so `SQLModel.metadata.create_all` registers the new table in the isolated test engine (depends on: T001)

**Checkpoint**: `group_task` table exists and is migrated; `group_tasks.router` is mounted with its shared parent-resolution dependency ready for every nested route in the phases below.

---

## Phase 3: User Story 1 - Create a Group-task and see it under its Project (Priority: P1) 🎯 MVP

**Goal**: A user creates a Group-task under an active Project and immediately sees it in that Project's own nested list, with every uniqueness/ordering rule scoped to the parent Project rather than global.

**Independent Test**: Open an active Project with no Group-tasks, create one with only title + description, confirm it appears in that Project's nested list with serial_num 0 and status "new"; confirm a Group-task with the same title under a *different* Project succeeds without conflict.

### Implementation for User Story 1

- [X] T008 [US1] Implement `_validate_group_task_fields(title, description, start_date, finished_date)` in `app/services.py`: reject blank-or-whitespace-only title/description (FR-008a) and values exceeding ~200/~2000 chars (FR-008); reject `finished_date` earlier than `start_date` when both present (FR-009) — same shape as Project's `_validate_common_fields`, deliberately not shared/extracted (depends on: T001)
- [X] T009 [US1] Implement `_check_group_task_title_conflict(session, project_id, title, exclude_id)` in `app/services.py`: reject if another *active* Group-task under the same `project_id` has this title (FR-005) (depends on: T001)
- [X] T010 [US1] Implement `_check_group_task_serial_num_conflict(session, project_id, serial_num, exclude_id)` in `app/services.py`: reject if another *active* Group-task under the same `project_id` has this `serial_num` (FR-006) (depends on: T001)
- [X] T011 [US1] Implement `create_group_task(session, project_id, *, title, description, start_date=None, finished_date=None, notes=None, status=Status.NEW)` in `app/services.py`: calls T008–T010, auto-assigns `serial_num` = (max active `serial_num` **within `project_id`**) + 1, or 0 if that Project has no active Group-task yet (FR-004), raises `services.ProjectValidationError` on any rejection (depends on: T008, T009, T010)
- [X] T012 [US1] Implement `list_active_group_tasks(session, project_id)` in `app/services.py`: `WHERE project_id = :project_id AND deleted = false`, ascending by `serial_num` (FR-018) (depends on: T001)
- [X] T013 [US1] `GET /projects/{project_id}/group-tasks/new` in `app/routers/group_tasks.py`: `project: Project = Depends(get_active_project_or_404)`, renders `group_tasks/new.html` with a blank form (depends on: T005)
- [X] T014 [US1] `POST /projects/{project_id}/group-tasks` in `app/routers/group_tasks.py`: calls `create_group_task`; on success `200` + `HX-Redirect: /projects/{project_id}`; on `ProjectValidationError`, `200` + OOB `#form-errors` fragment, form untouched (depends on: T011, T013)
- [X] T015 [US1] Modify `GET /projects/{id}` in `app/routers/projects.py`: also call `services.list_active_group_tasks(session, project_id=id)` and pass the result to the template context (depends on: T012)
- [X] T016 [P] [US1] Create `app/templates/partials/_group_task_row.html`: one `<tr>` per Group-task showing only `serial_num`, `title` (linked to its detail page), `status`, `start_date`, `finished_date` (description/notes excluded per FR-018), a separate Edit link, and **no** delete control (FR-019) (depends on: none)
- [X] T017 [P] [US1] [US4] Create `app/templates/partials/_group_task_form.html`: shared create/edit body (title, description, start_date, finished_date, notes, status select, and `serial_num` only when editing — mirroring `_project_form.html`'s pattern exactly); includes `_form_errors.html`; carries **no** `project_id` field of any kind — the form's own `hx-post`/`hx-put` target URL is the sole source of `project_id`, since every route is already nested under `/projects/{project_id}/group-tasks/...` (depends on: none)
- [X] T018 [US1] Create `app/templates/group_tasks/new.html`: extends `base.html`, includes `_group_task_form.html` configured to `hx-post="/projects/{{ project.id }}/group-tasks"` (depends on: T017)
- [X] T019 [US1] Modify `app/templates/projects/detail.html`: embed the nested Group-task table (loop of `_group_task_row.html`, empty-state text if none) and a "New group-task" link to `/projects/{{ project.id }}/group-tasks/new` (depends on: T015, T016)

### Tests for User Story 1

- [X] T020 [P] [US1] `tests/unit/test_group_task_service.py::test_serial_num_and_title_scoped_per_project` — `serial_num` auto-assignment/reuse computed only within `project_id` (two different Projects' first Group-tasks both get 0); a title active under Project A is rejected for another active Group-task under Project A but succeeds under Project B; blank/whitespace title or description rejected; length limits enforced; bad date ordering rejected (depends on: T011, T012)
- [X] T021 [US1] `tests/integration/test_group_task_routes.py::test_us1_create_and_nested_list_flow` — `POST` creates a Group-task and it appears in `GET /projects/{id}`'s nested list with serial_num 0; validation failure returns the OOB `#form-errors` fragment with the form untouched; a duplicate title under a *different* Project succeeds (depends on: T014, T019)

**Checkpoint**: A Group-task can be created under any active Project and is visible in that Project's own nested list; uniqueness is correctly scoped per-parent, not global.

---

## Phase 4: User Story 2 - A Project cannot be deleted while it has active Group-tasks (Priority: P1)

**Goal**: Activate the retrofit hook — `soft_delete_project` rejects deletion while active Group-tasks exist, surfacing the rejection through the `_page_errors.html` OOB container `002` built for this purpose.

**Independent Test**: Create a Group-task under an active Project, attempt to soft-delete that Project (rejected with an explanatory message), soft-delete the Group-task, retry (succeeds).

### Implementation for User Story 2

- [X] T022 [US2] Retrofit `soft_delete_project` in `app/services.py`: before flipping `deleted = true`, check `EXISTS(SELECT 1 FROM group_task WHERE project_id = :id AND deleted = false)`; if any exist, raise the existing `ProjectValidationError` with a message such as "Cannot delete: this project still has active group-tasks" (FR-016); succeeds unchanged when zero active Group-tasks exist (FR-017) (depends on: T001)
- [X] T023 [US2] Implement `soft_delete_group_task(session, project_id, group_task_id)` in `app/services.py`: unconditional this slice (no active-Task check exists yet, FR-012), freezes `serial_num` at its last active value (FR-014), raises `GroupTaskNotFoundError` if missing/already soft-deleted/not under that `project_id` (depends on: T001)
- [X] T024 [US2] Modify `DELETE /projects/{id}` in `app/routers/projects.py`: catch the new `ProjectValidationError` from T022 and render `_page_errors.html`'s OOB fragment (`200`, **no** `HX-Redirect`) instead of always succeeding; unchanged `404` and unchanged success path otherwise (depends on: T022)

### Tests for User Story 2

- [X] T025 [P] [US2] `tests/unit/test_project_service.py::test_soft_delete_blocked_by_active_group_tasks` — `soft_delete_project` raises when ≥1 active Group-task exists under that Project; succeeds once all are soft-deleted; succeeds unchanged when none ever existed (regression check) (depends on: T011, T022, T023)
- [X] T026 [US2] `tests/integration/test_projects_routes.py::test_delete_rejected_with_active_group_tasks` — `DELETE /projects/{id}` with an active Group-task returns `200` + the `#page-errors` OOB rejection fragment, no `HX-Redirect`, Project still listed at `/projects`; after soft-deleting the Group-task, the same `DELETE` now succeeds with `HX-Redirect: /projects` (depends on: T014, T024)

**Checkpoint**: Project deletion is correctly gated on Group-task existence; the previously-empty `_page_errors.html` container now has a real message to show.

---

## Phase 5: User Story 3 - View a Group-task's full details (Priority: P2)

**Goal**: A dedicated detail page shows every Group-task field, including description and notes (excluded from the nested list), plus the standing empty error area reserved for a future Task-existence check.

**Independent Test**: Create a Group-task, open its detail page via the nested list's link, confirm every field renders accurately plus a link back to the parent Project.

### Implementation for User Story 3

- [X] T027 [US3] Implement `get_active_group_task(session, project_id, group_task_id)` in `app/services.py`: returns `None` if missing, soft-deleted, or not under that `project_id` (depends on: T001)
- [X] T028 [US3] `GET /projects/{project_id}/group-tasks/{group_task_id}` in `app/routers/group_tasks.py`: `project: Project = Depends(get_active_project_or_404)`, then `get_active_group_task` or `404`, renders `group_tasks/detail.html` (depends on: T027, T005)
- [X] T029 [US3] Create `app/templates/group_tasks/detail.html`: extends `base.html`, includes `partials/_page_errors.html` (always present, empty this cycle per FR-022), shows every field including `description` and `notes`, a link back to `/projects/{{ project.id }}`, and an Edit link (depends on: T028)

### Tests for User Story 3

- [X] T030 [US3] `tests/integration/test_group_task_routes.py::test_us3_detail_view` — detail page shows every field incl. `description`/`notes`, a link back to the parent Project, and a `#page-errors` container in the rendered HTML; `404` when the Group-task is missing or soft-deleted (depends on: T028, T029)

**Checkpoint**: Every Group-task has a working detail page with the full field set and the future error area in place.

---

## Phase 6: User Story 4 - Edit a Group-task's fields (Priority: P2)

**Goal**: Every field, including `serial_num` and `status`, is editable with the same project-scoped validation rules as create.

**Independent Test**: Edit each field on an existing Group-task (incl. `serial_num`, `status`) and confirm changes persist in both the nested list and detail view; confirm scoping (a conflict within the same Project is rejected, the identical value under a different Project is not).

### Implementation for User Story 4

- [X] T031 [US4] Implement `update_group_task(session, project_id, group_task_id, *, serial_num, title, description, start_date=None, finished_date=None, notes=None, status)` in `app/services.py`: calls `_validate_group_task_fields` (T008), `_check_group_task_serial_num_conflict` treating an edit to the Group-task's own current value as a no-op (FR-007), `_check_group_task_title_conflict` (T009), free-form `status` transitions (FR-010); raises `GroupTaskNotFoundError` if missing (depends on: T008, T009, T010, T027)
- [X] T032 [US4] `GET /projects/{project_id}/group-tasks/{group_task_id}/edit` in `app/routers/group_tasks.py`: `project: Project = Depends(get_active_project_or_404)`, then `get_active_group_task` or `404`, renders `group_tasks/edit.html` pre-filled (depends on: T027, T005)
- [X] T033 [US4] `PUT /projects/{project_id}/group-tasks/{group_task_id}` in `app/routers/group_tasks.py`: calls `update_group_task`; same success (`HX-Redirect: /projects/{project_id}`) / failure (OOB `#form-errors`) contract as create; `404` per the shared dependency and `GroupTaskNotFoundError` (depends on: T031, T032)
- [X] T034 [US4] Create `app/templates/group_tasks/edit.html`: extends `base.html`, includes `_group_task_form.html` pre-filled, configured to `hx-put="/projects/{{ project.id }}/group-tasks/{{ group_task.id }}"` (depends on: T017, T032)

### Tests for User Story 4

- [X] T035 [P] [US4] `tests/unit/test_group_task_service.py::test_update_scoped_conflicts_and_status` — editing `serial_num`/`title` to a value already used by another active Group-task *in the same Project* is rejected and the original value is retained; editing to its own current value is a no-op success; the identical `serial_num`/`title` succeeds when the conflicting Group-task is under a *different* Project; bad date ordering rejected on edit; any `status` → any other `status` succeeds (depends on: T031)
- [X] T036 [US4] `tests/integration/test_group_task_routes.py::test_us4_edit_flow` — `GET` edit form is pre-filled; `PUT` success redirects to the parent Project; `PUT` validation failure returns the OOB `#form-errors` fragment (depends on: T033, T034)

**Checkpoint**: Every Group-task field, including `serial_num` and `status`, is editable with correct per-Project scoping.

---

## Phase 7: User Story 5 - Soft-delete a Group-task from its own detail page (Priority: P2)

**Goal**: Delete lives only on the Group-task's own detail page (mirroring `002`'s relocation of Project's own delete control), redirecting back to the parent Project on success.

**Independent Test**: Trigger delete from a Group-task's detail page, confirm the browser ends up on the parent Project's detail page with the Group-task no longer listed and its own detail URL now 404ing.

### Implementation for User Story 5

- [X] T037 [US5] `DELETE /projects/{project_id}/group-tasks/{group_task_id}` in `app/routers/group_tasks.py`: `project: Project = Depends(get_active_project_or_404)`, calls `soft_delete_group_task` (T023); on success `200` + `HX-Redirect: /projects/{project_id}`; `404` per the shared dependency and `GroupTaskNotFoundError` (depends on: T023, T005)
- [X] T038 [US5] Modify `app/templates/group_tasks/detail.html`: add the delete control — `hx-delete="/projects/{{ project.id }}/group-tasks/{{ group_task.id }}"`, `hx-swap="none"`, `hx-confirm="Delete this group-task?"` (depends on: T029, T037)

### Tests for User Story 5

- [X] T039 [US5] `tests/integration/test_group_task_routes.py::test_us5_soft_delete_flow` — delete control carries `hx-confirm`; `DELETE` returns `HX-Redirect` to the parent Project's detail page; the Group-task no longer appears in the nested list and its own detail URL now `404`s; the nested list's rendered HTML contains no `hx-delete` attribute anywhere (depends on: T037, T038)

**Checkpoint**: Deleting a Group-task is only reachable from its own detail page; the nested list remains pure navigation, mirroring Project's own established pattern.

---

## Phase 8: User Story 6 - Relocated Deleted Items view (Priority: P3)

**Goal**: A single `/deleted` view lists soft-deleted Projects and soft-deleted Group-tasks in two labeled sections, the latter grouped by (and correctly identifying) parent Project even if that parent is later also soft-deleted.

**Independent Test**: Soft-delete a Project and a Group-task (under a different, active Project), visit `/deleted`, confirm both sections render correctly with the Group-task's parent identified by serial_num/title.

### Implementation for User Story 6

- [X] T040 [US6] Implement `list_deleted_group_tasks_grouped_by_project(session)` in `app/services.py`: `SELECT * FROM group_task WHERE deleted = true`, resolve each row's parent Project via `session.get(Project, project_id)` **ignoring the parent's own `deleted` flag** (so a Group-task's entry still resolves correctly even if its parent Project is later also soft-deleted, per US6 acceptance scenario 4); group by parent ascending by the parent's own `serial_num`, Group-tasks within each group ascending by their own `serial_num` (FR-027, FR-028) (depends on: T001)
- [X] T041 [US6] Create `app/routers/deleted.py`: `GET /deleted` calling `services.list_deleted_projects()` and `services.list_deleted_group_tasks_grouped_by_project()`, rendering `deleted.html` with both result sets (depends on: T040)
- [X] T042 [US6] Mount the new router in `app/main.py`: `app.include_router(deleted.router)` (depends on: T041)
- [X] T043 [US6] Remove the `GET /projects/deleted` route from `app/routers/projects.py` — relocated, not aliased; no redirect is kept (FR-025) (depends on: T041)
- [X] T044 [US6] Create `app/templates/deleted.html` (top-level `templates/`, not under `projects/`): a "Deleted Projects" section (reuses `partials/_project_row.html` with `readonly=true`, unchanged behavior from 001/002) and a separate "Deleted Group-tasks" section — plain read-only text (no links, no edit/restore), each row showing the Group-task's own `serial_num`/`title` plus its parent Project's `serial_num`/`title`, grouped and ordered per T040 (depends on: T040)
- [X] T045 [US6] Delete `app/templates/projects/deleted.html` — its content is now in `deleted.html` (T044), not duplicated (depends on: T044)
- [X] T046 [US6] Update the existing "Deleted items" link in `app/templates/projects/list.html` to point at `/deleted` instead of `/projects/deleted` (depends on: T041)

### Tests for User Story 6

- [X] T047 [US6] Create `tests/integration/test_deleted_routes.py` — `GET /deleted` renders both sections; "Deleted Projects" behavior is unchanged from 001/002 (ascending `serial_num`); "Deleted Group-tasks" entries are grouped by parent ascending by the parent's `serial_num` with Group-tasks ascending by their own `serial_num` within each group; a Group-task's parent is still correctly identified after that parent Project is also later soft-deleted; `GET /projects/deleted` no longer resolves (depends on: T041, T042, T043, T044, T045, T046)

**Checkpoint**: `/deleted` is the single, correct source of soft-deleted history for both entities; the old URL is fully retired.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Confirm no regression to unrelated Project behavior and that the full slice validates end-to-end, including the cross-cutting FR-015a (parent-404) and FR-008a (blank/whitespace) rules that apply across every story above.

- [X] T048 Run `pytest tests/unit tests/integration` and confirm all pass, with no regression to Project's create/list/edit/detail behavior beyond the two documented retrofit changes (US2, US6) (depends on: T001–T047)
- [X] T049 Execute quickstart.md's manual validation scenarios (US1–US6) end-to-end, including the cross-cutting stale/direct-navigation 404 checks (FR-015a: detail/edit/delete/create routes 404 when `project_id` no longer resolves to an active Project) and the blank/whitespace rejection checks (FR-008a) (depends on: T048)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup**: Not applicable (Phase 1).
- **Foundational (Phase 2)**: No dependency on any user story; BLOCKS US1, US3, US4, US5 (all add routes to `group_tasks.py`, which needs T001 and T005). US2's service-layer retrofit (T022) only needs T001 (the table must exist for the existence check to query it); US6 similarly only needs T001.
- **User Story 1 (Phase 3, P1)**: Depends on Foundational only.
- **User Story 2 (Phase 4, P1)**: Depends on Foundational; its *Independent Test* additionally exercises US1 (to create a Group-task to block on) and US2's own T023 (to resolve the block) — both already present within this phase's own tasks, so the story is self-contained once Phase 3 has run.
- **User Story 3 (Phase 5, P2)**: Depends on Foundational; independent of US1/US2 except that a Group-task must exist to view (created via US1's routes in practice, but T027/T028/T029 have no code dependency on US1's tasks).
- **User Story 4 (Phase 6, P2)**: Depends on Foundational and on T027 (from US3, reused rather than reimplemented) and T008–T010 (from US1, reused rather than reimplemented).
- **User Story 5 (Phase 7, P2)**: Depends on Foundational, on T023 (US2's `soft_delete_group_task`, built there since US2's own Independent Test needs it first) and on T029 (US3's detail template, extended here with the delete control).
- **User Story 6 (Phase 8, P3)**: Depends on Foundational only for T040; its integration test (T047) also depends on US2's retrofit having been implemented if the test scenario soft-deletes a Project (it does, per US6 acceptance scenario 4), so Phase 4 should precede Phase 8 in practice even though there's no direct code dependency.
- **Polish (Phase 9)**: Depends on all six user stories being complete.

### Within Each User Story

- US1: T008–T010 (validation/conflict helpers) before T011 (create, which calls them); T012 independent of T008–T011 but same file. T013/T014 (routes) depend on T011. T015 (nested list on Project's own route) depends on T012 only. T016/T017 (partials) have no dependency on each other or on the service layer. T018 depends on T017; T019 depends on T015 and T016. Tests (T020, T021) come last.
- US2: T022 and T023 are independent additions to the same file (`services.py`); T024 depends on T022 only. Tests (T025, T026) come last.
- US3: T027 → T028 → T029, strictly sequential (each is the prerequisite of the next). Test (T030) last.
- US4: T031 depends on T008–T010 (US1) and T027 (US3); T032 depends on T027/T005; T033 depends on T031/T032; T034 depends on T017 (US1)/T032. Tests (T035, T036) last.
- US5: T037 depends on T023 (US2)/T005; T038 depends on T029 (US3)/T037. Test (T039) last.
- US6: T040 first (no dependency within this story); T041 depends on T040; T042/T043/T046 depend on T041; T044 depends on T040; T045 depends on T044. Test (T047) last, after every implementation task in this phase.

### Parallel Opportunities

- T005 and T007 (Foundational) can run in parallel with the migration sequence T002→T003→T004 — different files, same single dependency on T001.
- T016 and T017 (US1 partials) can run in parallel with each other and with T008–T012 (US1 service layer) — disjoint files.
- T020 (US1 unit test) can run in parallel with implementation tasks it doesn't depend on, once T011/T012 are done.
- T025 (US2 unit test) can run in parallel with T024 (US2 router change) once its own dependencies (T011, T022, T023) are done.
- T035 (US4 unit test) can run in parallel with T032–T034 (US4 routes/template) once T031 is done.

---

## Parallel Example: Foundational phase

```bash
# After T001 (GroupTask model) is done, these three can proceed together:
Task: "Generate + review + apply the group_task migration (T002-T004, sequential within itself)"
Task: "Scaffold app/routers/group_tasks.py with get_active_project_or_404 (T005)"
Task: "Update tests/conftest.py to import GroupTask (T007)"
```

## Parallel Example: User Story 1

```bash
# Once Foundational is complete, these can proceed together:
Task: "Implement _validate_group_task_fields, conflict checks, create_group_task, list_active_group_tasks in app/services.py (T008-T012)"
Task: "Create app/templates/partials/_group_task_row.html (T016)"
Task: "Create app/templates/partials/_group_task_form.html (T017)"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 2 (Foundational).
2. Complete Phase 3 (User Story 1: T008–T021).
3. **STOP and VALIDATE**: a Group-task can be created under any Project and appears in that Project's nested list, correctly scoped per-parent. Note that until Phase 4 (US2) lands, Project deletion remains unconditionally successful even with active Group-tasks present — a valid intermediate state, not a broken one, but the feature's stated cascade-blocking purpose isn't yet active.

### Incremental Delivery

1. Foundational → table + shared dependency exist.
2. US1 → Group-tasks can be created and seen (MVP).
3. US2 → cascade-block activates; this is the other half of this feature's stated purpose (activating the retrofit hook) and should land as soon after US1 as possible.
4. US3 → full detail view.
5. US4 → editing.
6. US5 → delete relocated to the Group-task's own detail page (also the second thing US2's Independent Test needs to fully resolve a block).
7. US6 → `/deleted` relocation and aggregation, last since it's P3 and depends only on soft-deleted data existing from the stories above.
8. Phase 9 → full regression pass and quickstart sign-off.

Because this feature's own framing names two things it exists to deliver — the Group-task entity itself (US1/US3/US4/US5) and the retrofit hook activation (US2) — treat **Phases 3 and 4 together** as the feature's true minimum meaningful state, exactly as `002`'s own tasks.md treated its two P1 stories together.

---

## Notes

- `[P]` tasks = different files, no unresolved dependency on another incomplete task
- `[US#]` labels map tasks to spec.md's user stories for traceability
- Commit after each task or logical group
- Stop at any phase checkpoint to validate story independently
- `app/models.py`'s `Project` class itself is not modified by any task in this list (no new fields) — only its *behavior* changes, via the `soft_delete_project` retrofit in `app/services.py` (T022)
- Task remains entirely unmodeled — no task in this list references it, per FR-029
