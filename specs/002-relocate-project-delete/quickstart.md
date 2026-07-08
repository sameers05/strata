# Quickstart: Validating the Project Deletion Relocation

This is a validation guide, not an implementation spec — see [data-model.md](./data-model.md) (no changes) and [contracts/projects-delete-contract.md](./contracts/projects-delete-contract.md) for the changed route contract.

## Prerequisites

- Same environment as 001-project-management: Python 3.12 venv, dependencies installed, `alembic upgrade head` already applied (no new migration in this feature).

## Setup

```bash
uvicorn app.main:app --reload
```

## Automated validation

```bash
pytest tests/unit tests/integration
```

`tests/unit` is unaffected by this feature (no service-layer change). `tests/integration/test_projects_routes.py` gains: an `HX-Redirect: /projects` assertion on the existing US4 delete flow, and a new test confirming the active list page's rendered HTML contains no `hx-delete` attribute anywhere.

## Manual validation scenarios

**US1 — Delete a project from its detail page**
1. Open an active project's detail page (`/projects/{id}`).
2. Trigger the delete control. Confirm the confirmation dialog appears (`hx-confirm`), and on confirming, the browser ends up back on `/projects` with no full reload of the detail page first.
3. Confirm the deleted project no longer appears on `/projects`, and its own detail URL now 404s.

**US2 — Project list is pure navigation**
1. Open `/projects`. Confirm no row has a delete control — only a title link (to detail) and an Edit link.
2. Confirm the only way to delete a project is to open its detail page first.

**US3 — Detail page is ready for a future rejection message**
1. View any active project's detail page. Confirm a `#page-errors` container is present in the rendered HTML (empty, since nothing can fail yet).
2. Trigger delete and confirm the outcome (redirect) happens without a full page reload of the detail page itself.

## Expected end state

`pytest tests/unit tests/integration` is green, all three scenarios above pass, and the active list, detail, edit, create, and Deleted Items views otherwise behave exactly as they did before this feature (no regression per FR-009).
