---

description: "Task list template for feature implementation"
---

# Tasks: Relocate Project Deletion from List to Detail View

**Input**: Design documents from `/specs/002-relocate-project-delete/` (plan.md, research.md, data-model.md, contracts/projects-delete-contract.md, quickstart.md, spec.md)

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/projects-delete-contract.md, quickstart.md — all present

**Tests**: Included — this feature extends `tests/integration/test_projects_routes.py` per the technical plan and per each user story's Independent Test criteria. No new unit tests: `app/services.py` is not modified in this cycle.

**Organization**: Tasks are grouped by user story (from spec.md), in priority order (P1, P1, P2).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no unresolved dependency on another incomplete task in this list)
- **[Story]**: Which user story this task serves (US1–US3), per spec.md
- File paths are relative to repo root

## Path Conventions

Single project, reusing the existing `app/` package and `tests/` layout from 001-project-management verbatim. No new directories.

---

## Phase 1: Setup

Not applicable — this feature introduces no new dependency, project structure, or tooling. It modifies one existing route handler and two existing templates, and adds one new template partial, all within the existing `app/` package from 001-project-management.

## Phase 2: Foundational

Not applicable — there is no shared infrastructure or blocking prerequisite common to all three user stories below; each story's tasks touch disjoint files (except where a same-file dependency is called out explicitly in that story's phase).

---

## Phase 3: User Story 1 - Delete a project from its detail page (Priority: P1) 🎯 MVP

**Goal**: A user can trigger a soft-delete from a single project's own detail page, and on success is returned to the active project list — since the detail page can no longer represent a project that was just deleted.

**Independent Test**: Open an active project's detail page, trigger its delete control, and confirm the browser ends up on `/projects` with the project no longer listed and its own detail URL now 404ing.

### Implementation for User Story 1

- [ ] T001 [US1] In `app/routers/projects.py`, change `DELETE /projects/{id}`'s success response from a bare `Response(status_code=200)` to `Response(status_code=200, headers={"HX-Redirect": "/projects"})`; leave the `ProjectNotFoundError` → `404` path unchanged (depends on: none — route already exists from 001-project-management)
- [ ] T002 [US1] In `app/templates/projects/detail.html`, add a delete control with `hx-delete="/projects/{{ project.id }}"`, `hx-swap="none"`, `hx-confirm="Delete this project?"` (depends on: none — template already exists from 001-project-management)

### Tests for User Story 1

- [ ] T003 [US1] In `tests/integration/test_projects_routes.py`, extend `test_us4_soft_delete_and_deleted_items_flow` (or add a focused assertion alongside it) to confirm the `DELETE` response carries `HX-Redirect: /projects` on success (depends on: T001)

**Checkpoint**: Deleting from the detail page works end-to-end and redirects to `/projects`; the existing 404 not-found path is unchanged.

---

## Phase 4: User Story 2 - Project list becomes pure navigation (Priority: P1)

**Goal**: The active project list offers no destructive control anywhere — only navigation (title link to detail, Edit link) — so deleting is reachable only by first opening a project's own detail page.

**Independent Test**: Load `/projects`, inspect every row, and confirm no delete/destructive control is present or reachable, while the title and Edit links still work.

### Implementation for User Story 2

- [ ] T004 [P] [US2] In `app/templates/partials/_project_row.html`, remove the delete control (`hx-delete`, `hx-target`, `hx-swap`, `hx-confirm` button) entirely, keeping only the title link to detail and the Edit link (depends on: none — independent of Phase 3's files)

### Tests for User Story 2

- [ ] T005 [US2] In `tests/integration/test_projects_routes.py`, add a test confirming the rendered `/projects` list page's HTML contains no `hx-delete` attribute anywhere (depends on: T004)

**Checkpoint**: The active list is pure navigation; deleting a project is only possible via that project's own detail page (Phase 3).

---

## Phase 5: User Story 3 - Detail page is ready to surface a future delete-rejection message (Priority: P2)

**Goal**: Every project detail page includes a standing, always-present, currently-empty in-place error-message area, so a later cascade-blocking rule (once Group-task exists) can reject a delete and explain why without further UI work.

**Independent Test**: Load any active project's detail page and confirm a designated error-message container is present in the rendered HTML (empty, since no rule can reject a delete yet).

### Implementation for User Story 3

- [ ] T006 [P] [US3] Create `app/templates/partials/_page_errors.html`: an out-of-band container, `id="page-errors"`, `hx-swap-oob="true"`, empty by default, structurally parallel to `_form_errors.html` but named distinctly since it's for page-level (non-form) action errors (depends on: none)
- [ ] T007 [US3] Include `_page_errors.html` once in `app/templates/projects/detail.html`, always present (depends on: T006, T002 — same file as User Story 1's delete control, edited after it)

### Tests for User Story 3

- [ ] T008 [US3] In `tests/integration/test_projects_routes.py`, add a test confirming a project detail page's rendered HTML contains an `id="page-errors"` container (depends on: T007)

**Checkpoint**: Every detail page load includes the ready error-message area; it remains unused this cycle since no rule can currently reject a delete.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Confirm no regression to unrelated behavior and that the full slice validates end-to-end.

- [ ] T009 Run `pytest tests/unit tests/integration` and confirm all pass, with no regression to list/create/edit/Deleted Items behavior (FR-009) (depends on: T001–T008)
- [ ] T010 Execute quickstart.md's manual validation scenarios (US1–US3) end-to-end as a final sanity pass (depends on: T009)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup / Foundational**: Not applicable (see Phase 1/2 above) — user story work can start immediately.
- **User Story 1 (Phase 3, P1)**: No dependency on other stories.
- **User Story 2 (Phase 4, P1)**: No dependency on other stories; touches only `_project_row.html`, fully disjoint from Phase 3's files.
- **User Story 3 (Phase 5, P2)**: Independent in principle (its own new partial, T006), but T007's inclusion of that partial into `detail.html` must happen after T002 (User Story 1's edit to the same file).
- **Polish (Phase 6)**: Depends on all three stories being complete.

### Within Each User Story

- User Story 1: T001 (route) and T002 (template) are independent edits to different files and could be done in either order, but both are needed before T003 (test) can pass.
- User Story 2: T004 before T005 (test needs the template change in place).
- User Story 3: T006 (new partial) can happen any time; T007 (include it in `detail.html`) must come after both T006 and T002; T008 (test) after T007.

### Parallel Opportunities

- T004 (User Story 2) can run in parallel with all of Phase 3 (User Story 1) — disjoint files.
- T006 (User Story 3's new partial) can run in parallel with Phase 3 and Phase 4 — it's a brand-new file with no dependency on either.
- T001 and T002 (both User Story 1) touch different files and can proceed in parallel.

---

## Parallel Example: Cross-story

```bash
# These can be done together, since they touch disjoint files:
Task: "Change DELETE /projects/{id} success response in app/routers/projects.py"        # T001, US1
Task: "Remove delete control from app/templates/partials/_project_row.html"              # T004, US2
Task: "Create app/templates/partials/_page_errors.html"                                  # T006, US3
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 3 (User Story 1: T001–T003).
2. **STOP and VALIDATE**: deleting from the detail page works and redirects to `/projects`. Note that until Phase 4 also lands, the list row's old delete control is still present alongside the new detail-page one — this is a valid intermediate state, not a broken one, but User Story 2 is needed to satisfy FR-001 fully.

### Incremental Delivery

1. Phase 3 (US1) → detail-page delete works.
2. Phase 4 (US2) → list-level delete control removed; the relocation is functionally complete (FR-001–FR-004, FR-006–FR-009 all satisfied).
3. Phase 5 (US3) → the forward-looking error-message area is in place, ready for a later cycle's rule.
4. Phase 6 → full regression pass and quickstart sign-off.

Because FR-001 ("list MUST NOT provide any delete control") is only fully satisfied once Phase 4 lands, treat **Phases 3 and 4 together** as this feature's true minimum complete state — Phase 3 alone is a useful, independently-testable increment, but not sufficient on its own to close out the spec.

---

## Notes

- `[P]` tasks = different files, no unresolved dependency on another incomplete task
- `[US#]` labels map tasks to spec.md's user stories for traceability
- Commit after each task or logical group
- Stop at any phase checkpoint to validate story independently
- `app/services.py` (specifically `soft_delete_project`) and `app/models.py` are not touched by any task in this list — the delete rule itself is unchanged (FR-006)
