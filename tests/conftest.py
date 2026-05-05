import pytest

import config as config_module


@pytest.fixture(autouse=True)
def reset_config_singleton():
    config_module._config_instance = None
    yield
    config_module._config_instance = None


@pytest.fixture(autouse=True)
def redirect_app_data(tmp_path, monkeypatch):
    """Redirect APPDATA paths to tmp_path so tests never touch the real data directory."""
    monkeypatch.setattr(config_module, "CONFIG_FILE", str(tmp_path / "config.json"))
    monkeypatch.setattr(config_module, "DATA_FILE", str(tmp_path / "blueprints.json"))
    monkeypatch.setattr(config_module, "SECRET_KEY_FILE", str(tmp_path / "secret.key"))
    monkeypatch.setattr(config_module, "_BASE_DIR", tmp_path)
