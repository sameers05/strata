import re

from fastapi.testclient import TestClient


def _create(client: TestClient, **fields):
    data = {"title": "Untitled", "description": "d", "status": "new", **fields}
    return client.post("/projects", data=data, follow_redirects=False)


def _row_ids(html: str) -> list[str]:
    """Numeric project ids linked from table rows, in document order."""
    return re.findall(r'href="/projects/(\d+)"', html)


def test_us1_create_and_list_flow(client: TestClient) -> None:
    r = _create(client, title="First Project", description="d1")
    assert r.status_code == 200
    assert r.headers.get("hx-redirect") == "/projects"

    r = _create(client, title="Second Project", description="d2")
    assert r.status_code == 200
    assert r.headers.get("hx-redirect") == "/projects"

    r = client.get("/projects")
    assert r.status_code == 200
    assert "First Project" in r.text
    assert "Second Project" in r.text
    first_pos = r.text.index("First Project")
    second_pos = r.text.index("Second Project")
    assert first_pos < second_pos  # serial_num 0 then 1, ascending

    # duplicate title: 200, OOB fragment, no redirect
    r = _create(client, title="First Project", description="dup")
    assert r.status_code == 200
    assert "hx-redirect" not in r.headers
    assert 'id="form-errors"' in r.text
    assert "hx-swap-oob" in r.text
    assert "already in use" in r.text

    # blank required field: same in-place rejection
    r = _create(client, title="   ", description="d")
    assert r.status_code == 200
    assert "hx-redirect" not in r.headers
    assert "Title is required" in r.text


def test_us2_view_detail_flow(client: TestClient) -> None:
    _create(client, title="Detail Project", description="A description")

    project_id = _row_ids(client.get("/projects").text)[0]

    r = client.get(f"/projects/{project_id}")
    assert r.status_code == 200
    assert "Detail Project" in r.text
    assert "A description" in r.text
    # blank optionals (start_date, finished_date, notes) rendered as empty, not an error
    assert r.status_code != 500


def test_us3_edit_flow(client: TestClient) -> None:
    _create(client, title="Edit Target", description="d")
    _create(client, title="Other Project", description="d")

    edit_id, other_id = _row_ids(client.get("/projects").text)

    # status new -> archived directly, no intermediate step, redirects
    r = client.put(
        f"/projects/{edit_id}",
        data={"serial_num": 0, "title": "Edit Target", "description": "d", "status": "archived"},
        follow_redirects=False,
    )
    assert r.status_code == 200
    assert r.headers.get("hx-redirect") == "/projects"

    detail = client.get(f"/projects/{edit_id}").text
    assert "archived" in detail

    # serial_num conflict: 200 + OOB fragment, original value unchanged
    r = client.put(
        f"/projects/{other_id}",
        data={"serial_num": 0, "title": "Other Project", "description": "d", "status": "new"},
    )
    assert r.status_code == 200
    assert "hx-redirect" not in r.headers
    assert "already in use" in r.text

    active_list = client.get("/projects").text
    assert ">1<" in active_list  # other_id's serial_num (1) is unchanged

    # finished_date before start_date rejected the same way
    r = client.put(
        f"/projects/{edit_id}",
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
    assert "hx-redirect" not in r.headers
    assert "earlier" in r.text

    # notes edit persists across a subsequent GET
    r = client.put(
        f"/projects/{edit_id}",
        data={
            "serial_num": 0,
            "title": "Edit Target",
            "description": "d",
            "notes": "a persisted note",
            "status": "archived",
        },
        follow_redirects=False,
    )
    assert r.status_code == 200
    assert r.headers.get("hx-redirect") == "/projects"

    detail = client.get(f"/projects/{edit_id}").text
    assert "a persisted note" in detail

    # renaming an active project to a soft-deleted project's former title succeeds
    client.delete(f"/projects/{other_id}")
    r = client.put(
        f"/projects/{edit_id}",
        data={"serial_num": 0, "title": "Other Project", "description": "d", "status": "archived"},
        follow_redirects=False,
    )
    assert r.status_code == 200
    assert r.headers.get("hx-redirect") == "/projects"


def test_us4_soft_delete_and_deleted_items_flow(client: TestClient) -> None:
    _create(client, title="To Delete", description="d")
    _create(client, title="Keep Me", description="d")

    delete_id, keep_id = _row_ids(client.get("/projects").text)

    r = client.delete(f"/projects/{delete_id}")
    assert r.status_code == 200

    r = client.get("/projects")
    assert "To Delete" not in r.text
    assert "Keep Me" in r.text

    r = client.get(f"/projects/{delete_id}")
    assert r.status_code == 404

    r = client.get("/projects/deleted")
    assert r.status_code == 200
    assert "To Delete" in r.text
    assert ">0<" in r.text  # serial_num frozen at its last active value

    # a second soft-delete; deleted items ascending by serial_num
    client.delete(f"/projects/{keep_id}")

    deleted_page = client.get("/projects/deleted").text
    first_pos = deleted_page.index("To Delete")
    second_pos = deleted_page.index("Keep Me")
    assert first_pos < second_pos

    # no edit/restore route reachable for a deleted item
    assert "hx-delete" not in deleted_page
    assert f"/projects/{delete_id}/edit" not in deleted_page
    r = client.get(f"/projects/{delete_id}/edit")
    assert r.status_code == 404


def test_quickstart_manual_scenarios_end_to_end(client: TestClient) -> None:
    r = client.get("/projects")
    assert r.status_code == 200
    assert "No projects yet" in r.text

    r = _create(client, title="Website Redesign", description="Redesign the marketing site")
    assert r.headers.get("hx-redirect") == "/projects"
    r = _create(client, title="Second Project", description="d")
    assert r.headers.get("hx-redirect") == "/projects"

    list_page = client.get("/projects").text
    assert ">0<" in list_page and ">1<" in list_page

    r = _create(client, title="Website Redesign", description="dup")
    assert "hx-redirect" not in r.headers
    assert "already in use" in r.text

    r = _create(client, title="", description="")
    assert "hx-redirect" not in r.headers

    project_id, other_id = _row_ids(list_page)

    detail = client.get(f"/projects/{project_id}").text
    assert "Website Redesign" in detail

    r = client.put(
        f"/projects/{project_id}",
        data={"serial_num": 0, "title": "Website Redesign", "description": "d", "status": "archived"},
        follow_redirects=False,
    )
    assert r.headers.get("hx-redirect") == "/projects"

    r = client.put(
        f"/projects/{other_id}",
        data={"serial_num": 0, "title": "Second Project", "description": "d", "status": "new"},
    )
    assert "already in use" in r.text
    assert ">1<" in client.get("/projects").text

    r = client.put(
        f"/projects/{project_id}",
        data={
            "serial_num": 0,
            "title": "Website Redesign",
            "description": "d",
            "start_date": "2026-02-01",
            "finished_date": "2026-01-01",
            "status": "archived",
        },
    )
    assert "earlier" in r.text

    r = client.put(
        f"/projects/{project_id}",
        data={
            "serial_num": 0,
            "title": "Website Redesign",
            "description": "d",
            "notes": "multi\nparagraph\nnote",
            "status": "archived",
        },
        follow_redirects=False,
    )
    assert r.headers.get("hx-redirect") == "/projects"
    assert "multi" in client.get(f"/projects/{project_id}").text

    client.delete(f"/projects/{project_id}")
    r = _create(client, title="Website Redesign", description="reused title after soft-delete")
    assert r.headers.get("hx-redirect") == "/projects"

    r = client.get(f"/projects/{project_id}")
    assert r.status_code == 404

    deleted_page = client.get("/projects/deleted").text
    assert "Website Redesign" in deleted_page
    assert "hx-delete" not in deleted_page
