from datetime import date
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session

from app import services
from app.database import get_session
from app.models import GroupTask, Project, Status

router = APIRouter(prefix="/panes/projects/{project_id}/group-tasks", tags=["group-tasks"])

templates = Jinja2Templates(directory=Path(__file__).resolve().parent.parent / "templates")


def get_active_project_or_404(
    project_id: int, session: Session = Depends(get_session)
) -> Project:
    project = services.get_active_project(session, project_id)
    if project is None:
        raise HTTPException(status_code=404)
    return project


def _parse_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def _render(request: Request, template: str, context: dict) -> str:
    return templates.get_template(template).render({"request": request, **context})


def _render_form_errors_oob(request: Request, errors: list[str]) -> str:
    return _render(request, "partials/_form_errors.html", {"errors": errors, "oob": True})


def _details_pane_default(project: Project, session: Session) -> tuple[str, dict]:
    group_tasks = services.list_active_group_tasks(session, project_id=project.id)
    if group_tasks:
        return "panes/details_group_task.html", {
            "group_task": group_tasks[0],
            "project_id": project.id,
        }
    return "panes/details_create_prompt.html", {
        "entity_label": "group-task",
        "new_url": f"/panes/projects/{project.id}/group-tasks/new",
    }


@router.get("")
def list_group_tasks(
    request: Request,
    project: Project = Depends(get_active_project_or_404),
    session: Session = Depends(get_session),
) -> Response:
    group_tasks = services.list_active_group_tasks(session, project_id=project.id)
    details_template, details_context = _details_pane_default(project, session)
    body = _render(
        request,
        "panes/left_group_tasks.html",
        {"project": project, "group_tasks": group_tasks},
    )
    body += _render(request, details_template, {**details_context, "oob": True})
    return HTMLResponse(body)


@router.get("/new")
def new_group_task_form(
    request: Request, project: Project = Depends(get_active_project_or_404)
) -> Response:
    return templates.TemplateResponse(
        request,
        "panes/details_group_task.html",
        {"group_task": None, "project_id": project.id},
    )


@router.post("")
def create_group_task(
    request: Request,
    title: Annotated[str, Form()],
    description: Annotated[str, Form()],
    start_date: Annotated[str | None, Form()] = None,
    finished_date: Annotated[str | None, Form()] = None,
    notes: Annotated[str | None, Form()] = None,
    status: Annotated[str, Form()] = Status.NEW.value,
    project: Project = Depends(get_active_project_or_404),
    session: Session = Depends(get_session),
) -> Response:
    parsed_start_date = _parse_date(start_date)
    parsed_finished_date = _parse_date(finished_date)
    parsed_status = Status(status)
    try:
        group_task = services.create_group_task(
            session,
            project.id,
            title=title,
            description=description,
            start_date=parsed_start_date,
            finished_date=parsed_finished_date,
            notes=notes,
            status=parsed_status,
        )
    except services.ProjectValidationError as exc:
        retained = GroupTask(
            project_id=project.id,
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
            "panes/details_group_task.html",
            {
                "group_task": retained,
                "project_id": project.id,
                "errors": list(exc.errors.values()),
            },
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
    group_tasks = services.list_active_group_tasks(session, project_id=project.id)
    body = _render(
        request,
        "panes/details_group_task.html",
        {"group_task": group_task, "project_id": project.id},
    )
    body += _render(
        request,
        "panes/_row_oob.html",
        {
            "row_template": "partials/_group_task_list_body.html",
            "group_tasks": group_tasks,
            "oob": True,
        },
    )
    return HTMLResponse(body)


@router.get("/{group_task_id}")
def select_group_task(
    request: Request,
    group_task_id: int,
    project: Project = Depends(get_active_project_or_404),
    session: Session = Depends(get_session),
) -> Response:
    group_task = services.get_active_group_task(session, project.id, group_task_id)
    if group_task is None:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(
        request,
        "panes/details_group_task.html",
        {"group_task": group_task, "project_id": project.id},
    )


@router.put("/{group_task_id}")
def update_group_task(
    request: Request,
    group_task_id: int,
    serial_num: Annotated[int, Form()],
    title: Annotated[str, Form()],
    description: Annotated[str, Form()],
    start_date: Annotated[str | None, Form()] = None,
    finished_date: Annotated[str | None, Form()] = None,
    notes: Annotated[str | None, Form()] = None,
    status: Annotated[str, Form()] = Status.NEW.value,
    project: Project = Depends(get_active_project_or_404),
    session: Session = Depends(get_session),
) -> Response:
    parsed_start_date = _parse_date(start_date)
    parsed_finished_date = _parse_date(finished_date)
    parsed_status = Status(status)
    try:
        group_task = services.update_group_task(
            session,
            project.id,
            group_task_id,
            serial_num=serial_num,
            title=title,
            description=description,
            start_date=parsed_start_date,
            finished_date=parsed_finished_date,
            notes=notes,
            status=parsed_status,
        )
    except services.GroupTaskNotFoundError:
        raise HTTPException(status_code=404) from None
    except services.ProjectValidationError as exc:
        retained = GroupTask(
            id=group_task_id,
            project_id=project.id,
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
            "panes/details_group_task.html",
            {
                "group_task": retained,
                "project_id": project.id,
                "errors": list(exc.errors.values()),
            },
        )
        body += _render_form_errors_oob(request, list(exc.errors.values()))
        return HTMLResponse(body)
    body = _render(
        request,
        "panes/details_group_task.html",
        {"group_task": group_task, "project_id": project.id},
    )
    body += _render(
        request,
        "panes/_row_oob.html",
        {"row_template": "partials/_group_task_row.html", "group_task": group_task, "oob": "true"},
    )
    return HTMLResponse(body)


@router.delete("/{group_task_id}")
def delete_group_task(
    request: Request,
    group_task_id: int,
    selected_type: Annotated[str | None, Query()] = None,
    selected_id: Annotated[str | None, Query()] = None,
    project: Project = Depends(get_active_project_or_404),
    session: Session = Depends(get_session),
) -> Response:
    try:
        services.soft_delete_group_task(session, project.id, group_task_id)
    except services.GroupTaskNotFoundError:
        raise HTTPException(status_code=404) from None
    body = _render(
        request,
        "partials/_row_delete.html",
        {"row_id": f"group-task-row-{group_task_id}"},
    )
    if selected_type == "group_task" and selected_id == str(group_task_id):
        details_template, details_context = _details_pane_default(project, session)
        body += _render(request, details_template, {**details_context, "oob": True})
    return HTMLResponse(body)
