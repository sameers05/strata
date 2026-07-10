import re

from fastapi.testclient import TestClient


def _create_project(client: TestClient, **fields):
    data = {"title": "Untitled Project", "description": "d", "status": "new", **fields}
    return client.post("/panes/projects", data=data)


def _create_group_task(client: TestClient, project_id: int, **fields):
    data = {"title": "Untitled Task", "description": "d", "status": "new", **fields}
    return client.post(f"/panes/projects/{project_id}/group-tasks", data=data)


def _row_ids(html: str) -> list[str]:
    return re.findall(r'id="project-row-(\d+)"', html)


def test_us1_drill_and_select(client: TestClient) -> None:
    _create_project(client, title="Parent Project")
    project_id = _row_ids(client.get("/panes/projects").text)[0]

    _create_group_task(client, project_id, title="First Task", description="d1")

    r = client.get(f"/panes/projects/{project_id}/group-tasks")
    assert r.status_code == 200
    assert "Parent Project" in r.text  # breadcrumb ancestor
    assert "First Task" in r.text
    assert 'id="details-pane" hx-swap-oob="true"' in r.text
    assert 'data-entity-type="group_task"' in r.text
    assert 'hx-get="/panes/deleted"' in r.text

    group_task_id = re.findall(r'id="group-task-row-(\d+)"', r.text)[0]

    r = client.get(f"/panes/projects/{project_id}/group-tasks/{group_task_id}")
    assert r.status_code == 200
    assert f'data-entity-type="group_task" data-entity-id="{group_task_id}"' in r.text
    assert "First Task" in r.text

    # 404 when the parent Project is missing/soft-deleted, independent of the
    # Group-task's own state (003's FR-015a, preserved)
    r = client.get(f"/panes/projects/999/group-tasks/{group_task_id}")
    assert r.status_code == 404
    r = client.get("/panes/projects/999/group-tasks")
    assert r.status_code == 404


def test_us2_create_group_task_flow(client: TestClient) -> None:
    _create_project(client, title="Parent Project")
    project_id = _row_ids(client.get("/panes/projects").text)[0]

    # blank create form
    r = client.get(f"/panes/projects/{project_id}/group-tasks/new")
    assert r.status_code == 200
    assert f'hx-post="/panes/projects/{project_id}/group-tasks"' in r.text
    assert "data-entity-type" not in r.text

    # success: the OOB fragment fully re-renders <tbody id="group-task-list-body">
    # (hx-swap-oob="true", default outerHTML, tag-preserving) rather than a
    # selector-targeted beforeend/innerHTML append, which strips the OOB element's
    # own wrapper tag (htmx docs) and would leave orphaned <td>s with no <tr>
    r = _create_group_task(client, project_id, title="Created Task", description="cd")
    assert r.status_code == 200
    assert 'data-entity-type="group_task"' in r.text
    assert "Created Task" in r.text
    assert 'id="group-task-list-body" hx-swap-oob="true"' in r.text
    assert "beforeend" not in r.text
    assert ":#group-task-list-body" not in r.text
    assert ">0<" in r.text

    # success into an already-populated list: the full tbody re-render still
    # includes both the pre-existing and the newly created row
    r = _create_group_task(client, project_id, title="Second Created Task", description="cd2")
    assert r.status_code == 200
    assert 'id="group-task-list-body" hx-swap-oob="true"' in r.text
    assert "Created Task" in r.text
    assert "Second Created Task" in r.text
    # the tbody's own oob flag must not leak into each row's own hx-swap-oob
    assert re.findall(r'hx-swap-oob="[^"]*"', r.text).count('hx-swap-oob="true"') == 1
    assert "hx-swap-oob=\"True\"" not in r.text

    # duplicate title: OOB #form-errors, entered values retained, no navigation
    r = _create_group_task(client, project_id, title="Created Task", description="dup")
    assert r.status_code == 200
    assert 'id="form-errors" hx-swap-oob="true"' in r.text
    assert "already in use" in r.text
    assert 'value="Created Task"' in r.text
    assert "data-entity-type" not in r.text

    # 404 on both the blank-form GET and the POST when project_id is missing/soft-deleted
    r = client.get("/panes/projects/999/group-tasks/new")
    assert r.status_code == 404
    r = _create_group_task(client, 999, title="Task", description="d")
    assert r.status_code == 404


def test_us3_edit_group_task_flow(client: TestClient) -> None:
    _create_project(client, title="Parent Project")
    project_id = _row_ids(client.get("/panes/projects").text)[0]
    _create_group_task(client, project_id, title="Edit Target", description="d")
    _create_group_task(client, project_id, title="Other Task", description="d")

    r = client.get(f"/panes/projects/{project_id}/group-tasks")
    edit_id, other_id = re.findall(r'id="group-task-row-(\d+)"', r.text)

    # success: updated details fragment + OOB row replacement
    r = client.put(
        f"/panes/projects/{project_id}/group-tasks/{edit_id}",
        data={"serial_num": 0, "title": "Edit Target", "description": "d", "status": "in-progress"},
    )
    assert r.status_code == 200
    assert f'data-entity-type="group_task" data-entity-id="{edit_id}"' in r.text
    assert f'id="group-task-row-{edit_id}" hx-swap-oob="true"' in r.text
    assert "in-progress" in r.text

    # serial_num conflict: OOB #form-errors, retained values, no row-replace fragment
    r = client.put(
        f"/panes/projects/{project_id}/group-tasks/{other_id}",
        data={"serial_num": 0, "title": "Other Task", "description": "d", "status": "new"},
    )
    assert r.status_code == 200
    assert "already in use" in r.text
    assert f'id="group-task-row-{other_id}" hx-swap-oob="true"' not in r.text

    # 404: missing project_id (checked first, independent of Group-task's own state)
    r = client.put(
        f"/panes/projects/999/group-tasks/{edit_id}",
        data={"serial_num": 0, "title": "Ghost", "description": "d", "status": "new"},
    )
    assert r.status_code == 404

    # 404: missing group_task_id
    r = client.put(
        f"/panes/projects/{project_id}/group-tasks/999",
        data={"serial_num": 0, "title": "Ghost", "description": "d", "status": "new"},
    )
    assert r.status_code == 404


def test_us4_delete_flow(client: TestClient) -> None:
    _create_project(client, title="Parent Project")
    project_id = _row_ids(client.get("/panes/projects").text)[0]
    _create_group_task(client, project_id, title="Task One", description="d")
    _create_group_task(client, project_id, title="Task Two", description="d")

    r = client.get(f"/panes/projects/{project_id}/group-tasks")
    one_id, two_id = re.findall(r'id="group-task-row-(\d+)"', r.text)

    # every Group-task row's delete control is unconditionally enabled (no `disabled`)
    assert f'hx-delete="/panes/projects/{project_id}/group-tasks/{one_id}"' in r.text
    row_one = r.text.split(f'id="group-task-row-{one_id}"')[1].split("</tr>")[0]
    assert "disabled" not in row_one

    # deleting an unrelated row leaves #details-pane untouched
    r = client.request(
        "DELETE",
        f"/panes/projects/{project_id}/group-tasks/{two_id}",
        params={"selected_type": "group_task", "selected_id": one_id},
    )
    assert r.status_code == 200
    assert f'id="group-task-row-{two_id}" hx-swap-oob="delete"' in r.text
    assert 'id="details-pane" hx-swap-oob="true"' not in r.text
    assert "Task Two" not in client.get(f"/panes/projects/{project_id}/group-tasks").text

    # re-add a second Group-task so a "next remaining" target exists
    _create_group_task(client, project_id, title="Task Three", description="d")
    three_id = re.findall(
        r'id="group-task-row-(\d+)"', client.get(f"/panes/projects/{project_id}/group-tasks").text
    )[1]

    # deleting the currently-selected Group-task auto-selects the next remaining one
    r = client.request(
        "DELETE",
        f"/panes/projects/{project_id}/group-tasks/{one_id}",
        params={"selected_type": "group_task", "selected_id": one_id},
    )
    assert r.status_code == 200
    assert f'id="group-task-row-{one_id}" hx-swap-oob="delete"' in r.text
    assert 'id="details-pane" hx-swap-oob="true"' in r.text
    assert f'data-entity-type="group_task" data-entity-id="{three_id}"' in r.text

    # deleting the last remaining selected Group-task falls back to the create-prompt
    r = client.request(
        "DELETE",
        f"/panes/projects/{project_id}/group-tasks/{three_id}",
        params={"selected_type": "group_task", "selected_id": three_id},
    )
    assert r.status_code == 200
    assert "No group-tasks yet" in r.text
    assert "data-entity-type" not in r.text

    # 404: missing project_id, missing group_task_id
    r = client.request("DELETE", f"/panes/projects/999/group-tasks/{three_id}")
    assert r.status_code == 404
    r = client.request("DELETE", f"/panes/projects/{project_id}/group-tasks/999")
    assert r.status_code == 404
