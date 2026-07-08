# Data Model: Relocate Project Deletion from List to Detail View

No entity, field, or validation-rule changes. This feature is a route-response and template-only relocation.

The `Project` entity, its fields, and its validation rules (R1–R8) are unchanged from [001-project-management/data-model.md](../001-project-management/data-model.md). In particular:

- **R6/R7/R8** (soft-delete semantics: `deleted` flag, frozen `serial_num`, no hard delete) are unaffected — `soft_delete_project` is not modified in this cycle (FR-006, FR-007).
- No new entity is introduced. Group-task, referenced only as future context for a later cycle's cascade-blocking rule, is explicitly out of scope here and does not appear in this feature's data model.

## Derived Views (unchanged)

- **Active project list**: unchanged query and ordering; only the row template's rendered controls change (delete control removed).
- **Project detail**: unchanged query (`WHERE id = :id AND deleted = false`, 404 otherwise); only the rendered template gains a delete control and an error-message container.
- **Deleted Items view**: entirely unaffected by this feature.
