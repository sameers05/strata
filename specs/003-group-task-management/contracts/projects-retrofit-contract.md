# Contract: Project Route Changes (retrofit for Group-task)

This documents the three existing Project routes this feature modifies. Everything else in `001-project-management`'s `projects-routes.md` and `002-relocate-project-delete`'s `projects-delete-contract.md` is unchanged.

## `GET /projects/{id}` — now also renders the nested Group-task list

| Method | Path | Purpose | Success response | Failure response |
|---|---|---|---|---|
| `GET` | `/projects/{id}` | Project detail, now including its active Group-tasks | `200`, full page `projects/detail.html`, now also rendering a nested table (`partials/_group_task_row.html` per row) of `services.list_active_group_tasks(session, project_id=id)`, ascending by `serial_num`, plus a "New group-task" link to `/projects/{id}/group-tasks/new` | `404` if the Project itself is missing or soft-deleted (unchanged from 001) |

No new failure mode: this route's own not-found behavior is unchanged; it simply has more to render on success.

## `DELETE /projects/{id}` — new rejection path when active Group-tasks exist

| Method | Path | Purpose | Success response | Failure response |
|---|---|---|---|---|
| `DELETE` | `/projects/{id}` | Soft-delete a Project, now gated on zero active Group-tasks | `200`, empty body + `HX-Redirect: /projects` (unchanged from 002) — only when zero active Group-tasks exist under this Project | `404` if already missing/soft-deleted (unchanged). **New**: `200` (not 4xx — same reasoning as the create/edit OOB convention) + OOB fragment targeting `#page-errors` (reusing `_page_errors.html` unchanged) when ≥1 active Group-task exists; the Project remains active, no `HX-Redirect` header is sent, and the button's existing `hx-swap="none"` means the page is left exactly as-is aside from the OOB error swap |

### Rejection fragment

```html
<div id="page-errors" hx-swap-oob="true">
  <ul class="errors">
    <li>Cannot delete: this project still has active group-tasks</li>
  </ul>
</div>
```

`#page-errors` is the same always-present container `002-relocate-project-delete` added to `projects/detail.html` specifically for this purpose (currently empty in that cycle). No new container, no new template.

## `GET /deleted` (relocated from `GET /projects/deleted`)

| Method | Path | Purpose | Success response | Failure response |
|---|---|---|---|---|
| `GET` | `/deleted` | Global Deleted Items view: soft-deleted Projects and soft-deleted Group-tasks, two labeled sections | `200`, full page `deleted.html` (moved out of `templates/projects/`) — "Deleted Projects" section unchanged from 001/002's behavior; "Deleted Group-tasks" section lists each deleted Group-task's `serial_num`/`title` plus its parent Project's `serial_num`/`title`, as plain read-only text (no links, no edit/restore controls), grouped by parent Project ascending by the parent's `serial_num`, Group-tasks within each group ascending by their own `serial_num` | — (empty-state text in either or both sections if nothing is soft-deleted yet, never an error) |

- `GET /projects/deleted` no longer exists as a route; the one existing link to it (in `base.html`'s nav or wherever the "Deleted items" link currently lives) is updated to point at `/deleted` (FR-025). No redirect/alias is kept — no other consumer of the old URL exists in this codebase.
- The "Deleted Group-tasks" section's parent-Project lookup deliberately does **not** require the parent to be active (see `data-model.md`'s Derived Views and `research.md`) — a Group-task whose parent was later also soft-deleted still displays correctly, by that parent's frozen identity.

## Not part of this contract

- Any change to `POST /projects`, `GET /projects/new`, `GET /projects/{id}/edit`, or `PUT /projects/{id}` — all unchanged from 001.
- Any restore/un-delete route anywhere — still forbidden (FR-013 for Group-task, unchanged FR-017 for Project).
