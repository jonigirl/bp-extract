"""Tests for setup_wizard.py."""

from unittest.mock import MagicMock, patch

import pytest

import setup_wizard


@pytest.fixture
def mock_config():
    cfg = MagicMock()
    cfg.get.side_effect = lambda key, *args: {
        "log_file": "/fake/Game.log",
        "backup_dir": "/fake/logbackups",
        "data_file": "blueprints.json",
        "platform": "Windows",
    }.get(key, args[0] if args else None)
    cfg.validate_paths.return_value = (True, "")
    cfg.is_first_run.return_value = True
    return cfg


class TestWelcome:
    def test_prints_header(self, capsys):
        setup_wizard.welcome()
        out = capsys.readouterr().out
        assert "BP Extract" in out
        assert "First Run Setup" in out


class TestConfirmPaths:
    def test_yes_returns_true(self, mock_config, capsys):
        with patch("builtins.input", return_value="y"):
            result = setup_wizard.confirm_paths(mock_config)
        assert result is True

    def test_no_returns_false(self, mock_config, capsys):
        with patch("builtins.input", return_value="n"):
            result = setup_wizard.confirm_paths(mock_config)
        assert result is False

    def test_custom_delegates_to_custom_paths(self, mock_config):
        with (
            patch("builtins.input", side_effect=["custom", "y"]),
            patch("setup_wizard.custom_paths", return_value=True) as mock_cp,
        ):
            result = setup_wizard.confirm_paths(mock_config)
        mock_cp.assert_called_once_with(mock_config)

    def test_invalid_input_loops_then_yes(self, mock_config, capsys):
        with patch("builtins.input", side_effect=["maybe", "y"]):
            result = setup_wizard.confirm_paths(mock_config)
        assert result is True

    def test_shows_warning_when_paths_invalid(self, mock_config, capsys):
        mock_config.validate_paths.return_value = (False, "Log file not found")
        with patch("builtins.input", return_value="y"):
            setup_wizard.confirm_paths(mock_config)
        out = capsys.readouterr().out
        assert "WARNING" in out or "Log file not found" in out


class TestCustomPaths:
    def test_updates_log_file_when_provided(self, mock_config):
        with (
            patch("builtins.input", side_effect=["/new/Game.log", "", "", "y"]),
            patch("setup_wizard.confirm_paths", return_value=True),
        ):
            setup_wizard.custom_paths(mock_config)
        mock_config.set.assert_any_call("log_file", "/new/Game.log")

    def test_skips_empty_log_file_input(self, mock_config):
        with (
            patch("builtins.input", side_effect=["", "", "", "y"]),
            patch("setup_wizard.confirm_paths", return_value=True),
        ):
            setup_wizard.custom_paths(mock_config)
        mock_config.set.assert_not_called()

    def test_updates_backup_dir_when_provided(self, mock_config):
        with (
            patch("builtins.input", side_effect=["", "/new/backups", "", "y"]),
            patch("setup_wizard.confirm_paths", return_value=True),
        ):
            setup_wizard.custom_paths(mock_config)
        mock_config.set.assert_any_call("backup_dir", "/new/backups")

    def test_updates_data_file_when_provided(self, mock_config):
        with (
            patch("builtins.input", side_effect=["", "", "new_data.json", "y"]),
            patch("setup_wizard.confirm_paths", return_value=True),
        ):
            setup_wizard.custom_paths(mock_config)
        mock_config.set.assert_any_call("data_file", "new_data.json")


class TestMigrateCsv:
    def test_skips_when_no_csv_file(self, capsys, tmp_path):
        with patch("os.path.exists", return_value=False):
            setup_wizard.migrate_csv()
        out = capsys.readouterr().out
        assert out == ""

    def test_skips_migration_when_user_declines(self, capsys, tmp_path):
        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.input", return_value="n"),
        ):
            setup_wizard.migrate_csv()
        out = capsys.readouterr().out
        # Should print the FOUND line but not attempt migration
        assert "FOUND" in out

    def test_calls_migrate_on_yes(self, tmp_path):
        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.input", return_value="y"),
            patch("setup_wizard.get_config") as mock_cfg,
            patch("core.migrate_csv_to_json", return_value=True) as mock_migrate,
            patch("os.rename"),
        ):
            mock_cfg.return_value.get.return_value = "blueprints.json"
            setup_wizard.migrate_csv()
        mock_migrate.assert_called_once()


class TestRunSetup:
    def test_returns_false_when_not_first_run(self, mock_config):
        mock_config.is_first_run.return_value = False
        with patch("setup_wizard.get_config", return_value=mock_config):
            result = setup_wizard.run_setup()
        assert result is False

    def test_returns_true_on_first_run(self, mock_config):
        with (
            patch("setup_wizard.get_config", return_value=mock_config),
            patch("setup_wizard.welcome"),
            patch("setup_wizard.confirm_paths", return_value=True),
            patch("setup_wizard.migrate_csv"),
            patch("setup_wizard.summary"),
        ):
            result = setup_wizard.run_setup()
        assert result is True

    def test_calls_all_wizard_steps_on_first_run(self, mock_config):
        with (
            patch("setup_wizard.get_config", return_value=mock_config),
            patch("setup_wizard.welcome") as mock_welcome,
            patch("setup_wizard.confirm_paths", return_value=True),
            patch("setup_wizard.migrate_csv") as mock_migrate,
            patch("setup_wizard.summary") as mock_summary,
        ):
            setup_wizard.run_setup()
        mock_welcome.assert_called_once()
        mock_migrate.assert_called_once()
        mock_summary.assert_called_once_with(mock_config)

    def test_saves_config_on_completion(self, mock_config):
        with (
            patch("setup_wizard.get_config", return_value=mock_config),
            patch("setup_wizard.welcome"),
            patch("setup_wizard.confirm_paths", return_value=True),
            patch("setup_wizard.migrate_csv"),
            patch("setup_wizard.summary"),
        ):
            setup_wizard.run_setup()
        mock_config.save.assert_called_once()
