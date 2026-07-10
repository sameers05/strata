# Feature Specification: Master-Detail Pane UI

**Feature Branch**: `004-master-detail-panes`

**Created**: 2026-07-09

**Status**: Draft

**Input**: User description: "Master-detail pane UI (replaces page-based navigation for Project and Group-task, designed to accommodate Task): Replace Strata's current full-page-per-entity navigation with a persistent two-pane layout — a resizable left navigation/list pane and a right details-pane that always shows the currently selected entity in an always-editable form. Single static home URL, no deep-linking. Left pane is a flat list with breadcrumb drill-down (Project → Group-task → future Task), a persistent Deleted Items link, a persistent + New control, and per-row delete guarded by active children. Right pane is always an editable form shared between create and edit, defaulting to the first item in a newly-drilled-into list, warning before discarding unsaved changes. Replaces all existing full-page routes for Project and Group-task; business rules unchanged; built entity-agnostically so Task's future slice reuses the same mechanics."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Browse the hierarchy in a persistent two-pane layout (Priority: P1)

A user opens Strata and sees a two-pane layout: the left pane lists active Projects, the right pane shows the first Project's full details (or a prompt to create one if none exist). The user drills into a Project's Group-tasks by clicking its title, and can jump back to any ancestor level via a breadcrumb — all without the browser ever leaving a single page or reloading.

**Why this priority**: This is the foundational replacement of full-page navigation and the entire value proposition of the feature. Every other story depends on this pane/drill mechanism existing.

**Independent Test**: Load the app, confirm both panes render with the described home state, click a Project's title to drill down, confirm the breadcrumb updates and the left pane now lists that Project's Group-tasks, click an ancestor breadcrumb link to jump directly back.

**Acceptance Scenarios**:

1. **Given** no drill-down has occurred, **When** the user loads the home page, **Then** the left pane shows all active Projects ordered ascending by serial_num, and the right pane shows the first Project's full details (or a create-prompt if no Projects exist).
2. **Given** the left pane shows a Project list, **When** the user clicks a Project's title, **Then** the left pane replaces its list with that Project's active Group-tasks, the breadcrumb shows the path down to that Project, and the details pane shows the first Group-task's details (or a create-prompt if that Project has no Group-tasks).
3. **Given** the left pane is drilled into a list, **When** the user clicks the "View" control on a row instead of its title, **Then** the details pane shows that row's own details without drilling the list into its children.
4. **Given** the left pane is drilled two or more levels deep, **When** the user clicks an ancestor link in the breadcrumb, **Then** the left pane jumps directly to that ancestor's list, skipping intermediate levels.
5. **Given** the browser is reloaded at any drill depth, **When** the page finishes loading, **Then** the app returns to the home state — root active-Project list, default details pane — with no attempt to restore the prior drill position.

---

### User Story 2 - Create a new entity from the current drill level (Priority: P1)

A user viewing any list level clicks a persistent "+ New" control, fills in a blank always-editable form in the details pane, and saves it. The new entity appears in the current list without leaving the page.

**Why this priority**: Equally critical to browsing — without a way to create entities, the panes cannot replace the create capability that existing full-page routes currently provide, and this feature removes those routes entirely.

**Independent Test**: From any drill level, with the list either empty or populated, click "+ New," fill in required fields, save, and confirm the new row appears in the left pane list with the details pane showing it as the selected entity.

**Acceptance Scenarios**:

1. **Given** any drill level, **When** the user clicks "+ New [entity]," **Then** the details pane shows a blank form for that entity type.
2. **Given** a blank form, **When** the user submits valid values, **Then** the entity is created, the left pane list updates to include the new row, and the details pane shows the saved entity as selected.
3. **Given** a blank form, **When** the user submits invalid values, **Then** a validation error appears in a fixed error area of the details pane, the form retains the values the user entered, and no navigation occurs.
4. **Given** an empty list at any drill level, **When** the user views that level, **Then** the details pane shows a prompt to create the first entity, and the persistent "+ New" control remains available.

---

### User Story 3 - Edit an existing entity's fields (Priority: P1)

A user selects an existing row and sees its full field set in the same always-editable form used for creation, changes a value, and saves.

**Why this priority**: Also required to preserve existing edit capability that the removed full-page routes currently provide, and is central to the "always-editable, no read-only mode" concept the feature is built around.

**Independent Test**: Select an existing row, confirm the form is pre-populated with its current values, change a field, save, and confirm the change is reflected in both the left pane row and the details pane.

**Acceptance Scenarios**:

1. **Given** an entity is selected via its row's title or "View" control, **When** its details load, **Then** the details pane form is pre-populated with all of that entity's current field values.
2. **Given** a pre-populated form, **When** the user changes a field and saves, **Then** the change persists, the left pane's row updates to reflect any changed displayed field (title, status, serial_num), and the details pane reflects the saved state.
3. **Given** a pre-populated form, **When** the user submits invalid values, **Then** the same validation-error behavior as creation occurs — a fixed-area error message, with the form retaining the user's entered values.

---

### User Story 4 - Delete an entity guarded by active children (Priority: P2)

A user clicks a row's delete control. If that entity has no active children, a confirmation prompt appears and, on confirmation, the entity is soft-deleted and its row disappears from the list in place. If it has active children, the delete control is disabled and cannot be activated.

**Why this priority**: Preserves the existing delete and cascade-block rules from prior slices, but is exercised less frequently than browsing, creating, and editing.

**Independent Test**: View a list containing one entity with active children and one without. Confirm the blocked row's delete control is disabled, and confirm the other row's delete control triggers the confirmation prompt and removes the row in place once confirmed.

**Acceptance Scenarios**:

1. **Given** a row's entity has zero active children, **When** the user views that row, **Then** its delete control is enabled.
2. **Given** a row's entity has one or more active children, **When** the user views that row, **Then** its delete control is disabled and does not trigger deletion if interacted with.
3. **Given** an enabled delete control, **When** the user activates it and confirms the resulting prompt, **Then** the entity is soft-deleted and its row is removed from the left pane list in place.
4. **Given** a list containing multiple rows, **When** the list loads, **Then** every row's delete-eligibility (active-children check) is determined as part of that same list load, without a separate lookup per row.

---

### User Story 5 - Resize the two panes via a draggable divider (Priority: P2)

A user drags the vertical divider between the two panes to resize them; the layout adjusts live, and the chosen split is restored the next time the app is loaded.

**Why this priority**: Ergonomic improvement, independent of the core create/edit/delete/browse flows and does not block any other story.

**Independent Test**: Drag the divider to a new position, reload the browser, and confirm the same split position is restored.

**Acceptance Scenarios**:

1. **Given** the default two-pane layout, **When** the user drags the divider, **Then** both panes resize live as the divider moves.
2. **Given** the user has resized the panes and reloads the browser, **When** the home page loads, **Then** the panes render at the previously chosen split position.
3. **Given** no prior resize has occurred (first-ever load), **When** the home page loads, **Then** the panes render at a sensible default split.

---

### User Story 6 - View soft-deleted history from any drill level (Priority: P2)

A user clicks the persistent "Deleted Items" link, available at any drill depth, to see the existing read-only Deleted view (Deleted Projects, Deleted Group-tasks) in place of the normal list, with the details pane showing nothing while that view is active.

**Why this priority**: Preserves the existing relocated Deleted Items capability for full parity with prior slices, but is a secondary, occasional-use view.

**Independent Test**: From any drill depth, click "Deleted Items," confirm the left pane swaps to the two-section read-only view and the details pane shows no selectable content, then return to normal browsing and confirm it resumes correctly.

**Acceptance Scenarios**:

1. **Given** any drill depth, **When** the user clicks "Deleted Items," **Then** the left pane shows the labeled read-only sections (Deleted Projects, Deleted Group-tasks) instead of the active list.
2. **Given** the Deleted Items view is active, **When** the user looks at the details pane, **Then** it shows no selectable or editable content.
3. **Given** the Deleted Items view is active, **When** the user returns to normal browsing, **Then** the left pane resumes ordinary list/drill behavior at the level the user returns to.

---

### User Story 7 - Warn before discarding unsaved changes (Priority: P3)

A user who has changed a field in the details pane without saving, then clicks a different row, drills to a different level, or otherwise navigates within the app, is asked to confirm before those changes are discarded.

**Why this priority**: Valuable data-loss-prevention polish. The app remains functionally safe without it — unsaved changes simply never persisted — so this only improves the experience around accidental navigation.

**Independent Test**: Edit a field without saving, click a different row, confirm a warning prompt appears; verify that confirming discards the edit and proceeds, while cancelling keeps the user on the still-edited form.

**Acceptance Scenarios**:

1. **Given** the details pane has unsaved changes, **When** the user clicks a different row, activates "+ New," or changes drill level, **Then** a confirmation prompt appears before that navigation proceeds.
2. **Given** the confirmation prompt, **When** the user confirms discarding, **Then** the navigation proceeds and the unsaved changes are lost.
3. **Given** the confirmation prompt, **When** the user cancels, **Then** the user remains on the current, still-edited form with their changes intact.
4. **Given** the details pane has no unsaved changes, **When** the user navigates elsewhere in the app, **Then** no confirmation prompt appears.

---

### Edge Cases

- What happens when a list at any drill level is empty? The details pane shows a create-first prompt, and the persistent "+ New" control remains available (per User Story 2).
- What happens when the entity currently open in the details pane is itself deleted via its own row's delete control in the active list? The details pane auto-selects the next remaining active item in that list, or the empty/create-prompt state if none remain.
- What happens when a user clicks a Group-task's title before Task exists as an entity? The title directly selects that Group-task's own details into the details pane, per the same single-click-target behavior FR-006 specifies for entity types with no children — it does not drill into an empty child list.
- What happens when a user tries to resize the divider to an extreme position? Both panes retain a reasonable minimum width so neither can be fully collapsed.
- What happens when the user is in the Deleted Items view and wants to return to normal browsing? A dedicated "Back"/root control (distinct from the breadcrumb) exits the Deleted Items view.

## Clarifications

### Session 2026-07-09

- Q: Before Task exists as an entity, what should clicking a Group-task's title do? → A: Select that Group-task's own details into the details pane directly, the same single-click-target behavior FR-006 specifies for entity types with no children — not drill into an empty child list. There is no Task-level UI, list, or "+ New Task" control in this feature; when Task's own future slice ships, that slice is responsible for retrofitting Group-task's title-click behavior from select to drill, the same pattern already used for the Project→Group-task cascade-delete-block retrofit in 003.
- Q: When the entity currently open in the details pane is deleted via its own row's delete control, what should the details pane show next? → A: Auto-select the next remaining active item in that list, or the empty/create-prompt state if none remain.
- Q: How does the user exit the Deleted Items view back to normal list browsing? → A: A dedicated "Back"/root control, kept separate from the breadcrumb (which is reserved for normal drill-path navigation).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST present a single persistent two-pane layout — a left list/navigation pane and a right details pane — at one static application URL, with no other URL representing application state.
- **FR-002**: The system MUST NOT support deep-linking or server-side routing to a specific drill level, selected entity, or the Deleted Items view; reloading the browser MUST always return to the home state (root active-Project list, default details pane).
- **FR-003**: In its home state, the left pane MUST list all active Projects ordered ascending by serial_num.
- **FR-004**: The system MUST let a user drill the left pane down into an entity's active children by clicking that entity's title. In this feature's scope, this applies to Project → active Group-tasks; drilling from Group-task → active Tasks does not apply until Task exists as an entity (see FR-006).
- **FR-005**: The system MUST let a user select an entity's own full details into the details pane without drilling into its children, via a distinct "View" control on each row of an entity type that has children (Project, and Group-task once Task exists).
- **FR-006**: For an entity type that currently has no children — Group-task, until Task exists as an entity, and Task itself once it exists (since Task has no further children) — the system MUST let the row's title directly select that entity's details into the details pane rather than drilling further, collapsing the title/View distinction into a single click target. There is no Task-level UI, list, or "+ New Task" control built as part of this feature. When Task's own future slice ships, that slice is responsible for retrofitting Group-task's title-click behavior from this single-click select into the drill behavior of FR-004, the same retrofit pattern already used for the Project→Group-task cascade-delete-block change in 003.
- **FR-007**: The left pane MUST display a breadcrumb of the current drill path, with every ancestor level rendered as a clickable link that jumps the left pane directly to that ancestor's list.
- **FR-008**: The left pane MUST always display a persistent "Deleted Items" link, regardless of drill depth, that swaps the left pane into a read-only view listing soft-deleted Projects and soft-deleted Group-tasks (and soft-deleted Tasks, once Task exists) in labeled sections.
- **FR-009**: While the Deleted Items view is active, the details pane MUST show no selectable or editable content.
- **FR-009a**: The system MUST provide a dedicated "Back"/root control, separate from the breadcrumb, that exits the Deleted Items view and returns the left pane to normal list/drill behavior at the level the user was at before activating it.
- **FR-010**: The left pane MUST always display a persistent "+ New [entity]" control appropriate to the current drill level, visible whether the current list is empty or populated.
- **FR-011**: Activating "+ New [entity]" MUST blank the details pane into an empty, always-editable form for creating a new entity at the current drill level.
- **FR-012**: Each row in an active list MUST display, at minimum, the entity's title, status, and serial_num.
- **FR-013**: Each row in an active list MUST display a delete control.
- **FR-014**: The system MUST disable a row's delete control whenever that entity currently has one or more active children.
- **FR-015**: The system MUST determine delete-eligibility (presence of active children) for every row in a list as part of that same list load, using one combined data-fetch rather than a separate fetch per row.
- **FR-016**: Activating an enabled delete control MUST prompt the user for confirmation before deleting, matching the confirmation behavior already used elsewhere in the system.
- **FR-017**: On successful deletion, the system MUST remove the deleted row from the currently displayed list in place, without a full reload of the pane.
- **FR-017a**: When the entity currently open in the details pane is deleted via its own row's delete control, the system MUST automatically select the next remaining active item in that same list into the details pane, or show the create-prompt empty state if no active items remain.
- **FR-018**: The details pane MUST always present the selected, newly-created, or edited entity's complete field set in a single always-editable form with one save action; there is no separate read-only view mode.
- **FR-019**: When the left pane drills into a non-empty list, the system MUST default the details pane to that list's first active item, ordered by serial_num.
- **FR-020**: When the left pane drills into an empty list, the details pane MUST show a prompt to create the first entity at that level, in addition to the persistent "+ New" control.
- **FR-021**: The create form and the edit form for a given entity type MUST be the same form UI, differing only in whether it starts blank or pre-populated with an existing entity's values.
- **FR-022**: On a validation failure during create or edit, the system MUST surface the error in a fixed error-display area within the details pane without discarding the user's entered form values and without navigating away.
- **FR-023**: On successful create or edit, the system MUST update the details pane to reflect the saved entity and update the corresponding row in the left pane list to reflect any changed displayed fields (title, status, serial_num).
- **FR-024**: The system MUST let the user resize the two panes by dragging a divider between them, with both panes resizing live as the divider moves.
- **FR-025**: The system MUST persist the user's chosen divider position across browser reloads.
- **FR-026**: The system MUST warn the user with a confirmation prompt before discarding unsaved changes in the details pane whenever the user attempts to select a different row, activate "+ New," or change drill level while unsaved changes exist.
- **FR-027**: The system MUST remove all prior full-page routes for Project and Group-task (list, detail, new, edit, and the relocated Deleted Items view) as part of this feature, replacing them entirely with the two-pane experience.
- **FR-028**: The system MUST preserve all existing business rules (uniqueness scoping, cascade-delete blocking, field validation) unchanged; this feature changes presentation and navigation only.
- **FR-029**: The pane, list, drill, and details mechanics MUST be implemented entity-agnostically: the underlying list, drill, create/edit form, and delete mechanics MUST be reusable by a future Task slice without requiring a further redesign of the pane architecture. This entity-agnostic requirement covers only the shared mechanics — it does not imply that any Task-specific UI, list, or controls (e.g., a Task list or "+ New Task" control) are built as part of this feature.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can view any Project's, Group-task's, or (once it exists) Task's full details without a single full browser page reload — every drill and select action is handled as an in-page pane update.
- **SC-002**: Reloading the browser at any point always returns the user to the home Project list within one page load, with no broken or dangling application state to recover.
- **SC-003**: A user can tell at a glance, without opening a row, whether it can be deleted, and a delete-blocked row never allows a deletion to proceed.
- **SC-004**: Creating or editing an entity and seeing the result reflected in the left pane list happens in a single interaction (activating Save), with no full page reload.
- **SC-005**: A user with unsaved changes is warned before losing them every time they attempt to navigate elsewhere within the app.
- **SC-006**: A returning user's chosen pane-width split is restored on every subsequent visit, barring explicit browser data clearing.
- **SC-007**: List responsiveness for showing delete-eligibility does not degrade as the number of rows in a list grows within the expected scale (up to ~200 active items per parent, consistent with Group-task's existing scale).

## Assumptions

- The application remains a single-user, browser-based tool with no multi-user real-time sync concerns, consistent with prior slices' scale.
- "Active children" for delete-eligibility means non-soft-deleted children only, matching the existing soft-delete semantics from prior slices.
- The two-pane layout targets desktop/wide-viewport browser usage; a dedicated mobile/narrow-viewport layout is out of scope for this feature.
- Divider drag interaction and its persisted position are client-side-only concerns (no server-side storage of layout preference is required).
- Default divider split position and minimum pane widths are chosen by implementation without further product sign-off, consistent with this project's existing "minimal functional styling" approach.
- The existing confirmation-prompt pattern used for delete actions is reused as-is for the new unsaved-changes warning.
- Task's own future slice will supply its create/edit fields and validation rules; this feature only guarantees the pane mechanics can host them, not what those fields are.
