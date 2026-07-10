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


def test_deleted_view_both_sections(client: TestClient) -> None:
    _create_project(client, title="Project Alpha")  # serial_num 0
    _create_project(client, title="Project Beta")  # serial_num 1
    alpha_id, beta_id = _row_ids(client.get("/panes/projects").text)

    _create_group_task(client, alpha_id, title="Alpha Task One")  # serial_num 0
    _create_group_task(client, alpha_id, title="Alpha Task Two")  # serial_num 1
    _create_group_task(client, beta_id, title="Beta Task One")  # serial_num 0

    alpha_task_one_id, alpha_task_two_id = re.findall(
        r'id="group-task-row-(\d+)"', client.get(f"/panes/projects/{alpha_id}/group-tasks").text
    )
    beta_task_one_id = re.findall(
        r'id="group-task-row-(\d+)"', client.get(f"/panes/projects/{beta_id}/group-tasks").text
    )[0]

    # soft-delete both of Alpha's Group-tasks, then Alpha itself (now unblocked)
    client.request("DELETE", f"/panes/projects/{alpha_id}/group-tasks/{alpha_task_one_id}")
    client.request("DELETE", f"/panes/projects/{alpha_id}/group-tasks/{alpha_task_two_id}")
    r = client.request("DELETE", f"/panes/projects/{alpha_id}")
    assert r.status_code == 200
    assert f'id="project-row-{alpha_id}" hx-swap-oob="delete"' in r.text

    # soft-delete Beta's one Group-task, but Beta itself stays active
    client.request("DELETE", f"/panes/projects/{beta_id}/group-tasks/{beta_task_one_id}")

    r = client.get("/panes/deleted")
    assert r.status_code == 200
    # bundled OOB empty #details-pane fragment (Deleted Items shows no selectable content)
    assert 'id="details-pane" hx-swap-oob="true"' in r.text
    assert "data-entity-type" not in r.text

    # "Deleted Projects" section: unchanged 001/002 behavior — only Alpha is here,
    # since Beta itself was never soft-deleted
    assert "Project Alpha" in r.text
    assert f'id="project-row-{beta_id}"' not in r.text

    # "Deleted Group-tasks" section: grouped by parent ascending by the parent's own
    # serial_num (Alpha=0 before Beta=1), Group-tasks within each group ascending by
    # their own serial_num
    alpha_task_one_pos = r.text.index("Alpha Task One")
    alpha_task_two_pos = r.text.index("Alpha Task Two")
    beta_task_one_pos = r.text.index("Beta Task One")
    assert alpha_task_one_pos < alpha_task_two_pos < beta_task_one_pos

    # a Group-task's parent is still correctly identified even after that parent
    # Project was also later soft-deleted (Alpha, here) — its title still renders
    # as the group header for its Group-tasks section
    assert r.text.index("Project Alpha") < alpha_task_one_pos


def test_deleted_view_empty_state(client: TestClient) -> None:
    r = client.get("/panes/deleted")
    assert r.status_code == 200
    assert "No deleted projects" in r.text
    assert "No deleted group-tasks" in r.text


def test_old_deleted_url_no_longer_resolves(client: TestClient) -> None:
    _create_project(client, title="Some Project")
    project_id = _row_ids(client.get("/panes/projects").text)[0]
    client.request("DELETE", f"/panes/projects/{project_id}")

    r = client.get("/deleted")
    assert r.status_code == 404
