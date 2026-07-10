# Data Model: Master-Detail Pane UI

## No new or changed database entities

This feature is presentation/navigation only (FR-028): it introduces **no new tables, columns, or migrations**. `Project` and `GroupTask` (see `specs/003-group-task-management/data-model.md` for their full field/validation rules) are unchanged. `Status` enum is unchanged. No Alembic revision is part of this feature.

## New derived views (query-level, not schema-level)

### Project list with batched delete-eligibility (FR-015)

A new read query, `list_active_projects_with_delete_eligibility`, replacing plain `list_active_projects` as the source for the left-pane Project list:

```sql
SELECT project.*, COUNT(group_task.id) AS active_children
FROM project
LEFT JOIN group_task
  ON group_task.project_id = project.id AND group_task.deleted = false
WHERE project.deleted = false
GROUP BY project.id
ORDER BY project.serial_num ASC
```

Returned as `list[tuple[Project, bool]]` (the boolean is `active_children > 0`, i.e. "has active children" — a row's delete control is disabled exactly when this is `true`). Uses the existing `ix_group_task_project_id` index (added in 003); no new index needed.

### Group-task list — delete-eligibility is unconditional this feature

No batched query exists for Group-task's own children, because `task` is not a table (Task doesn't exist yet, per spec.md's Clarifications). Every Group-task row's delete control is unconditionally enabled. `list_active_group_tasks` is unchanged; the left-pane Group-task list route pairs each row with a hardcoded "eligible" flag rather than a query result. This is expected to be replaced with a real batched query, following the exact shape above, once Task's future slice adds a `task` table.

### "Next active item" after a selected-and-deleted entity (FR-017a)

No new query — this reuses `list_active_projects_with_delete_eligibility` / `list_active_group_tasks`, called again immediately after the triggering soft-delete has committed. The deleted row is already absent from the result (its `deleted` flag flipped before the re-query), so "first result by `serial_num`, or none" is exactly FR-017a's rule, identical to the existing "first item of a freshly-drilled-into list" rule (FR-019).

## Client-side (non-persisted) state

None of the following are server entities; they exist only in the browser and are documented here because they're load-bearing for this feature's contracts (see `contracts/client-state-contract.md`):

| State | Lifetime | Storage | Purpose |
|---|---|---|---|
| Divider split position | Survives reload | `localStorage` | FR-024/FR-025 |
| Last-shown left-pane list URL | Page lifetime only, cleared on reload | In-memory (Alpine store) | Back control target when leaving Deleted Items (FR-009a) |
| Details-pane dirty flag + initial-value snapshot | Reset every time `#details-pane` is swapped | In-memory (Alpine component scoped to the form) | Unsaved-changes navigation guard (FR-026) |
| Selected entity type/id | Re-derived from the DOM on every request that needs it (not tracked independently) | `data-entity-type`/`data-entity-id` attributes on `#details-pane`'s root, rendered server-side each swap | FR-017a's deleted-while-selected comparison |

## Server-rendered fragment self-description (DOM contract, not a data entity)

Every details-pane fragment's root element carries `data-entity-type="project"` or `data-entity-type="group_task"` plus `data-entity-id="{id}"` when it represents a saved, selected entity; both attributes are absent (or empty) for the blank-create form and for the Deleted-Items empty state. This is the mechanism that lets an otherwise-stateless server answer "was the entity just deleted also the one currently shown?" (see research.md) without a session store — it is DOM state describing what the last response rendered, not a new persisted concept.
