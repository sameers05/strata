from datetime import date
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session

from app import services
from app.database import get_session
from app.models import Project, Status

router = APIRouter(tags=["projects"])

templates = Jinja2Templates(directory=Path(__file__).resolve().parent.parent / "templates")


def _parse_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def _render(request: Request, template: str, context: dict) -> str:
    return templates.get_template(template).render({"request": request, **context})


def _render_form_errors_oob(request: Request, errors: list[str]) -> str:
    return _render(request, "partials/_form_errors.html", {"errors": errors, "oob": True})


def _details_pane_default(session: Session) -> tuple[str, dict]:
    projects = services.list_active_projects_with_delete_eligibility(session)
    if projects:
        first_project, _ = projects[0]
        return "panes/details_project.html", {"project": first_project}
    return "panes/details_create_prompt.html", {
        "entity_label": "project",
        "new_url": "/panes/projects/new",
    }


@router.get("/")
def home(request: Request, session: Session = Depends(get_session)) -> Response:
    projects = services.list_active_projects_with_delete_eligibility(session)
    details_template, details_context = _details_pane_default(session)
    return templates.TemplateResponse(
        request,
        "base.html",
        {
            "left_pane_template": "panes/left_projects.html",
            "projects": projects,
            "details_pane_template": details_template,
            **details_context,
        },
    )


@router.get("/panes/projects")
def list_projects(request: Request, session: Session = Depends(get_session)) -> Response:
    projects = services.list_active_projects_with_delete_eligibility(session)
    details_template, details_context = _details_pane_default(session)
    body = _render(request, "panes/left_projects.html", {"projects": projects})
    body += _render(request, details_template, {**details_context, "oob": True})
    return HTMLResponse(body)


@router.get("/panes/projects/new")
def new_project_form(request: Request) -> Response:
    return templates.TemplateResponse(request, "panes/details_project.html", {"project": None})


@router.post("/panes/projects")
def create_project(
    request: Request,
    title: Annotated[str, Form()],
    description: Annotated[str, Form()],
    start_date: Annotated[str | None, Form()] = None,
    finished_date: Annotated[str | None, Form()] = None,
    notes: Annotated[str | None, Form()] = None,
    status: Annotated[str, Form()] = Status.NEW.value,
    session: Session = Depends(get_session),
) -> Response:
    parsed_start_date = _parse_date(start_date)
    parsed_finished_date = _parse_date(finished_date)
    parsed_status = Status(status)
    try:
        project = services.create_project(
            session,
            title=title,
            description=description,
            start_date=parsed_start_date,
            finished_date=parsed_finished_date,
            notes=notes,
            status=parsed_status,
        )
    except services.ProjectValidationError as exc:
        retained = Project(
            serial_num=0,
            title=title,
            description=description,
            start_date=parsed_start_date,
            finished_date=parsed_finished_date,
            notes=notes,
            status=parsed_status,
            deleted=False,
        )
        body = _render(
            request,
            "panes/details_project.html",
            {"project": retained, "errors": list(exc.errors.values())},
        )
        body += _render_form_errors_oob(request, list(exc.errors.values()))
        return HTMLResponse(body)
    # A selector-targeted OOB swap (beforeend:/innerHTML:#selector) strips the OOB
    # element's own wrapper tag for every swap style except outerHTML (htmx docs:
    # "the encapsulating tag pair will be stripped for all strategies other than
    # outerHTML") — appending a single <tr> that way discards the <tr> itself,
    # leaving orphaned <td> elements with no row boundary. Re-rendering the whole
    # tbody via a plain hx-swap-oob="true" (default outerHTML, matched by the
    # tbody's own id) is correct regardless of whether the list was previously
    # empty, had one item, or had many.
    projects = services.list_active_projects_with_delete_eligibility(session)
    body = _render(request, "panes/details_project.html", {"project": project})
    body += _render(
        request,
        "panes/_row_oob.html",
        {"row_template": "partials/_project_list_body.html", "projects": projects, "oob": True},
    )
    return HTMLResponse(body)


@router.get("/panes/projects/{project_id}")
def select_project(
    request: Request, project_id: int, session: Session = Depends(get_session)
) -> Response:
    project = services.get_active_project(session, project_id)
    if project is None:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(request, "panes/details_project.html", {"project": project})


@router.put("/panes/projects/{project_id}")
def update_project(
    request: Request,
    project_id: int,
    serial_num: Annotated[int, Form()],
    title: Annotated[str, Form()],
    description: Annotated[str, Form()],
    start_date: Annotated[str | None, Form()] = None,
    finished_date: Annotated[str | None, Form()] = None,
    notes: Annotated[str | None, Form()] = None,
    status: Annotated[str, Form()] = Status.NEW.value,
    session: Session = Depends(get_session),
) -> Response:
    parsed_start_date = _parse_date(start_date)
    parsed_finished_date = _parse_date(finished_date)
    parsed_status = Status(status)
    try:
        project = services.update_project(
            session,
            project_id,
            serial_num=serial_num,
            title=title,
            description=description,
            start_date=parsed_start_date,
            finished_date=parsed_finished_date,
            notes=notes,
            status=parsed_status,
        )
    except services.ProjectNotFoundError:
        raise HTTPException(status_code=404) from None
    except services.ProjectValidationError as exc:
        retained = Project(
            id=project_id,
            serial_num=serial_num,
            title=title,
            description=description,
            start_date=parsed_start_date,
            finished_date=parsed_finished_date,
            notes=notes,
            status=parsed_status,
            deleted=False,
        )
        body = _render(
            request,
            "panes/details_project.html",
            {"project": retained, "errors": list(exc.errors.values())},
        )
        body += _render_form_errors_oob(request, list(exc.errors.values()))
        return HTMLResponse(body)
    body = _render(request, "panes/details_project.html", {"project": project})
    body += _render(
        request,
        "panes/_row_oob.html",
        {
            "row_template": "partials/_project_row.html",
            "project": project,
            "has_active_children": services.has_active_group_tasks(session, project_id),
            "oob": "true",
        },
    )
    return HTMLResponse(body)


@router.delete("/panes/projects/{project_id}")
def delete_project(
    request: Request,
    project_id: int,
    selected_type: Annotated[str | None, Query()] = None,
    selected_id: Annotated[str | None, Query()] = None,
    session: Session = Depends(get_session),
) -> Response:
    try:
        services.soft_delete_project(session, project_id)
    except services.ProjectNotFoundError:
        raise HTTPException(status_code=404) from None
    except services.ProjectValidationError as exc:
        return HTMLResponse(
            _render(
                request,
                "partials/_delete_errors.html",
                {"delete_errors": list(exc.errors.values()), "oob": True},
            )
        )
    # Full tbody re-render (hx-swap-oob="true", default outerHTML, tag-preserving,
    # matched by the tbody's own id) rather than a per-row hx-swap-oob="delete" —
    # this handles every case uniformly, including removing the last remaining row,
    # which must now show the "No projects yet." placeholder (the case a per-row
    # removal can't express on its own). Same fix already proven correct for create.
    projects = services.list_active_projects_with_delete_eligibility(session)
    body = _render(
        request,
        "panes/_row_oob.html",
        {"row_template": "partials/_project_list_body.html", "projects": projects, "oob": True},
    )
    if selected_type == "project" and selected_id == str(project_id):
        details_template, details_context = _details_pane_default(session)
        body += _render(request, details_template, {**details_context, "oob": True})
    return HTMLResponse(body)
