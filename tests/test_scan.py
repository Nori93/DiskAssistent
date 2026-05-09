"""
Integration tests for scanning endpoints.
"""


class TestScanStart:
    def test_empty_path_returns_400(self, client):
        resp = client.post("/api/scan/start", json={"path": ""})
        assert resp.status_code == 400

    def test_blank_path_returns_400(self, client):
        resp = client.post("/api/scan/start", json={"path": "   "})
        assert resp.status_code == 400

    def test_valid_path_returns_job_id(self, client, tmp_path):
        resp = client.post("/api/scan/start", json={"path": str(tmp_path)})
        assert resp.status_code == 200
        data = resp.json()
        assert "job_id" in data
        assert isinstance(data["job_id"], int)


class TestScanStatus:
    def test_nonexistent_job_returns_404(self, client):
        resp = client.get("/api/scan/status/99999")
        assert resp.status_code == 404

    def test_status_of_started_job(self, client, tmp_path):
        start = client.post("/api/scan/start", json={"path": str(tmp_path)})
        assert start.status_code == 200
        job_id = start.json()["job_id"]

        resp = client.get(f"/api/scan/status/{job_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == job_id
        assert data["status"] in ("pending", "running", "done", "error")


class TestScanHistory:
    def test_history_returns_list(self, client):
        resp = client.get("/api/scan/history")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_history_contains_started_job(self, client, tmp_path):
        client.post("/api/scan/start", json={"path": str(tmp_path)})
        resp = client.get("/api/scan/history")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1


class TestActiveScan:
    def test_active_returns_none_or_dict(self, client):
        resp = client.get("/api/scan/active")
        assert resp.status_code == 200
        # Either null or a job dict
        assert resp.json() is None or isinstance(resp.json(), dict)
