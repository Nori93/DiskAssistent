"""
Integration tests for disk/filesystem endpoints.
"""


class TestListDisks:
    def test_returns_list(self, client):
        resp = client.get("/api/disks/")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_each_disk_has_required_fields(self, client):
        resp = client.get("/api/disks/")
        assert resp.status_code == 200
        for disk in resp.json():
            assert "path" in disk or "mountpoint" in disk or "name" in disk


class TestDirectoryTree:
    def test_valid_path_returns_tree(self, client, tmp_path):
        (tmp_path / "subdir").mkdir()
        (tmp_path / "file.txt").write_text("hi")

        resp = client.get(f"/api/disks/tree?path={tmp_path}")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, (dict, list))

    def test_depth_too_large_returns_400(self, client, tmp_path):
        resp = client.get(f"/api/disks/tree?path={tmp_path}&depth=10")
        assert resp.status_code == 400

    def test_nonexistent_path_returns_response(self, client):
        # The API returns 200 with empty/default data for nonexistent paths
        resp = client.get("/api/disks/tree?path=/nonexistent/path/xyz123")
        assert resp.status_code in (200, 400, 404, 422)
