# Feature Specification: Relocate Project Deletion from List to Detail View

**Feature Branch**: `002-relocate-project-delete`

**Created**: 2026-07-08

**Status**: Draft

**Input**: User description: "Relocate Project deletion from list to detail view. Modify the existing Project entity's deletion UI, in preparation for a forthcoming cascade-blocking rule (to be added in a later cycle once Group-task exists). This cycle covers only the UI/mechanical relocation — no new business rule is introduced yet. Remove the soft-delete action from the active Project list view entirely; the list becomes pure navigation with no destructive action available from it. Add a soft-delete action to the Project detail view instead — a control the user can trigger only from within a single Project's own detail page. On successful deletion from the detail page, redirect the browser back to the active Project list, since the detail page can no longer represent a project that has just been deleted. The detail page must have a mechanism to display a validation-style error message in place, without a full page reload, for use by a future rule that isn't part of this cycle. The underlying soft-delete business logic itself is unchanged — deletion from the detail page still always succeeds unconditionally, exactly as it did from the list row before this change. Out of scope: no new validation rule, no reference to Group-task or any other entity, no change to how Projects are listed, created, or edited."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Delete a project from its detail page (Priority: P1)

A user viewing a single project's detail page wants to delete (soft-delete) that project directly from there, since deletion is now a detail-page-only action tied to the one project currently being viewed.

**Why this priority**: This is the entire point of the relocation — without it, users would have no way to delete a project at all once the list-view control is removed. This is the minimum required for the feature to preserve existing capability.

**Independent Test**: Can be fully tested by opening a project's detail page, triggering its delete control, and confirming the project disappears from the active project list and its detail page can no longer be viewed (consistent with existing soft-delete behavior).

**Acceptance Scenarios**:

1. **Given** an active project's detail page is open, **When** the user triggers the delete control on that page, **Then** the project is soft-deleted and the user ends up viewing the active project list, with the deleted project no longer appearing there.
2. **Given** a project has just been successfully deleted from its detail page, **When** the user is returned to the active project list, **Then** no full-page reload of the detail page occurs first — the browser transitions directly to the list.
3. **Given** an active project's detail page is open, **When** the user does not trigger delete, **Then** all existing detail-page information and the edit link continue to work exactly as before.

---

### User Story 2 - Project list becomes pure navigation (Priority: P1)

A user browsing the active project list should see only navigational links (to view or edit a project) and no destructive control, since deleting now requires opening a project's own detail page first.

**Why this priority**: Equally critical to User Story 1 — the relocation isn't complete, and the future cascade-blocking rule can't be safely introduced later, unless the list-level delete path is fully removed rather than merely duplicated.

**Independent Test**: Can be fully tested by loading the active project list and confirming no delete/destructive control is rendered anywhere in it, for any row, while view/edit links remain present and functional.

**Acceptance Scenarios**:

1. **Given** the active project list is displayed, **When** the user inspects any row, **Then** no delete or soft-delete control is present or reachable from that row.
2. **Given** the active project list is displayed, **When** the user wants to delete a project, **Then** the only way to do so is to first navigate to that project's own detail page.

---

### User Story 3 - Detail page is ready to surface a future delete-rejection message (Priority: P2)

A user attempting to delete a project from the detail page should land on a page that already has a designated, always-present place for an in-place validation-style message, so that a later cycle's cascade-blocking rule can reject a delete attempt and explain why — without requiring further UI changes when that rule is introduced.

**Why this priority**: Not required for this cycle's deletion to function (deletion always succeeds right now), but it is the explicit preparatory purpose of this cycle per the feature description. Lower priority than Stories 1 and 2 because no user-visible failure can occur yet — this story is only verifiable structurally.

**Independent Test**: Can be tested by confirming the detail page renders a designated error-message area on every load, and that the delete interaction is wired to update that area in place (without a full page reload) rather than to a full-page error view — even though, in this cycle, that area is never populated because delete cannot currently fail.

**Acceptance Scenarios**:

1. **Given** any active project's detail page is loaded, **When** the page renders, **Then** a designated area for an in-place validation-style message is present on the page (empty, since nothing has failed).
2. **Given** the delete control on the detail page, **When** it is triggered, **Then** the outcome (success or a hypothetical future rejection) is handled without a full page reload of the detail page itself.

---

### Edge Cases

- What happens if a user attempts to delete a project that has already been soft-deleted (e.g., a stale detail page left open in another tab, or a duplicate/rapid trigger of the control)? The system must not crash; it should behave consistently with the project no longer being available (matching existing not-found handling for soft-deleted or missing projects).
- What happens if the user reloads or revisits a stale link to a project's delete-capable detail page after it has already been deleted elsewhere? The detail page for a soft-deleted project must not be viewable, matching existing behavior — the user cannot reach a delete control for a project that no longer exists as active.
- What happens to the list view immediately after a successful delete performed from the detail page? The list must reflect the deletion (the project no longer appears there) the next time it is viewed.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The active Project list view MUST NOT provide any control that deletes or soft-deletes a project; the list MUST offer only navigational links (view, edit) for each project.
- **FR-002**: The Project detail page MUST provide a delete control that soft-deletes the specific project currently being viewed.
- **FR-003**: Deletion MUST remain reachable only by first navigating to a single project's own detail page — there is no bulk or list-level delete path.
- **FR-004**: When a delete triggered from the detail page succeeds, the system MUST return the user to the active Project list, without first fully reloading the detail page.
- **FR-005**: The Project detail page MUST include a designated, always-present mechanism capable of displaying a validation-style error message in place, without a full page reload, for use by a future business rule.
- **FR-006**: In this cycle, a delete attempt initiated from the detail page MUST always succeed unconditionally — no new rejection rule is introduced; behavior is equivalent to the prior list-row delete's unconditional success.
- **FR-007**: All previously-established soft-delete semantics (the deleted project's ordering value is frozen, it appears read-only in the Deleted Items view, and it is never hard-deleted) MUST remain unchanged.
- **FR-008**: Attempting to delete a project that is already soft-deleted or no longer exists MUST NOT crash the system and MUST be handled consistently with existing not-found behavior.
- **FR-009**: No other existing behavior for listing, creating, or editing projects may change as part of this feature.

### Key Entities

- **Project**: The existing entity being deleted; this feature changes only where and how its soft-delete action is triggered and how success/failure is communicated, not the entity's data or the delete rule's outcome.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 0% of active project list rows expose a delete control — every deletion in the system originates from a project's own detail page.
- **SC-002**: 100% of successful project deletions performed from the detail page result in the user viewing the active project list immediately after, with no intervening full-page reload of the detail page.
- **SC-003**: Every project detail page load includes a ready, inspectable in-place message area, so a future validation rule can be wired to it with no additional UI work.
- **SC-004**: 100% of pre-existing list, create, edit, and Deleted Items behaviors continue to pass their prior acceptance scenarios unchanged after this relocation.

## Assumptions

- The soft-delete rule itself (unconditional success) is unchanged in this cycle; a later cycle, once the Group-task entity exists, will add logic capable of rejecting a delete attempt and will populate the message area this cycle only prepares.
- "Without a full page reload" describes user-visible behavior only (the transition should feel like an in-app action rather than a hard navigation); it does not mandate any particular technical mechanism.
- The list view retains its existing per-project view and edit links; only the delete control is removed from it.
- No confirmation-dialog requirement, permission model, or additional entity is introduced by this feature; any existing confirm-before-delete interaction pattern carries over to the relocated control unchanged in spirit.
