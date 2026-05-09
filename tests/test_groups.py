"""
Integration tests for GET /api/groups/ and related endpoints.
"""

from tests.conftest import make_file, make_group


class TestListGroups:
    def test_empty_returns_result(self, client):
        resp = client.get("/api/groups/")
        assert resp.status_code == 200
        data = resp.json()
        # Response is {"groups": [...], "ungrouped_count": N}
        assert "ungrouped_count" in data
        assert isinstance(data["groups"], list)

    def test_returns_inserted_group(self, client, db_session):
        make_group(db_session, name="MyGame", category="Games")
        resp = client.get("/api/groups/")
        assert resp.status_code == 200
        names = [g["name"] for g in resp.json()["groups"]]
        assert "MyGame" in names

    def test_filter_by_category(self, client, db_session):
        make_group(db_session, name="GameGroup", category="Games")
        make_group(db_session, name="DocGroup", root_path="/tmp/DocGroup", category="Documents")
        resp = client.get("/api/groups/?category=Games")
        assert resp.status_code == 200
        cats = [g["category"] for g in resp.json()["groups"]]
        assert all(c == "Games" for c in cats)


class TestGetGroup:
    def test_get_existing_group(self, client, db_session):
        grp = make_group(db_session)
        resp = client.get(f"/api/groups/{grp.id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == grp.id
        assert "files" in resp.json()

    def test_get_nonexistent_returns_404(self, client):
        resp = client.get("/api/groups/99999")
        assert resp.status_code == 404

    def test_group_includes_its_files(self, client, db_session):
        grp = make_group(db_session)
        make_file(
            db_session,
            name="gamefile.exe",
            full_path=f"{grp.root_path}/gamefile.exe",
            group_id=grp.id,
        )
        resp = client.get(f"/api/groups/{grp.id}")
        assert resp.status_code == 200
        assert len(resp.json()["files"]) == 1
        assert resp.json()["files"][0]["name"] == "gamefile.exe"


class TestUpdateGroup:
    def test_update_category(self, client, db_session):
        grp = make_group(db_session, category="Other")
        resp = client.patch(f"/api/groups/{grp.id}", json={"category": "Games"})
        assert resp.status_code == 200
        assert resp.json()["category"] == "Games"

    def test_update_description(self, client, db_session):
        grp = make_group(db_session)
        resp = client.patch(f"/api/groups/{grp.id}", json={"description": "My favourite game"})
        assert resp.status_code == 200
        assert resp.json()["description"] == "My favourite game"

    def test_update_nonexistent_returns_404(self, client):
        resp = client.patch("/api/groups/99999", json={"category": "Games"})
        assert resp.status_code == 404
