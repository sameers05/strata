# Contract: Pane Mutation Routes (FastAPI + HTMX/Jinja2)

`POST`/`PUT`/`DELETE` routes. All reuse the existing, unchanged service-layer functions (`create_project`, `update_project`, `soft_delete_project`, `create_group_task`, `update_group_task`, `soft_delete_group_task`) per FR-028 — only the response shape changes, from `HX-Redirect` (prior slices' full-page navigation) to direct fragment + out-of-band swaps (this feature has no separate page to redirect to).

## Routes

| Method | Path | Purpose | Success response | Failure response |
|---|---|---|---|---|
| `POST` | `/panes/projects` | Create a Project | `200`: `#details-pane` fragment (primary target) showing the saved Project, populated, `data-entity-id` now set + OOB `<tr hx-swap-oob="beforeend:#project-list-body">` appending the new row to the left pane's Project list | `200` + OOB `#form-errors` fragment inside the (still-blank, values-retained) details-pane form — same mechanism as prior slices, just rendered in place rather than on a dedicated page |
| `PUT` | `/panes/projects/{project_id}` | Update a Project | `200`: `#details-pane` fragment (updated) + OOB `<tr id="project-row-{id}" hx-swap-oob="true">` replacing the existing row in the left pane | `200` + OOB `#form-errors`, form retains entered values. `404` if `project_id` missing/soft-deleted |
| `DELETE` | `/panes/projects/{project_id}` | Soft-delete a Project, triggered from its own row's delete control | `200`, empty-bodied primary response (`hx-swap="none"` — see "Row removal" below) + OOB `<tr id="project-row-{id}" hx-swap-oob="delete">` removing the row. **If** the request's echoed `selected_type`/`selected_id` (see below) match `project`/`{project_id}`: response body additionally contains an OOB `#details-pane` swap to the next remaining active Project or the create-prompt | `200` + OOB `#page-errors`-equivalent rejection (cascade-block: active Group-tasks exist) — **no** `hx-swap-oob="delete"` row fragment in this response, so the row survives. `404` if `project_id` missing/soft-deleted |
| `POST` | `/panes/projects/{project_id}/group-tasks` | Create a Group-task under `project_id` | `200`: `#details-pane` fragment (saved, populated) + OOB append of the new row into the currently-shown Group-task list | `200` + OOB `#form-errors`, form retains values. `404` if `project_id` missing/soft-deleted (checked before validation) |
| `PUT` | `/panes/projects/{project_id}/group-tasks/{group_task_id}` | Update a Group-task, nested under its parent Project (`project: Project = Depends(get_active_project_or_404)`, same as 003), delegating to the unchanged `update_group_task(session, project_id, group_task_id, ...)` | `200`: `#details-pane` fragment (updated) + OOB row replacement in the left pane's Group-task list | `200` + OOB `#form-errors`, form retains values. `404` if `project_id` missing/soft-deleted (checked first, independent of the Group-task's own state), or if `group_task_id` missing/soft-deleted |
| `DELETE` | `/panes/projects/{project_id}/group-tasks/{group_task_id}` | Soft-delete a Group-task, nested under its parent Project, triggered from its own row's delete control | `200`, empty-bodied primary response (`hx-swap="none"`) + OOB `<tr id="group-task-row-{id}" hx-swap-oob="delete">` removing the row. **If** echoed `selected_type`/`selected_id` match `group_task`/`{group_task_id}`: OOB `#details-pane` swap to the next remaining active Group-task in that same Project's list, or the create-prompt | `404` if `project_id` missing/soft-deleted, or if `group_task_id` missing/soft-deleted. Unconditional otherwise — no active-Task check exists yet (FR-006/FR-029) |

## Row removal: explicit OOB `hx-swap-oob="delete"`, not `hx-swap="delete"` on the request

Both `DELETE` routes' delete controls declare `hx-swap="none"` (no `hx-target`) rather than htmx's built-in `hx-swap="delete"` + `hx-target="closest tr"` pattern. Row removal instead happens via an explicit out-of-band fragment in the response body: `<tr id="project-row-{id}" hx-swap-oob="delete"></tr>` (or the Group-task equivalent), present only when the delete actually succeeded.

This is required, not a style preference: a cascade-block rejection (active Group-tasks blocking a Project's delete) is itself a `200` response — the same "reject with a `200` carrying an OOB error fragment, not a 4xx" pattern this project has used since 001's own validation-error handling, necessary here because the rejection also needs to deliver an OOB `#details-pane` error swap, and htmx only processes OOB swaps out of a response it treats as successful. If the delete control used `hx-swap="delete"`, htmx would remove the row on **any** `200` — including the cascade-block rejection — regardless of whether the delete actually happened, silently making a blocked delete look like it succeeded. Making row removal an explicit, conditionally-present OOB element means the row is removed if and only if the server actually included that fragment, which it only does on genuine success.

## Parent-resolution contract for Group-task mutation routes (003's FR-015a, preserved)

`PUT` and `DELETE` above both declare `project: Project = Depends(get_active_project_or_404)`, identical to the read routes in `contracts/pane-read-routes.md` and unchanged from 003 — the parent-active check runs before the Group-task itself is looked up or mutated, for every one of these routes, not only on create.

## FR-017a mechanism: `selected_type` / `selected_id` request parameters

Every delete control's `hx-vals='js:{selected_type: document.getElementById("details-pane").dataset.entityType, selected_id: document.getElementById("details-pane").dataset.entityId}'` reads `#details-pane`'s `data-entity-type`/`data-entity-id` attributes directly off the DOM at request time — a plain synchronous read via htmx's native `js:`-prefixed `hx-vals`, not an Alpine store (see research.md's FR-017a section and `data-model.md`'s "Server-rendered fragment self-description"). The `DELETE` handler compares these to the entity it just soft-deleted:

```python
if selected_type == "project" and selected_id == project_id:
    # include the OOB "select next active item" details-pane fragment
```

When they don't match (the user deleted a row that wasn't the one open in the details pane), the response contains only the row-removal instruction — `#details-pane` is left untouched, preserving any unsaved state there. This is why the delete controls are **not** gated by the dirty-check nav guard (`contracts/client-state-contract.md`): deleting an unrelated row never discards details-pane edits, so there is nothing to warn about.

## Validation error fragment (unchanged shape, reused container)

Identical mechanism to 001/003 — `#form-errors`, `hx-swap-oob="true"`, populated with the same human-readable messages the existing `ProjectValidationError`/service-layer checks already produce:

```html
<div id="form-errors" hx-swap-oob="true">
  <ul class="errors">
    <li>This title is already in use by another active group-task in this project.</li>
  </ul>
</div>
```

## Cascade-block rejection (Project delete blocked by active Group-tasks, unchanged rule from 003)

Rendered as an OOB fragment targeting a fixed error area (the same role `_page_errors.html` played in prior slices, now scoped to live inside `#details-pane`'s chrome rather than a full page). This response is a `200` (see "Row removal" above for why) but deliberately omits the `hx-swap-oob="delete"` row fragment — the row survives because the response simply doesn't instruct the client to remove it, not because of any special-case status code.

## Not part of this contract

- Any route addressing a Task entity — out of scope (FR-006, FR-029).
- Read/navigation routes — see `contracts/pane-read-routes.md`.
- Any route reassigning a Group-task's `project_id` — permanently out of scope (unchanged from 003, FR-030 in 003's spec).
