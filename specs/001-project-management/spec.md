# Feature Specification: Project Management

**Feature Branch**: `001-project-management`

**Created**: 2026-07-07

**Status**: Draft

**Input**: User description: "Feature: Project management (first vertical slice of Strata's 3-level hierarchy). Build the Project entity as a complete, standalone vertical slice — model, persistence, and basic UI — with no dependency yet on Group-task or Task (those are separate future slices)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Create and list projects (Priority: P1)

A user creates a new project by supplying a title and description, and immediately sees it appear in the list of active projects, ordered by serial number.

**Why this priority**: Capturing a new project and being able to see the running list is the minimum useful capability of this slice — without it, nothing else has a reason to exist.

**Independent Test**: Can be fully tested by creating one or more projects with only the required fields and confirming they appear in the active list in ascending serial_num order, with serial_num auto-assigned starting at 0.

**Acceptance Scenarios**:

1. **Given** no projects exist yet, **When** a user creates a project with a title and description, **Then** the project is saved with serial_num 0, status "new", and appears in the active project list.
2. **Given** one or more active projects exist with serial_num 0..N, **When** a user creates another project, **Then** the new project is auto-assigned serial_num (max active serial_num) + 1.
3. **Given** an active project already has the title "Website Redesign", **When** a user attempts to create another active project with the exact same title, **Then** the creation is rejected with a validation error.
4. **Given** a user attempts to create a project without a title or without a description, **When** the create action is submitted, **Then** the creation is rejected with a validation error.

---

### User Story 2 - View project details (Priority: P2)

A user opens a single project from the list to see all of its fields in one place.

**Why this priority**: Once projects exist, users need to inspect the full detail (dates, notes, status, description) beyond what fits in a list row.

**Independent Test**: Can be fully tested by creating a project, opening its detail view, and confirming every field (serial_num, title, description, start_date, finished_date, notes, status) is displayed accurately.

**Acceptance Scenarios**:

1. **Given** an active project exists, **When** a user opens its detail view, **Then** all of its fields are displayed, including optional fields left blank.

---

### User Story 3 - Edit project details (Priority: P3)

A user updates any field on an existing project, including moving it to a different status or renumbering it, as the project evolves.

**Why this priority**: Projects change over time (status shifts, notes accumulate, dates get added) — editing is required for the entity to stay useful, but only matters once creation and viewing already work.

**Independent Test**: Can be fully tested by editing each field on an existing project (including status and serial_num) and confirming the changes persist and are reflected in list and detail views.

**Acceptance Scenarios**:

1. **Given** an active project, **When** a user edits its status from "new" directly to "archived" (or any other status), **Then** the change is accepted with no restriction on the transition.
2. **Given** two active projects with serial_num 3 and 5, **When** a user edits the second project's serial_num to 3, **Then** the edit is rejected with a validation error and the project's serial_num remains 5.
3. **Given** an active project with start_date set and finished_date blank, **When** a user sets finished_date to a date earlier than start_date, **Then** the edit is rejected with a validation error.
4. **Given** an active project, **When** a user edits its notes field, **Then** the updated notes are saved and displayed on subsequent views.
5. **Given** an active project titled "Website Redesign" and a soft-deleted project that was also titled "Website Redesign", **When** a user creates or renames another active project to "Website Redesign", **Then** the operation succeeds because the soft-deleted project's title is no longer reserved.

---

### User Story 4 - Soft-delete a project and view Deleted Items (Priority: P4)

A user removes a project they no longer want cluttering active views, and can still find it later in a permanent, read-only Deleted Items view.

**Why this priority**: Cleanup is valuable but depends on projects already existing and being editable; it's the least critical path to a usable slice.

**Independent Test**: Can be fully tested by soft-deleting an active project, confirming it disappears from the active list and detail views, and confirming it appears read-only in the Deleted Items view ordered by its frozen serial_num.

**Acceptance Scenarios**:

1. **Given** an active project in any status (including "archived"), **When** a user soft-deletes it, **Then** it immediately disappears from the active project list and can no longer be opened from normal views.
2. **Given** a project has just been soft-deleted, **When** a user opens the Deleted Items view, **Then** the project appears there with its fields intact and its serial_num frozen at its last active value.
3. **Given** a project in the Deleted Items view, **When** a user attempts to edit or un-delete it, **Then** no such action is available — the view is strictly read-only.
4. **Given** multiple soft-deleted projects, **When** a user opens the Deleted Items view, **Then** they are listed in ascending order by serial_num.

---

### Edge Cases

- What happens when a project is created for the very first time ever? Serial_num MUST be assigned 0.
- What happens when the active project list is empty? The list view MUST display an empty state rather than an error.
- What happens when a project's serial_num is edited to match its own current value? This MUST be treated as a no-op success, not a conflict (it does not collide with a *different* project).
- What happens when a project with the highest serial_num is soft-deleted, then a new project is created? The new project's serial_num is computed only from remaining active projects, so it MAY reuse a numeric value that a now-deleted project still displays (frozen) in the Deleted Items view — this is expected, since uniqueness is scoped to active projects only.
- What happens when both start_date and finished_date are cleared after having been set? This MUST be permitted; both are optional and independent.
- What happens when a user tries to soft-delete a project that is already soft-deleted? This MUST NOT be possible — soft-deleted projects offer no delete action since they are not present in any editable view.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow creating a new project by supplying a required title and required description; start_date, finished_date, and notes are optional at creation.
- **FR-002**: System MUST default a newly created project's status to "new".
- **FR-003**: System MUST auto-assign each new project's serial_num as (the maximum serial_num among currently active projects) + 1, or 0 if no active project exists.
- **FR-004**: System MUST enforce title uniqueness among active (non-deleted) projects, rejecting a create or edit that would duplicate another active project's title.
- **FR-005**: System MUST allow a title that matches a soft-deleted project's title, since soft-deleted titles are not reserved.
- **FR-006**: System MUST enforce a maximum title length of approximately 200 characters, rejecting values that exceed it.
- **FR-007**: System MUST enforce a maximum description length of approximately 2000 characters, rejecting values that exceed it.
- **FR-008**: System MUST allow users to manually edit serial_num on any active project.
- **FR-009**: System MUST enforce serial_num uniqueness among active projects, rejecting an edit that would set a project's serial_num to a value already used by a different active project, and leaving the project's existing serial_num unchanged when rejected.
- **FR-010**: System MUST accept an edit that sets a project's serial_num to its own current value without treating it as a conflict.
- **FR-011**: System MUST validate, whenever both start_date and finished_date are present on a project, that finished_date is not before start_date, rejecting any create or edit that violates this.
- **FR-012**: System MUST allow start_date and finished_date to each be set, edited, or left blank independently of the other.
- **FR-013**: System MUST restrict status to one of: new, in-progress, complete, blocked, deferred, archived.
- **FR-014**: System MUST allow status to be changed to any other allowed value at any time, with no enforced sequence or restricted transitions.
- **FR-015**: System MUST provide a single free-text notes field per project that can be edited at any time and is intended to accumulate content over the project's life.
- **FR-016**: System MUST allow a project to be soft-deleted regardless of its current status, including "archived".
- **FR-017**: System MUST NOT provide any mechanism to permanently (hard) delete a project.
- **FR-018**: System MUST exclude soft-deleted projects from all normal (active) listing and detail views immediately upon deletion.
- **FR-019**: System MUST make a soft-deleted project visible only in a dedicated Deleted Items view.
- **FR-020**: System MUST treat the Deleted Items view as strictly read-only, offering no edit or restore/un-delete action for the projects shown there.
- **FR-021**: System MUST freeze a project's serial_num at its last active value at the moment of soft-deletion.
- **FR-022**: System MUST order both the active project list and the Deleted Items view ascending by serial_num.
- **FR-023**: System MUST provide a list view of all active projects.
- **FR-024**: System MUST provide a detail/view screen for a single project showing all of its fields.
- **FR-025**: System MUST allow editing of every field (title, description, start_date, finished_date, notes, status, serial_num) on an active project, subject to the validation rules above.
- **FR-026**: System MUST NOT require, expose, or reference any Group-task or Task concepts as part of this slice.
- **FR-027**: System MUST NOT require user authentication or support multiple distinct user accounts for this slice.

### Key Entities

- **Project**: Represents a unit of work at the top of Strata's hierarchy. Attributes: serial_num (integer, user-editable, unique among active projects, default ordering key), title (required, unique among active projects, ~200 char max), description (required at creation, editable, ~2000 char max summary), start_date (optional), finished_date (optional, must not precede start_date when both present), notes (optional, unbounded free text, accumulative), status (enum: new, in-progress, complete, blocked, deferred, archived; default "new"), soft-delete flag (independent of status; frozen serial_num once set).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can create a project and see it appear in the active project list within the same interaction, with no page reload delay perceptible beyond standard network/render time.
- **SC-002**: 100% of attempts to create or edit a project with a title or serial_num that duplicates another active project are rejected with a clear, actionable validation message, and zero duplicate active titles or serial_nums ever persist in the system.
- **SC-003**: 100% of soft-deleted projects disappear from active list and detail views immediately, and are permanently and accurately retrievable in the Deleted Items view in serial_num order.
- **SC-004**: In a list of up to 500 projects, a user can find any specific project by its serial_num position without any additional search or filter tooling.
- **SC-005**: Every newly created project defaults to status "new" and can be moved to any of the other five statuses in a single edit action, with no blocked or multi-step transition ever required.
- **SC-006**: A user can locate the full history of removed projects (Deleted Items) with 100% accuracy relative to what was soft-deleted, with no data loss on deletion.

## Assumptions

- This is a single-user application with no authentication; all views and actions are available to whoever accesses the system.
- No created_at/updated_at timestamp tracking is required for this slice, per the feature description.
- "Reasonable max length" for title is interpreted as ~200 characters and for description as ~2000 characters; notes has no enforced maximum beyond practical storage limits.
- No pagination, search, or filtering is required for this slice; the active list and Deleted Items view are simple ordered lists, expected to comfortably handle up to several hundred projects.
- Because serial_num uniqueness is scoped only to active projects, an active project may share a numeric serial_num value with a soft-deleted project's frozen value; this is accepted as correct behavior, not a defect.
- This slice defines only the Project entity; Group-task and Task entities, and any relationship between Project and those future entities, are explicitly out of scope and will be specified in later cycles.
