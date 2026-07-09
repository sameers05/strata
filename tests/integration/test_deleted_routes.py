from fastapi.testclient import TestClient


def _create_project(client: TestClient, **fields):
    data = {"title": "Untitled Project", "description": "d", "status": "new", **fields}
    return client.post("/projects", data=data, follow_redirects=False)


def _create_group_task(client: TestClient, project_id: int, **fields):
    data = {"title": "Untitled Task", "description": "d", "status": "new", **fields}
    return client.post(
        f"/projects/{project_id}/group-tasks", data=data, follow_redirects=False
    )


def test_deleted_view_both_sections(client: TestClient) -> None:
    _create_project(client, title="Project Alpha")  # id=1, serial_num 0
    _create_project(client, title="Project Beta")  # id=2, serial_num 1
    alpha_id, beta_id = 1, 2

    _create_group_task(client, alpha_id, title="Alpha Task One")  # id=1, serial_num 0
    _create_group_task(client, alpha_id, title="Alpha Task Two")  # id=2, serial_num 1
    _create_group_task(client, beta_id, title="Beta Task One")  # id=3, serial_num 0

    # soft-delete both of Alpha's Group-tasks, then Alpha itself (now unblocked)
    client.delete(f"/projects/{alpha_id}/group-tasks/1")
    client.delete(f"/projects/{alpha_id}/group-tasks/2")
    r = client.delete(f"/projects/{alpha_id}")
    assert r.headers.get("hx-redirect") == "/projects"

    # soft-delete Beta's one Group-task, but Beta itself stays active
    client.delete(f"/projects/{beta_id}/group-tasks/3")

    r = client.get("/deleted")
    assert r.status_code == 200

    # "Deleted Projects" section: unchanged 001/002 behavior — only Alpha is here,
    # since Beta itself was never soft-deleted
    assert "Project Alpha" in r.text
    assert 'id="project-row-2"' not in r.text

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
    r = client.get("/deleted")
    assert r.status_code == 200
    assert "No deleted projects" in r.text
    assert "No deleted group-tasks" in r.text


def test_old_projects_deleted_url_no_longer_resolves(client: TestClient) -> None:
    _create_project(client, title="Some Project")
    client.delete("/projects/1")

    r = client.get("/projects/deleted")
    assert r.status_code == 404
