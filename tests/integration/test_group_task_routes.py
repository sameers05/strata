from fastapi.testclient import TestClient

from app.database import get_session
from app.services import soft_delete_group_task


def _create_project(client: TestClient, **fields):
    data = {"title": "Untitled Project", "description": "d", "status": "new", **fields}
    return client.post("/projects", data=data, follow_redirects=False)


def _create_group_task(client: TestClient, project_id: int, **fields):
    data = {"title": "Untitled Task", "description": "d", "status": "new", **fields}
    return client.post(
        f"/projects/{project_id}/group-tasks", data=data, follow_redirects=False
    )


def test_us1_create_and_nested_list_flow(client: TestClient) -> None:
    _create_project(client, title="Parent Project")
    project_id = 1

    r = _create_group_task(client, project_id, title="First Task", description="d1")
    assert r.status_code == 200
    assert r.headers.get("hx-redirect") == f"/projects/{project_id}"

    detail = client.get(f"/projects/{project_id}")
    assert detail.status_code == 200
    assert "First Task" in detail.text
    # serial_num 0 rendered somewhere in the nested list row
    assert 'id="group-task-row-1"' in detail.text

    # validation failure: 200 + OOB #form-errors fragment, form untouched (no redirect)
    r = _create_group_task(client, project_id, title="   ", description="d")
    assert r.status_code == 200
    assert "hx-redirect" not in r.headers
    assert 'id="form-errors"' in r.text
    assert "Title is required" in r.text

    # a duplicate title under a *different* Project succeeds
    _create_project(client, title="Other Project")
    other_project_id = 2
    r = _create_group_task(client, other_project_id, title="First Task", description="d2")
    assert r.status_code == 200
    assert r.headers.get("hx-redirect") == f"/projects/{other_project_id}"


def test_group_task_routes_404_when_parent_project_missing(client: TestClient) -> None:
    r = client.get("/projects/999/group-tasks/new")
    assert r.status_code == 404

    r = _create_group_task(client, 999, title="Task", description="d")
    assert r.status_code == 404


def test_group_task_routes_404_when_parent_project_soft_deleted(client: TestClient) -> None:
    _create_project(client, title="Soon Deleted")
    project_id = 1
    client.delete(f"/projects/{project_id}")

    r = client.get(f"/projects/{project_id}/group-tasks/new")
    assert r.status_code == 404

    r = _create_group_task(client, project_id, title="Task", description="d")
    assert r.status_code == 404


def test_us3_detail_view(client: TestClient) -> None:
    _create_project(client, title="Detail Project")
    project_id = 1
    _create_group_task(
        client,
        project_id,
        title="Detail Task",
        description="A full description",
        notes="Some notes",
        start_date="2026-01-01",
        finished_date="2026-02-01",
    )
    group_task_id = 1

    r = client.get(f"/projects/{project_id}/group-tasks/{group_task_id}")
    assert r.status_code == 200
    assert "Detail Task" in r.text
    assert "A full description" in r.text
    assert "Some notes" in r.text
    assert "2026-01-01" in r.text
    assert "2026-02-01" in r.text
    assert f"/projects/{project_id}" in r.text  # link back to the parent Project
    assert 'id="page-errors"' in r.text

    # 404 when the Group-task is missing
    r = client.get(f"/projects/{project_id}/group-tasks/999")
    assert r.status_code == 404

    # 404 when the Group-task is soft-deleted
    session = next(client.app.dependency_overrides[get_session]())
    soft_delete_group_task(session, project_id, group_task_id)

    r = client.get(f"/projects/{project_id}/group-tasks/{group_task_id}")
    assert r.status_code == 404


def test_us4_edit_flow(client: TestClient) -> None:
    _create_project(client, title="Edit Project")
    project_id = 1
    _create_group_task(client, project_id, title="Original Title", description="d")
    group_task_id = 1

    # GET edit form is pre-filled
    r = client.get(f"/projects/{project_id}/group-tasks/{group_task_id}/edit")
    assert r.status_code == 200
    assert "Original Title" in r.text

    # PUT success redirects to the parent Project
    r = client.put(
        f"/projects/{project_id}/group-tasks/{group_task_id}",
        data={
            "serial_num": 0,
            "title": "Updated Title",
            "description": "updated",
            "status": "in-progress",
        },
        follow_redirects=False,
    )
    assert r.status_code == 200
    assert r.headers.get("hx-redirect") == f"/projects/{project_id}"

    detail = client.get(f"/projects/{project_id}/group-tasks/{group_task_id}")
    assert "Updated Title" in detail.text
    assert "in-progress" in detail.text

    # PUT validation failure returns the OOB #form-errors fragment
    r = client.put(
        f"/projects/{project_id}/group-tasks/{group_task_id}",
        data={
            "serial_num": 0,
            "title": "   ",
            "description": "updated",
            "status": "new",
        },
    )
    assert r.status_code == 200
    assert "hx-redirect" not in r.headers
    assert 'id="form-errors"' in r.text
    assert "Title is required" in r.text


def test_us5_soft_delete_flow(client: TestClient) -> None:
    _create_project(client, title="Delete Project")
    project_id = 1
    _create_group_task(client, project_id, title="Doomed Task", description="d")
    group_task_id = 1

    detail = client.get(f"/projects/{project_id}/group-tasks/{group_task_id}")
    assert "hx-confirm" in detail.text
    assert f'hx-delete="/projects/{project_id}/group-tasks/{group_task_id}"' in detail.text

    r = client.delete(f"/projects/{project_id}/group-tasks/{group_task_id}")
    assert r.status_code == 200
    assert r.headers.get("hx-redirect") == f"/projects/{project_id}"

    # no longer appears in the nested list, and the nested list itself carries no
    # hx-delete for any group-task (the Project's own delete control is unrelated
    # and legitimately still present on this page)
    project_detail = client.get(f"/projects/{project_id}")
    assert "Doomed Task" not in project_detail.text
    assert f'hx-delete="/projects/{project_id}/group-tasks/' not in project_detail.text

    r = client.get(f"/projects/{project_id}/group-tasks/{group_task_id}")
    assert r.status_code == 404
