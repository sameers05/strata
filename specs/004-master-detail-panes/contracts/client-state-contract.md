# Contract: Client-Side (Alpine + HTMX) Conventions

This is a UI/DOM contract, not an HTTP route contract — it documents the conventions the shell (`base.html`) and every pane fragment must follow for the client-side mechanics in `research.md` to work. Alpine.js is scoped narrowly to the two things vanilla HTMX can't express: unsaved-changes guarding and divider drag+persistence (per the plan input). Everything else stays plain HTMX (`hx-get`/`hx-post`/`hx-put`/`hx-delete`, OOB swaps).

## 1. Unsaved-changes navigation guard

- **Marker attribute**: `data-pane-nav` — present on every row title/View link, every breadcrumb link, the "+ New [entity]" control, the "Deleted Items" link, and the Back control. **Absent** from the details-pane's own Save button and the divider's drag handle.
- **Dirty tracking**: an Alpine component wrapping `#details-pane`'s form snapshots each field's value on `x-init` (i.e., every time the pane is swapped in, since swapped-in content re-runs `x-init`). Any `input`/`change` event on a form field sets an in-memory `dirty` flag to `true`.
- **Interception**: one Alpine listener at the shell root, bound once, on the document-wide `htmx:confirm` event (fired by htmx before *every* htmx-triggered request, cancelable). The handler is a no-op unless `evt.detail.elt` carries `data-pane-nav`. When it does and `dirty` is `true`, the handler calls the browser's native `confirm(...)`; on cancel, the request is prevented; on confirm (or when `dirty` is `false`), the request proceeds normally.
- **Reset**: `dirty` returns to `false` automatically whenever `#details-pane` is swapped (new DOM → new `x-init` → new snapshot), including after a successful Save.
- **Why delete controls don't need this**: they don't carry `data-pane-nav`. Deleting a row never touches `#details-pane` unless that row happens to be the selected entity (`contracts/pane-mutation-routes.md`'s FR-017a mechanism), which is a server-computed outcome the user didn't have a chance to "cancel" anyway — the dirty-guard's purpose (protect in-progress edits from being silently replaced by clicking *elsewhere*) doesn't apply to deleting the row you're not editing.

## 2. Selected-entity self-description

- `#details-pane`'s root element carries `data-entity-type` (`"project"` or `"group_task"`) and `data-entity-id` (the entity's id) whenever it shows a saved, selected entity. Both are absent/empty for the blank-create form and the Deleted-Items empty state.
- Every delete control's `hx-vals` reads these two attributes off `#details-pane` at request time (`hx-vals='js:{selected_type: document.getElementById("details-pane").dataset.entityType, selected_id: document.getElementById("details-pane").dataset.entityId}'`) and sends them as request parameters — this is how the otherwise-stateless server implements FR-017a (`contracts/pane-mutation-routes.md`). This is a direct DOM read, not an Alpine store — unlike §4 below (which genuinely needs a store, since "last list URL" has no DOM element of its own to live on), the selected entity's type/id is already sitting on `#details-pane`'s own attributes, so mirroring it into a second, separately-updated store would just be duplicate state (research.md).

## 3. Divider drag + persistence

- An Alpine component at the shell root owns the left pane's width as a percentage (`x-data="{ splitPct: ... }"`), bound to both panes' inline widths.
- On `pointerdown` on the divider, subsequent `pointermove` events update `splitPct` live (both panes resize live, FR-024). On `pointerup`, the final value is written to `localStorage` under a fixed key.
- On initial page load (`base.html`'s root `x-init`), the shell reads that `localStorage` key; if present, it's applied before/at first paint; if absent (first-ever load, or cleared storage), `splitPct` falls back to a default (30/70).
- This is the **only** piece of state in this feature that survives a browser reload — consistent with FR-025, and distinct from drill/selection state, which FR-002 explicitly requires to reset on every reload.

## 4. Last-shown left-pane list URL (Back control target)

- A separate, in-memory-only Alpine store (not `localStorage` — see research.md) records the URL of the most recently rendered left-pane **list** fragment (`/panes/projects` or `/panes/projects/{id}/group-tasks`).
- Updated via an `htmx:afterSwap` listener scoped to `#left-pane`: after any swap, if the just-rendered view is a list (not the Deleted Items view), record its source URL; if it *is* the Deleted Items view, don't overwrite the store.
- The Back control's `hx-get` target is bound to this store's current value, defaulting to `/panes/projects` if nothing has been recorded yet.
- This store is never read from or written to `localStorage` and is naturally reset on reload (a fresh page load has no memory of it), matching FR-002.

## What Alpine is explicitly *not* used for

Everything else in this feature is achievable with plain HTMX and needs no Alpine component: list/details swaps (`hx-get` + `hx-target`), row insertion/replacement/removal (OOB swaps — `hx-swap-oob="beforeend:..."` on create, `hx-swap-oob="true"` on edit, `hx-swap-oob="delete"` on delete; the delete control itself uses `hx-swap="none"`, not `hx-swap="delete"`, so row removal only happens when the server explicitly includes that OOB fragment — see `contracts/pane-mutation-routes.md`'s "Row removal" section and research.md), form submission and validation-error display (`hx-post`/`hx-put` + OOB `#form-errors`), and delete confirmation for the *destructive action itself* (existing `hx-confirm`, unchanged from prior slices — this is a different confirm than the unsaved-changes one above, and both can coexist since they gate different things: `hx-confirm` gates the delete action's own destructiveness, the `htmx:confirm` dirty-guard gates *other* navigation away from unsaved edits).
