from pathlib import Path

from fastapi import APIRouter, Depends, Request, Response
from fastapi.templating import Jinja2Templates
from sqlmodel import Session

from app import services
from app.database import get_session

router = APIRouter(tags=["deleted"])

templates = Jinja2Templates(directory=Path(__file__).resolve().parent.parent / "templates")


@router.get("/deleted")
def deleted_items(request: Request, session: Session = Depends(get_session)) -> Response:
    projects = services.list_deleted_projects(session)
    group_task_groups = services.list_deleted_group_tasks_grouped_by_project(session)
    return templates.TemplateResponse(
        request,
        "deleted.html",
        {"projects": projects, "group_task_groups": group_task_groups},
    )
