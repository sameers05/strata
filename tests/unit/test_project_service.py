from datetime import date

import pytest
from sqlmodel import Session

from app.models import Status
from app.services import (
    ProjectNotFoundError,
    ProjectValidationError,
    create_project,
    get_active_project,
    list_active_projects,
    list_deleted_projects,
    soft_delete_project,
    update_project,
)


def test_serial_num_assignment_and_reuse(session: Session) -> None:
    first = create_project(session, title="First", description="d")
    assert first.serial_num == 0

    second = create_project(session, title="Second", description="d")
    assert second.serial_num == 1

    # soft-deleting the project holding the current max serial_num frees it up
    soft_delete_project(session, second.id)
    third = create_project(session, title="Third", description="d")
    assert third.serial_num == 1


def test_serial_num_uniqueness_conflict_and_noop(session: Session) -> None:
    a = create_project(session, title="A", description="d")
    b = create_project(session, title="B", description="d")

    with pytest.raises(ProjectValidationError) as exc_info:
        update_project(
            session,
            b.id,
            serial_num=a.serial_num,
            title=b.title,
            description=b.description,
            status=Status.NEW,
        )
    assert "serial_num" in exc_info.value.errors

    unchanged = get_active_project(session, b.id)
    assert unchanged.serial_num == b.serial_num

    # editing to its own current value succeeds as a no-op
    result = update_project(
        session,
        b.id,
        serial_num=b.serial_num,
        title=b.title,
        description="updated description",
        status=Status.NEW,
    )
    assert result.serial_num == b.serial_num
    assert result.description == "updated description"


def test_title_uniqueness_active_scope(session: Session) -> None:
    active = create_project(session, title="Unique Title", description="d")
    other = create_project(session, title="Other Title", description="d")

    with pytest.raises(ProjectValidationError) as exc_info:
        create_project(session, title="Unique Title", description="d")
    assert "title" in exc_info.value.errors

    with pytest.raises(ProjectValidationError) as exc_info:
        update_project(
            session,
            other.id,
            serial_num=other.serial_num,
            title="Unique Title",
            description=other.description,
            status=Status.NEW,
        )
    assert "title" in exc_info.value.errors

    # a title matching a soft-deleted project's title is allowed
    soft_delete_project(session, active.id)
    reused = create_project(session, title="Unique Title", description="d")
    assert reused.title == "Unique Title"


def test_date_ordering_validation(session: Session) -> None:
    with pytest.raises(ProjectValidationError) as exc_info:
        create_project(
            session,
            title="Bad Dates",
            description="d",
            start_date=date(2026, 2, 1),
            finished_date=date(2026, 1, 1),
        )
    assert "finished_date" in exc_info.value.errors

    project = create_project(
        session,
        title="Good Dates",
        description="d",
        start_date=date(2026, 1, 1),
        finished_date=date(2026, 2, 1),
    )

    with pytest.raises(ProjectValidationError) as exc_info:
        update_project(
            session,
            project.id,
            serial_num=project.serial_num,
            title=project.title,
            description=project.description,
            start_date=date(2026, 3, 1),
            finished_date=date(2026, 1, 1),
            status=Status.NEW,
        )
    assert "finished_date" in exc_info.value.errors

    # each may be set/cleared independently
    cleared = update_project(
        session,
        project.id,
        serial_num=project.serial_num,
        title=project.title,
        description=project.description,
        start_date=None,
        finished_date=date(2026, 2, 1),
        status=Status.NEW,
    )
    assert cleared.start_date is None
    assert cleared.finished_date == date(2026, 2, 1)


def test_status_free_form_transitions(session: Session) -> None:
    project = create_project(session, title="Status Test", description="d")
    assert project.status == Status.NEW

    updated = update_project(
        session,
        project.id,
        serial_num=project.serial_num,
        title=project.title,
        description=project.description,
        status=Status.ARCHIVED,
    )
    assert updated.status == Status.ARCHIVED

    back = update_project(
        session,
        project.id,
        serial_num=project.serial_num,
        title=project.title,
        description=project.description,
        status=Status.IN_PROGRESS,
    )
    assert back.status == Status.IN_PROGRESS


def test_soft_delete_visibility_and_frozen_serial_num(session: Session) -> None:
    a = create_project(session, title="A", description="d")
    b = create_project(session, title="B", description="d")

    soft_delete_project(session, a.id)

    active_ids = {p.id for p in list_active_projects(session)}
    assert a.id not in active_ids
    assert b.id in active_ids
    assert get_active_project(session, a.id) is None

    deleted = list_deleted_projects(session)
    assert len(deleted) == 1
    assert deleted[0].id == a.id
    assert deleted[0].serial_num == a.serial_num

    with pytest.raises(ProjectNotFoundError):
        soft_delete_project(session, a.id)

    with pytest.raises(ProjectNotFoundError):
        soft_delete_project(session, 999999)

    # deleted list is ascending by serial_num
    soft_delete_project(session, b.id)
    deleted = list_deleted_projects(session)
    assert [p.serial_num for p in deleted] == sorted(p.serial_num for p in deleted)


def test_length_limits(session: Session) -> None:
    with pytest.raises(ProjectValidationError) as exc_info:
        create_project(session, title="x" * 201, description="d")
    assert "title" in exc_info.value.errors

    with pytest.raises(ProjectValidationError) as exc_info:
        create_project(session, title="Valid Title", description="x" * 2001)
    assert "description" in exc_info.value.errors

    project = create_project(session, title="Editable", description="d")

    with pytest.raises(ProjectValidationError) as exc_info:
        update_project(
            session,
            project.id,
            serial_num=project.serial_num,
            title="y" * 201,
            description=project.description,
            status=Status.NEW,
        )
    assert "title" in exc_info.value.errors

    with pytest.raises(ProjectValidationError) as exc_info:
        update_project(
            session,
            project.id,
            serial_num=project.serial_num,
            title=project.title,
            description="y" * 2001,
            status=Status.NEW,
        )
    assert "description" in exc_info.value.errors


def test_blank_or_whitespace_title_and_description_rejected(session: Session) -> None:
    with pytest.raises(ProjectValidationError) as exc_info:
        create_project(session, title="   ", description="d")
    assert "title" in exc_info.value.errors

    with pytest.raises(ProjectValidationError) as exc_info:
        create_project(session, title="Valid Title", description="  \t\n  ")
    assert "description" in exc_info.value.errors

    project = create_project(session, title="Blank Edit Target", description="d")

    with pytest.raises(ProjectValidationError) as exc_info:
        update_project(
            session,
            project.id,
            serial_num=project.serial_num,
            title="",
            description=project.description,
            status=Status.NEW,
        )
    assert "title" in exc_info.value.errors

    with pytest.raises(ProjectValidationError) as exc_info:
        update_project(
            session,
            project.id,
            serial_num=project.serial_num,
            title=project.title,
            description="   ",
            status=Status.NEW,
        )
    assert "description" in exc_info.value.errors
