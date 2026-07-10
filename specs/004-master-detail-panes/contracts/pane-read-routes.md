# Contract: Pane Read/Navigation Routes (FastAPI + HTMX/Jinja2)

Server-rendered fragments, same no-JSON-API convention as prior slices. All routes in this contract are `GET` and either render the full shell (`GET /` only) or a single pane's replacement content, always paired with the OOB `#details-pane` default described below where noted.

## Shared rule: list fragments always bundle a `#details-pane` default (FR-019)

Every route below marked "bundles details default" returns, in the same response:

1. The primary fragment (targets `#left-pane` via the requesting element's `hx-target`, or is the initial embedded content on `GET /`).
2. An out-of-band `<div id="details-pane" hx-swap-oob="true">...</div>` containing either that list's first active item's full details (ordered by `serial_num`) or a create-prompt if the list is empty.

This is one round trip, not two (see research.md).

## Routes

| Method | Path | Purpose | Bundles details default? | Success response | Failure |
|---|---|---|---|---|---|
| `GET` | `/` | Home shell | Yes (embedded, not OOB — it's the initial render) | `200`, full page: shell (`base.html`) with `#left-pane` = root active Project list, `#details-pane` = first active Project's details or create-prompt | Never fails (empty DB just renders the empty/create-prompt states) |
| `GET` | `/panes/projects` | Left-pane: root active Project list (breadcrumb = none, "+ New Project", "Deleted Items" link) | Yes | `200`, `#left-pane` fragment + OOB `#details-pane` | Never fails |
| `GET` | `/panes/projects/{project_id}/group-tasks` | Left-pane: drill into a Project's active Group-tasks (breadcrumb = "Projects › {project.title}", "+ New Group-task", "Deleted Items" link) | Yes | `200`, `#left-pane` fragment + OOB `#details-pane` | `404` if `project_id` missing or soft-deleted |
| `GET` | `/panes/deleted` | Left-pane: two-section read-only Deleted Items view (Deleted Projects, Deleted Group-tasks grouped by parent — same content/grouping as prior `/deleted`) | Yes, but the "default" here is always the fixed **empty** state (FR-009), never a create-prompt or item | `200`, `#left-pane` fragment + OOB `#details-pane` (empty, no selectable content) | Never fails |
| `GET` | `/panes/projects/new` | Details-pane: blank create form for a Project | No | `200`, `#details-pane` fragment, blank form, `data-entity-type`/`data-entity-id` absent | Never fails |
| `GET` | `/panes/projects/{project_id}` | Details-pane: select a Project's own details (via row title or "View") | No | `200`, `#details-pane` fragment, populated form, `data-entity-type="project"` `data-entity-id="{id}"` | `404` if missing or soft-deleted |
| `GET` | `/panes/projects/{project_id}/group-tasks/new` | Details-pane: blank create form for a Group-task under `project_id` (form's own `hx-post` targets `/panes/projects/{project_id}/group-tasks`) | No | `200`, `#details-pane` fragment, blank form | `404` if `project_id` missing or soft-deleted |
| `GET` | `/panes/projects/{project_id}/group-tasks/{group_task_id}` | Details-pane: select a Group-task's own details directly (FR-006 — title click, no drill, since Task doesn't exist), nested under its parent Project, mirroring 003 | No | `200`, `#details-pane` fragment, populated form, `data-entity-type="group_task"` `data-entity-id="{id}"` | `404` if `project_id` missing/soft-deleted (checked first, via `get_active_project_or_404`, independent of the Group-task's own state — 003's FR-015a, preserved unchanged per FR-028), **or** if `group_task_id` missing/soft-deleted/not under that `project_id` |

## Parent-resolution contract for Group-task routes (003's FR-015a, preserved)

Every route above that nests under `/panes/projects/{project_id}/group-tasks/...` declares `project: Project = Depends(get_active_project_or_404)` in its own signature — the same shared dependency 003 introduced, unmodified in behavior. FastAPI resolves it (and therefore any 404) before the route body runs and before any Group-task lookup happens, so a stale link to a Group-task under a since-deleted Project 404s regardless of whether the Group-task row itself would otherwise resolve. This applies to every nested route in this contract, not only the list route.

## Back control (FR-009a) — no dedicated server route

The Back control out of the Deleted Items view is a plain `hx-get` pointed at whichever of `/panes/projects` or `/panes/projects/{project_id}/group-tasks` the client last recorded as the active list (see `contracts/client-state-contract.md`). It is one of the two routes above, not a new endpoint — the server has no concept of "Back," only of "render this list."

## Validation error / not-found conventions (unchanged shape from prior slices)

404s use the existing plain `HTTPException(status_code=404)` pattern — unchanged from 001/003. There is no new error-fragment convention introduced by read routes; validation errors only ever occur on the mutation routes (see `contracts/pane-mutation-routes.md`).

## Not part of this contract

- Any route addressing a Task entity — Task does not exist (FR-006, FR-029).
- `POST`/`PUT`/`DELETE` routes — see `contracts/pane-mutation-routes.md`.
- Divider position and dirty-tracking — client-only, see `contracts/client-state-contract.md`.
