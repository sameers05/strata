# Contract: Project Routes (FastAPI + HTMX/Jinja2)

Strata is server-rendered (HTMX + Jinja2), so the "contract" this feature exposes is a set of HTTP routes returning either full HTML pages or small HTML fragments. There is no separate JSON API for this slice. All routes live in `app/routers/projects.py`, base path `/projects`.

This is the fixed interaction convention for this slice and future ones (see research.md's HTMX pattern decision):

- The list (`/projects`) is the persistent partial-swap surface.
- Create and edit are dedicated, fully navigable pages whose forms submit via HTMX, but resolve on success via a full-page redirect (`HX-Redirect`) back to the list.
- Validation failure never uses a 4xx status; it returns `200 OK` with only an out-of-band fragment for a fixed error container, leaving the form and its entered values untouched.
- Delete acts directly on a row in the list via `hx-delete`, removing just that row.

## Routes

| Method | Path | Purpose | Success response | Failure response |
|---|---|---|---|---|
| `GET` | `/projects` | Active project list, ascending by `serial_num` | `200`, full page `projects/list.html` (includes `partials/_project_row.html` per row) | — (empty state rendered inline, never an error, per spec edge case) |
| `GET` | `/projects/new` | Dedicated create page | `200`, full page `projects/new.html` (includes `partials/_project_form.html`, blank) | — |
| `POST` | `/projects` | Create a project (submitted via `hx-post` from `/projects/new`) | `200`, empty/minimal body + `HX-Redirect: /projects` header | `200` (not 4xx) + OOB fragment (`hx-swap-oob="true"`) targeting `#form-errors` on the current page; form DOM untouched, values persist |
| `GET` | `/projects/{id}` | Single project detail | `200`, full page `projects/detail.html` | `404` if missing or soft-deleted |
| `GET` | `/projects/{id}/edit` | Dedicated edit page, pre-filled | `200`, full page `projects/edit.html` (includes `partials/_project_form.html`, populated) | `404` if missing or soft-deleted |
| `PUT` | `/projects/{id}` | Update a project (submitted via `hx-put` from `/projects/{id}/edit`), incl. `status` and `serial_num` | `200`, empty/minimal body + `HX-Redirect: /projects` header | `200` (not 4xx) + OOB fragment targeting `#form-errors`; form DOM untouched |
| `DELETE` | `/projects/{id}` | Soft-delete a project, triggered by `hx-delete` on a control within that row in `/projects`, `hx-target` = the row, `hx-swap="delete"` | `200`, empty body — HTMX removes the `<tr>` from the DOM regardless of body content | `404` if already missing/soft-deleted (row removal does not occur; error surfaced per implementation's choice, e.g. a toast — not specified further as this is an edge case with no normal path to it) |
| `GET` | `/projects/deleted` | Deleted Items view, ascending by `serial_num`, strictly read-only | `200`, full page `projects/deleted.html` (no edit/restore controls rendered anywhere on it) | — |

## Validation error contract (HTML, out-of-band swap — not JSON, not 4xx)

On `POST /projects` or `PUT /projects/{id}` failing any of R1–R6 (data-model.md), the server responds `200 OK` with a body containing **only** a fragment like:

```html
<div id="form-errors" hx-swap-oob="true">
  <ul class="errors">
    <li>This title is already in use by another active project.</li>
  </ul>
</div>
```

`#form-errors` is a fixed, always-present container on both `new.html` and `edit.html`. HTMX applies the OOB swap by matching this `id` regardless of the triggering element's own `hx-target`. The form fields themselves are not part of the response, so the browser never re-renders them — whatever the user typed remains exactly as they left it. This satisfies SC-002's "clear, actionable validation message" requirement while matching the fixed HTMX convention (200-only responses, OOB error swap, no form re-render).

## Not part of this contract

- Any route under a Group-task or Task path — out of scope per FR-026.
- Any authentication/session route — out of scope per FR-027.
- Any restore/un-delete route for `/projects/deleted` items — explicitly forbidden by FR-020.
- Any container/deployment-specific routing or health-check endpoints — Podman containerization is deferred to Stage 5.
