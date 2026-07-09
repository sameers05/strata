# Contract: Group-task Routes (FastAPI + HTMX/Jinja2)

Server-rendered, same convention as `001-project-management`'s `projects-routes.md` and unchanged by `002`: no separate JSON API. All routes live in `app/routers/group_tasks.py`, mounted at `/projects/{project_id}/group-tasks`.

Fixed conventions carried over unchanged:

- Create and edit are dedicated, fully navigable pages whose forms submit via HTMX, resolving on success via `HX-Redirect` — but to the **parent Project's detail page** (`/projects/{project_id}`), not to a Group-task list page (there is no standalone Group-task list; the only list is the nested one embedded on the Project detail page).
- Validation failure returns `200 OK` with only an out-of-band fragment targeting `#form-errors` (reusing `_form_errors.html` unchanged), leaving the form and its entered values untouched — identical mechanism to Project's.
- Delete is triggered only from the Group-task's own detail page (`hx-delete`, `hx-swap="none"`, `hx-confirm`), and redirects to the parent Project's detail page on success — mirroring the relocation `002` already established for Project's own delete.
- **New in this contract**: every route below declares `project: Project = Depends(get_active_project_or_404)` — one shared FastAPI dependency (research.md), not five separate checks — and 404s immediately if the parent Project is missing or soft-deleted, *before* attempting to look up the Group-task itself (FR-015a). This applies even to routes where the Group-task's own ID would otherwise resolve successfully.

## Routes

| Method | Path | Purpose | Success response | Failure response |
|---|---|---|---|---|
| `GET` | `/projects/{project_id}/group-tasks/new` | Dedicated create page, scoped to one Project | `200`, full page `group_tasks/new.html` (includes `partials/_group_task_form.html`, blank) | `404` if `project_id` missing or soft-deleted |
| `POST` | `/projects/{project_id}/group-tasks` | Create a Group-task under `project_id` | `200`, empty/minimal body + `HX-Redirect: /projects/{project_id}` | `200` (not 4xx) + OOB fragment targeting `#form-errors`; form untouched. `404` if `project_id` missing or soft-deleted (checked before any validation) |
| `GET` | `/projects/{project_id}/group-tasks/{group_task_id}` | Single Group-task detail, all fields incl. description/notes | `200`, full page `group_tasks/detail.html` (includes `_page_errors.html`, always present but empty this cycle) | `404` if `project_id` missing/soft-deleted, **or** if `group_task_id` missing/soft-deleted/not under that `project_id` |
| `GET` | `/projects/{project_id}/group-tasks/{group_task_id}/edit` | Dedicated edit page, pre-filled | `200`, full page `group_tasks/edit.html` (includes `partials/_group_task_form.html`, populated) | Same 404 conditions as detail, above |
| `PUT` | `/projects/{project_id}/group-tasks/{group_task_id}` | Update a Group-task (incl. `status`, `serial_num`; `project_id` itself is never a form field) | `200`, empty/minimal body + `HX-Redirect: /projects/{project_id}` | `200` + OOB fragment targeting `#form-errors`, form untouched. `404` per the same parent/Group-task conditions above |
| `DELETE` | `/projects/{project_id}/group-tasks/{group_task_id}` | Soft-delete a Group-task, triggered from its own detail page (`hx-delete`, `hx-swap="none"`, `hx-confirm`) | `200`, empty body + `HX-Redirect: /projects/{project_id}` | `404` per the same parent/Group-task conditions above. Unconditional otherwise — no active-Task check exists yet (FR-012) |

## Parent-resolution contract (FR-015a)

`app/routers/group_tasks.py` defines exactly one dependency function:

```python
def get_active_project_or_404(
    project_id: int, session: Session = Depends(get_session)
) -> Project:
    project = services.get_active_project(session, project_id)
    if project is None:
        raise HTTPException(status_code=404)
    return project
```

Every route above takes `project: Project = Depends(get_active_project_or_404)` in its own signature — none re-implements this check inline, and none calls it manually as a function-body statement. FastAPI resolves the dependency (and therefore the 404) before the route body ever runs, and before any Group-task lookup, form parsing, or validation happens. A stale link to `/projects/999/group-tasks/1` where Project 999 never existed (or was later soft-deleted) 404s regardless of whether Group-task 1 exists, and regardless of which HTTP method is used. Because the check exists in this one function only, any future change to it (message, logging, behavior) applies to all five routes automatically.

## Validation error contract (unchanged shape, reused container)

Identical to `001-project-management`'s contract — `#form-errors`, `hx-swap-oob="true"`, populated with human-readable messages from the same style of validation errors (blank/whitespace title or description per FR-008a, length limits, duplicate title/serial_num *within this Project*, bad date ordering):

```html
<div id="form-errors" hx-swap-oob="true">
  <ul class="errors">
    <li>This title is already in use by another active group-task in this project.</li>
  </ul>
</div>
```

## Not part of this contract

- Any route under a Task path — out of scope per FR-029.
- Any route that reassigns a Group-task's `project_id` — permanently out of scope per FR-030; no such route exists or is planned.
- The nested list itself has no dedicated route — it is rendered as part of `GET /projects/{project_id}` (see `projects-retrofit-contract.md`).
- The `/deleted` view's "Deleted Group-tasks" section — read-only, no mutating routes, no links; see `projects-retrofit-contract.md`.
