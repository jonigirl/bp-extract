"""Tests for launch.py."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import launch


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
        with patch.dict("sys.modules", {"flask": None}):
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
        with (
            patch("launch.check_python_version"),
            patch("launch.find_virtual_env", return_value=None),
            patch("launch.check_flask_installed", return_value=True),
            patch("launch.find_free_port", return_value=5000),
            patch("launch.webbrowser.open"),
            patch("launch.time.sleep"),
            patch("launch.subprocess.run") as mock_run,
        ):
            launch.main()
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "app.py" in args

    def test_handles_keyboard_interrupt_gracefully(self):
        with (
            patch("launch.check_python_version"),
            patch("launch.find_virtual_env", return_value=None),
            patch("launch.check_flask_installed", return_value=True),
            patch("launch.find_free_port", return_value=5000),
            patch("launch.webbrowser.open"),
            patch("launch.time.sleep"),
            patch("launch.subprocess.run", side_effect=KeyboardInterrupt),
            pytest.raises(SystemExit) as exc_info,
        ):
            launch.main()
        assert exc_info.value.code == 0
