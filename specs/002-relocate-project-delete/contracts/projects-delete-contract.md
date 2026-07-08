# Contract Change: `DELETE /projects/{id}`

This documents only the part of the Project routes contract ([001-project-management/contracts/projects-routes.md](../../001-project-management/contracts/projects-routes.md)) that changes in this feature. Every other route (list, new, create, detail, edit, update, deleted-items) is unchanged.

## Before (001-project-management)

| Method | Path | Trigger | Success response | Failure response |
|---|---|---|---|---|
| `DELETE` | `/projects/{id}` | `hx-delete` on a row control in `/projects` | `200`, empty body — HTMX removes the `<tr>` via `hx-swap="delete"` | `404` if already missing/soft-deleted |

## After (this feature)

| Method | Path | Trigger | Success response | Failure response |
|---|---|---|---|---|
| `DELETE` | `/projects/{id}` | `hx-delete` on a control within a project's own detail page (`/projects/{id}`) | `200`, empty body + **`HX-Redirect: /projects`** | `404` if already missing/soft-deleted — **unchanged** |

- The list view (`_project_row.html`) no longer has any delete trigger; `DELETE /projects/{id}` is reachable only from the detail page.
- On success, the browser is redirected to `/projects` (matching `POST /projects` / `PUT /projects/{id}`'s existing success contract) instead of an in-place row removal, since the row no longer exists as the origin of the action.
- The `404` failure path is byte-for-byte unchanged from 001-project-management.
- No new validation-rejection response exists yet in this cycle (FR-006) — a future cycle will add a case where this route can respond with an OOB `#page-errors` fragment instead of succeeding, once a cascade-blocking rule exists. That response shape is not part of this contract yet; only the container it will target is being introduced (see below).

## New: page-level error fragment container (currently always empty)

`app/templates/partials/_page_errors.html`, included once on `projects/detail.html`:

```html
<div id="page-errors" hx-swap-oob="true">
  <!-- empty in this cycle; a future rule will populate this with a rejection message -->
</div>
```

This is structurally parallel to the existing `#form-errors` OOB pattern used by create/edit (see 001-project-management's contract), but under a distinct id (`page-errors`) since it belongs to a page-level action rather than a form submission. No route in this cycle populates it with content.
