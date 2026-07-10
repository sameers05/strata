import re

from fastapi.testclient import TestClient


def _create(client: TestClient, **fields):
    data = {"title": "Untitled", "description": "d", "status": "new", **fields}
    return client.post("/panes/projects", data=data)


def _row_ids(html: str) -> list[str]:
    """Numeric project ids of rows present in the given fragment, in document order."""
    return re.findall(r'id="project-row-(\d+)"', html)


def test_us1_home_and_list_and_select(client: TestClient) -> None:
    # empty DB: home shows the create-prompt, not a Project's details
    r = client.get("/")
    assert r.status_code == 200
    assert "No projects yet" in r.text
    assert "Create your first project" in r.text

    _create(client, title="First Project", description="d1")
    _create(client, title="Second Project", description="d2")

    # home now embeds the first active Project's details directly (no OOB, initial render)
    r = client.get("/")
    assert r.status_code == 200
    assert "First Project" in r.text
    assert 'data-entity-type="project"' in r.text

    project_id = _row_ids(r.text)[0]

    # list fragment + OOB details default in one response
    r = client.get("/panes/projects")
    assert r.status_code == 200
    assert "First Project" in r.text
    assert "Second Project" in r.text
    assert 'id="details-pane" hx-swap-oob="true"' in r.text
    assert 'data-entity-type="project"' in r.text
    assert 'hx-get="/panes/deleted"' in r.text

    # direct select: populated fragment, correctly self-describing
    r = client.get(f"/panes/projects/{project_id}")
    assert r.status_code == 200
    assert f'data-entity-type="project" data-entity-id="{project_id}"' in r.text
    assert "First Project" in r.text

    # 404 on missing / soft-deleted
    r = client.get("/panes/projects/999")
    assert r.status_code == 404


def test_us2_create_project_flow(client: TestClient) -> None:
    # blank create form
    r = client.get("/panes/projects/new")
    assert r.status_code == 200
    assert 'hx-post="/panes/projects"' in r.text
    assert "data-entity-type" not in r.text

    # success: the OOB fragment fully re-renders <tbody id="project-list-body">
    # (hx-swap-oob="true", default outerHTML, tag-preserving) rather than a
    # selector-targeted beforeend/innerHTML append, which strips the OOB element's
    # own wrapper tag (htmx docs) and would leave orphaned <td>s with no <tr>
    r = _create(client, title="Created Project", description="cd")
    assert r.status_code == 200
    assert 'data-entity-type="project"' in r.text
    assert "Created Project" in r.text
    assert 'id="project-list-body" hx-swap-oob="true"' in r.text
    assert "beforeend" not in r.text
    assert ":#project-list-body" not in r.text  # no selector-targeted OOB syntax at all
    assert ">0<" in r.text  # first project's auto-assigned serial_num

    # success into an already-populated list: the full tbody re-render still
    # includes both the pre-existing and the newly created row
    r = _create(client, title="Second Created Project", description="cd2")
    assert r.status_code == 200
    assert 'id="project-list-body" hx-swap-oob="true"' in r.text
    assert "Created Project" in r.text
    assert "Second Created Project" in r.text
    # the tbody's own oob flag must not leak into each row's own hx-swap-oob
    # (a prior bug: rows rendered inside the tbody re-render each picked up
    # hx-swap-oob="True" from the shared Jinja include context)
    assert re.findall(r'hx-swap-oob="[^"]*"', r.text).count('hx-swap-oob="true"') == 1
    assert "hx-swap-oob=\"True\"" not in r.text

    # duplicate title: OOB #form-errors, entered values retained, no row added, no navigation
    r = _create(client, title="Created Project", description="dup")
    assert r.status_code == 200
    assert 'id="form-errors" hx-swap-oob="true"' in r.text
    assert "already in use" in r.text
    assert 'value="Created Project"' in r.text
    assert "hx-swap-oob=\"beforeend" not in r.text
    assert "data-entity-type" not in r.text

    # blank required field: same in-place rejection, values retained
    r = _create(client, title="Valid Title", description="   ")
    assert r.status_code == 200
    assert "Description is required" in r.text
    assert 'value="Valid Title"' in r.text


def test_us3_edit_project_flow(client: TestClient) -> None:
    _create(client, title="Edit Target", description="d")
    _create(client, title="Other Project", description="d")

    r = client.get("/panes/projects")
    edit_id, other_id = _row_ids(r.text)

    # success: updated details fragment + OOB row replacement, in one response
    r = client.put(
        f"/panes/projects/{edit_id}",
        data={"serial_num": 0, "title": "Edit Target", "description": "d", "status": "archived"},
    )
    assert r.status_code == 200
    assert 'data-entity-type="project" data-entity-id="' + edit_id + '"' in r.text
    assert f'id="project-row-{edit_id}" hx-swap-oob="true"' in r.text
    assert "archived" in r.text

    r = client.get(f"/panes/projects/{edit_id}")
    assert "archived" in r.text

    # serial_num conflict: OOB #form-errors, retained values, no row-replace fragment
    r = client.put(
        f"/panes/projects/{other_id}",
        data={"serial_num": 0, "title": "Other Project", "description": "d", "status": "new"},
    )
    assert r.status_code == 200
    assert "already in use" in r.text
    assert f'id="project-row-{other_id}" hx-swap-oob="true"' not in r.text
    assert 'data-entity-type="project" data-entity-id="' + other_id + '"' in r.text

    # finished_date before start_date rejected the same way
    r = client.put(
        f"/panes/projects/{edit_id}",
        data={
            "serial_num": 0,
            "title": "Edit Target",
            "description": "d",
            "start_date": "2026-02-01",
            "finished_date": "2026-01-01",
            "status": "archived",
        },
    )
    assert r.status_code == 200
    assert "earlier" in r.text

    # 404 on missing/soft-deleted
    r = client.put(
        "/panes/projects/999",
        data={"serial_num": 0, "title": "Ghost", "description": "d", "status": "new"},
    )
    assert r.status_code == 404


def test_us4_delete_flow(client: TestClient) -> None:
    _create(client, title="Guarded Project", description="d")
    _create(client, title="Free Project", description="d")
    _create(client, title="Third Project", description="d")
    guarded_id, free_id, third_id = _row_ids(client.get("/panes/projects").text)

    client.post(
        f"/panes/projects/{guarded_id}/group-tasks",
        data={"title": "Blocking Task", "description": "d", "status": "new"},
    )

    # delete control disabled when active Group-tasks exist, enabled otherwise
    r = client.get("/panes/projects")
    rows = {
        pid: r.text.split(f'id="project-row-{pid}"')[1].split("</tr>")[0]
        for pid in (guarded_id, free_id, third_id)
    }
    assert f'hx-delete="/panes/projects/{guarded_id}"' in r.text
    assert "disabled" in rows[guarded_id]
    assert "disabled" not in rows[free_id]
    assert "disabled" not in rows[third_id]

    # cascade-block rejection: 200, OOB #delete-errors populated, no row-removal fragment, row survives
    r = client.request(
        "DELETE",
        f"/panes/projects/{guarded_id}",
        params={"selected_type": "", "selected_id": ""},
    )
    assert r.status_code == 200
    assert 'id="delete-errors" hx-swap-oob="true"' in r.text
    assert "active group-tasks" in r.text
    assert f'id="project-row-{guarded_id}" hx-swap-oob="delete"' not in r.text
    assert "Guarded Project" in client.get("/panes/projects").text

    # deleting an unrelated row (not the one shown in #details-pane) leaves #details-pane untouched
    r = client.request(
        "DELETE",
        f"/panes/projects/{free_id}",
        params={"selected_type": "project", "selected_id": guarded_id},
    )
    assert r.status_code == 200
    assert f'id="project-row-{free_id}" hx-swap-oob="delete"' in r.text
    assert 'id="details-pane" hx-swap-oob="true"' not in r.text
    assert "Free Project" not in client.get("/panes/projects").text

    # deleting the currently-selected Project auto-selects the next remaining active one
    r = client.request(
        "DELETE",
        f"/panes/projects/{third_id}",
        params={"selected_type": "project", "selected_id": third_id},
    )
    assert r.status_code == 200
    assert f'id="project-row-{third_id}" hx-swap-oob="delete"' in r.text
    assert 'id="details-pane" hx-swap-oob="true"' in r.text
    assert 'data-entity-type="project"' in r.text
    assert "Guarded Project" in r.text  # only remaining active Project left

    # unblock and remove the last remaining (selected) Project -> falls back to the create-prompt
    group_task_id = re.findall(
        r'id="group-task-row-(\d+)"', client.get(f"/panes/projects/{guarded_id}/group-tasks").text
    )[0]
    client.request("DELETE", f"/panes/projects/{guarded_id}/group-tasks/{group_task_id}")
    r = client.request(
        "DELETE",
        f"/panes/projects/{guarded_id}",
        params={"selected_type": "project", "selected_id": guarded_id},
    )
    assert r.status_code == 200
    assert "No projects yet" in r.text
    assert "data-entity-type" not in r.text

    # 404 on missing/soft-deleted
    r = client.request("DELETE", "/panes/projects/999")
    assert r.status_code == 404


def test_us5_shell_markup(client: TestClient) -> None:
    r = client.get("/")
    assert r.status_code == 200
    assert 'id="pane-divider"' in r.text
    assert "strata-split-pct" in r.text
    assert "splitPct" in r.text
    # live drag/resize/persistence behavior itself is manual-only (quickstart.md),
    # not driveable via httpx TestClient


def test_us7_nav_guard_markup(client: TestClient) -> None:
    _create(client, title="Nav Guard Project", description="d")
    project_id = _row_ids(client.get("/panes/projects").text)[0]

    r = client.get("/panes/projects")
    # every required nav control in the root list carries data-pane-nav
    assert re.search(r'<a hx-get="/panes/projects/\d+/group-tasks"[^>]*data-pane-nav', r.text)
    assert re.search(r'<a hx-get="/panes/projects/\d+" hx-target="#details-pane"[^>]*data-pane-nav', r.text)
    assert re.search(r'<a hx-get="/panes/projects/new"[^>]*data-pane-nav', r.text)
    assert re.search(r'<a hx-get="/panes/deleted"[^>]*data-pane-nav', r.text)
    # absent from the delete control
    delete_button = r.text[r.text.index("<button") : r.text.index("</button>") + len("</button>")]
    assert "data-pane-nav" not in delete_button

    # absent from the Save button (details-pane form)
    detail = client.get(f"/panes/projects/{project_id}").text
    save_button = detail[detail.index("<button") : detail.index("</button>") + len("</button>")]
    assert "data-pane-nav" not in save_button

    # breadcrumb "Projects" link, "+ New Group-task", and Deleted Items link all carry
    # it in a drilled view
    r = client.get(f"/panes/projects/{project_id}/group-tasks")
    assert re.search(r'<a hx-get="/panes/projects" hx-target="#left-pane"[^>]*data-pane-nav', r.text)
    assert re.search(r'<a hx-get="/panes/projects/\d+/group-tasks/new"[^>]*data-pane-nav', r.text)
    assert re.search(r'<a hx-get="/panes/deleted"[^>]*data-pane-nav', r.text)

    # Back control (Deleted Items view) carries it too
    r = client.get("/panes/deleted")
    assert "data-pane-nav" in r.text.split("</p>")[0]
