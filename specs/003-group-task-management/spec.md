# Feature Specification: Group-task Management

**Feature Branch**: `003-group-task-management`

**Created**: 2026-07-08

**Status**: Draft

**Input**: User description: "Feature: Group-task management (second vertical slice of Strata's 3-level hierarchy). Build the Group-task entity as a complete vertical slice, nested under Project — model, persistence, and UI — with no dependency yet on Task. This slice also activates a previously-prepared retrofit hook on Project's deletion logic: a Project cannot be soft-deleted while it has any active Group-tasks. Group-task itself cannot yet block on active Tasks (Task doesn't exist), so its own soft-delete stays unconditional this cycle, mirroring how Project's soft-delete was unconditional before the prior cycle. Includes a nested Group-task list on the Project detail page, dedicated create/detail/edit pages for Group-task, delete relocated to the Group-task's own detail page (redirecting back to the parent Project), and a renamed global Deleted Items view at /deleted showing soft-deleted Projects and soft-deleted Group-tasks as two separate sections."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Create a Group-task and see it under its Project (Priority: P1)

A user opens an active Project and adds a Group-task to it by supplying a title and description; the new Group-task immediately appears in that Project's own nested list, ordered by serial number.

**Why this priority**: Without the ability to create and see Group-tasks scoped to a Project, no other capability in this slice — viewing, editing, deleting, or cascade-blocking — has anything to act on.

**Independent Test**: Can be fully tested by opening an active Project with no Group-tasks yet, creating one with only the required fields, and confirming it appears in that Project's nested list with serial_num 0, status "new", while a Group-task with the same title created under a *different* Project succeeds without conflict.

**Acceptance Scenarios**:

1. **Given** an active Project with no Group-tasks yet, **When** a user creates a Group-task under it with a title and description, **Then** it is saved with serial_num 0, status "new", and appears in that Project's nested Group-task list.
2. **Given** a Project already has active Group-tasks with serial_num 0..N, **When** a user creates another Group-task under the same Project, **Then** the new one is auto-assigned serial_num (max active serial_num within that Project) + 1.
3. **Given** a Group-task titled "Design Review" already exists (active) under Project A, **When** a user creates another active Group-task titled "Design Review" under Project A, **Then** the creation is rejected with a validation error.
4. **Given** a Group-task titled "Design Review" already exists (active) under Project A, **When** a user creates a Group-task titled "Design Review" under Project B, **Then** the creation succeeds, since title uniqueness is scoped per Project.
5. **Given** a user attempts to create a Group-task without a title or without a description, **When** the create action is submitted, **Then** the creation is rejected with a validation error and the form is left in place, unchanged, via the established out-of-band error pattern.
6. **Given** a user attempts to create a Group-task with a title or description consisting only of whitespace, **When** the create action is submitted, **Then** the creation is rejected with the same validation error as a fully blank field.
7. **Given** a stale or hand-typed link to the create-Group-task page for a Project that no longer exists or has been soft-deleted, **When** a user follows that link (or submits to it directly), **Then** the request 404s rather than creating a Group-task under a nonexistent or deleted parent.

---

### User Story 2 - A Project cannot be deleted while it has active Group-tasks (Priority: P1)

A user tries to soft-delete a Project that still has active Group-tasks underneath it, and is stopped with a clear explanation instead of silently orphaning that work.

**Why this priority**: This is the rule that this slice exists to activate — the previously-prepared error area on the Project detail page was built specifically for this check, and it must take effect the moment Group-tasks exist, otherwise Project deletion still silently discards live child work.

**Independent Test**: Can be fully tested by creating a Group-task under an active Project, attempting to soft-delete that Project and confirming rejection with an explanatory message, then soft-deleting the Group-task and confirming the same Project can now be soft-deleted successfully.

**Acceptance Scenarios**:

1. **Given** an active Project with at least one active Group-task, **When** a user attempts to soft-delete that Project, **Then** the deletion is rejected, the Project remains active, and a clear message (e.g., "Cannot delete: this project still has active group-tasks") appears in the Project detail page's standing error area.
2. **Given** an active Project whose only Group-task has just been soft-deleted, **When** a user attempts to soft-delete that Project, **Then** the deletion succeeds, since no active Group-tasks remain.
3. **Given** an active Project with no Group-tasks at all, **When** a user attempts to soft-delete it, **Then** the deletion succeeds exactly as it did before this feature existed.

---

### User Story 3 - View a Group-task's full details (Priority: P2)

A user opens a single Group-task from its parent Project's nested list to see every one of its fields, including description and notes, which are deliberately left out of the nested list row.

**Why this priority**: Once Group-tasks can be created, users need to inspect full detail beyond the summary row — this is also where the delete control and the future Task-rejection message area live, so later stories depend on this page existing.

**Independent Test**: Can be fully tested by creating a Group-task, opening its detail page via the link in the parent Project's nested list, and confirming every field is displayed accurately, along with a link back to the parent Project.

**Acceptance Scenarios**:

1. **Given** an active Group-task exists under a Project, **When** a user opens its detail view, **Then** all of its fields (serial_num, title, description, start_date, finished_date, notes, status) are displayed, including optional fields left blank, plus a link back to the parent Project.
2. **Given** a Group-task's detail page is open, **When** the page renders, **Then** a standing, always-present (currently empty) error-message area is present, ready for a future Task-existence check.
3. **Given** a stale or hand-typed link to a Group-task's detail, edit, or delete route whose parent Project no longer exists or has been soft-deleted, **When** a user follows that link (or submits to it directly), **Then** the request 404s, even if the Group-task's own identifier would otherwise be valid.

---

### User Story 4 - Edit a Group-task's fields (Priority: P2)

A user updates any field on an existing Group-task, including its serial_num or status, as the work item evolves.

**Why this priority**: Group-tasks change over time just as Projects do; editing matters once creation and viewing already work, and is required before deletion scenarios are meaningfully testable against realistic data.

**Independent Test**: Can be fully tested by editing each field on an existing Group-task (including serial_num and status) and confirming the changes persist and are reflected in both the nested list and the detail view.

**Acceptance Scenarios**:

1. **Given** an active Group-task, **When** a user edits its status to any other allowed value, **Then** the change is accepted with no restriction on the transition.
2. **Given** two active Group-tasks under the same Project with serial_num 1 and 2, **When** a user edits the second one's serial_num to 1, **Then** the edit is rejected with a validation error and its serial_num remains 2.
3. **Given** an active Group-task with serial_num 4, **When** a user edits its serial_num to 4 (its own current value), **Then** the edit succeeds as a no-op, not a conflict.
4. **Given** an active Group-task with start_date set and finished_date blank, **When** a user sets finished_date to a date earlier than start_date, **Then** the edit is rejected with a validation error.
5. **Given** an active Group-task under Project A titled "Design Review" and an active Group-task under Project B also titled "Design Review", **When** a user edits either one's title to any other unique value within its own Project, **Then** the edit succeeds, unaffected by the other Project's Group-task.

---

### User Story 5 - Soft-delete a Group-task from its own detail page (Priority: P2)

A user removes a Group-task they no longer want active, from that Group-task's own detail page, and is returned to the parent Project's detail page.

**Why this priority**: Deletion is the mechanism that resolves User Story 2's cascade-block, and — mirroring the Project slice's own prior relocation — must live only on the entity's own detail page, not in the nested list row.

**Independent Test**: Can be fully tested by opening an active Group-task's detail page, triggering its delete control, and confirming the browser ends up back on the parent Project's detail page with the Group-task no longer listed there and its own detail URL now 404ing.

**Acceptance Scenarios**:

1. **Given** an active Group-task's detail page is open, **When** a user triggers its delete control, **Then** a confirmation prompt appears, and on confirming, the Group-task is soft-deleted and the browser is redirected to its parent Project's detail page (`/projects/{project_id}`).
2. **Given** a Group-task has just been soft-deleted, **When** a user reloads its parent Project's detail page, **Then** the Group-task no longer appears in the nested list, and its own detail URL now 404s.
3. **Given** a Project's nested Group-task list is rendered, **When** a user inspects any row, **Then** no delete control is present — only a link to the Group-task's detail page and a separate Edit link.

---

### User Story 6 - Relocated Deleted Items view shows both deleted Projects and Group-tasks (Priority: P3)

A user visits a single, renamed Deleted Items page to see every soft-deleted Project and every soft-deleted Group-task, the latter grouped under and labeled by its original parent Project for context.

**Why this priority**: This view is valuable read-only history, but only becomes meaningfully richer once Group-tasks exist to delete — it depends on User Story 5 and is not on the critical path to the feature's core value (creation and cascade-blocking).

**Independent Test**: Can be fully tested by soft-deleting a Project and a Group-task (under a different, still-active Project), visiting `/deleted`, and confirming both appear in their own clearly labeled section, with the Group-task's parent Project identified by serial_num and title.

**Acceptance Scenarios**:

1. **Given** the existing Deleted Items link previously pointed at `/projects/deleted`, **When** a user follows that link after this feature ships, **Then** it now points at `/deleted` and the page loads successfully.
2. **Given** one or more soft-deleted Projects exist, **When** a user opens `/deleted`, **Then** they appear in a "Deleted Projects" section exactly as they did before this feature, ordered ascending by serial_num.
3. **Given** one or more soft-deleted Group-tasks exist across different parent Projects, **When** a user opens `/deleted`, **Then** they appear in a separate "Deleted Group-tasks" section as plain, non-editable text showing each Group-task's serial_num and title plus its parent Project's serial_num and title, grouped by parent Project (groups ordered ascending by the parent Project's serial_num, and Group-tasks within each group ordered ascending by their own serial_num).
4. **Given** a Group-task's parent Project is later also soft-deleted, **When** a user opens `/deleted`, **Then** the Group-task's entry still correctly identifies that parent Project by its frozen serial_num and title.

---

### Edge Cases

- What happens when a Group-task is created for the very first time ever under a given Project? Its serial_num MUST be assigned 0, independent of serial_num values used by Group-tasks under any other Project.
- What happens when a Project's nested Group-task list has no active Group-tasks? The nested list MUST display an empty state rather than an error.
- What happens when a Group-task's serial_num is edited to match its own current value? This MUST be treated as a no-op success, not a conflict.
- What happens when a Group-task with the highest serial_num under a Project is soft-deleted, then a new Group-task is created under that same Project? The new Group-task's serial_num is computed only from that Project's remaining active Group-tasks, so it MAY reuse a numeric value a now-deleted Group-task still displays (frozen) in the Deleted Items view.
- What happens when a user attempts to soft-delete a Project whose Group-tasks are all already soft-deleted? The deletion MUST succeed, since the cascade-block only counts active Group-tasks.
- What happens when a user attempts to soft-delete a Group-task that is already soft-deleted? This MUST NOT be reachable — soft-deleted Group-tasks offer no delete action since they only appear in the read-only Deleted Items view.
- What happens to a Group-task's own soft-delete attempt in this slice? It MUST succeed unconditionally, since no active-Task check can exist yet (Task is out of scope); this mirrors Project's own unconditional soft-delete prior to this cycle.
- What happens when the same title or serial_num is used by Group-tasks under two different Projects? This MUST be permitted, since both uniqueness rules are scoped to the parent Project, not global.
- What happens when any nested Group-task route (nested list rendering on the Project detail page, create, detail, edit, or delete) is reached via direct navigation — a stale bookmark or typed URL — whose parent Project no longer exists or has been soft-deleted? Every such route MUST 404, not just the case where the Group-task itself is missing.
- What happens when a user submits a title or description containing only whitespace (spaces, tabs, newlines)? This MUST be rejected exactly as a fully blank field would be, on both create and edit.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow creating a new Group-task under a specific, active parent Project by supplying a required title and required description; start_date, finished_date, and notes are optional at creation.
- **FR-002**: System MUST require every Group-task to belong to exactly one parent Project at creation, and MUST NOT allow a Group-task to be reassigned to a different Project afterward.
- **FR-003**: System MUST default a newly created Group-task's status to "new".
- **FR-004**: System MUST auto-assign each new Group-task's serial_num as (the maximum serial_num among currently active Group-tasks under the same parent Project) + 1, or 0 if that Project has no active Group-tasks yet.
- **FR-005**: System MUST enforce title uniqueness among active Group-tasks within the same parent Project only, allowing the same title to be reused by Group-tasks under different Projects.
- **FR-006**: System MUST enforce serial_num uniqueness among active Group-tasks within the same parent Project only, rejecting an edit that would set a Group-task's serial_num to a value already used by a different active Group-task in the same Project, and leaving the existing serial_num unchanged when rejected.
- **FR-007**: System MUST accept an edit that sets a Group-task's serial_num to its own current value without treating it as a conflict.
- **FR-008**: System MUST enforce a maximum title length of approximately 200 characters and a maximum description length of approximately 2000 characters, rejecting values that exceed either.
- **FR-008a**: System MUST reject a title or description that is blank or consists only of whitespace, on both create and edit, matching the same rule already enforced for Project — built into Group-task's service layer from the start, not deferred.
- **FR-009**: System MUST validate, whenever both start_date and finished_date are present on a Group-task, that finished_date is not before start_date, rejecting any create or edit that violates this; both fields remain independently optional.
- **FR-010**: System MUST restrict a Group-task's status to the same six values as Project (new, in-progress, complete, blocked, deferred, archived), defaulting to "new", with free-form transitions between any two values at any time.
- **FR-011**: System MUST provide a single free-text notes field per Group-task that can be edited at any time.
- **FR-012**: System MUST allow a Group-task to be soft-deleted regardless of its current status, unconditionally in this slice (no check for active Tasks, since Task does not yet exist); this check is explicitly deferred to a future slice.
- **FR-013**: System MUST NOT provide any mechanism to permanently (hard) delete a Group-task, and MUST NOT provide any un-delete mechanism.
- **FR-014**: System MUST freeze a Group-task's serial_num at its last active value at the moment of soft-deletion.
- **FR-015**: System MUST exclude soft-deleted Group-tasks from the parent Project's nested list and from direct detail-page access (a request for a soft-deleted Group-task's detail page MUST 404).
- **FR-015a**: System MUST return a 404 from every nested Group-task route — nested list rendering on the Project detail page, create, detail, edit, and delete — whenever the referenced parent Project does not exist or is soft-deleted, not only when the Group-task itself is missing; this covers direct navigation to a nested Group-task URL (e.g., a stale bookmark or typed link) whose parent Project is gone.
- **FR-016**: System MUST reject an attempt to soft-delete a Project while it has any active (non-deleted) Group-tasks, leaving the Project active, and MUST surface a clear rejection message (e.g., "Cannot delete: this project still has active group-tasks") via the Project detail page's existing standing error-message area.
- **FR-017**: System MUST allow a Project to be soft-deleted once it has zero active Group-tasks, whether because none were ever created or because all have been soft-deleted.
- **FR-018**: System MUST display, on each Project's detail page, a nested table of that Project's active Group-tasks ordered ascending by serial_num, showing only serial_num, title, status, start_date, and finished_date per row (description and notes excluded from this summary view).
- **FR-019**: System MUST provide, on each row of the nested Group-task list, a link to that Group-task's own detail page and a separate Edit link, and MUST NOT provide any delete control on that row.
- **FR-020**: System MUST provide a dedicated create page for a Group-task, scoped to one parent Project, submitted via an HTMX form; on success it MUST redirect back to that parent Project's detail page, and on validation failure it MUST respond using the same out-of-band error-banner pattern established for Project (200 OK, OOB error fragment, form left in place, no destructive swap).
- **FR-021**: System MUST provide a dedicated detail page for a single Group-task showing every one of its fields (including description and notes), a link back to its parent Project, an Edit link, and the sole soft-delete control for that Group-task.
- **FR-022**: System MUST include, on every Group-task detail page, a standing, always-present (currently empty) error-message container mirroring the Project detail page's pattern, reserved for a future active-Task rejection message.
- **FR-023**: System MUST provide a dedicated edit page for a single Group-task, allowing every field (including serial_num and status) to be edited, using the same validation rules and out-of-band error pattern as create; on success it MUST redirect back to the parent Project's detail page.
- **FR-024**: System MUST trigger a Group-task's soft-delete only from that Group-task's own detail page (via a confirm-guarded control), and on success MUST redirect the browser to the parent Project's detail page.
- **FR-025**: System MUST relocate the global Deleted Items view from its prior URL to `/deleted`, and MUST update the one existing link that pointed to the prior URL to point at `/deleted` instead.
- **FR-026**: System MUST display, on the `/deleted` view, a "Deleted Projects" section behaving exactly as the prior Deleted Items view did, and a separate, clearly labeled "Deleted Group-tasks" section.
- **FR-027**: System MUST show, for each entry in the Deleted Group-tasks section, that Group-task's serial_num and title plus its parent Project's serial_num and title, as plain read-only text with no links and no edit or restore action.
- **FR-028**: System MUST group Deleted Group-tasks section entries by parent Project, ordering groups ascending by the parent Project's own serial_num, and ordering Group-tasks within each group ascending by their own serial_num.
- **FR-029**: System MUST NOT introduce, expose, or reference any Task concept as part of this slice.
- **FR-030**: System MUST NOT provide any mechanism to reassign a Group-task from one Project to another, now or in any future slice per current design intent.
- **FR-031**: System MUST NOT require user authentication or support multiple distinct user accounts for this slice.

### Key Entities

- **Group-task**: Represents a unit of work nested one level under a Project in Strata's hierarchy. Attributes: project_id (required reference to its parent Project, immutable after creation), serial_num (integer, user-editable, unique among active Group-tasks within the same parent Project, default ordering key within that Project), title (required, unique among active Group-tasks within the same parent Project, ~200 char max), description (required at creation, editable, ~2000 char max), start_date (optional), finished_date (optional, must not precede start_date when both present), notes (optional, unbounded free text), status (enum: new, in-progress, complete, blocked, deferred, archived; default "new"), soft-delete flag (independent of status; frozen serial_num once set).
- **Project** (existing entity, modified relationship only): now gates its own soft-delete on the absence of active Group-tasks beneath it; no other change to its own fields.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can create a Group-task under a Project and see it appear in that Project's nested list within the same interaction, with a correctly auto-assigned serial_num scoped to that Project alone.
- **SC-002**: 100% of attempts to create or edit a Group-task with a title or serial_num that duplicates another active Group-task *within the same parent Project* are rejected with a clear, actionable validation message, while identical titles or serial_nums across different Projects are never falsely rejected.
- **SC-003**: 100% of attempts to soft-delete a Project that still has at least one active Group-task are blocked with a clear explanatory message, and the same Project can be soft-deleted successfully as soon as zero active Group-tasks remain under it.
- **SC-004**: A user can view every field of any Group-task from its own detail page and soft-delete it from that same page, landing back on the parent Project's detail page immediately after, with no full page reload of the detail page itself.
- **SC-005**: The `/deleted` view accurately and permanently lists 100% of soft-deleted Projects and soft-deleted Group-tasks, with every Group-task entry correctly attributed to and grouped under its original parent Project's identity.
- **SC-006**: In a Project containing up to 200 Group-tasks, a user can locate any specific Group-task by its serial_num position in the nested list without any additional search or filter tooling.

## Assumptions

- This is a single-user application with no authentication; all views and actions are available to whoever accesses the system.
- No created_at/updated_at timestamp tracking is required for Group-task, matching Project's existing convention.
- "Reasonable max length" for title is interpreted as ~200 characters and for description as ~2000 characters, matching Project's existing convention; notes has no enforced maximum.
- No pagination, search, or filtering is required for the nested Group-task list, the create/edit/detail pages, or the `/deleted` view; all are expected to comfortably handle the volumes implied by SC-006.
- A Group-task can only be created under a Project that is currently active; no UI path ever presents a link to create, view, edit, or delete a Group-task under a soft-deleted Project (soft-deleted Projects appear only in the read-only `/deleted` view), but per FR-015a this is still explicitly enforced at the route level with a 404, to cover direct or stale navigation to such a URL.
- The prior Deleted Items URL is fully replaced by `/deleted`; no redirect or backward-compatible alias for the old URL is required, since the one existing link to it is updated as part of this feature.
- Task remains entirely unmodeled this cycle; the "Group-task cannot be soft-deleted while it has active Tasks" rule is a placeholder for a future slice and has no effect until Task exists — Group-task's own soft-delete is unconditional until then.
- Cross-Project reassignment of a Group-task is out of scope now and permanently, per explicit design intent — no UI, route, or future consideration is implied by this exclusion.
