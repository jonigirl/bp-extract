"""Tests for launch.py."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import launch


class TestWaitForPort:
    def test_returns_true_when_port_ready(self):
        with patch("socket.create_connection"):
            result = launch.wait_for_port("127.0.0.1", 5000, timeout=1.0)
        assert result is True

    def test_returns_false_when_timeout_elapses(self):
        # timeout=0.0 means deadline is already in the past; loop never runs
        result = launch.wait_for_port("127.0.0.1", 9999, timeout=0.0)
        assert result is False


class TestRunFlask:
    def test_calls_run_server_with_port(self):
        with patch("app.run_server") as mock_run_server:
            launch._run_flask(5001)
        mock_run_server.assert_called_once_with(5001, browser_watchdog=True)


class TestCheckPythonVersion:
    def test_passes_on_current_python(self):
        # Current interpreter satisfies 3.12+ (enforced by pyproject.toml)
        launch.check_python_version()  # should not raise or exit

    def test_exits_on_old_python(self):
        with patch.object(sys, "version_info", (3, 11, 0)):
            with pytest.raises(SystemExit):
                launch.check_python_version()


class TestFindVirtualEnv:
    def test_returns_path_when_venv_exists(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        venv = tmp_path / ".venv"
        venv.mkdir()
        result = launch.find_virtual_env()
        assert result == Path(".venv")

    def test_returns_none_when_no_venv(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = launch.find_virtual_env()
        assert result is None


class TestCheckFlaskInstalled:
    def test_returns_true_when_flask_importable(self):
        # Flask is a project dependency and should always be importable in tests
        result = launch.check_flask_installed()
        assert result is True

    def test_returns_false_when_flask_not_importable(self, capsys):
        from importlib.metadata import PackageNotFoundError

        with patch(
            "importlib.metadata.version", side_effect=PackageNotFoundError("flask")
        ):
            result = launch.check_flask_installed()
        assert result is False
        out = capsys.readouterr().out
        assert "Flask" in out or "flask" in out.lower()


class TestFindFreePort:
    def test_returns_integer(self):
        port = launch.find_free_port()
        assert isinstance(port, int)

    def test_returned_port_is_in_valid_range(self):
        port = launch.find_free_port()
        assert 5000 <= port < 5100

    def test_returns_none_when_all_ports_taken(self):
        # Simulate every connect_ex returning 0 (port in use)
        with patch("socket.socket") as mock_socket_cls:
            mock_sock = MagicMock()
            mock_sock.connect_ex.return_value = 0
            mock_socket_cls.return_value = mock_sock
            result = launch.find_free_port()
        assert result is None


class TestMain:
    def test_exits_when_flask_not_installed(self, capsys):
        with (
            patch("launch.check_python_version"),
            patch("launch.find_virtual_env", return_value=None),
            patch("launch.check_flask_installed", return_value=False),
            pytest.raises(SystemExit) as exc_info,
        ):
            launch.main()
        assert exc_info.value.code == 1

    def test_exits_when_no_free_port(self, capsys):
        with (
            patch("launch.check_python_version"),
            patch("launch.find_virtual_env", return_value=None),
            patch("launch.check_flask_installed", return_value=True),
            patch("launch.find_free_port", return_value=None),
            pytest.raises(SystemExit) as exc_info,
        ):
            launch.main()
        assert exc_info.value.code == 1

    def test_runs_app_when_all_checks_pass(self):
        mock_thread = MagicMock()
        mock_thread.join.return_value = None
        with (
            patch("launch.check_python_version"),
            patch("launch.find_virtual_env", return_value=None),
            patch("launch.check_flask_installed", return_value=True),
            patch("launch.find_free_port", return_value=5000),
            patch("launch.wait_for_port", return_value=True),
            patch("launch.webbrowser.open") as mock_wb,
            patch("threading.Thread", return_value=mock_thread),
        ):
            launch.main()
        mock_thread.start.assert_called_once()
        mock_wb.assert_called_once_with("http://127.0.0.1:5000")

    def test_handles_keyboard_interrupt_gracefully(self):
        mock_thread = MagicMock()
        mock_thread.join.side_effect = KeyboardInterrupt
        with (
            patch("launch.check_python_version"),
            patch("launch.find_virtual_env", return_value=None),
            patch("launch.check_flask_installed", return_value=True),
            patch("launch.find_free_port", return_value=5000),
            patch("launch.wait_for_port", return_value=True),
            patch("launch.webbrowser.open"),
            patch("threading.Thread", return_value=mock_thread),
            pytest.raises(SystemExit) as exc_info,
        ):
            launch.main()
        assert exc_info.value.code == 0
