"""
Integration tests for GET /api/files/ and related endpoints.
"""

from tests.conftest import make_file, make_group


class TestListFiles:
    def test_empty_returns_empty_list(self, client):
        resp = client.get("/api/files/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_returns_inserted_file(self, client, db_session):
        make_file(db_session, name="readme.txt", full_path="/tmp/readme.txt")
        resp = client.get("/api/files/")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1
        assert resp.json()["items"][0]["name"] == "readme.txt"

    def test_filter_by_category(self, client, db_session):
        make_file(db_session, name="a.mp3", full_path="/tmp/a.mp3", category="Music")
        make_file(db_session, name="b.txt", full_path="/tmp/b.txt", category="Documents")
        resp = client.get("/api/files/?category=Music")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["name"] == "a.mp3"

    def test_filter_by_extension(self, client, db_session):
        make_file(db_session, name="x.pdf", full_path="/tmp/x.pdf", extension=".pdf")
        make_file(db_session, name="y.txt", full_path="/tmp/y.txt", extension=".txt")
        resp = client.get("/api/files/?extension=pdf")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1
        assert resp.json()["items"][0]["extension"] == ".pdf"

    def test_search_by_name(self, client, db_session):
        make_file(db_session, name="report_2026.docx", full_path="/tmp/report_2026.docx")
        make_file(db_session, name="photo.jpg", full_path="/tmp/photo.jpg")
        resp = client.get("/api/files/?search=report")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1
        assert "report" in resp.json()["items"][0]["name"]

    def test_pagination_limit(self, client, db_session):
        for i in range(5):
            make_file(db_session, name=f"file{i}.txt", full_path=f"/tmp/file{i}.txt")
        resp = client.get("/api/files/?limit=2&offset=0")
        assert resp.status_code == 200
        assert len(resp.json()["items"]) == 2
        assert resp.json()["total"] == 5

    def test_filter_by_group_id_zero_returns_ungrouped(self, client, db_session):
        make_file(db_session, name="ungrouped.txt", full_path="/tmp/ungrouped.txt", group_id=None)
        grp = make_group(db_session)
        make_file(db_session, name="grouped.txt", full_path="/tmp/grouped.txt", group_id=grp.id)
        resp = client.get("/api/files/?group_id=0")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1
        assert resp.json()["items"][0]["name"] == "ungrouped.txt"


class TestGetFile:
    def test_get_existing_file(self, client, db_session):
        rec = make_file(db_session)
        resp = client.get(f"/api/files/{rec.id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == rec.id

    def test_get_nonexistent_returns_404(self, client):
        resp = client.get("/api/files/99999")
        assert resp.status_code == 404


class TestUpdateFile:
    def test_update_category(self, client, db_session):
        rec = make_file(db_session)
        resp = client.patch(f"/api/files/{rec.id}", json={"category": "Music"})
        assert resp.status_code == 200
        assert resp.json()["category"] == "Music"
        assert resp.json()["category_overridden"] is True

    def test_update_tags(self, client, db_session):
        rec = make_file(db_session)
        resp = client.patch(f"/api/files/{rec.id}", json={"tags": "important,work"})
        assert resp.status_code == 200
        assert resp.json()["tags"] == "important,work"

    def test_update_nonexistent_returns_404(self, client):
        resp = client.patch("/api/files/99999", json={"category": "Music"})
        assert resp.status_code == 404


class TestFileStats:
    def test_stats_empty(self, client):
        resp = client.get("/api/files/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_files" in data
        assert data["total_files"] == 0

    def test_stats_counts_categories(self, client, db_session):
        make_file(db_session, name="a.mp3", full_path="/tmp/a.mp3", category="Music")
        make_file(db_session, name="b.mp3", full_path="/tmp/b.mp3", category="Music")
        make_file(db_session, name="c.txt", full_path="/tmp/c.txt", category="Documents")
        resp = client.get("/api/files/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_files"] == 3
        by_cat = {c["category"]: c["count"] for c in data["by_category"]}
        assert by_cat["Music"] == 2
        assert by_cat["Documents"] == 1
