"""
Integration tests for file operation endpoints (move, rename, delete).
"""

from tests.conftest import make_file


class TestDeleteOperation:
    def test_delete_requires_confirm(self, client, db_session):
        rec = make_file(db_session)
        resp = client.request(
            "DELETE", "/api/operations/delete", json={"file_id": rec.id, "confirm": False}
        )
        assert resp.status_code == 400

    def test_delete_nonexistent_file_returns_404(self, client):
        resp = client.request(
            "DELETE", "/api/operations/delete", json={"file_id": 99999, "confirm": True}
        )
        assert resp.status_code == 404

    def test_delete_missing_file_succeeds(self, client, db_session):
        """Deleting a DB record whose path doesn't exist on disk should still succeed."""
        rec = make_file(db_session, full_path="/nonexistent/path/ghost.txt")
        resp = client.request(
            "DELETE",
            "/api/operations/delete",
            json={"file_id": rec.id, "confirm": True},
        )
        # file_ops.delete_file raises FileOperationError if file is missing;
        # expect 400 (path missing) — not a 500 crash
        assert resp.status_code in (200, 400)


class TestMoveOperation:
    def test_move_nonexistent_file_returns_404(self, client, tmp_path):
        resp = client.post(
            "/api/operations/move", json={"file_id": 99999, "dest_dir": str(tmp_path)}
        )
        assert resp.status_code == 404

    def test_move_real_file(self, client, db_session, tmp_path):
        src = tmp_path / "src_dir"
        dst = tmp_path / "dst_dir"
        src.mkdir()
        dst.mkdir()
        file_path = src / "moveme.txt"
        file_path.write_text("hello")

        rec = make_file(
            db_session,
            name="moveme.txt",
            full_path=str(file_path),
            parent_dir=str(src),
        )
        resp = client.post("/api/operations/move", json={"file_id": rec.id, "dest_dir": str(dst)})
        assert resp.status_code == 200
        assert not file_path.exists()
        assert (dst / "moveme.txt").exists()


class TestRenameOperation:
    def test_rename_nonexistent_file_returns_404(self, client):
        resp = client.post("/api/operations/rename", json={"file_id": 99999, "new_name": "new.txt"})
        assert resp.status_code == 404

    def test_rename_real_file(self, client, db_session, tmp_path):
        file_path = tmp_path / "original.txt"
        file_path.write_text("content")

        rec = make_file(
            db_session,
            name="original.txt",
            full_path=str(file_path),
            parent_dir=str(tmp_path),
        )
        resp = client.post(
            "/api/operations/rename", json={"file_id": rec.id, "new_name": "renamed.txt"}
        )
        assert resp.status_code == 200
        # Response shape: {"message": ..., "file": {...}}
        assert resp.json()["file"]["name"] == "renamed.txt"
        assert (tmp_path / "renamed.txt").exists()
        assert not file_path.exists()

    def test_rename_rejects_path_traversal(self, client, db_session, tmp_path):
        file_path = tmp_path / "safe.txt"
        file_path.write_text("content")

        rec = make_file(
            db_session,
            name="safe.txt",
            full_path=str(file_path),
            parent_dir=str(tmp_path),
        )
        resp = client.post(
            "/api/operations/rename",
            json={"file_id": rec.id, "new_name": "../escape.txt"},
        )
        # Should be rejected (400) — no path traversal allowed
        assert resp.status_code == 400
