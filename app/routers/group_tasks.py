from datetime import date
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response
from fastapi.templating import Jinja2Templates
from sqlmodel import Session

from app import services
from app.database import get_session
from app.models import Project, Status

router = APIRouter(prefix="/projects/{project_id}/group-tasks", tags=["group-tasks"])

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


def _render_form_errors(request: Request, exc: services.ProjectValidationError) -> Response:
    return templates.TemplateResponse(
        request,
        "partials/_form_errors.html",
        {"errors": list(exc.errors.values())},
    )


@router.get("/new")
def new_group_task_form(
    request: Request, project: Project = Depends(get_active_project_or_404)
) -> Response:
    return templates.TemplateResponse(
        request, "group_tasks/new.html", {"project": project}
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
    try:
        services.create_group_task(
            session,
            project.id,
            title=title,
            description=description,
            start_date=_parse_date(start_date),
            finished_date=_parse_date(finished_date),
            notes=notes,
            status=Status(status),
        )
    except services.ProjectValidationError as exc:
        return _render_form_errors(request, exc)
    return Response(status_code=200, headers={"HX-Redirect": f"/projects/{project.id}"})


@router.get("/{group_task_id}")
def group_task_detail(
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
        "group_tasks/detail.html",
        {"project": project, "group_task": group_task},
    )


@router.get("/{group_task_id}/edit")
def edit_group_task_form(
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
        "group_tasks/edit.html",
        {"project": project, "group_task": group_task},
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
    try:
        services.update_group_task(
            session,
            project.id,
            group_task_id,
            serial_num=serial_num,
            title=title,
            description=description,
            start_date=_parse_date(start_date),
            finished_date=_parse_date(finished_date),
            notes=notes,
            status=Status(status),
        )
    except services.GroupTaskNotFoundError:
        raise HTTPException(status_code=404) from None
    except services.ProjectValidationError as exc:
        return _render_form_errors(request, exc)
    return Response(status_code=200, headers={"HX-Redirect": f"/projects/{project.id}"})


@router.delete("/{group_task_id}")
def delete_group_task(
    group_task_id: int,
    project: Project = Depends(get_active_project_or_404),
    session: Session = Depends(get_session),
) -> Response:
    try:
        services.soft_delete_group_task(session, project.id, group_task_id)
    except services.GroupTaskNotFoundError:
        raise HTTPException(status_code=404) from None
    return Response(status_code=200, headers={"HX-Redirect": f"/projects/{project.id}"})
