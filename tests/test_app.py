from unittest.mock import patch

import pytest

import app as app_module
from app import app

SAMPLE_BLUEPRINTS = [
    {"name": "Zeta Blueprint", "timestamp": "2024-01-01T10:00:00"},
    {"name": "Alpha Blueprint", "timestamp": "2024-01-02T11:00:00"},
    {"name": "Mu Blueprint", "timestamp": "2024-01-03T12:00:00"},
]


@pytest.fixture
def client(tmp_path):
    app.config["TESTING"] = True
    app_module.DATA_FILE = str(tmp_path / "test_data.json")
    app_module.LOG_FILE = str(tmp_path / "Game.log")
    app_module.BACKUP_DIR = str(tmp_path / "logbackups")
    app_module._pause_event.clear()
    app_module._scanning_event.clear()
    with app.test_client() as c:
        yield c
    app_module._pause_event.clear()
    app_module._scanning_event.clear()


class TestIndexRoute:
    def test_returns_200(self, client):
        response = client.get("/")
        assert response.status_code == 200


class TestBlueprintsEndpoint:
    def test_returns_200_with_blueprints_key(self, client):
        with patch("app.get_blueprints_from_json", return_value=SAMPLE_BLUEPRINTS):
            response = client.get("/api/blueprints")
        assert response.status_code == 200
        data = response.get_json()
        assert "blueprints" in data

    def test_returns_total_count(self, client):
        with patch("app.get_blueprints_from_json", return_value=SAMPLE_BLUEPRINTS):
            response = client.get("/api/blueprints")
        data = response.get_json()
        assert data["total_count"] == 3

    def test_search_filters_by_name(self, client):
        with patch("app.get_blueprints_from_json", return_value=SAMPLE_BLUEPRINTS):
            response = client.get("/api/blueprints?search=alpha")
        data = response.get_json()
        assert len(data["blueprints"]) == 1
        assert data["blueprints"][0]["name"] == "Alpha Blueprint"

    def test_search_is_case_insensitive(self, client):
        with patch("app.get_blueprints_from_json", return_value=SAMPLE_BLUEPRINTS):
            response = client.get("/api/blueprints?search=ZETA")
        data = response.get_json()
        assert len(data["blueprints"]) == 1
        assert data["blueprints"][0]["name"] == "Zeta Blueprint"

    def test_search_returns_empty_for_no_match(self, client):
        with patch("app.get_blueprints_from_json", return_value=SAMPLE_BLUEPRINTS):
            response = client.get("/api/blueprints?search=xyzzy")
        data = response.get_json()
        assert data["blueprints"] == []
        assert data["total_count"] == 0

    def test_sort_by_name_ascending(self, client):
        with patch(
            "app.get_blueprints_from_json", return_value=list(SAMPLE_BLUEPRINTS)
        ):
            response = client.get("/api/blueprints?sort=name")
        names = [bp["name"] for bp in response.get_json()["blueprints"]]
        assert names == sorted(names)

    def test_sort_by_name_descending(self, client):
        with patch(
            "app.get_blueprints_from_json", return_value=list(SAMPLE_BLUEPRINTS)
        ):
            response = client.get("/api/blueprints?sort=name&reverse=true")
        names = [bp["name"] for bp in response.get_json()["blueprints"]]
        assert names == sorted(names, reverse=True)

    def test_default_sort_is_timestamp_descending(self, client):
        with patch(
            "app.get_blueprints_from_json", return_value=list(SAMPLE_BLUEPRINTS)
        ):
            response = client.get("/api/blueprints")
        timestamps = [bp["timestamp"] for bp in response.get_json()["blueprints"]]
        assert timestamps == sorted(timestamps, reverse=True)

    def test_returns_503_when_data_file_not_set(self, client):
        original = app_module.DATA_FILE
        app_module.DATA_FILE = None
        try:
            response = client.get("/api/blueprints")
            assert response.status_code == 503
        finally:
            app_module.DATA_FILE = original


class TestStatsEndpoint:
    def test_returns_200_with_expected_keys(self, client):
        with (
            patch("app.get_blueprints_from_json", return_value=SAMPLE_BLUEPRINTS),
            patch(
                "app.load_existing_blueprints",
                return_value={"Zeta Blueprint", "Alpha Blueprint", "Mu Blueprint"},
            ),
        ):
            response = client.get("/api/stats")
        assert response.status_code == 200
        data = response.get_json()
        assert "total_count" in data
        assert "today_count" in data
        assert "monitoring_paused" in data
        assert "is_scanning" in data

    def test_total_count_matches_known_blueprints(self, client):
        with (
            patch("app.get_blueprints_from_json", return_value=SAMPLE_BLUEPRINTS),
            patch("app.load_existing_blueprints", return_value={"A", "B"}),
        ):
            response = client.get("/api/stats")
        assert response.get_json()["total_count"] == 2


class TestPauseResumeEndpoints:
    def test_pause_returns_200(self, client):
        response = client.post("/api/pause")
        assert response.status_code == 200
        assert "paused" in response.get_json()["status"].lower()

    def test_pause_sets_pause_event(self, client):
        client.post("/api/pause")
        assert app_module._pause_event.is_set()

    def test_resume_returns_200(self, client):
        app_module._pause_event.set()
        response = client.post("/api/resume")
        assert response.status_code == 200
        assert "resumed" in response.get_json()["status"].lower()

    def test_resume_clears_pause_event(self, client):
        app_module._pause_event.set()
        client.post("/api/resume")
        assert not app_module._pause_event.is_set()


class TestStatusEndpoint:
    def test_returns_200(self, client):
        assert client.get("/api/status").status_code == 200

    def test_contains_expected_keys(self, client):
        data = client.get("/api/status").get_json()
        assert "log_file" in data
        assert "data_file" in data
        assert "backup_dir" in data
        assert "monitoring_paused" in data
        assert "is_scanning" in data
        assert "log_exists" in data

    def test_log_exists_false_when_file_missing(self, client):
        data = client.get("/api/status").get_json()
        assert data["log_exists"] is False


class TestScanBackupsEndpoint:
    def test_returns_200_and_starts_scan(self, client):
        with patch("app.scan_backups"):
            response = client.post("/api/scan-backups")
        assert response.status_code == 200
        assert "status" in response.get_json()

    def test_returns_400_when_scan_already_running(self, client):
        app_module._scanning_event.set()
        response = client.post("/api/scan-backups")
        assert response.status_code == 400
        assert "error" in response.get_json()


class TestExportCsvEndpoint:
    def test_returns_csv_content(self, client):
        with patch("app.get_blueprints_from_json", return_value=SAMPLE_BLUEPRINTS):
            response = client.get("/api/export/csv")
        assert response.status_code == 200
        assert "text/csv" in response.content_type
        text = response.data.decode("utf-8")
        assert "Blueprint Name" in text
        assert "Zeta Blueprint" in text

    def test_csv_has_header_row(self, client):
        with patch("app.get_blueprints_from_json", return_value=[]):
            response = client.get("/api/export/csv")
        lines = response.data.decode("utf-8").strip().splitlines()
        assert lines[0].lower().startswith("blueprint name")


class TestErrorHandlers:
    def test_404_returns_json_error(self, client):
        response = client.get("/api/this/does/not/exist")
        assert response.status_code == 404
        data = response.get_json()
        assert "error" in data
