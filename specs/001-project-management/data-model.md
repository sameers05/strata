# Data Model: Project Management

## Entity: `Project`

Single table, `project`. No related entities in this slice (Group-task and Task are explicitly out of scope per FR-026).

| Field | Type | Required | Default | Notes |
|---|---|---|---|---|
| `id` | integer (PK) | — | auto | Internal surrogate primary key; never exposed as the user-facing ordering/identity field (that's `serial_num`). |
| `serial_num` | integer | yes | computed (see rule R1) | User-editable. Unique among active (`deleted = false`) rows. Frozen at last active value once soft-deleted. |
| `title` | string, max ~200 chars | yes | — | Unique among active rows (soft-deleted titles are not reserved, FR-005). |
| `description` | string, max ~2000 chars | yes (at creation) | — | Editable after creation. |
| `start_date` | date | no | null | Independent of `finished_date`; either may be set/cleared independently. |
| `finished_date` | date | no | null | Must not be earlier than `start_date` when both are present (R3). |
| `notes` | `str`, no `max_length` (TEXT affinity, genuinely unbounded) | no | null / empty | Free-text, accumulative, editable at any time. |
| `status` | enum: `new`, `in-progress`, `complete`, `blocked`, `deferred`, `archived` | yes | `new` | Any value may transition to any other value at any time — no restricted transitions. |
| `deleted` | boolean | yes | `false` | Soft-delete flag. Independent of `status` (an `archived` project can still be soft-deleted, FR-016). |

## Validation Rules

- **R1 — `serial_num` auto-assignment (create only)**: `serial_num = MAX(serial_num WHERE deleted = false) + 1`, or `0` if no active project exists (FR-003, and the "first project ever" edge case).
- **R2 — `serial_num` uniqueness (create & edit)**: Reject if the target `serial_num` matches another *active* project's `serial_num`. Setting a project's `serial_num` to its own current value is a no-op success, not a conflict (FR-009, FR-010).
- **R3 — date ordering**: When both `start_date` and `finished_date` are present, reject if `finished_date < start_date` (FR-011). Either field may be null independently at any time (FR-012).
- **R4 — title uniqueness (create & edit)**: Reject if the target `title` matches another *active* project's `title`, exact match. Soft-deleted projects' titles do not count (FR-004, FR-005).
- **R5 — length limits**: `title` ≤ ~200 chars, `description` ≤ ~2000 chars (FR-006, FR-007). `notes` has no enforced maximum.
- **R6 — status domain**: `status` must be one of the six listed values (FR-013); any value → any other value is allowed with no restriction (FR-014).
- **R7 — soft-delete freezes `serial_num`**: The moment `deleted` flips to `true`, `serial_num` is no longer recomputed or eligible for uniqueness checks against active rows — it is simply frozen at its last value (FR-021). A later active project may legitimately reuse that same number (documented edge case, not a defect).
- **R8 — no hard delete**: There is no code path that removes a `project` row from the table (FR-017); "delete" always means setting `deleted = true`.

## Derived Views (not separate entities, just filtered queries)

- **Active project list**: `SELECT * FROM project WHERE deleted = false ORDER BY serial_num ASC` (FR-022, FR-023).
- **Project detail**: `SELECT * FROM project WHERE id = :id AND deleted = false` (404/not-found if soft-deleted or missing — FR-018).
- **Deleted Items view**: `SELECT * FROM project WHERE deleted = true ORDER BY serial_num ASC`, rendered strictly read-only — no edit or restore action exposed in the UI or routes (FR-019, FR-020, FR-022).

## State / Lifecycle Summary

```
[create] → status=new, deleted=false
              │  (status editable to any of the 6 values, any time, no restriction)
              ▼
        any status ──── soft-delete ────▶ deleted=true (frozen serial_num, read-only forever)
```

There is no un-delete path (FR-020) and no hard-delete path (FR-017) — `deleted=true` is a terminal state for a given row.
