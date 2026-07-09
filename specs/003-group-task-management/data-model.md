# Data Model: Group-task Management

## Entity: `GroupTask`

New table, `group_task`. Nested one level under `Project` (many `GroupTask` rows per `Project`, via `project_id`). Task remains out of scope entirely (FR-029).

| Field | Type | Required | Default | Notes |
|---|---|---|---|---|
| `id` | integer (PK) | — | auto | Internal surrogate primary key; not the user-facing ordering/identity field. |
| `project_id` | integer (FK → `project.id`) | yes | — | Set once at creation, never editable afterward (FR-002, FR-030). No `ON DELETE CASCADE` — hard delete never happens system-wide, so cascade semantics never trigger. |
| `serial_num` | integer | yes | computed (see rule R1) | User-editable. Unique among active (`deleted = false`) rows **within the same `project_id`**, not globally. Frozen at last active value once soft-deleted. |
| `title` | string, max ~200 chars | yes | — | Unique among active rows **within the same `project_id`**; the same title may exist under a different Project (FR-005). |
| `description` | string, max ~2000 chars | yes (at creation) | — | Editable after creation. Rejected if blank or whitespace-only (FR-008a), same as `title`. |
| `start_date` | date | no | null | Independent of `finished_date`. |
| `finished_date` | date | no | null | Must not be earlier than `start_date` when both present (R4). |
| `notes` | `str`, no `max_length` (TEXT affinity) | no | null / empty | Free-text, editable at any time. |
| `status` | enum: `new`, `in-progress`, `complete`, `blocked`, `deferred`, `archived` (reuses Project's existing `Status` enum — no new enum type) | yes | `new` | Free-form transitions, no restriction. |
| `deleted` | boolean | yes | `false` | Soft-delete flag, independent of `status`. Unconditional in this slice (no active-Task check — Task doesn't exist yet, FR-012). |

## Relationship: `Project` 1 — many `GroupTask`

- No ORM `Relationship()` declared on either model, matching the existing codebase's style (`project_id` is queried manually, per the user-supplied plan input) — consistent with `Project` having no back-reference to its Group-tasks either.
- `Project` gains one new invariant from this slice (no new fields of its own): **R-project-1 — cascade-block**: a Project's `soft_delete_project` MUST reject (raising `ProjectValidationError`) if any `group_task` row with that `project_id` has `deleted = false` (FR-016). Succeeds once zero such rows remain (FR-017).

## Validation Rules

- **R1 — `serial_num` auto-assignment (create only), scoped by parent**: `serial_num = MAX(serial_num WHERE project_id = :project_id AND deleted = false) + 1`, or `0` if that Project has no active Group-task yet (FR-004).
- **R2 — `serial_num` uniqueness (create & edit), scoped by parent**: Reject if the target `serial_num` matches another *active* Group-task's `serial_num` **under the same `project_id`**. Setting a Group-task's `serial_num` to its own current value is a no-op success (FR-006, FR-007). Two Group-tasks under *different* Projects may freely share a `serial_num`.
- **R3 — title uniqueness (create & edit), scoped by parent**: Reject if the target `title` matches another *active* Group-task's `title` **under the same `project_id`**, exact match. Soft-deleted Group-tasks' titles are not reserved, same as Project (FR-005).
- **R4 — date ordering**: When both `start_date` and `finished_date` are present, reject if `finished_date < start_date` (FR-009). Either field may be null independently at any time.
- **R5 — length and blank/whitespace limits**: `title` ≤ ~200 chars, `description` ≤ ~2000 chars (FR-008); both are also rejected if blank or consisting only of whitespace (FR-008a), matching Project's existing rule.
- **R6 — status domain**: `status` must be one of the six values shared with Project (FR-010); any value → any other value allowed with no restriction.
- **R7 — soft-delete freezes `serial_num`**: The moment `deleted` flips to `true`, `serial_num` is no longer recomputed or eligible for uniqueness checks against active rows in that Project — it is frozen at its last value (FR-014). A later active Group-task under the same Project may legitimately reuse that number (documented edge case, not a defect).
- **R8 — no hard delete, no un-delete**: There is no code path that removes a `group_task` row, and none that clears `deleted` back to `false` (FR-013).
- **R9 — parent-Project gate on every nested route**: `project_id` MUST resolve to a Project that exists and is not soft-deleted, checked as the first step of every nested route — list rendering (embedded on the Project's own detail page), create, detail, edit, delete — 404ing otherwise, independent of whether the Group-task itself would otherwise be found (FR-015a). This is the one rule that does **not** apply to the read-only `/deleted` view (see Derived Views below).
- **R10 — Group-task's own soft-delete is unconditional this slice**: No check against active Tasks is possible or performed (Task does not exist); this is an explicitly deferred rule for a future slice, not a gap (FR-012).
- **R11 — no reassignment**: `project_id` is accepted only at creation and never appears as an editable field on the edit form/route; there is no route or service function that changes an existing Group-task's `project_id` (FR-002, FR-030).

## Derived Views (not separate entities, just filtered/joined queries)

- **Nested active Group-task list** (embedded on `GET /projects/{project_id}`): `SELECT * FROM group_task WHERE project_id = :project_id AND deleted = false ORDER BY serial_num ASC` (FR-018). Requires R9 (parent Project active) to have already passed, or the parent page itself already 404'd.
- **Group-task detail / edit**: `SELECT * FROM group_task WHERE project_id = :project_id AND id = :group_task_id AND deleted = false` — 404 if the Group-task is missing/soft-deleted (FR-015), **and** 404 if the parent Project itself is missing/soft-deleted regardless of the Group-task's own state (R9/FR-015a) — the parent check happens first, independently.
- **Deleted Group-tasks section (`/deleted`)**: `SELECT * FROM group_task WHERE deleted = true`, then for each row resolve its parent Project **by ID directly, ignoring the parent's own `deleted` flag** (`session.get(Project, project_id)`), since a Group-task's entry must still correctly identify its parent even if that parent was also later soft-deleted (FR's US6 acceptance scenario 4). Grouped by parent Project, groups ordered ascending by the parent's own (possibly frozen) `serial_num`, Group-tasks within each group ordered ascending by their own (frozen) `serial_num` (FR-027, FR-028). This is the one query in the whole feature that deliberately does not gate on parent-active status — see research.md.
- **Deleted Projects section (`/deleted`)**: `SELECT * FROM project WHERE deleted = true ORDER BY serial_num ASC` — unchanged from 001/002 (FR-026).

## State / Lifecycle Summary

```
[create under active Project] → status=new, deleted=false, project_id fixed forever
              │  (status editable to any of the 6 values, any time, no restriction)
              │  (serial_num, title, description, dates, notes editable any time, project_id never)
              ▼
        any status ──── soft-delete (unconditional this slice) ────▶ deleted=true (frozen serial_num, read-only forever)
```

There is no un-delete path and no hard-delete path — `deleted=true` is terminal, same as Project. Unlike Project, a future slice will add a precondition to this transition (active-Task check) — explicitly not implemented here (R10).

### Project's lifecycle gains one new edge, unchanged otherwise

```
active Project, zero active Group-tasks ──── soft-delete ────▶ deleted=true   (unchanged from 001/002)
active Project, ≥1 active Group-task    ──── soft-delete ────▶ REJECTED, ProjectValidationError,
                                                                 surfaced via _page_errors.html OOB (new, this slice)
```
