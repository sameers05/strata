# Research: Relocate Project Deletion from List to Detail View

No items required external research — this feature reuses 001-project-management's established stack and HTMX convention verbatim. The decisions below are the small number of feature-local choices needed to fill in the plan and design artifacts; none required user clarification.

## DELETE success response: adopt the HX-Redirect pattern

- **Decision**: On a successful `DELETE /projects/{id}`, change the response from a bare `200` empty body to `200` + `HX-Redirect: /projects`, mirroring `POST /projects` and `PUT /projects/{id}`'s existing success contract exactly. The `404` path (missing or already-deleted) is unchanged.
- **Rationale**: Once delete is triggered from the detail page rather than a list row, a bare `200` with no redirect would leave the browser sitting on a detail page for a project that no longer exists as active — there is nothing left to render there. `HX-Redirect` is the app's one existing mechanism for "send the browser to `/projects` after a successful mutation," so reusing it keeps a single mental model for all three mutating routes (create, edit, delete) rather than inventing a second success signal.
- **Alternatives considered**: Keep the bare `200` and have the client-side handle navigation via a `hx-on::after-request` handler or similar — rejected, since it introduces a second, template-side navigation mechanism when the server-driven `HX-Redirect` already solves this identically to create/edit; a full-page redirect response (`303`) — rejected, since it doesn't match the HTMX convention (`HX-Redirect` header, not an HTTP redirect status) already fixed by 001-project-management's research.md.

## A distinct page-level error partial, not a reused `_form_errors.html`

- **Decision**: Introduce `_page_errors.html` as a new, structurally parallel partial (`id="page-errors"`, `hx-swap-oob="true"`, empty list by default) rather than reusing `_form_errors.html`'s `#form-errors` container on the detail page.
- **Rationale**: `_form_errors.html` is conceptually tied to a `<form>` submission's validation errors (create/edit). The detail page has no form; its delete action is a standalone page-level action. Keeping the id and partial distinct avoids conflating "a field was rejected" with "an action on this page was rejected" once the future cascade-blocking rule needs to populate it, and avoids any risk of a future form on the same page double-targeting one shared id.
- **Alternatives considered**: Reuse `#form-errors` directly on the detail page — rejected as a false economy; the two partials are nearly identical today, but sharing an id across a form-error use case and a page-action-error use case would make the future rule's target ambiguous and harder to reason about.

## `hx-swap="none"` on the relocated delete button

- **Decision**: The detail page's delete button carries `hx-swap="none"`, matching the reasoning already applied to `_project_form.html`'s submit behavior.
- **Rationale**: On success there is no response body to swap (only headers), so this has no effect there. On a hypothetical future rejection (once the cascade-blocking rule exists), the response would contain only the OOB `#page-errors` fragment; without `hx-swap="none"`, HTMX's default swap behavior would still apply to the (empty) non-OOB portion of the response and could clear surrounding DOM. Setting it now means the future rule's response contract requires no template rework.
- **Alternatives considered**: Leave the default swap and defer this concern to the future cycle — rejected, since the feature description explicitly asks this cycle to prepare the error-display mechanism, and getting the swap behavior right is part of "prepared," not an added scope item.

## Confirm-dialog behavior carries over unchanged

- **Decision**: The relocated delete button keeps `hx-confirm="Delete this project?"`, identical in spirit to the row control it replaces.
- **Rationale**: Nothing in the feature description asks for a change to the confirmation UX — only the trigger's location and the post-action response contract change.
- **Alternatives considered**: Dropping or changing the confirmation copy — rejected as out of scope; not requested.

## No model, service, or migration change

- **Decision**: `app/models.py`, `app/services.py` (specifically `soft_delete_project`), and `alembic/` are not touched.
- **Rationale**: FR-006 and the feature's explicit scope both state the underlying delete rule (unconditional success) is unchanged this cycle; only the trigger location and response/UI mechanics move.
- **Alternatives considered**: None — this is a hard scope boundary from the spec, not a judgment call.
