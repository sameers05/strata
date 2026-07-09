from datetime import date

from sqlmodel import Session, select

from app.models import GroupTask, Project, Status


class ProjectValidationError(Exception):
    def __init__(self, errors: dict[str, str]) -> None:
        self.errors = errors
        super().__init__("; ".join(f"{field}: {message}" for field, message in errors.items()))


class ProjectNotFoundError(Exception):
    pass


class GroupTaskNotFoundError(Exception):
    pass


def _validate_common_fields(
    title: str,
    description: str,
    start_date: date | None,
    finished_date: date | None,
) -> dict[str, str]:
    errors: dict[str, str] = {}
    if not title.strip():
        errors["title"] = "Title is required."
    elif len(title) > 200:
        errors["title"] = "Title must be 200 characters or fewer."
    if not description.strip():
        errors["description"] = "Description is required."
    elif len(description) > 2000:
        errors["description"] = "Description must be 2000 characters or fewer."
    if start_date is not None and finished_date is not None and finished_date < start_date:
        errors["finished_date"] = "Finished date cannot be earlier than start date."
    return errors


def _check_title_conflict(
    session: Session, title: str, exclude_id: int | None
) -> str | None:
    statement = select(Project).where(Project.deleted == False, Project.title == title)  # noqa: E712
    if exclude_id is not None:
        statement = statement.where(Project.id != exclude_id)
    if session.exec(statement).first() is not None:
        return "This title is already in use by another active project."
    return None


def _check_serial_num_conflict(
    session: Session, serial_num: int, exclude_id: int | None
) -> str | None:
    statement = select(Project).where(
        Project.deleted == False, Project.serial_num == serial_num  # noqa: E712
    )
    if exclude_id is not None:
        statement = statement.where(Project.id != exclude_id)
    if session.exec(statement).first() is not None:
        return "This serial number is already in use by another active project."
    return None


def create_project(
    session: Session,
    *,
    title: str,
    description: str,
    start_date: date | None = None,
    finished_date: date | None = None,
    notes: str | None = None,
    status: Status = Status.NEW,
) -> Project:
    errors = _validate_common_fields(title, description, start_date, finished_date)

    title_error = _check_title_conflict(session, title, exclude_id=None)
    if title_error:
        errors["title"] = title_error

    if errors:
        raise ProjectValidationError(errors)

    max_serial_num = session.exec(
        select(Project.serial_num)
        .where(Project.deleted == False)  # noqa: E712
        .order_by(Project.serial_num.desc())
    ).first()
    next_serial_num = 0 if max_serial_num is None else max_serial_num + 1

    project = Project(
        serial_num=next_serial_num,
        title=title,
        description=description,
        start_date=start_date,
        finished_date=finished_date,
        notes=notes,
        status=status,
        deleted=False,
    )
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


def update_project(
    session: Session,
    project_id: int,
    *,
    serial_num: int,
    title: str,
    description: str,
    start_date: date | None = None,
    finished_date: date | None = None,
    notes: str | None = None,
    status: Status,
) -> Project:
    project = session.get(Project, project_id)
    if project is None or project.deleted:
        raise ProjectNotFoundError(project_id)

    errors = _validate_common_fields(title, description, start_date, finished_date)

    if serial_num != project.serial_num:
        serial_num_error = _check_serial_num_conflict(
            session, serial_num, exclude_id=project_id
        )
        if serial_num_error:
            errors["serial_num"] = serial_num_error

    title_error = _check_title_conflict(session, title, exclude_id=project_id)
    if title_error:
        errors["title"] = title_error

    if errors:
        raise ProjectValidationError(errors)

    project.serial_num = serial_num
    project.title = title
    project.description = description
    project.start_date = start_date
    project.finished_date = finished_date
    project.notes = notes
    project.status = status
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


def soft_delete_project(session: Session, project_id: int) -> Project:
    project = session.get(Project, project_id)
    if project is None or project.deleted:
        raise ProjectNotFoundError(project_id)

    has_active_group_task = (
        session.exec(
            select(GroupTask.id).where(
                GroupTask.project_id == project_id,
                GroupTask.deleted == False,  # noqa: E712
            )
        ).first()
        is not None
    )
    if has_active_group_task:
        raise ProjectValidationError(
            {"group_tasks": "Cannot delete: this project still has active group-tasks"}
        )

    project.deleted = True
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


def list_active_projects(session: Session) -> list[Project]:
    statement = (
        select(Project)
        .where(Project.deleted == False)  # noqa: E712
        .order_by(Project.serial_num.asc())
    )
    return list(session.exec(statement).all())


def get_active_project(session: Session, project_id: int) -> Project | None:
    project = session.get(Project, project_id)
    if project is None or project.deleted:
        return None
    return project


def list_deleted_projects(session: Session) -> list[Project]:
    statement = (
        select(Project)
        .where(Project.deleted == True)  # noqa: E712
        .order_by(Project.serial_num.asc())
    )
    return list(session.exec(statement).all())


def _validate_group_task_fields(
    title: str,
    description: str,
    start_date: date | None,
    finished_date: date | None,
) -> dict[str, str]:
    errors: dict[str, str] = {}
    if not title.strip():
        errors["title"] = "Title is required."
    elif len(title) > 200:
        errors["title"] = "Title must be 200 characters or fewer."
    if not description.strip():
        errors["description"] = "Description is required."
    elif len(description) > 2000:
        errors["description"] = "Description must be 2000 characters or fewer."
    if start_date is not None and finished_date is not None and finished_date < start_date:
        errors["finished_date"] = "Finished date cannot be earlier than start date."
    return errors


def _check_group_task_title_conflict(
    session: Session, project_id: int, title: str, exclude_id: int | None
) -> str | None:
    statement = select(GroupTask).where(
        GroupTask.deleted == False,  # noqa: E712
        GroupTask.project_id == project_id,
        GroupTask.title == title,
    )
    if exclude_id is not None:
        statement = statement.where(GroupTask.id != exclude_id)
    if session.exec(statement).first() is not None:
        return "This title is already in use by another active group-task in this project."
    return None


def _check_group_task_serial_num_conflict(
    session: Session, project_id: int, serial_num: int, exclude_id: int | None
) -> str | None:
    statement = select(GroupTask).where(
        GroupTask.deleted == False,  # noqa: E712
        GroupTask.project_id == project_id,
        GroupTask.serial_num == serial_num,
    )
    if exclude_id is not None:
        statement = statement.where(GroupTask.id != exclude_id)
    if session.exec(statement).first() is not None:
        return "This serial number is already in use by another active group-task in this project."
    return None


def create_group_task(
    session: Session,
    project_id: int,
    *,
    title: str,
    description: str,
    start_date: date | None = None,
    finished_date: date | None = None,
    notes: str | None = None,
    status: Status = Status.NEW,
) -> GroupTask:
    errors = _validate_group_task_fields(title, description, start_date, finished_date)

    title_error = _check_group_task_title_conflict(session, project_id, title, exclude_id=None)
    if title_error:
        errors["title"] = title_error

    if errors:
        raise ProjectValidationError(errors)

    max_serial_num = session.exec(
        select(GroupTask.serial_num)
        .where(GroupTask.deleted == False, GroupTask.project_id == project_id)  # noqa: E712
        .order_by(GroupTask.serial_num.desc())
    ).first()
    next_serial_num = 0 if max_serial_num is None else max_serial_num + 1

    group_task = GroupTask(
        project_id=project_id,
        serial_num=next_serial_num,
        title=title,
        description=description,
        start_date=start_date,
        finished_date=finished_date,
        notes=notes,
        status=status,
        deleted=False,
    )
    session.add(group_task)
    session.commit()
    session.refresh(group_task)
    return group_task


def list_active_group_tasks(session: Session, project_id: int) -> list[GroupTask]:
    statement = (
        select(GroupTask)
        .where(GroupTask.deleted == False, GroupTask.project_id == project_id)  # noqa: E712
        .order_by(GroupTask.serial_num.asc())
    )
    return list(session.exec(statement).all())


def update_group_task(
    session: Session,
    project_id: int,
    group_task_id: int,
    *,
    serial_num: int,
    title: str,
    description: str,
    start_date: date | None = None,
    finished_date: date | None = None,
    notes: str | None = None,
    status: Status,
) -> GroupTask:
    group_task = session.get(GroupTask, group_task_id)
    if group_task is None or group_task.deleted or group_task.project_id != project_id:
        raise GroupTaskNotFoundError(group_task_id)

    errors = _validate_group_task_fields(title, description, start_date, finished_date)

    if serial_num != group_task.serial_num:
        serial_num_error = _check_group_task_serial_num_conflict(
            session, project_id, serial_num, exclude_id=group_task_id
        )
        if serial_num_error:
            errors["serial_num"] = serial_num_error

    title_error = _check_group_task_title_conflict(
        session, project_id, title, exclude_id=group_task_id
    )
    if title_error:
        errors["title"] = title_error

    if errors:
        raise ProjectValidationError(errors)

    group_task.serial_num = serial_num
    group_task.title = title
    group_task.description = description
    group_task.start_date = start_date
    group_task.finished_date = finished_date
    group_task.notes = notes
    group_task.status = status
    session.add(group_task)
    session.commit()
    session.refresh(group_task)
    return group_task


def get_active_group_task(
    session: Session, project_id: int, group_task_id: int
) -> GroupTask | None:
    group_task = session.get(GroupTask, group_task_id)
    if group_task is None or group_task.deleted or group_task.project_id != project_id:
        return None
    return group_task


def soft_delete_group_task(session: Session, project_id: int, group_task_id: int) -> GroupTask:
    group_task = session.get(GroupTask, group_task_id)
    if group_task is None or group_task.deleted or group_task.project_id != project_id:
        raise GroupTaskNotFoundError(group_task_id)

    group_task.deleted = True
    session.add(group_task)
    session.commit()
    session.refresh(group_task)
    return group_task


def list_deleted_group_tasks_grouped_by_project(
    session: Session,
) -> list[tuple[Project, list[GroupTask]]]:
    deleted_group_tasks = session.exec(
        select(GroupTask).where(GroupTask.deleted == True)  # noqa: E712
    ).all()

    group_tasks_by_project_id: dict[int, list[GroupTask]] = {}
    for group_task in deleted_group_tasks:
        group_tasks_by_project_id.setdefault(group_task.project_id, []).append(group_task)

    groups: list[tuple[Project, list[GroupTask]]] = []
    for project_id, group_tasks in group_tasks_by_project_id.items():
        # ignores the parent's own `deleted` flag by design (FR's US6 acceptance scenario 4)
        parent = session.get(Project, project_id)
        group_tasks.sort(key=lambda gt: gt.serial_num)
        groups.append((parent, group_tasks))

    groups.sort(key=lambda pair: pair[0].serial_num)
    return groups
