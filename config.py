"""Configuration management for BP Extract.

Handles:
- Auto-detection of Star Citizen installation paths
- Cross-platform support (Windows/Mac/Linux)
- Configuration persistence via JSON
- First-run setup
- CSV to JSON migration
"""

import json
import os
import platform
from pathlib import Path

CONFIG_FILE = "config.json"
DATA_FILE = "blueprints.json"


class Config:
    """Application configuration manager."""

    def __init__(self):
        self.config_path = Path(CONFIG_FILE)
        self.data_path = Path(DATA_FILE)
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
            "data_file": str(self.data_path),
            "poll_interval": 0.5,
            "wait_interval": 1.0,
            "first_run": True,
            "platform": platform.system(),
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
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2)

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

        if not os.path.exists(backup_dir):
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
