"""Configuration management for BP Extract.

Handles:
- Auto-detection of Star Citizen installation paths
- Cross-platform support (Windows/Mac/Linux)
- Configuration persistence via JSON
- First-run setup
- CSV to JSON migration
"""

import json
import logging
import os
import platform
import shutil
from pathlib import Path

_BASE_DIR = Path(__file__).parent

logger = logging.getLogger(__name__)


def get_app_data_dir() -> Path:
    """Return the platform-appropriate user-writable data directory, creating it if needed."""
    system = platform.system()
    if system == "Windows":
        base = Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming")))
    elif system == "Darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(
            os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))
        )
    app_dir = base / "BPExtract"
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


CONFIG_FILE = str(get_app_data_dir() / "config.json")
DATA_FILE = str(get_app_data_dir() / "blueprints.json")
SECRET_KEY_FILE = str(get_app_data_dir() / "secret.key")


def _migrate_legacy_data() -> None:
    """Copy config and data files from the legacy script-relative location to the app data directory."""
    app_data_config = Path(CONFIG_FILE)
    app_data_data = Path(DATA_FILE)
    legacy_config = _BASE_DIR / "config.json"
    legacy_data = _BASE_DIR / "blueprints.json"

    if not app_data_config.exists() and legacy_config.exists():
        shutil.copy2(str(legacy_config), str(app_data_config))
        logger.info("Migrated config from %s to %s", legacy_config, app_data_config)

    if not app_data_data.exists() and legacy_data.exists():
        shutil.copy2(str(legacy_data), str(app_data_data))
        logger.info("Migrated blueprints from %s to %s", legacy_data, app_data_data)


def get_or_create_secret_key() -> bytes:
    """Return the persistent secret key, generating and saving it if it does not exist."""
    key_path = Path(SECRET_KEY_FILE)
    if key_path.exists():
        return key_path.read_bytes()
    key = os.urandom(32)
    key_path.write_bytes(key)
    return key


class Config:
    """Application configuration manager."""

    def __init__(self):
        _migrate_legacy_data()
        self.config_path = Path(CONFIG_FILE)
        self.config = self._load_config()

    def _load_config(self) -> dict:
        """Load configuration from file or create defaults."""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return self._create_default_config()
        return self._create_default_config()

    def _create_default_config(self) -> dict:
        """Create default configuration."""
        log_file, backup_dir = self._detect_sc_paths()

        return {
            "log_file": log_file,
            "backup_dir": backup_dir,
            "data_file": DATA_FILE,
            "poll_interval": 0.5,
            "wait_interval": 1.0,
            "first_run": True,
            "platform": platform.system(),
            "ui_mode": "browser",
        }

    def _detect_sc_paths(self) -> tuple:
        """Auto-detect Star Citizen installation paths.

        Returns: (log_file_path, backup_dir_path)
        """
        system = platform.system()

        if system == "Windows":
            return self._detect_windows_paths()
        elif system == "Darwin":  # macOS
            return self._detect_macos_paths()
        elif system == "Linux":
            return self._detect_linux_paths()
        else:
            return None, None

    def _detect_windows_paths(self) -> tuple:
        """Detect Star Citizen paths on Windows."""
        # Common installation locations
        common_paths = [
            r"C:\Program Files\Roberts Space Industries\StarCitizen\LIVE",
            r"E:\Roberts Space Industries\StarCitizen\LIVE",
            r"D:\Roberts Space Industries\StarCitizen\LIVE",
            r"C:\Games\StarCitizen\LIVE",
        ]

        for base_path in common_paths:
            log_file = os.path.join(base_path, "Game.log")
            backup_dir = os.path.join(base_path, "logbackups")

            if os.path.exists(log_file):
                return log_file, backup_dir

        # Fallback to most common location
        return (
            r"C:\Program Files\Roberts Space Industries\StarCitizen\LIVE\Game.log",
            r"C:\Program Files\Roberts Space Industries\StarCitizen\LIVE\logbackups",
        )

    def _detect_macos_paths(self) -> tuple:
        """Detect Star Citizen paths on macOS."""
        common_paths = [
            os.path.expanduser("~/Library/Application Support/Star Citizen"),
            os.path.expanduser("~/Games/StarCitizen"),
        ]

        for base_path in common_paths:
            # SC on macOS might be in a different structure
            log_file = os.path.join(base_path, "LIVE", "Game.log")
            backup_dir = os.path.join(base_path, "LIVE", "logbackups")

            if os.path.exists(log_file):
                return log_file, backup_dir

        # Fallback
        return None, None

    def _detect_linux_paths(self) -> tuple:
        """Detect Star Citizen paths on Linux (via Proton/Wine)."""
        common_paths = [
            os.path.expanduser("~/.local/share/StarCitizen"),
            os.path.expanduser("~/.wine/drive_c/Roberts Space Industries/StarCitizen"),
            os.path.expanduser("~/Games/StarCitizen"),
        ]

        for base_path in common_paths:
            log_file = os.path.join(base_path, "LIVE", "Game.log")
            backup_dir = os.path.join(base_path, "LIVE", "logbackups")

            if os.path.exists(log_file):
                return log_file, backup_dir

        # Fallback
        return None, None

    def save(self) -> None:
        """Save configuration to file."""
        self.config["first_run"] = False
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2)
        except IOError as e:
            logger.error("Failed to save config to %s: %s", self.config_path, e)

    def get(self, key: str, default=None):
        """Get configuration value."""
        return self.config.get(key, default)

    def set(self, key: str, value) -> None:
        """Set configuration value."""
        self.config[key] = value

    def is_first_run(self) -> bool:
        """Check if this is first run."""
        return self.config.get("first_run", True)

    def validate_paths(self) -> tuple:
        """Validate that configured paths exist.

        Returns: (is_valid, error_message)
        """
        log_file = self.get("log_file")
        backup_dir = self.get("backup_dir")

        if not log_file:
            return False, "Log file path not configured"

        if not os.path.exists(log_file):
            return (
                False,
                f"Game.log not found at: {log_file}\n"
                "Please check your Star Citizen installation path.",
            )

        if not backup_dir or not os.path.exists(backup_dir):
            return (
                False,
                f"Backup directory not found at: {backup_dir}\n"
                "This may be OK if you haven't played yet.",
            )

        return True, None

    def __repr__(self) -> str:
        return f"<Config log_file={self.get('log_file')} data_file={self.get('data_file')}>"


# Global config instance
_config_instance = None


def get_config() -> Config:
    """Get or create global config instance."""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance
