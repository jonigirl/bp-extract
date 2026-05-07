from unittest.mock import MagicMock, patch

import pytest

import app as app_module
from app import app

SAMPLE_BLUEPRINTS = [
    {"name": "Zeta Blueprint", "timestamp": "2024-01-01T10:00:00"},
    {"name": "Alpha Blueprint", "timestamp": "2024-01-02T11:00:00"},
    {"name": "Mu Blueprint", "timestamp": "2024-01-03T12:00:00"},
]

XHR_HEADERS = {"X-Requested-With": "XMLHttpRequest"}


@pytest.fixture
def client(tmp_path):
    app.config["TESTING"] = True
    app_module.DATA_FILE = str(tmp_path / "test_data.json")
    app_module.LOG_FILE = str(tmp_path / "Game.log")
    app_module.BACKUP_DIR = str(tmp_path / "logbackups")
    app_module._pause_event.clear()
    app_module._scanning_event.clear()
    if app_module.config is not None:
        app_module.config.set("first_run", False)
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
        with patch("app.get_blueprints_from_json", return_value=SAMPLE_BLUEPRINTS):
            response = client.get("/api/stats")
        assert response.status_code == 200
        data = response.get_json()
        assert "total_count" in data
        assert "today_count" in data
        assert "monitoring_paused" in data
        assert "is_scanning" in data

    def test_total_count_matches_blueprints_list(self, client):
        with patch("app.get_blueprints_from_json", return_value=SAMPLE_BLUEPRINTS):
            response = client.get("/api/stats")
        assert response.get_json()["total_count"] == len(SAMPLE_BLUEPRINTS)


class TestPauseResumeEndpoints:
    def test_pause_returns_200(self, client):
        response = client.post("/api/pause", headers=XHR_HEADERS)
        assert response.status_code == 200
        assert "paused" in response.get_json()["status"].lower()

    def test_pause_sets_pause_event(self, client):
        client.post("/api/pause", headers=XHR_HEADERS)
        assert app_module._pause_event.is_set()

    def test_pause_rejected_without_xhr_header(self, client):
        response = client.post("/api/pause")
        assert response.status_code == 403

    def test_resume_returns_200(self, client):
        app_module._pause_event.set()
        response = client.post("/api/resume", headers=XHR_HEADERS)
        assert response.status_code == 200
        assert "resumed" in response.get_json()["status"].lower()

    def test_resume_clears_pause_event(self, client):
        app_module._pause_event.set()
        client.post("/api/resume", headers=XHR_HEADERS)
        assert not app_module._pause_event.is_set()

    def test_resume_rejected_without_xhr_header(self, client):
        response = client.post("/api/resume")
        assert response.status_code == 403


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
            response = client.post("/api/scan-backups", headers=XHR_HEADERS)
        assert response.status_code == 200
        assert "status" in response.get_json()

    def test_returns_400_when_scan_already_running(self, client):
        app_module._scanning_event.set()
        response = client.post("/api/scan-backups", headers=XHR_HEADERS)
        assert response.status_code == 400
        assert "error" in response.get_json()

    def test_scan_rejected_without_xhr_header(self, client):
        response = client.post("/api/scan-backups")
        assert response.status_code == 403


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


class TestHeartbeatEndpoint:
    def test_returns_200(self, client):
        response = client.get("/api/heartbeat")
        assert response.status_code == 200
        assert response.get_json()["ok"] is True

    def test_updates_last_heartbeat(self, client):
        import time

        before = time.time()
        client.get("/api/heartbeat")
        with app_module._heartbeat_lock:
            hb = app_module._last_heartbeat
        assert hb is not None
        assert hb >= before


class TestBrowserWatchdog:
    def test_exits_when_heartbeat_expires(self):
        import threading
        import time

        import app as app_module

        original_hb = app_module._last_heartbeat
        called = threading.Event()

        def fake_exit(code):
            called.set()
            raise SystemExit(code)

        try:
            app_module._last_heartbeat = time.time() - 999
            with (
                patch.object(app_module.time, "sleep", return_value=None),
                patch.object(app_module.os, "_exit", side_effect=fake_exit),
            ):
                app_module._start_browser_watchdog(timeout=0.01)
                assert called.wait(timeout=2.0), "watchdog did not fire"
        finally:
            app_module._last_heartbeat = original_hb

    def test_does_not_exit_before_first_heartbeat(self):
        import threading

        import app as app_module

        original_hb = app_module._last_heartbeat
        exited = threading.Event()
        enough_polls = threading.Event()
        call_count = [0]

        def fake_sleep(n):
            call_count[0] += 1
            if call_count[0] >= 5:
                enough_polls.set()

        try:
            app_module._last_heartbeat = None
            with (
                patch.object(app_module.time, "sleep", side_effect=fake_sleep),
                patch.object(
                    app_module.os, "_exit", side_effect=lambda c: exited.set()
                ),
            ):
                app_module._start_browser_watchdog(timeout=0.01)
                enough_polls.wait(timeout=2.0)
            assert not exited.is_set()
        finally:
            app_module._last_heartbeat = original_hb

    def test_flush_skipped_when_stdout_is_none(self):
        import sys
        import threading
        import time

        import app as app_module

        original_hb = app_module._last_heartbeat
        called = threading.Event()

        def fake_exit(code):
            called.set()
            raise SystemExit(code)

        try:
            app_module._last_heartbeat = time.time() - 999
            with (
                patch.object(app_module.time, "sleep", return_value=None),
                patch.object(app_module.os, "_exit", side_effect=fake_exit),
                patch.object(sys, "stdout", None),
            ):
                app_module._start_browser_watchdog(timeout=0.01)
                assert called.wait(timeout=2.0), "watchdog crashed with stdout=None"
        finally:
            app_module._last_heartbeat = original_hb


class TestErrorHandlers:
    def test_404_returns_json_error(self, client):
        response = client.get("/api/this/does/not/exist")
        assert response.status_code == 404
        data = response.get_json()
        assert "error" in data


class TestSetupRoute:
    def test_get_redirects_to_setup_on_first_run(self, client, monkeypatch):
        mock_cfg = MagicMock()
        mock_cfg.is_first_run.return_value = True
        mock_cfg.get.side_effect = lambda k, *a: {
            "log_file": "/fake/Game.log",
            "backup_dir": "/fake/backups",
            "data_file": "blueprints.json",
        }.get(k, a[0] if a else None)
        monkeypatch.setattr(app_module, "config", mock_cfg)
        response = client.get("/")
        assert response.status_code == 302
        assert "/setup" in response.headers["Location"]

    def test_get_setup_returns_200(self, client, monkeypatch):
        mock_cfg = MagicMock()
        mock_cfg.is_first_run.return_value = True
        mock_cfg.get.side_effect = lambda k, *a: {
            "log_file": "/fake/Game.log",
            "backup_dir": "/fake/backups",
            "data_file": "blueprints.json",
        }.get(k, a[0] if a else None)
        monkeypatch.setattr(app_module, "config", mock_cfg)
        response = client.get("/setup")
        assert response.status_code == 200

    def test_setup_redirects_to_index_after_not_first_run(self, client, monkeypatch):
        mock_cfg = MagicMock()
        mock_cfg.is_first_run.return_value = False
        monkeypatch.setattr(app_module, "config", mock_cfg)
        response = client.get("/setup")
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/")

    def test_post_setup_saves_and_redirects(self, client, monkeypatch):
        mock_cfg = MagicMock()
        monkeypatch.setattr(app_module, "config", mock_cfg)
        monkeypatch.setattr(app_module, "start_monitoring", lambda: None)
        response = client.post(
            "/setup",
            data={
                "log_file": "/new/Game.log",
                "backup_dir": "/new/backups",
                "data_file": "new.json",
            },
            headers={"Host": "127.0.0.1:5000"},
        )
        assert response.status_code == 302
        mock_cfg.set.assert_any_call("log_file", "/new/Game.log")
        mock_cfg.save.assert_called_once()

    def test_post_setup_rejects_non_local_host(self, client):
        response = client.post(
            "/setup",
            data={"log_file": "/x"},
            headers={"Host": "evil.example.com"},
        )
        assert response.status_code == 403


class TestSettingsEndpoint:
    def test_get_settings_returns_200(self, client):
        response = client.get("/api/settings")
        assert response.status_code == 200

    def test_get_settings_contains_expected_keys(self, client):
        response = client.get("/api/settings")
        data = response.get_json()
        assert "ui_mode" in data
        assert "log_file" in data
        assert "backup_dir" in data
        assert "poll_interval" in data

    def test_post_settings_requires_xhr(self, client):
        response = client.post("/api/settings", json={"ui_mode": "browser"})
        assert response.status_code == 403

    def test_post_settings_updates_ui_mode(self, client, monkeypatch):
        mock_cfg = MagicMock()
        mock_cfg.get.side_effect = lambda k, *a: (
            "browser" if k == "ui_mode" else a[0] if a else None
        )
        monkeypatch.setattr(app_module, "config", mock_cfg)
        response = client.post(
            "/api/settings",
            json={"ui_mode": "tray"},
            headers=XHR_HEADERS,
        )
        assert response.status_code == 200
        mock_cfg.set.assert_any_call("ui_mode", "tray")
        mock_cfg.save.assert_called_once()

    def test_post_settings_rejects_invalid_ui_mode(self, client):
        response = client.post(
            "/api/settings",
            json={"ui_mode": "invalid"},
            headers=XHR_HEADERS,
        )
        assert response.status_code == 400

    def test_post_settings_rejects_invalid_poll_interval(self, client):
        response = client.post(
            "/api/settings",
            json={"poll_interval": 999},
            headers=XHR_HEADERS,
        )
        assert response.status_code == 400
