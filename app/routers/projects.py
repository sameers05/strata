from datetime import date
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response
from fastapi.templating import Jinja2Templates
from sqlmodel import Session

from app import services
from app.database import get_session
from app.models import Status

router = APIRouter(prefix="/projects", tags=["projects"])

templates = Jinja2Templates(directory=Path(__file__).resolve().parent.parent / "templates")


def _parse_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def _render_form_errors(request: Request, exc: services.ProjectValidationError) -> Response:
    return templates.TemplateResponse(
        request,
        "partials/_form_errors.html",
        {"errors": list(exc.errors.values())},
    )


@router.get("")
def list_projects(request: Request, session: Session = Depends(get_session)) -> Response:
    projects = services.list_active_projects(session)
    return templates.TemplateResponse(request, "projects/list.html", {"projects": projects})


@router.get("/new")
def new_project_form(request: Request) -> Response:
    return templates.TemplateResponse(request, "projects/new.html", {})


@router.post("")
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
    try:
        services.create_project(
            session,
            title=title,
            description=description,
            start_date=_parse_date(start_date),
            finished_date=_parse_date(finished_date),
            notes=notes,
            status=Status(status),
        )
    except services.ProjectValidationError as exc:
        return _render_form_errors(request, exc)
    return Response(status_code=200, headers={"HX-Redirect": "/projects"})


@router.get("/deleted")
def deleted_projects(request: Request, session: Session = Depends(get_session)) -> Response:
    projects = services.list_deleted_projects(session)
    return templates.TemplateResponse(request, "projects/deleted.html", {"projects": projects})


@router.get("/{project_id}")
def project_detail(
    request: Request, project_id: int, session: Session = Depends(get_session)
) -> Response:
    project = services.get_active_project(session, project_id)
    if project is None:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(request, "projects/detail.html", {"project": project})


@router.get("/{project_id}/edit")
def edit_project_form(
    request: Request, project_id: int, session: Session = Depends(get_session)
) -> Response:
    project = services.get_active_project(session, project_id)
    if project is None:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(request, "projects/edit.html", {"project": project})


@router.put("/{project_id}")
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
    try:
        services.update_project(
            session,
            project_id,
            serial_num=serial_num,
            title=title,
            description=description,
            start_date=_parse_date(start_date),
            finished_date=_parse_date(finished_date),
            notes=notes,
            status=Status(status),
        )
    except services.ProjectNotFoundError:
        raise HTTPException(status_code=404) from None
    except services.ProjectValidationError as exc:
        return _render_form_errors(request, exc)
    return Response(status_code=200, headers={"HX-Redirect": "/projects"})


@router.delete("/{project_id}")
def delete_project(project_id: int, session: Session = Depends(get_session)) -> Response:
    try:
        services.soft_delete_project(session, project_id)
    except services.ProjectNotFoundError:
        raise HTTPException(status_code=404) from None
    return Response(status_code=200)
