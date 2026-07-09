from datetime import date

import pytest
from sqlmodel import Session

from app.models import Status
from app.services import (
    ProjectValidationError,
    create_group_task,
    create_project,
    list_active_group_tasks,
    update_group_task,
)


def test_serial_num_and_title_scoped_per_project(session: Session) -> None:
    project_a = create_project(session, title="Project A", description="d")
    project_b = create_project(session, title="Project B", description="d")

    # serial_num auto-assignment is scoped per project: both first Group-tasks get 0
    a_first = create_group_task(session, project_a.id, title="Task", description="d")
    assert a_first.serial_num == 0
    b_first = create_group_task(session, project_b.id, title="Task", description="d")
    assert b_first.serial_num == 0

    a_second = create_group_task(session, project_a.id, title="Second", description="d")
    assert a_second.serial_num == 1

    # a title active under project_a is rejected for another active Group-task under project_a...
    with pytest.raises(ProjectValidationError) as exc_info:
        create_group_task(session, project_a.id, title="Task", description="d")
    assert "title" in exc_info.value.errors

    # a second, differently-titled Group-task under project_b is unaffected by project_a's conflict
    b_second = create_group_task(session, project_b.id, title="Task 2", description="d")
    assert b_second.serial_num == 1

    listed_a = list_active_group_tasks(session, project_a.id)
    assert [gt.serial_num for gt in listed_a] == [0, 1]

    # blank/whitespace title or description rejected
    with pytest.raises(ProjectValidationError) as exc_info:
        create_group_task(session, project_a.id, title="   ", description="d")
    assert "title" in exc_info.value.errors

    with pytest.raises(ProjectValidationError) as exc_info:
        create_group_task(session, project_a.id, title="Valid", description="   ")
    assert "description" in exc_info.value.errors

    # length limits enforced
    with pytest.raises(ProjectValidationError) as exc_info:
        create_group_task(session, project_a.id, title="x" * 201, description="d")
    assert "title" in exc_info.value.errors

    with pytest.raises(ProjectValidationError) as exc_info:
        create_group_task(session, project_a.id, title="Valid title", description="x" * 2001)
    assert "description" in exc_info.value.errors

    # bad date ordering rejected
    with pytest.raises(ProjectValidationError) as exc_info:
        create_group_task(
            session,
            project_a.id,
            title="Dated",
            description="d",
            start_date=date(2026, 2, 1),
            finished_date=date(2026, 1, 1),
        )
    assert "finished_date" in exc_info.value.errors


def test_title_conflict_scoped_per_project_not_global(session: Session) -> None:
    project_a = create_project(session, title="Project A", description="d")
    project_b = create_project(session, title="Project B", description="d")

    create_group_task(session, project_a.id, title="Shared Title", description="d")

    # a Group-task with the same title under a *different* project succeeds
    other = create_group_task(session, project_b.id, title="Shared Title", description="d")
    assert other.title == "Shared Title"


def test_update_scoped_conflicts_and_status(session: Session) -> None:
    project_a = create_project(session, title="Project A", description="d")
    project_b = create_project(session, title="Project B", description="d")

    a_first = create_group_task(session, project_a.id, title="First", description="d")
    a_second = create_group_task(session, project_a.id, title="Second", description="d")
    b_first = create_group_task(session, project_b.id, title="First", description="d")

    # editing serial_num/title to a value used by another active Group-task in the
    # *same* project is rejected, and the original value is retained
    with pytest.raises(ProjectValidationError) as exc_info:
        update_group_task(
            session,
            project_a.id,
            a_second.id,
            serial_num=a_first.serial_num,
            title=a_second.title,
            description=a_second.description,
            status=Status.NEW,
        )
    assert "serial_num" in exc_info.value.errors

    with pytest.raises(ProjectValidationError) as exc_info:
        update_group_task(
            session,
            project_a.id,
            a_second.id,
            serial_num=a_second.serial_num,
            title=a_first.title,
            description=a_second.description,
            status=Status.NEW,
        )
    assert "title" in exc_info.value.errors

    unchanged = list_active_group_tasks(session, project_a.id)
    unchanged_second = next(gt for gt in unchanged if gt.id == a_second.id)
    assert unchanged_second.serial_num == a_second.serial_num
    assert unchanged_second.title == a_second.title

    # editing to its own current value is a no-op success
    result = update_group_task(
        session,
        project_a.id,
        a_second.id,
        serial_num=a_second.serial_num,
        title=a_second.title,
        description="updated description",
        status=Status.NEW,
    )
    assert result.serial_num == a_second.serial_num
    assert result.description == "updated description"

    # the identical serial_num/title succeeds when the conflicting Group-task is
    # under a *different* project
    updated_cross_project = update_group_task(
        session,
        project_b.id,
        b_first.id,
        serial_num=a_first.serial_num,
        title=a_first.title,
        description=b_first.description,
        status=Status.NEW,
    )
    assert updated_cross_project.serial_num == a_first.serial_num
    assert updated_cross_project.title == a_first.title

    # bad date ordering rejected on edit
    with pytest.raises(ProjectValidationError) as exc_info:
        update_group_task(
            session,
            project_a.id,
            a_second.id,
            serial_num=a_second.serial_num,
            title=a_second.title,
            description=a_second.description,
            start_date=date(2026, 2, 1),
            finished_date=date(2026, 1, 1),
            status=Status.NEW,
        )
    assert "finished_date" in exc_info.value.errors

    # any status -> any other status succeeds
    archived = update_group_task(
        session,
        project_a.id,
        a_second.id,
        serial_num=a_second.serial_num,
        title=a_second.title,
        description=a_second.description,
        status=Status.ARCHIVED,
    )
    assert archived.status == Status.ARCHIVED
    reverted = update_group_task(
        session,
        project_a.id,
        a_second.id,
        serial_num=a_second.serial_num,
        title=a_second.title,
        description=a_second.description,
        status=Status.NEW,
    )
    assert reverted.status == Status.NEW
