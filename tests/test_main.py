"""Tests for main.py."""

from unittest.mock import MagicMock, patch

import pytest

import main as main_module


@pytest.fixture
def mock_config():
    cfg = MagicMock()
    cfg.get.side_effect = lambda key, *args: {
        "log_file": "/fake/Game.log",
        "backup_dir": "/fake/logbackups",
        "data_file": "blueprints.json",
        "poll_interval": 0.5,
        "wait_interval": 1.0,
    }.get(key, args[0] if args else None)
    cfg.validate_paths.return_value = (True, "")
    return cfg


class TestMain:
    def test_exits_when_paths_invalid(self, mock_config, capsys):
        mock_config.validate_paths.return_value = (False, "Game.log not found")
        with (
            patch("main.get_config", return_value=mock_config),
            patch("main.run_setup"),
            pytest.raises(SystemExit) as exc_info,
        ):
            main_module.main()
        assert exc_info.value.code == 1
        out = capsys.readouterr().out
        assert "Game.log not found" in out

    def test_scans_backups_when_user_answers_yes(self, mock_config):
        with (
            patch("main.get_config", return_value=mock_config),
            patch("main.run_setup"),
            patch("builtins.input", return_value="y"),
            patch("main.scan_backups", return_value={"Alpha"}) as mock_scan,
            patch("main.tail_log", side_effect=KeyboardInterrupt),
        ):
            main_module.main()
        mock_scan.assert_called_once()

    def test_skips_scan_when_user_answers_no(self, mock_config):
        with (
            patch("main.get_config", return_value=mock_config),
            patch("main.run_setup"),
            patch("builtins.input", return_value="n"),
            patch("main.scan_backups") as mock_scan,
            patch("main.tail_log", side_effect=KeyboardInterrupt),
        ):
            main_module.main()
        mock_scan.assert_not_called()

    def test_invalid_scan_choice_loops_then_no(self, mock_config):
        with (
            patch("main.get_config", return_value=mock_config),
            patch("main.run_setup"),
            patch("builtins.input", side_effect=["maybe", "n"]),
            patch("main.scan_backups") as mock_scan,
            patch("main.tail_log", side_effect=KeyboardInterrupt),
        ):
            main_module.main()
        mock_scan.assert_not_called()

    def test_calls_tail_log_with_config_values(self, mock_config):
        with (
            patch("main.get_config", return_value=mock_config),
            patch("main.run_setup"),
            patch("builtins.input", return_value="n"),
            patch("main.tail_log", side_effect=KeyboardInterrupt) as mock_tail,
        ):
            main_module.main()
        mock_tail.assert_called_once()
        kwargs = mock_tail.call_args.kwargs
        assert kwargs.get("poll_interval") == 0.5
        assert kwargs.get("wait_interval") == 1.0

    def test_keyboard_interrupt_exits_cleanly(self, mock_config, capsys):
        with (
            patch("main.get_config", return_value=mock_config),
            patch("main.run_setup"),
            patch("builtins.input", return_value="n"),
            patch("main.tail_log", side_effect=KeyboardInterrupt),
        ):
            main_module.main()  # should not raise
        out = capsys.readouterr().out
        assert "Stopping" in out or "stopping" in out.lower()

    def test_calls_run_setup(self, mock_config):
        with (
            patch("main.get_config", return_value=mock_config),
            patch("main.run_setup") as mock_setup,
            patch("builtins.input", return_value="n"),
            patch("main.tail_log", side_effect=KeyboardInterrupt),
        ):
            main_module.main()
        mock_setup.assert_called_once()
