import json
import platform
from unittest.mock import patch

import config as config_module
from config import Config, get_config


class TestConfigLoadConfig:
    def test_missing_file_creates_defaults(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config_module, "CONFIG_FILE", str(tmp_path / "config.json"))
        c = Config()
        assert "log_file" in c.config
        assert "data_file" in c.config
        assert c.config["first_run"] is True

    def test_valid_json_loads_correctly(self, tmp_path, monkeypatch):
        cfg_file = tmp_path / "config.json"
        saved = {
            "log_file": "/some/Game.log",
            "backup_dir": "/some/logbackups",
            "data_file": "/some/data.json",
            "poll_interval": 1.0,
            "wait_interval": 2.0,
            "first_run": False,
            "platform": "Windows",
        }
        cfg_file.write_text(json.dumps(saved), encoding="utf-8")
        monkeypatch.setattr(config_module, "CONFIG_FILE", str(cfg_file))
        c = Config()
        assert c.config["log_file"] == "/some/Game.log"
        assert c.config["first_run"] is False

    def test_corrupt_json_falls_back_to_defaults(self, tmp_path, monkeypatch):
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text("{ not valid json{{", encoding="utf-8")
        monkeypatch.setattr(config_module, "CONFIG_FILE", str(cfg_file))
        c = Config()
        assert "log_file" in c.config
        assert c.config["first_run"] is True


class TestCreateDefaultConfig:
    def test_returns_expected_keys(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config_module, "CONFIG_FILE", str(tmp_path / "config.json"))
        c = Config()
        expected = {
            "log_file",
            "backup_dir",
            "data_file",
            "poll_interval",
            "wait_interval",
            "first_run",
            "platform",
        }
        assert expected.issubset(c.config.keys())

    def test_platform_key_matches_system(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config_module, "CONFIG_FILE", str(tmp_path / "config.json"))
        c = Config()
        assert c.config["platform"] == platform.system()

    def test_poll_interval_is_numeric(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config_module, "CONFIG_FILE", str(tmp_path / "config.json"))
        c = Config()
        assert isinstance(c.config["poll_interval"], float)


class TestConfigGetSet:
    def test_get_returns_stored_value(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config_module, "CONFIG_FILE", str(tmp_path / "config.json"))
        c = Config()
        c.config["poll_interval"] = 0.5
        assert c.get("poll_interval") == 0.5

    def test_get_returns_default_for_missing_key(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config_module, "CONFIG_FILE", str(tmp_path / "config.json"))
        c = Config()
        assert c.get("no_such_key", "fallback") == "fallback"

    def test_set_updates_value(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config_module, "CONFIG_FILE", str(tmp_path / "config.json"))
        c = Config()
        c.set("poll_interval", 2.0)
        assert c.get("poll_interval") == 2.0


class TestConfigIsFirstRun:
    def test_true_by_default(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config_module, "CONFIG_FILE", str(tmp_path / "config.json"))
        c = Config()
        assert c.is_first_run() is True

    def test_false_after_setting_flag(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config_module, "CONFIG_FILE", str(tmp_path / "config.json"))
        c = Config()
        c.set("first_run", False)
        assert c.is_first_run() is False


class TestConfigSave:
    def test_writes_json_file(self, tmp_path, monkeypatch):
        cfg_file = tmp_path / "config.json"
        monkeypatch.setattr(config_module, "CONFIG_FILE", str(cfg_file))
        c = Config()
        c.save()
        assert cfg_file.exists()
        data = json.loads(cfg_file.read_text(encoding="utf-8"))
        assert "log_file" in data

    def test_sets_first_run_false_on_save(self, tmp_path, monkeypatch):
        cfg_file = tmp_path / "config.json"
        monkeypatch.setattr(config_module, "CONFIG_FILE", str(cfg_file))
        c = Config()
        assert c.config["first_run"] is True
        c.save()
        assert c.config["first_run"] is False


class TestConfigValidatePaths:
    def test_missing_log_file_path_returns_error(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config_module, "CONFIG_FILE", str(tmp_path / "config.json"))
        c = Config()
        c.set("log_file", None)
        valid, msg = c.validate_paths()
        assert valid is False
        assert msg is not None

    def test_nonexistent_log_file_returns_error(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config_module, "CONFIG_FILE", str(tmp_path / "config.json"))
        c = Config()
        c.set("log_file", str(tmp_path / "nonexistent.log"))
        valid, msg = c.validate_paths()
        assert valid is False
        assert "Game.log" in msg or "not found" in msg.lower()

    def test_valid_paths_return_true(self, tmp_path, monkeypatch):
        log_file = tmp_path / "Game.log"
        backup_dir = tmp_path / "logbackups"
        log_file.write_text("", encoding="utf-8")
        backup_dir.mkdir()
        monkeypatch.setattr(config_module, "CONFIG_FILE", str(tmp_path / "config.json"))
        c = Config()
        c.set("log_file", str(log_file))
        c.set("backup_dir", str(backup_dir))
        valid, msg = c.validate_paths()
        assert valid is True
        assert msg is None

    def test_log_exists_but_backup_dir_missing(self, tmp_path, monkeypatch):
        log_file = tmp_path / "Game.log"
        log_file.write_text("", encoding="utf-8")
        monkeypatch.setattr(config_module, "CONFIG_FILE", str(tmp_path / "config.json"))
        c = Config()
        c.set("log_file", str(log_file))
        c.set("backup_dir", str(tmp_path / "nonexistent_backups"))
        valid, msg = c.validate_paths()
        assert valid is False
        assert "backup" in msg.lower()


class TestConfigRepr:
    def test_repr_includes_log_file_path(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config_module, "CONFIG_FILE", str(tmp_path / "config.json"))
        c = Config()
        c.set("log_file", "/test/Game.log")
        result = repr(c)
        assert isinstance(result, str)
        assert "/test/Game.log" in result


class TestDetectScPaths:
    def test_macos_falls_back_to_none(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config_module, "CONFIG_FILE", str(tmp_path / "config.json"))
        with patch("config.platform.system", return_value="Darwin"):
            c = Config()
        assert c.config["log_file"] is None

    def test_linux_falls_back_to_none(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config_module, "CONFIG_FILE", str(tmp_path / "config.json"))
        with patch("config.platform.system", return_value="Linux"):
            c = Config()
        assert c.config["log_file"] is None

    def test_unknown_system_returns_none(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config_module, "CONFIG_FILE", str(tmp_path / "config.json"))
        with patch("config.platform.system", return_value="FreeBSD"):
            c = Config()
        assert c.config["log_file"] is None

    def test_windows_returns_first_found_path(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config_module, "CONFIG_FILE", str(tmp_path / "config.json"))
        expected_log = (
            r"C:\Program Files\Roberts Space Industries\StarCitizen\LIVE\Game.log"
        )
        expected_backup = (
            r"C:\Program Files\Roberts Space Industries\StarCitizen\LIVE\logbackups"
        )
        with (
            patch("config.os.path.exists", side_effect=lambda p: p == expected_log),
            patch("config.platform.system", return_value="Windows"),
        ):
            c = Config()
        assert c.config["log_file"] == expected_log
        assert c.config["backup_dir"] == expected_backup


class TestGetConfig:
    def test_returns_config_instance(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config_module, "CONFIG_FILE", str(tmp_path / "config.json"))
        result = get_config()
        assert isinstance(result, Config)

    def test_returns_same_instance_on_repeat_calls(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config_module, "CONFIG_FILE", str(tmp_path / "config.json"))
        first = get_config()
        second = get_config()
        assert first is second
