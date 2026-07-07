# Research: Project Management

All items below were resolved without needing user clarification — the spec's checklist confirmed no `NEEDS CLARIFICATION` markers remain. These are implementation-approach decisions needed to fill in Technical Context and downstream design.

**Scope note**: Rootless Podman containerization, and verifying `DATABASE_URL` behavior inside vs. outside a container, are deferred to Stage 5 and are explicitly not part of this research or plan. This slice targets a local venv only.

## Language/runtime version

- **Decision**: Target Python 3.12.
- **Rationale**: The host (Fedora 44) already ships Python 3.14.6, but 3.14 is only months old; FastAPI/SQLModel/Alembic's transitive dependency graph (pydantic-core, greenlet, uvloop wheels) lags behind the newest CPython by a release or two on first availability. 3.12 is fully supported by the whole stack today with no wheel-availability risk, and Podman's build image can pin an exact Python version independent of host Python.
- **Alternatives considered**: Python 3.14 (host default) — rejected for now due to dependency wheel lag risk on a from-scratch project; Python 3.11 — no advantage over 3.12, and 3.12 has faster startup/lower memory (relevant on the 32GB shared host running other containers).

## Testing strategy

- **Decision**: pytest, with `httpx.ASGITransport` (or FastAPI's `TestClient`, which wraps it) for integration tests against the real ASGI app, and plain SQLModel `Session` fixtures for unit tests of service-layer logic. Each test gets an isolated SQLite database (file-per-test-session or `:memory:` with `StaticPool`) via `tests/conftest.py` fixtures, so uniqueness/serial_num tests never interact with each other **or** with the local dev database at `./data/strata.db`. The suite must at minimum cover: duplicate title rejection (active-only scope), serial_num conflict rejection (including the same-value edit being a no-op, not a conflict), serial_num auto-assignment (including reuse of a number after the project holding it is soft-deleted), date-ordering validation, soft-delete visibility rules (disappears from active views, appears read-only in Deleted Items, frozen serial_num), and free-form status transitions.
- **Rationale**: This is the de facto standard for FastAPI + SQLModel projects; it lets business-rule tests (uniqueness, serial_num assignment, date ordering) run fast and isolated at the service layer, while route tests validate the actual HTTP/HTMX contract (including the `HX-Redirect` success path and the out-of-band error-fragment failure path — see HTMX pattern below). Isolating the test DB from `./data/strata.db` prevents a test run from ever corrupting local dev data.
- **Alternatives considered**: unittest — more boilerplate, no ecosystem advantage; testing only through routes — rejected because it would make the four cross-row invariants (FR-004, FR-009, FR-010, FR-011) harder to test exhaustively without a lot of HTTP fixture overhead per case.

## Enforcing active-scoped title & serial_num uniqueness

- **Decision**: Enforce both invariants in the service layer (`project_service.py`) inside a single DB transaction per create/edit call, using a query scoped to `WHERE deleted = false` before the insert/update commits. Do not rely on a plain unique DB constraint on `title` or `serial_num` alone, since both must exclude soft-deleted rows (FR-005 explicitly allows a soft-deleted title to be reused).
- **Rationale**: SQLite supports partial unique indexes (`CREATE UNIQUE INDEX ... WHERE deleted = 0`), which is the right belt-and-suspenders backstop against races, but the primary rejection path (returning a clean validation error rather than a raw DB `IntegrityError`) must happen in application code so the UI can show FR-004/FR-009's "clear, actionable validation message" (SC-002). The service layer check-then-write happens inside one transaction to close the race window; the partial unique index catches anything that slips through under concurrent access.
- **Alternatives considered**: DB-only enforcement via partial unique index + catching `IntegrityError` at the router — rejected as the sole mechanism because translating a raw constraint violation into a field-specific validation message is fragile (parsing driver error text) compared to a pre-check in the service layer; the index remains as a safety net, not the primary UX path.

## `serial_num` auto-assignment

- **Decision**: On create, compute `serial_num = (MAX(serial_num) among active projects) + 1`, or `0` if no active project exists, inside the same transaction as the insert (`SELECT ... FOR UPDATE`-equivalent via SQLite's single-writer lock is sufficient here since SQLite serializes writers).
- **Rationale**: Matches FR-003 and the edge case ("first project ever gets 0") exactly. SQLite's single-writer model means a straightforward "compute max, then insert" inside one connection/transaction is race-free in practice for this single-user, low-concurrency application — no need for row-level locking tricks that don't exist in SQLite anyway.
- **Alternatives considered**: A separate auto-increment "next serial_num" counter table — rejected as unnecessary complexity; it wouldn't reflect soft-deletes correctly against FR-003's "max among active projects" rule anyway, since deleting the highest-serial_num project should let a new project reuse that number (per the spec's edge case), which a monotonic counter would prevent.

## Soft-delete representation

- **Decision**: A boolean `deleted` column (default `false`) on the same `project` table, rather than a separate archive table. `serial_num` is simply left untouched (frozen) at the moment `deleted` flips to `true`, since it's never recomputed for soft-deleted rows.
- **Rationale**: Simplest model that satisfies FR-016 through FR-021 exactly: one flag, one query filter (`WHERE deleted = false` for active views, `WHERE deleted = true` for Deleted Items), no migration/copy step, no risk of the two tables' schemas drifting.
- **Alternatives considered**: Separate `deleted_projects` table — rejected, adds a second schema to keep in sync for a field set that's currently identical, with no query or storage benefit at this scale (≤500 rows per SC-004).

## Status enum

- **Decision**: A Python `enum.StrEnum` (or `str, Enum` for 3.12) with the six values from FR-013, stored as a SQLite `TEXT` column via SQLModel, with no state-machine/transition table — any value can be set to any other value at any time (FR-014).
- **Rationale**: Directly matches the requirement of unrestricted transitions; a state machine would add complexity the spec explicitly says isn't needed.
- **Alternatives considered**: Integer-coded status with a lookup table — rejected as unnecessary indirection for six fixed, spec-defined values.

## HTMX + Jinja2 interaction pattern (fixed convention for this and future slices)

- **Decision**:
  - The list view (`GET /projects`) is the persistent partial-swap surface: it stays loaded and receives in-place row updates.
  - Create (`GET /projects/new`) and Edit (`GET /projects/{id}/edit`) are separate, fully navigable dedicated pages — not fragments opened over the list. Their forms submit via `hx-post` / `hx-put` respectively.
  - On successful create/edit, the server responds with an `HX-Redirect` header pointing back to `/projects`; the browser performs a full navigation and the list re-renders fully server-side. There is no targeted DOM patch on success.
  - On validation failure (duplicate title, `serial_num` conflict, invalid date ordering, etc.), the server responds **`200 OK`** (deliberately not a 4xx, so HTMX's default response handling doesn't short-circuit the swap) containing *only* an out-of-band (`hx-swap-oob="true"`) fragment targeting a fixed error-container `<div>` already present on the page. The form itself is not included in the response and is therefore not re-rendered — entered values persist naturally because that part of the DOM is never touched.
  - Soft-delete is triggered from a row in the list view via `hx-delete` (to `DELETE /projects/{id}`) targeting that row directly, with `hx-swap="delete"` so the `<tr>` is removed from the DOM in place on success — no reload, no navigation, no separate confirmation page.
  - Because the row markup (`_project_row.html`) and form markup (`_project_form.html`) are each defined once as partials and included from both the full-page templates and any place a fragment is needed, there's a single source of truth for what a row/form looks like.
- **Rationale**: This keeps every mutating action's success path resolving to one canonical place (the server-rendered `/projects` list, or the untouched form on failure) rather than juggling multiple partial-swap targets and re-render states, which is easy to get subtly wrong with HTMX. Returning `200` instead of `422` on validation failure is required for the OOB swap to apply reliably under HTMX's default behavior (HTMX only swaps non-OOB targets on 2xx by default; OOB elements still need the response to be treated as swappable). Reusing the same partials from both full pages and fragment responses guarantees the row/form the user sees on first load is pixel-identical to what appears after any subsequent update.
- **Alternatives considered**: Re-rendering the whole form fragment with inline per-field errors and a 422 status (my initial approach before this constraint was specified) — rejected per explicit direction, since it discards user-entered values that aren't re-populated by the server and fights HTMX's default 2xx-only swap behavior; targeting the create/edit forms as swappable fragments over the list (modal-style) — rejected, the user wants them as separate fully navigable pages; a JSON API consumed by client-side JS — rejected, contradicts the stated stack and adds a second contract with no corresponding requirement.

## HTMX delivery mechanism

- **Decision**: HTMX is vendored (a pinned `htmx.min.js` checked into `app/static/`) and served by FastAPI's `StaticFiles` mount, not loaded from a CDN.
- **Rationale**: Strata is a self-hosted, single-user app (README: Podman on a home server) — a CDN `<script>` tag would make the UI depend on outbound internet access and a third-party host's uptime for a tool that should work fully offline/air-gapped. Vendoring also pins the exact HTMX version under version control instead of trusting whatever a CDN happens to serve at request time.
- **Alternatives considered**: CDN `<script src="https://unpkg.com/htmx.org@.../htmx.min.js">` — rejected for the offline/self-hosted reasons above; a Python package wrapper for HTMX — unnecessary, HTMX is a single static JS file with no build step.

## `notes` field representation

- **Decision**: `notes` is a plain `str` SQLModel field with no `max_length`, giving it SQLite `TEXT` affinity and genuinely unbounded length.
- **Rationale**: Matches the spec's "unbounded free text, accumulative" requirement exactly (FR-015, Key Entities) with no artificial cap to maintain or migrate later.
- **Alternatives considered**: A capped `VARCHAR`-style field like `title`/`description` — rejected, spec explicitly distinguishes `notes` as having no enforced maximum.

## Database URL configuration

- **Decision**: `app/database.py` reads `DATABASE_URL` from the environment, defaulting to `sqlite:///./data/strata.db` when unset. The `data/` directory lives inside the repo but is gitignored; the file is created at runtime, not committed.
- **Rationale**: Lets local dev "just work" with zero configuration while leaving a clean seam for Stage 5's containerized deployment to override the URL (e.g., pointing at a mounted volume path) without any code change — that override and its container-vs-venv verification are explicitly out of scope for this plan.
- **Alternatives considered**: Hardcoding the SQLite path — rejected, would require a code change (not just an env var) to point at a different location under Podman later.

## Migrations

- **Decision**: The `Project` SQLModel class is the source of truth; the initial migration is produced with `alembic revision --autogenerate` against it, then manually reviewed and cleaned up (autogenerate reliably detects columns/types but not everything, e.g. the partial unique indexes on `title` and `serial_num` scoped to `deleted = false` may need hand-adjustment) before being applied.
- **Rationale**: Autogenerate-then-review is the standard, lowest-effort-with-safety-net Alembic workflow, and keeps the migration in sync with the model by construction rather than by hand-transcription. This slice introduces exactly one table, so one reviewed migration is the natural unit, keeping `alembic/versions/` easy to read as the project grows into Group-task and Task in later slices.
- **Alternatives considered**: Hand-writing the migration from scratch — rejected as pure duplicated effort with more room for the migration and model to drift apart; applying autogenerate output unreviewed — rejected, since autogenerate is known to miss or mis-render partial/conditional indexes, which this schema relies on.
